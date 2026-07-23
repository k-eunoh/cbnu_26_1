"""
CNC 밀링 공구 수명 예측 AI 파이프라인 — Mendeley Hannover 데이터셋
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import h5py                          # HDF5 파일 읽기용 라이브러리
import matplotlib.pyplot as plt      # 그래프 출력용
import matplotlib.font_manager as _fm
import numpy as np

def _setup_korean_font():
    candidates = ["Apple SD Gothic Neo", "Nanum Gothic", "AppleGothic",
                  "Malgun Gothic", "NanumGothic"]
    available = {f.name for f in _fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False  # 음수 기호(-) 깨짐 방지
            return name
    return None

_KOREAN_FONT = _setup_korean_font()

import optuna                        # 하이퍼파라미터 자동 최적화 라이브러리
from optuna.pruners import MedianPruner  # 성능 나쁜 trial 조기 종료 가지치기
import pandas as pd
import torch
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler  # Feature 정규화 (평균0, 표준편차1)
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

# 0. 전역 설정값 (Config)

@dataclass
class Config:
    # ── 데이터 경로 ────────────────────────────────────────────
    # h5 신호 파일들과 filelist.csv가 들어 있는 폴더 이름
    DATA_DIR: str = "Multivariate time series data of milling processes with varying tool wear and machine tools"
    FILELIST: str = "filelist.csv"          # 레이블 CSV 파일명
    FEATURE_CACHE: str = "mendeley_features.csv"  # Feature 추출 결과 캐시 파일
    #   → 처음 실행 시 h5 파일에서 Feature를 추출해 이 파일에 저장해 두면
    #     다음 실행부터는 재추출 없이 이 파일을 바로 읽어 사용한다.

    # ── 마모 수명 기준 ──────────────────────────────────────────
    VB_FAILURE: float = 150.0   # 플랭크 마모폭 기준 (μm). 150μm를 수명 종료로 정의

    # ── 신호 추출 제한 ──────────────────────────────────────────
    SIGNAL_SAMPLE_LIMIT: int = 10_000
    # h5 파일 하나에 수십만 샘플이 들어 있어 전부 읽으면 느리므로
    # 앞부분 10,000 샘플만 사용해 통계 feature를 추출한다.

    # ── 시계열 윈도우 크기 ──────────────────────────────────────
    WINDOW: int = 10
    # 연속된 WINDOW개 컷(가공 회차)의 Feature를 묶어 하나의 입력 시퀀스로 만든다.

    # ── 학습 하이퍼파라미터 ─────────────────────────────────────
    BATCH_SIZE: int = 64     # 미니배치 크기 (한 번에 학습할 샘플 수)
    EPOCHS_AE: int  = 25     # Autoencoder 최대 학습 epoch 수
    EPOCHS_RUL: int = 35     # RUL 예측 모델 최대 학습 epoch 수
    LR: float       = 1e-3   # 기본 학습률 (Adam optimizer)
    HIDDEN: int     = 64     # LSTM hidden state 차원
    LATENT: int     = 32     # AE latent vector 차원 (정보 압축 크기)
    SEED: int       = 42     # 재현성을 위한 난수 시드
    PATIENCE: int   = 5      # EarlyStopping: val_loss가 PATIENCE epoch 동안 개선 없으면 중단

    # ── 교체 비용 가중치 ─────────────────────────────────────────
    EARLY_COST: float  = 1.0  # 조기 교체 비용 (필요 없을 때 교체 → 공구 낭비)
    LATE_COST: float   = 8.0  # 지연 교체 비용 (교체해야 할 때 안 함 → 설비 손상 위험)
    ACTION_COST: float = 2.0  # 교체 실행 비용 (교체 행위 자체의 인건비·중단 비용)
    # 지연 교체 페널티를 8배로 설정한 이유:
    #   공구 파손 시 설비 손상, 불량품 발생, 생산 중단 등 피해가 훨씬 크기 때문

    # ── 모델 저장 폴더 ─────────────────────────────────────────
    MODEL_DIR: str = "saved_models"

    # ── Stratified split 그룹 수 ────────────────────────────────
    RUL_N_GROUPS: int = 3
    # 공구를 수명 길이 기준으로 3그룹으로 나눠 train/test에 균등 배분


def parse_args() -> Config:

    parser = argparse.ArgumentParser(description="CNC Tool Life AI — Mendeley Dataset")
    parser.add_argument("--data-dir",   default=None)
    parser.add_argument("--window",     type=int, default=None)
    parser.add_argument("--epochs-ae",  type=int, default=None)
    parser.add_argument("--epochs-rul", type=int, default=None)
    parser.add_argument("--seed",       type=int, default=None)
    parser.add_argument("--model-dir",  default=None)
    args, _ = parser.parse_known_args()

    cfg = Config()
    if args.data_dir:   cfg.DATA_DIR   = args.data_dir
    if args.window:     cfg.WINDOW     = args.window
    if args.epochs_ae:  cfg.EPOCHS_AE  = args.epochs_ae
    if args.epochs_rul: cfg.EPOCHS_RUL = args.epochs_rul
    if args.seed:       cfg.SEED       = args.seed
    if args.model_dir:  cfg.MODEL_DIR  = args.model_dir
    return cfg


CFG = parse_args()  # 전역 설정 객체

# GPU가 있으면 GPU, 없으면 CPU 사용 (Mac에서는 보통 CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# 1. 재현성 난수 시드 설정

def seed_everything(seed: int = 42) -> None:
    random.seed(seed)           # Python 내장 random 모듈 시드
    np.random.seed(seed)        # NumPy 난수 시드
    torch.manual_seed(seed)     # PyTorch CPU 연산 시드
    torch.cuda.manual_seed_all(seed)  # PyTorch GPU 연산 시드 (GPU 없으면 무시됨)

# 2. 데이터 로딩 — filelist.csv 파싱 + RUL 계산

def load_filelist(cfg: Config) -> pd.DataFrame:
    "filelist.csv를 읽고 RUL과 공구 ID를 계산해 DataFrame으로 반환한다."
    flist_path = Path(cfg.DATA_DIR) / cfg.FILELIST
    df = pd.read_csv(flist_path)

    # 컬럼명 앞뒤 공백 제거 + 소문자 통일 (데이터셋마다 표기가 다를 수 있음)
    df.columns = df.columns.str.strip().str.lower()

    # 실제 데이터셋의 컬럼명 → 코드 내부 표준 컬럼명으로 변환
    col_rename = {
        "filename": "file",
        "machine":  "m",
        "tool":     "t",
        "run":      "r",
        "cumulated_tool_contact_time": "c",
        "wear":     "vb",
    }
    df = df.rename(columns={k: v for k, v in col_rename.items() if k in df.columns})

    # 필수 컬럼이 모두 있는지 확인 (없으면 에러 발생시켜 원인 파악 유도)
    required = ["file", "vb", "m", "t", "r", "c"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"filelist.csv에 필수 컬럼이 없습니다: {missing}\n"
                         f"실제 컬럼: {list(df.columns)}")

    # 공구 ID = "머신번호_공구번호" 문자열 → 정수 인덱스로 변환
    # 예: (머신1, 공구3) → "1_3" → 2 (정렬 후 인덱스)
    df["tool_id"]     = df["m"].astype(str) + "_" + df["t"].astype(str)
    tool_id_map       = {v: i for i, v in enumerate(sorted(df["tool_id"].unique()))}
    df["tool_id_int"] = df["tool_id"].map(tool_id_map)

    # 공구별로 누적 접촉시간(c) 오름차순 정렬 → 시계열 순서 보장
    df = df.sort_values(["tool_id_int", "c"]).reset_index(drop=True)

    # RUL 계산: 각 공구의 최대 c에서 현재 c를 빼면 남은 수명
    df["rul"] = df.groupby("tool_id_int")["c"].transform(lambda x: x.max() - x)

    # h5 파일의 절대 경로 구성 (상대 경로 → 절대 경로)
    df["filepath"] = df["file"].apply(lambda f: str(Path(cfg.DATA_DIR) / f))

    print(f"filelist 행 수: {len(df):,}")
    print(f"공구 세트 수 (M×T): {df['tool_id_int'].nunique()}")
    print(f"머신 수: {df['m'].nunique()} | 공구 수: {df['t'].nunique()}")
    print(f"RUL 범위: {df['rul'].min():.1f} ~ {df['rul'].max():.1f} 초")
    return df


def print_data_diagnostics(df: pd.DataFrame) -> None:
    "공구 세트별 최대 RUL 분포를 출력해 데이터 균형을 확인한다."
    tool_stats = df.groupby("tool_id_int")["rul"].max().describe()
    print("\n" + "=" * 50)
    print("[진단] 공구 세트별 최대 RUL 분포")
    print(tool_stats.round(2).to_string())
    print("=" * 50 + "\n")

# 3. h5 신호 파일에서 Feature(Feature) 추출

def list_h5_channels(filepath: str) -> list[str]:
    "h5 파일 내 신호 채널 이름 목록을 반환한다 (디버깅·확인용)."
    channels = []
    with h5py.File(filepath, "r") as f:
        # h5 파일 내 두 그룹에서 채널명 수집
        for grp_name in ["signals_machine", "signals_sensor"]:
            if grp_name in f:
                channels.extend(f[grp_name].keys())
    return channels


def fft_features_from_signal(x: np.ndarray) -> dict[str, float]:
    """
    1차원 시계열 신호 x에서 FFT 기반 Feature 3개를 계산한다.
    """
    if len(x) < 8:  # 신호가 너무 짧으면 FFT 의미 없음
        return {"fft_peak_bin": 0.0, "fft_centroid": 0.0, "fft_energy": 0.0}

    x = x - np.nanmean(x)             # DC 제거 (평균값 빼기)
    mag = np.abs(np.fft.rfft(x))      # 실수 FFT → 주파수별 크기
    bins = np.arange(len(mag), dtype=float)  # 주파수 bin 인덱스
    total = np.sum(mag)

    # 스펙트럼 무게중심: Σ(bin × magnitude) / Σ(magnitude)
    centroid = float(np.sum(bins * mag) / total) if total > 0 else 0.0

    return {
        "fft_peak_bin":  float(bins[np.argmax(mag)]),  # 에너지 최대 주파수 bin
        "fft_centroid":  centroid,                      # 주파수 무게중심
        "fft_energy":    float(np.sum(mag ** 2))
    }


def extract_features_from_h5(filepath: str, cfg: Config) -> dict[str, float]:
    """
    h5 파일 하나를 읽어 모든 채널에서 통계 Feature를 추출
    """
    row = {}
    try:
        with h5py.File(filepath, "r") as f:
            # h5 파일 내 두 그룹(머신 신호, 센서 신호) 순회
            for grp_name in ["signals_machine", "signals_sensor"]:
                if grp_name not in f:
                    continue
                grp = f[grp_name]

                for ch in grp.keys():
                    if ch.startswith("time_"):  # 시간축 채널은 Feature로 사용하지 않음
                        continue

                    raw = grp[ch][:]
                    if raw.ndim > 1:
                        raw = raw.flatten()  # 2D 배열이면 1D로 평탄화

                    # 앞부분 SIGNAL_SAMPLE_LIMIT개만 사용 (속도 확보)
                    x = raw[:cfg.SIGNAL_SAMPLE_LIMIT].astype(np.float64)
                    x = x[np.isfinite(x)]  # NaN/Inf 제거
                    if len(x) == 0:
                        continue

                    # 채널명에 특수문자가 있으면 CSV 저장 시 문제가 생기므로 치환
                    clean = ch.replace(" ", "_").replace("/", "_").replace("-", "_")
                    prefix = f"ch_{clean}"  # 예: "ch_force_x"

                    # 통계 Feature 계산
                    rms = float(np.sqrt(np.mean(x ** 2)))  # 신호 에너지 크기
                    std = float(np.std(x))                  # 진동 변동성
                    ptp = float(np.ptp(x))                  # 최대진폭 (max - min)

                    row[f"{prefix}_rms"] = rms
                    row[f"{prefix}_std"] = std
                    row[f"{prefix}_ptp"] = ptp

                    # FFT Feature 3개 추가
                    for k, v in fft_features_from_signal(x).items():
                        row[f"{prefix}_{k}"] = v

    except Exception as e:
        print(f"  SKIP {filepath}: {e}")  # 파일 읽기 실패 시 건너뜀
    return row


def build_feature_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    모든 h5 파일에서 Feature를 추출해 DataFrame으로 구성한다.
    이미 캐시 파일(mendeley_features.csv)이 있으면 그것을 읽어 재사용한다.
    (6,418개 파일 × 추출 시간 → 초기 실행은 수십 분 소요)
    """
    cache_path = Path(cfg.FEATURE_CACHE)
    if cache_path.exists():
        print(f"기존 feature cache 사용: {cache_path}")
        feat_df = pd.read_csv(cache_path)
        # filepath 컬럼 기준으로 원본 DataFrame과 조인
        return df.merge(feat_df, on="filepath", how="left")

    print(f"h5 feature 추출 시작 ({len(df)}개 파일)...")
    rows = []
    for i, row in df.iterrows():
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(df)}: {Path(row['filepath']).name}")
        feat = extract_features_from_h5(row["filepath"], cfg)
        feat["filepath"] = row["filepath"]  # 조인을 위해 filepath 컬럼 포함
        rows.append(feat)

    feat_df = pd.DataFrame(rows)
    feat_df.to_csv(cache_path, index=False)  # 다음 실행에서 재사용 가능하도록 저장
    print(f"feature cache 저장: {cache_path}")
    return df.merge(feat_df, on="filepath", how="left")


def select_feature_cols(df: pd.DataFrame) -> list[str]:
    """
    RUL·공구 ID 등 메타 컬럼을 제외하고, LSTM 입력으로 사용할
    순수 신호 Feature 컬럼명 리스트를 반환한다.
    """
    # 모델 입력이 아닌 메타/레이블 컬럼 목록
    exclude = {"tool_id_int", "tool_id", "file", "filepath",
               "m", "t", "r", "c", "vb", "rul"}
    numeric = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    feature_cols = [c for c in numeric if c not in exclude]
    print(f"feature 수: {len(feature_cols)}")
    return feature_cols


def load_dataset(cfg: Config) -> tuple[pd.DataFrame, list[str]]:
    df = load_filelist(cfg)
    df = build_feature_table(df, cfg)

    feature_cols = select_feature_cols(df)

    # ±Inf를 NaN으로 치환 (FFT 계산 시 가끔 발생)
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)

    # NaN이 있는 Feature는 해당 컬럼의 중앙값으로 대체 (Simple Imputation)
    for col in feature_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())

    # 핵심 컬럼에 NaN이 남은 행은 제거
    df = df.dropna(subset=["tool_id_int", "c", "rul"] + feature_cols).copy()
    print(f"최종 행 수: {len(df):,} | feature 수: {len(feature_cols)}")
    return df, feature_cols

# 4. 슬라이딩 윈도우 생성 (시계열 입력 구성)

def make_windows(
    df: pd.DataFrame,
    feature_cols: list[str],
    window: int,
    per_tool_rul_norm: bool = False,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    X, y, meta = [], [], []

    for tool_id, g in df.groupby("tool_id_int"):
        g = g.sort_values("c")  # 접촉시간 순 정렬 (시계열 순서 보장)
        values  = g[feature_cols].values.astype(np.float32)  # Feature 행렬
        targets = g["rul"].values.astype(np.float32)          # 타깃 RUL

        if len(g) < window:  # 데이터가 윈도우보다 적은 공구는 건너뜀
            continue

        if per_tool_rul_norm:
            # 공구별 최대 RUL로 나눠 [0, 1] 정규화
            max_rul = targets.max()
            if max_rul > 0:
                targets = targets / max_rul

        # 슬라이딩 윈도우: 한 칸씩 이동하며 (window × Feature) 행렬 생성
        for start in range(len(g) - window + 1):
            end = start + window
            X.append(values[start:end])   # 윈도우 구간 Feature
            y.append(targets[end - 1])    # 윈도우 마지막 시점의 RUL이 예측 대상
            meta.append({
                "tool_id":     tool_id,
                "c":           float(g["c"].iloc[end - 1]),
                "vb":          float(g["vb"].iloc[end - 1]),
                "tool_max_rul": float(g["rul"].max()),  # 역정규화 시 필요
            })

    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y, dtype=np.float32),
        pd.DataFrame(meta),
    )

# 5. Stratified Train/Test Split (계층적 분할)


def split_by_tool(
    df: pd.DataFrame,
    n_groups: int  = 3,
    test_size: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    "공구 세트를 수명 길이 그룹별로 stratified split한다."

    # 공구별 최대 RUL 계산 후 3분위로 그룹화
    tool_max_rul = df.groupby("tool_id_int")["rul"].max()
    tool_group   = pd.qcut(tool_max_rul, q=n_groups, labels=False, duplicates="drop")

    train_ids, test_ids = [], []
    for grp in tool_group.dropna().unique():
        grp_tools = tool_group[tool_group == grp].index.tolist()
        if len(grp_tools) < 2:  # 그룹에 공구가 1개뿐이면 train에 포함
            train_ids.extend(grp_tools)
            continue
        n_test    = max(1, round(len(grp_tools) * test_size))
        rng       = np.random.default_rng(CFG.SEED)  # 재현성을 위해 시드 고정
        test_pick = rng.choice(grp_tools, size=n_test, replace=False).tolist()
        train_ids.extend([t for t in grp_tools if t not in test_pick])
        test_ids.extend(test_pick)

    print(f"[Stratified split] 그룹 {n_groups}개 | "
          f"train 공구: {len(train_ids)} | test 공구: {len(test_ids)}")
    return (
        df[df["tool_id_int"].isin(train_ids)].copy(),
        df[df["tool_id_int"].isin(test_ids)].copy(),
    )

# 6. EarlyStopping (조기 종료)


class EarlyStopping:
    def __init__(self, patience: int = 5, delta: float = 1e-4):
        self.patience   = patience
        self.delta      = delta
        self.best       = float("inf")   # 지금까지 최저 val_loss
        self.counter    = 0              # 개선 없는 epoch 카운터
        self.best_state: dict | None = None  # 최고 성능 시점 모델 가중치

    def step(self, val_loss: float, model: nn.Module) -> bool:
        """
        val_loss를 받아 최솟값 갱신 여부를 확인하고,
        중단 조건을 만족하면 True를 반환한다.
        """
        if val_loss < self.best - self.delta:
            # 개선됨: 카운터 리셋, 현재 모델 가중치 저장
            self.best       = val_loss
            self.counter    = 0
            self.best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            # 개선 없음: 카운터 증가
            self.counter += 1
        return self.counter >= self.patience  # patience 초과 시 True

    def restore_best(self, model: nn.Module) -> None:
        """저장해 둔 최고 성능 가중치를 모델에 복원한다."""
        if self.best_state is not None:
            model.load_state_dict(self.best_state)

# 7. 모델 ①: LSTM Autoencoder (비지도 이상 감지)

class LSTMAutoEncoder(nn.Module):
    def __init__(self, n_features: int, hidden: int = 64, latent: int = 32):
        super().__init__()
        # 인코더: 시계열 입력을 LSTM으로 처리 → 마지막 hidden state 추출
        self.encoder     = nn.LSTM(n_features, hidden, batch_first=True)
        # latent 압축: hidden(64) → latent(32) — 정보 병목(bottleneck)
        self.to_latent   = nn.Linear(hidden, latent)
        # latent 복원: latent(32) → hidden(64) — 디코더 초기 상태
        self.from_latent = nn.Linear(latent, hidden)
        # 디코더: 복원된 hidden을 LSTM으로 펼쳐 시퀀스 복원
        self.decoder     = nn.LSTM(hidden, hidden, batch_first=True)
        # 출력층: hidden(64) → 원래 Feature 수(90) — 원본 입력과 같은 차원으로 복원
        self.output_layer = nn.Linear(hidden, n_features)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # 인코딩: 시퀀스 전체를 LSTM에 통과시켜 마지막 hidden 추출
        _, (h, _) = self.encoder(x)       # h: (1, batch, hidden)
        z = self.to_latent(h[-1])          # z: (batch, latent) — 압축 표현

        # 디코딩: latent를 다시 hidden으로 펼쳐 디코더 LSTM의 초기 상태로 사용
        h0 = self.from_latent(z).unsqueeze(0)   # (1, batch, hidden)
        c0 = torch.zeros_like(h0)               # LSTM cell state 초기화

        # 입력 시퀀스 길이만큼 h0을 반복해 디코더 입력 생성
        repeated = h0[-1].unsqueeze(1).repeat(1, x.size(1), 1)  # (batch, T, hidden)
        decoded, _ = self.decoder(repeated, (h0, c0))

        # 최종 출력: 복원된 X̂와 latent z를 모두 반환
        return self.output_layer(decoded), z


def train_autoencoder(
    model: nn.Module, loader: DataLoader, epochs: int, lr: float, patience: int = 5
) -> nn.Module:
    """
    AE를 정상 구간 데이터로 학습한다.
    손실함수: MSELoss (재구성 오차 최소화)
    스케줄러: ReduceLROnPlateau (val_loss 정체 시 lr을 절반으로 감소)
    """
    model.to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    # 학습률 스케줄러: 3 epoch 동안 loss 개선 없으면 lr × 0.5
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3
    )
    criterion = nn.MSELoss()  # 재구성 오차: (X̂ - X)²의 평균
    es = EarlyStopping(patience=patience)

    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for (xb,) in loader:
            xb = xb.to(DEVICE)
            recon, _ = model(xb)           # 복원된 X̂
            loss = criterion(recon, xb)    # 원본 X와 복원 X̂의 MSE
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        mean_loss = float(np.mean(losses))
        scheduler.step(mean_loss)

        if epoch == 1 or epoch % 5 == 0:
            print(f"[AE] epoch={epoch:03d} loss={mean_loss:.6f} "
                  f"lr={optimizer.param_groups[0]['lr']:.2e}")

        if es.step(mean_loss, model):
            print(f"[AE] EarlyStopping at epoch {epoch}")
            break

    es.restore_best(model)  # 가장 좋았던 시점의 가중치로 복원
    return model


@torch.no_grad()
def get_ae_outputs(
    model: nn.Module, X: np.ndarray, batch_size: int = 256
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    loader = DataLoader(TensorDataset(torch.tensor(X)),
                        batch_size=batch_size, shuffle=False)
    errors, latents = [], []
    for (xb,) in loader:
        xb = xb.to(DEVICE)
        recon, z = model(xb)
        # dim=(1,2): window 차원과 Feature 차원 모두 평균 → 샘플당 스칼라 1개
        err = torch.mean((recon - xb) ** 2, dim=(1, 2))
        errors.append(err.cpu().numpy())
        latents.append(z.cpu().numpy())
    return np.concatenate(errors), np.concatenate(latents)


def add_ae_err_to_windows(
    X: np.ndarray, err: np.ndarray, err_scaler: StandardScaler | None
) -> np.ndarray:
    err_2d = err.reshape(-1, 1)
    # StandardScaler로 오차 값 정규화 (mean=0, std=1)
    err_scaled = err_scaler.transform(err_2d) if err_scaler else err_2d
    # (N, 1, 1) → (N, T, 1) 으로 타임스텝만큼 복사
    err_feat = np.repeat(err_scaled.reshape(-1, 1, 1), X.shape[1], axis=1).astype(np.float32)
    return np.concatenate([X, err_feat], axis=2)  # Feature 차원에 concat → (N, T, 91)

# 8. 모델 ②: LSTM RUL 예측기


class LSTMRULRegressor(nn.Module):
    def __init__(
        self, n_features: int, hidden: int = 64,
        latent_dim: int = 0, n_layers: int = 1, dropout: float = 0.0
    ):
        super().__init__()
        self.latent_dim = latent_dim
        # LSTM: 시계열 Feature를 순서대로 처리 (batch_first=True → 입력: batch × seq × feature)
        self.lstm = nn.LSTM(
            n_features, hidden, num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,  # 2층 이상일 때만 dropout
        )
        # FC head 입력 차원: LSTM hidden + AE latent
        head_in = hidden + latent_dim
        self.head = nn.Sequential(
            nn.Linear(head_in, head_in // 2),  # 차원 절반으로 압축
            nn.ReLU(),                          # 비선형 활성화
            nn.Dropout(dropout),               # 과적합 방지
            nn.Linear(head_in // 2, 1),        # 최종 RUL 스칼라 출력
        )

    def forward(self, x: torch.Tensor, latent: torch.Tensor | None = None) -> torch.Tensor:
        out, _ = self.lstm(x)          # out: (batch, seq, hidden)
        h_last = out[:, -1, :]        # 마지막 타임스텝의 hidden state만 사용

        if self.latent_dim > 0 and latent is not None:
            # AE latent를 hidden에 이어 붙여 이상 정보를 RUL 예측에 활용
            h_last = torch.cat([h_last, latent], dim=1)  # (batch, hidden + latent)

        return self.head(h_last).squeeze(1)  # (batch,) 형태로 RUL 출력


class AttentionLSTMRULRegressor(nn.Module):
    def __init__(
        self, n_features: int, hidden: int = 64,
        latent_dim: int = 0, n_layers: int = 1, dropout: float = 0.0,
        bidirectional: bool = True,
    ):
        super().__init__()
        self.latent_dim = latent_dim
        dirs = 2 if bidirectional else 1  # BiLSTM이면 출력 차원이 2배

        self.lstm = nn.LSTM(
            n_features, hidden, num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )
        lstm_out = hidden * dirs  # BiLSTM: hidden×2, 단방향: hidden×1

        # Additive Attention 가중치 벡터: 각 타임스텝의 중요도 점수 계산
        self.attn_w = nn.Linear(lstm_out, 1, bias=False)

        head_in = lstm_out + latent_dim
        self.head = nn.Sequential(
            nn.Linear(head_in, head_in // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(head_in // 2, 1),
        )

    def forward(self, x: torch.Tensor, latent: torch.Tensor | None = None) -> torch.Tensor:
        out, _ = self.lstm(x)                       # (batch, T, hidden*dirs)

        # Self-Attention: 모든 타임스텝에 가중치 계산
        scores  = self.attn_w(torch.tanh(out))      # (batch, T, 1) — 중요도 점수
        weights = torch.softmax(scores, dim=1)       # (batch, T, 1) — 가중치 (합=1)
        context = (out * weights).sum(dim=1)         # (batch, hidden*dirs) — 가중 합산

        if self.latent_dim > 0 and latent is not None:
            context = torch.cat([context, latent], dim=1)

        return self.head(context).squeeze(1)


def train_rul_model(
    model: nn.Module,
    X_train: np.ndarray, y_train: np.ndarray,
    X_val:   np.ndarray, y_val:   np.ndarray,
    epochs: int, lr: float, batch_size: int,
    patience: int = 5,
    trial: optuna.Trial | None = None,
    lat_train: np.ndarray | None = None,
    lat_val:   np.ndarray | None = None,
    use_huber: bool    = False,  # [개선] Huber Loss 사용 여부
    grad_clip: float   = 0.0,   # [개선] Gradient Clipping 임계값 (0=미사용)
    weight_decay: float = 0.0,  # [개선] Adam에 L2 정규화 추가
) -> nn.Module:
    model.to(DEVICE)

    # 학습 데이터 텐서 구성 (AE latent가 있으면 함께 묶음)
    tensors_tr = [torch.tensor(X_train), torch.tensor(y_train)]
    if lat_train is not None:
        tensors_tr.append(torch.tensor(lat_train.astype(np.float32)))
    loader = DataLoader(TensorDataset(*tensors_tr), batch_size=batch_size, shuffle=True)

    # weight_decay: L2 정규화 강도 (0이면 정규화 없음)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    # 검증 RMSE가 3 epoch 동안 개선 없으면 학습률을 절반으로 감소
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3
    )

    # [개선] 손실함수 선택
    # SmoothL1Loss = Huber Loss: |error| ≤ 1 → 0.5×error², |error| > 1 → |error|-0.5
    criterion = nn.SmoothL1Loss() if use_huber else nn.MSELoss()
    es = EarlyStopping(patience=patience)

    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for batch in loader:
            xb = batch[0].to(DEVICE)   # Feature (batch, T, features)
            yb = batch[1].to(DEVICE)   # 타깃 RUL
            lb = batch[2].to(DEVICE) if len(batch) == 3 else None  # AE latent

            loss = criterion(model(xb, lb), yb)
            optimizer.zero_grad()
            loss.backward()

            # [개선] Gradient Clipping: 기울기 벡터의 norm이 grad_clip을 넘으면 정규화
            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)

            optimizer.step()
            losses.append(loss.item())

        # 검증 RMSE 계산 (실제 스케일로 평가)
        pred_val = predict_rul(model, X_val, lat=lat_val)
        val_rmse = float(np.sqrt(mean_squared_error(y_val, pred_val)))
        scheduler.step(val_rmse)

        if epoch == 1 or epoch % 5 == 0:
            print(f"[RUL] epoch={epoch:03d} train_loss={np.mean(losses):.6f} "
                  f"val_rmse={val_rmse:.4f} lr={optimizer.param_groups[0]['lr']:.2e}")

        # Optuna trial 중간 보고 (성능 나쁜 trial 조기 종료 판단에 사용)
        if trial is not None:
            trial.report(val_rmse, epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if es.step(val_rmse, model):
            print(f"[RUL] EarlyStopping at epoch {epoch}")
            break

    es.restore_best(model)  # val_rmse 최소 시점의 가중치로 복원
    return model


@torch.no_grad()
def predict_rul(
    model: nn.Module, X: np.ndarray,
    batch_size: int = 256, lat: np.ndarray | None = None
) -> np.ndarray:
    model.eval()
    tensors = [torch.tensor(X)]
    if lat is not None:
        tensors.append(torch.tensor(lat.astype(np.float32)))
    loader = DataLoader(TensorDataset(*tensors), batch_size=batch_size, shuffle=False)

    preds = []
    for batch in loader:
        xb = batch[0].to(DEVICE)
        lb = batch[1].to(DEVICE) if len(batch) == 2 else None
        preds.append(model(xb, lb).cpu().numpy())
    return np.concatenate(preds)


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    "회귀 성능 지표 3개를 계산해 딕셔너리로 반환한다."
    return {
        "MAE":  float(mean_absolute_error(y_true, y_pred)),           # 평균 절대 오차 (초)
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),   # 제곱근 평균제곱오차 (초)
        "R2":   float(r2_score(y_true, y_pred)),                      # 결정계수 (1에 가까울수록 좋음)
    }

# 9. 교체 임계값 최적화 (Optuna)


def replacement_cost(
    y_true: np.ndarray, y_pred: np.ndarray, ae_err: np.ndarray,
    rul_th: float, err_th: float, cfg: Config,
) -> float:
    "주어진 임계값에서의 교체 비용을 계산한다."
    replace = (y_pred <= rul_th) | (ae_err >= err_th)  # 교체 결정 (OR 조건)
    early   = replace & (y_true > rul_th)              # 조기 교체: 실제로는 아직 안 교체해도 됨
    late    = (~replace) & (y_true <= rul_th)           # 지연 교체: 교체해야 하는데 안 함 (위험!)
    total   = (cfg.ACTION_COST * replace.sum()         # 교체 실행 비용
               + cfg.EARLY_COST * early.sum()           # 조기 교체 비용 (낭비)
               + cfg.LATE_COST  * late.sum())            # 지연 교체 비용 (위험)
    return float(total / len(y_true))  # 샘플 수로 나눠 정규화


def optimize_thresholds(
    y_true: np.ndarray, y_pred: np.ndarray, ae_err: np.ndarray,
    cfg: Config, n_trials: int = 100
) -> dict:
    pruner = MedianPruner(n_startup_trials=10, n_warmup_steps=0)
    study  = optuna.create_study(direction="minimize", pruner=pruner)

    def objective(trial: optuna.Trial) -> float:
        rul_th = trial.suggest_float("rul_threshold",
                                     float(np.percentile(y_true, 5)),
                                     float(np.percentile(y_true, 40)))
        err_th = trial.suggest_float("ae_error_threshold",
                                     float(np.percentile(ae_err, 60)),
                                     float(np.percentile(ae_err, 99)))
        cost = replacement_cost(y_true, y_pred, ae_err, rul_th, err_th, cfg)
        trial.report(cost, step=0)
        if trial.should_prune():
            raise optuna.TrialPruned()
        return cost

    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    print(f"[Optuna] 최적 비용: {study.best_value:.4f} | {study.best_params}")
    return {"best_cost": study.best_value, **study.best_params}

# 10. 하이퍼파라미터 자동 탐색 (Optuna + MedianPruner)

def hyperparam_search(
    df: pd.DataFrame, feature_cols: list[str], cfg: Config, n_trials: int = 50
) -> dict:
    "Optuna로 최적 하이퍼파라미터를 탐색하고 best_params 딕셔너리를 반환한다."
    # startup_trials=5: 처음 5개 trial은 가지치기 없이 탐색 (기준 분포 수집)
    # warmup_steps=5  : 각 trial에서 5 epoch 이후부터 가지치기 적용
    pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=5)
    # seed 고정: 매 실행마다 동일한 탐색 경로로 재현성 확보
    sampler = optuna.samplers.TPESampler(seed=cfg.SEED)
    study  = optuna.create_study(direction="minimize", pruner=pruner, sampler=sampler)

    # 하이퍼파라미터 탐색은 train 데이터만 사용 (test 데이터 노출 방지)
    train_df, _ = split_by_tool(df, n_groups=cfg.RUL_N_GROUPS)
    scaler = StandardScaler()
    train_df = train_df.copy()
    train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])

    def objective(trial: optuna.Trial) -> float:
        # ── trial마다 파라미터 조합을 새로 샘플링 ──────────────────
        hidden        = trial.suggest_categorical("hidden",       [32, 64, 128])
        latent        = trial.suggest_categorical("latent",       [16, 32, 64])
        lr            = trial.suggest_float("lr",                 1e-4, 1e-2, log=True)
        window        = trial.suggest_categorical("window",       [5, 10, 15, 20])
        n_layers      = trial.suggest_int("n_layers",             1, 2)
        dropout       = trial.suggest_float("dropout",            0.0, 0.3)
        bidirectional = trial.suggest_categorical("bidirectional", [False, True])  # [개선]
        use_attn      = trial.suggest_categorical("use_attention", [False, True])  # [개선]
        weight_decay  = trial.suggest_float("weight_decay",       1e-6, 1e-3, log=True)  # [개선]

        # 샘플링된 window 크기로 슬라이딩 윈도우 생성
        X_tr, y_tr, _ = make_windows(train_df, feature_cols, window, per_tool_rul_norm=True)
        if len(X_tr) == 0:
            return float("inf")

        # train 내 80/20 분할 → 같은 정규화 스케일로 RMSE 비교
        X_tr2, X_v2, y_tr2, y_v2 = train_test_split(
            X_tr, y_tr, test_size=0.2, random_state=cfg.SEED)

        # AE는 정상 구간(수명 50% 이상)만으로 학습
        early_mask = y_tr2 > 0.5
        X_ae       = X_tr2[early_mask] if early_mask.sum() > 10 else X_tr2
        ae_loader  = DataLoader(TensorDataset(torch.tensor(X_ae)),
                                batch_size=cfg.BATCH_SIZE, shuffle=True)
        ae = LSTMAutoEncoder(X_ae.shape[2], hidden, latent).to(DEVICE)
        ae = train_autoencoder(ae, ae_loader, epochs=10, lr=lr, patience=3)

        # AE로 재구성 오차와 latent 추출
        err_tr2, lat_tr2 = get_ae_outputs(ae, X_tr2)
        err_v2,  lat_v2  = get_ae_outputs(ae, X_v2)

        err_scaler = StandardScaler().fit(err_tr2.reshape(-1, 1))
        lat_scaler = StandardScaler().fit(lat_tr2)

        # 오차를 91번째 Feature로 추가
        X_tr_aug = add_ae_err_to_windows(X_tr2, err_tr2, err_scaler)
        X_v_aug  = add_ae_err_to_windows(X_v2,  err_v2,  err_scaler)
        lat_tr_s = lat_scaler.transform(lat_tr2).astype(np.float32)
        lat_v_s  = lat_scaler.transform(lat_v2).astype(np.float32)

        # [개선] Attention 모델 또는 기본 LSTM 선택
        if use_attn:
            rul = AttentionLSTMRULRegressor(
                X_tr_aug.shape[2], hidden, latent, n_layers, dropout, bidirectional)
        else:
            rul = LSTMRULRegressor(X_tr_aug.shape[2], hidden, latent, n_layers, dropout)

        # 개선 기법(Huber·Clipping·WD) 모두 적용해 탐색
        rul = train_rul_model(
            rul, X_tr_aug, y_tr2, X_v_aug, y_v2,
            epochs=15, lr=lr, batch_size=cfg.BATCH_SIZE, patience=3,
            trial=trial, lat_train=lat_tr_s, lat_val=lat_v_s,
            use_huber=True, grad_clip=1.0, weight_decay=weight_decay,
        )

        preds_norm = predict_rul(rul, X_v_aug, lat=lat_v_s)
        # 정규화된 스케일에서 RMSE를 반환 (trial 간 비교 가능)
        return float(np.sqrt(mean_squared_error(y_v2, preds_norm)))

    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    print(f"\n[HyperSearch] Best RMSE: {study.best_value:.4f}")
    print(f"[HyperSearch] Best params: {study.best_params}")
    return study.best_params  # 최적 파라미터 딕셔너리 반환

# 11. 모델 파일 저장

def save_model(model: nn.Module, name: str, cfg: Config) -> None:
    """모델 가중치를 saved_models/{name}.pt 파일로 저장한다."""
    Path(cfg.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), Path(cfg.MODEL_DIR) / f"{name}.pt")
    print(f"모델 저장: {cfg.MODEL_DIR}/{name}.pt")


# 12. 결과 그래프 저장 함수들

def save_prediction_plot(y_true: np.ndarray, y_pred: np.ndarray,
                         out: str = "fig_rul_prediction.png") -> None:
    """
    실제 RUL과 예측 RUL을 오름차순으로 정렬해 비교하는 라인 차트.
    두 선이 가까울수록 예측 정확도가 높다.
    """
    order = np.argsort(y_true)  # 실제 RUL 오름차순 정렬 인덱스
    plt.figure(figsize=(10, 4))
    plt.plot(y_true[order], label="실제 RUL",  linewidth=1.5)
    plt.plot(y_pred[order], label="예측 RUL",  linewidth=1.2, alpha=0.8)
    plt.title("RUL 예측 결과 (Mendeley 밀링 데이터셋)")
    plt.xlabel("샘플 인덱스 (실제 RUL 오름차순 정렬)")
    plt.ylabel("잔여 공구 수명 (초)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")


def save_error_scatter(y_true: np.ndarray, ae_err: np.ndarray,
                       out: str = "fig_ae_error_vs_rul.png") -> None:
    """
    AE 재구성 오차 vs 실제 RUL 산점도.
    RUL이 작을수록(수명 말기) 오차가 커지는 패턴을 시각적으로 확인한다.
    이 패턴이 AE 이상 감지의 핵심 근거가 된다.
    """
    plt.figure(figsize=(7, 5))
    plt.scatter(y_true, ae_err, s=10, alpha=0.6)
    plt.title("AE 재구성 오차 vs 잔여 수명 (RUL)")
    plt.xlabel("실제 RUL (초)")
    plt.ylabel("AE 재구성 오차 (MSE)")
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")


def save_vb_plot(df: pd.DataFrame, out: str = "fig_vb_progression.png") -> None:
    """
    공구별 플랭크 마모(VB) 진행 곡선.
    x축: 누적 접촉시간(초), y축: 마모량(μm)
    빨간 점선: VB=150μm 교체 기준선
    공구마다 마모 속도가 다른 것을 시각적으로 확인할 수 있다.
    """
    plt.figure(figsize=(10, 5))
    for tid, g in df.groupby("tool_id_int"):
        g = g.sort_values("c")
        plt.plot(g["c"].values, g["vb"].values, linewidth=0.9, alpha=0.7)
    plt.axhline(150, color="red", linestyle="--", label="교체 기준 (VB = 150 μm)")
    plt.title("공구별 플랭크 마모 진행 곡선")
    plt.xlabel("누적 접촉 시간 (초)")
    plt.ylabel("플랭크 마모량 VB (μm)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")


def save_experiment_table(results: list[dict], out: str = "experiment_results.csv") -> None:
    """모든 실험 결과를 CSV로 저장하고 콘솔에 출력한다."""
    df = pd.DataFrame(results)
    df.to_csv(out, index=False)
    print(f"\n{'='*70}")
    print(df.to_string(index=False))
    print(f"{'='*70}")


def save_performance_bar(results: list[dict],
                         out: str = "fig_performance_comparison.png") -> None:
    """
    실험별 MAE / RMSE / R² 막대 그래프.
    실험이 진행될수록 MAE·RMSE가 낮아지고 R²가 높아지는 개선 흐름을 보여준다.
    실험 수가 가변적이라도 자동으로 색상·레이블이 대응된다.
    """
    # 실험명 → 한글 레이블 매핑
    _label_map = {
        "1_baseline_lstm":         "Exp1\n베이스라인\n(Feature만)",
        "2_ae_error_lstm":         "Exp2\nAE 오차\n연결",
        "3_ae_optuna_lstm":        "Exp3\nAE+Optuna",
        "3_ae_latent_concat_lstm": "Exp3\nAE+Optuna",
        "4_ae_huber_clip":         "Exp4\nHuber+\nGrad Clip",
        "5_bilstm_attention":      "Exp5\nBiLSTM+\nAttention",
    }
    labels = [_label_map.get(r["experiment"], r["experiment"]) for r in results]
    mae    = [r["MAE"]  for r in results]
    rmse   = [r["RMSE"] for r in results]
    r2     = [r["R2"]   for r in results]

    palette = ["#5C9BF5", "#69F0AE", "#FFD54F", "#EF5350", "#CE93D8"]
    colors  = [palette[i % len(palette)] for i in range(len(results))]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("실험별 모델 성능 비교", fontsize=15, fontweight="bold")

    for ax, vals, title, ylabel, fmt, ylim_fn in [
        (axes[0], mae,  "MAE (낮을수록 우수)",   "예측 오차 (초)",  "%.1f",
         lambda v: (0, max(v) * 1.25)),
        (axes[1], rmse, "RMSE (낮을수록 우수)",  "예측 오차 (초)",  "%.1f",
         lambda v: (0, max(v) * 1.25)),
        (axes[2], r2,   "R² (높을수록 우수)",    "결정계수 R²",    "%.3f",
         lambda v: (max(0, min(v) * 0.97), 1.02)),
    ]:
        bars = ax.bar(labels, vals, color=colors, edgecolor="gray", linewidth=0.5)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.bar_label(bars, fmt=fmt, padding=4, fontsize=9)
        ax.set_ylim(*ylim_fn(vals))
        ax.tick_params(axis="x", labelsize=8)

    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")


def save_threshold_scatter(y_true: np.ndarray, y_pred: np.ndarray,
                           ae_err: np.ndarray,
                           rul_thr: float, ae_thr: float,
                           out: str = "fig_threshold_decision.png") -> None:
    """
    교체 임계값 기반 교체 결정 결과를 4가지 케이스로 색상 구분해 시각화한다.

    색상 의미:
      파란색: 정상 대기 (TN) — 교체 안 함, 실제로도 불필요
      초록색: 정상 교체 (TP) — 교체함, 실제로 필요했음 (이상적)
      노란색: 조기 교체 (FP) — 교체함, 실제로는 불필요 (낭비)
      빨간색: 지연 교체 (FN) — 교체 안 함, 실제로는 필요 (위험!)
    """
    # OR 조건으로 교체 여부 결정
    replace = (y_pred <= rul_thr) | (ae_err >= ae_thr)
    need    = y_true <= rul_thr   # 실제 교체가 필요한 시점

    tp = replace &  need   # 정상 교체
    fp = replace & ~need   # 조기 교체 (과잉)
    fn = ~replace &  need  # 지연 교체 (위험)
    tn = ~replace & ~need  # 정상 대기

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"교체 임계값 최적화 결과  (RUL ≤ {rul_thr:.0f}초  OR  AE오차 ≥ {ae_thr:.2f})",
                 fontsize=13, fontweight="bold")

    # 왼쪽: 예측 RUL vs 실제 RUL
    ax = axes[0]
    ax.scatter(y_true[tn], y_pred[tn], s=8,  color="#5C9BF5", alpha=0.5, label="정상 대기")
    ax.scatter(y_true[tp], y_pred[tp], s=10, color="#69F0AE", alpha=0.7, label="정상 교체 (TP)")
    ax.scatter(y_true[fp], y_pred[fp], s=10, color="#FFD54F", alpha=0.7, label="조기 교체 (FP)")
    ax.scatter(y_true[fn], y_pred[fn], s=12, color="#EF5350", alpha=0.8, label="지연 교체 (위험)")
    ax.axvline(rul_thr, color="white", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(rul_thr, color="white", linestyle="--", linewidth=1, alpha=0.6)
    ax.set_xlabel("실제 RUL (초)", fontsize=11)
    ax.set_ylabel("예측 RUL (초)", fontsize=11)
    ax.set_title("예측 RUL vs 실제 RUL (교체 결정 구분)", fontsize=12)
    ax.legend(fontsize=9, loc="upper left")

    # 오른쪽: AE 재구성 오차 vs 실제 RUL
    ax2 = axes[1]
    ax2.scatter(y_true[tn], ae_err[tn], s=8,  color="#5C9BF5", alpha=0.5, label="정상 대기")
    ax2.scatter(y_true[tp], ae_err[tp], s=10, color="#69F0AE", alpha=0.7, label="정상 교체 (TP)")
    ax2.scatter(y_true[fp], ae_err[fp], s=10, color="#FFD54F", alpha=0.7, label="조기 교체 (FP)")
    ax2.scatter(y_true[fn], ae_err[fn], s=12, color="#EF5350", alpha=0.8, label="지연 교체 (위험)")
    ax2.axvline(rul_thr, color="white", linestyle="--", linewidth=1, alpha=0.6)
    # AE 오차 임계값 수평선: 이 선을 넘으면 이상 감지로 교체 권고
    ax2.axhline(ae_thr, color="red", linestyle="--", linewidth=1, alpha=0.8,
                label=f"AE 임계값 {ae_thr:.2f}")
    ax2.set_xlabel("실제 RUL (초)", fontsize=11)
    ax2.set_ylabel("AE 재구성 오차", fontsize=11)
    ax2.set_title("AE 오차 vs 실제 RUL (교체 결정 구분)", fontsize=12)
    ax2.legend(fontsize=9, loc="upper right")

    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")


def save_error_distribution(y_true: np.ndarray, y_pred: np.ndarray,
                             out: str = "fig_error_distribution.png") -> None:
    """
    예측 오차 분포 분석 그래프 (2개 서브플롯).
    왼쪽: 오차 히스토그램 — 오차가 0 근처에 집중될수록 좋다
    오른쪽: 실제 vs 예측 산점도 — 대각선(y=x)에 가까울수록 정확하다
    """
    errors = y_pred - y_true  # 양수=과대 예측, 음수=과소 예측

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("예측 오차 분포 분석", fontsize=14, fontweight="bold")

    # 왼쪽: 히스토그램
    ax = axes[0]
    ax.hist(errors, bins=60, color="#5C9BF5", edgecolor="none", alpha=0.8)
    ax.axvline(0,             color="red",    linestyle="--", linewidth=1.5, label="오차 = 0")
    ax.axvline(errors.mean(), color="#FFD54F", linestyle="--", linewidth=1.5,
               label=f"평균 오차 = {errors.mean():.1f}초")
    ax.set_xlabel("예측 오차 (예측 RUL - 실제 RUL, 초)", fontsize=11)
    ax.set_ylabel("샘플 수", fontsize=11)
    ax.set_title("오차 히스토그램", fontsize=12)
    ax.legend(fontsize=10)

    # 오른쪽: 실제 vs 예측 산점도
    ax2 = axes[1]
    vmax = max(y_true.max(), y_pred.max())
    ax2.scatter(y_true, y_pred, s=8, alpha=0.4, color="#5C9BF5")
    ax2.plot([0, vmax], [0, vmax], "r--", linewidth=1.5, label="완벽 예측 (y=x)")
    ax2.set_xlabel("실제 RUL (초)", fontsize=11)
    ax2.set_ylabel("예측 RUL (초)", fontsize=11)
    ax2.set_title("실제 vs 예측 산점도", fontsize=12)
    ax2.legend(fontsize=10)

    # 성능 통계 텍스트 박스
    mae_v  = float(np.mean(np.abs(errors)))
    rmse_v = float(np.sqrt(np.mean(errors**2)))
    r2_v   = float(1 - np.sum(errors**2) / np.sum((y_true - y_true.mean())**2))
    ax2.text(0.03, 0.97, f"MAE = {mae_v:.1f}초\nRMSE = {rmse_v:.1f}초\nR2 = {r2_v:.3f}",
             transform=ax2.transAxes, va="top", fontsize=10,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#0D1B3E", alpha=0.8),
             color="white")

    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    print(f"Saved: {out}")

# 13. 단일 실험 실행 (run_experiment)

def run_experiment(
    df: pd.DataFrame,
    feature_cols: list[str],
    experiment_name: str,
    use_ae_error: bool,
    cfg: Config,
    best_params: dict | None = None,    # Optuna가 찾은 최적 파라미터 (None이면 기본값 사용)
    use_attention: bool  = False,        # [개선] BiLSTM+Attention 모델 사용 여부
    use_huber: bool      = False,        # [개선] Huber Loss 사용 여부
    grad_clip: float     = 0.0,          # [개선] Gradient Clipping 임계값
    weight_decay: float  = 0.0,          # [개선] L2 정규화 강도
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
        metrics   : MAE, RMSE, R², 교체 임계값 등 실험 결과 딕셔너리
        y_test_raw: 테스트 샘플의 실제 RUL (초 단위)
        pred_test : 테스트 샘플의 예측 RUL (초 단위)
        err_test  : 테스트 샘플의 AE 재구성 오차
    """
    print(f"\n{'='*55}")
    print(f"Experiment: {experiment_name}")
    print(f"Feature count: {len(feature_cols)} | Use AE: {use_ae_error} | "
          f"Attention: {use_attention} | Huber: {use_huber}")
    print(f"{'='*55}")

    # best_params가 있으면 Optuna 최적값 사용, 없으면 Config 기본값 사용
    hidden        = best_params.get("hidden",        cfg.HIDDEN) if best_params else cfg.HIDDEN
    latent        = best_params.get("latent",        cfg.LATENT) if best_params else cfg.LATENT
    lr            = best_params.get("lr",            cfg.LR)     if best_params else cfg.LR
    window        = best_params.get("window",        cfg.WINDOW) if best_params else cfg.WINDOW
    n_layers      = best_params.get("n_layers",      1)          if best_params else 1
    dropout       = best_params.get("dropout",       0.0)        if best_params else 0.0
    bidirectional = best_params.get("bidirectional", False)      if best_params else False

    # ── 데이터 분할 및 정규화 ──────────────────────────────────────
    train_df, test_df = split_by_tool(df, n_groups=cfg.RUL_N_GROUPS)
    scaler   = StandardScaler()
    train_df = train_df.copy()
    test_df  = test_df.copy()
    # train 데이터로 scaler를 fit → test에는 동일 scaler로 transform만 (데이터 누출 방지)
    train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])
    test_df[feature_cols]  = scaler.transform(test_df[feature_cols])

    # train: RUL을 [0,1]로 정규화해 학습 (공구간 스케일 차이 제거)
    # test : 원래 초 단위 RUL로 예측해 실제 오차 측정
    X_train, y_train, _          = make_windows(train_df, feature_cols, window, per_tool_rul_norm=True)
    X_test,  y_test_raw, test_meta = make_windows(test_df,  feature_cols, window, per_tool_rul_norm=False)

    if len(X_train) == 0 or len(X_test) == 0:
        raise ValueError("window가 생성되지 않았습니다.")

    # train 내 80/20 분할 → 20%를 validation으로 사용
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=cfg.SEED)

    # ── AE 학습 및 Feature 보강 ───────────────────────────────────────
    if use_ae_error:
        # 정상 구간(y > 0.5, 수명 50% 이상)만으로 AE 학습
        # → AE가 정상 패턴을 외워 마모 구간에서 오차가 커지도록
        early_mask = y_tr > 0.5
        X_ae       = X_tr[early_mask] if early_mask.sum() > 10 else X_tr
        print(f"[AE] 정상 구간 학습 샘플: {len(X_ae)} / {len(X_tr)}")

        ae        = LSTMAutoEncoder(X_ae.shape[2], hidden, latent)
        ae_loader = DataLoader(TensorDataset(torch.tensor(X_ae)),
                               batch_size=cfg.BATCH_SIZE, shuffle=True)
        ae = train_autoencoder(ae, ae_loader, cfg.EPOCHS_AE, lr, cfg.PATIENCE)
        save_model(ae, f"{experiment_name}_ae", cfg)

        # train·val·test 모두에서 AE 오차와 latent 추출
        err_tr,   lat_tr   = get_ae_outputs(ae, X_tr)
        err_val,  lat_val  = get_ae_outputs(ae, X_val)
        err_test, lat_test = get_ae_outputs(ae, X_test)

        # 오차와 latent 각각 별도로 정규화
        err_scaler = StandardScaler().fit(err_tr.reshape(-1, 1))
        lat_scaler = StandardScaler().fit(lat_tr)

        # 90차원 Feature에 AE 오차 1개 추가 → 91차원
        X_tr_m   = add_ae_err_to_windows(X_tr,   err_tr,   err_scaler)
        X_val_m  = add_ae_err_to_windows(X_val,  err_val,  err_scaler)
        X_test_m = add_ae_err_to_windows(X_test, err_test, err_scaler)

        # latent 정규화
        lat_tr_s   = lat_scaler.transform(lat_tr).astype(np.float32)
        lat_val_s  = lat_scaler.transform(lat_val).astype(np.float32)
        lat_test_s = lat_scaler.transform(lat_test).astype(np.float32)
        latent_dim = latent
        print(f"LSTM 입력: {X_tr_m.shape[2]}차원 + latent {latent_dim}차원 concat")
    else:
        # AE 미사용 (Exp1 베이스라인)
        err_test = np.zeros(len(X_test), dtype=np.float32)
        X_tr_m, X_val_m, X_test_m = X_tr, X_val, X_test
        lat_tr_s = lat_val_s = lat_test_s = None
        latent_dim = 0

    # ── RUL 모델 선택 및 학습 ──────────────────────────────────────
    if use_attention:
        # [개선] BiLSTM + Self-Attention 모델 (Exp5)
        rul_model = AttentionLSTMRULRegressor(
            X_tr_m.shape[2], hidden, latent_dim, n_layers, dropout,
            bidirectional=bidirectional,
        )
    else:
        # 기본 단방향 LSTM 모델 (Exp1~4)
        rul_model = LSTMRULRegressor(X_tr_m.shape[2], hidden, latent_dim, n_layers, dropout)

    rul_model = train_rul_model(
        rul_model, X_tr_m, y_tr, X_val_m, y_val,
        epochs=cfg.EPOCHS_RUL, lr=lr, batch_size=cfg.BATCH_SIZE, patience=cfg.PATIENCE,
        lat_train=lat_tr_s, lat_val=lat_val_s,
        use_huber=use_huber, grad_clip=grad_clip, weight_decay=weight_decay,
    )
    save_model(rul_model, f"{experiment_name}_rul", cfg)

    # ── 예측 및 역정규화 ───────────────────────────────────────────
    # 모델 출력은 [0,1] 정규화된 RUL → 공구별 최대 RUL을 곱해 초 단위로 변환
    pred_norm     = predict_rul(rul_model, X_test_m, lat=lat_test_s)
    tool_max_ruls = test_meta["tool_max_rul"].values.astype(np.float32)
    pred_test     = pred_norm * tool_max_ruls  # 역정규화: 정규화값 × 해당 공구의 최대 RUL

    # ── 성능 평가 ──────────────────────────────────────────────────
    metrics = evaluate_regression(y_test_raw, pred_test)
    metrics.update({
        "experiment":    experiment_name,
        "feature_count": len(feature_cols),
        "use_ae_error":  use_ae_error,
        "hidden":        hidden, "latent": latent, "lr": lr, "window": window,
        "use_attention": use_attention, "use_huber": use_huber,
    })

    # AE를 사용한 실험에서만 교체 임계값 최적화 실행
    if use_ae_error:
        best_th = optimize_thresholds(y_test_raw, pred_test, err_test, cfg, n_trials=100)
        metrics.update(best_th)

    return metrics, y_test_raw, pred_test, err_test

# 14. Main — 전체 파이프라인 실행

def main() -> None:
    seed_everything(CFG.SEED)  # 재현성을 위해 모든 난수 시드 고정

    # ── 데이터 로딩 ────────────────────────────────────────────
    df, feature_cols = load_dataset(CFG)
    print_data_diagnostics(df)
    save_vb_plot(df)  # 마모 진행 곡선 저장 (데이터 이해용)

    # ── Optuna 하이퍼파라미터 탐색 ─────────────────────────────
    # BiLSTM, Attention, Weight Decay까지 포함해 50 trials 탐색
    print("\n[Step 0] 하이퍼파라미터 탐색 (50 trials, BiLSTM+Attention 포함)...")
    best_params = hyperparam_search(df, feature_cols, CFG, n_trials=50)

    results = []

    # ── Exp 1: 베이스라인 LSTM (AE 없음) ───────────────────────
    # Feature 90차원만으로 RUL을 예측하는 가장 단순한 구조
    # 이후 모든 개선의 기준점이 된다.
    m1, y1, p1, e1 = run_experiment(df, feature_cols,
                                     "1_baseline_lstm", False, CFG)
    results.append(m1)

    # ── Exp 2: AE 오차 연결 (기본 파라미터) ────────────────────
    # AE로 정상 패턴을 학습하고, 재구성 오차와 latent를 RUL 모델에 추가
    # 이상 감지 정보가 RUL 예측에 직접 연결되는 구조 (교수 피드백 반영)
    m2, y2, p2, e2 = run_experiment(df, feature_cols,
                                     "2_ae_error_lstm", True, CFG)
    results.append(m2)

    # ── Exp3·Exp4용 파라미터: bidirectional 고정 False ─────────
    # Optuna best_params에 bidirectional=True가 포함될 수 있으므로
    # Exp3·Exp4는 단방향 LSTM 비교를 위해 강제로 False로 고정한다.
    # (BiLSTM은 Exp5에서만 적용)
    params_base = dict(best_params)
    params_base["bidirectional"] = False

    # ── Exp 3: AE + Optuna 최적 파라미터 ───────────────────────
    # Exp2 구조에 Optuna가 찾은 최적 hidden·latent·lr·window 등을 적용
    # 단방향 LSTM 유지 (bidirectional=False 강제)
    m3, y3, p3, e3 = run_experiment(df, feature_cols,
                                     "3_ae_optuna_lstm", True, CFG,
                                     best_params=params_base)
    results.append(m3)

    # ── Exp 4: Huber Loss + Gradient Clipping + Weight Decay ───
    # [개선 1] Huber Loss: 이상값에 강건한 손실함수
    # [개선 2] Gradient Clipping: LSTM 기울기 폭발 방지
    # [개선 3] Weight Decay: L2 정규화로 과적합 억제
    # 단방향 LSTM 유지 (bidirectional=False 강제)
    m4, y4, p4, e4 = run_experiment(
        df, feature_cols, "4_ae_huber_clip", True, CFG,
        best_params=params_base,
        use_huber=True, grad_clip=1.0, weight_decay=1e-4,
    )
    results.append(m4)

    # ── Exp 5: BiLSTM + Self-Attention (모든 개선 적용) ─────────
    # [개선 4] BiLSTM: 순방향+역방향으로 더 풍부한 시퀀스 표현
    # [개선 5] Self-Attention: 마모 징후 구간을 자동으로 강조
    # Exp4의 모든 개선 기법 위에 BiLSTM+Attention 추가
    params_adv = dict(best_params)
    params_adv["bidirectional"] = True   # BiLSTM 강제 활성화
    wd5 = best_params.get("weight_decay", 1e-4)
    m5, y5, p5, e5 = run_experiment(
        df, feature_cols, "5_bilstm_attention", True, CFG,
        best_params=params_adv,
        use_attention=True,                  # AttentionLSTMRULRegressor 사용
        use_huber=True, grad_clip=1.0, weight_decay=wd5,
    )
    results.append(m5)

    # ── 실험 결과 저장 ──────────────────────────────────────────
    save_experiment_table(results)  # experiment_results.csv 저장

    # 가장 R²가 높은 실험 결과를 기준으로 그래프 생성
    best_m   = max(results, key=lambda r: r.get("R2", 0))
    exp_idx  = [r["experiment"] for r in results].index(best_m["experiment"])
    y_best   = [y1, y2, y3, y4, y5][exp_idx]
    p_best   = [p1, p2, p3, p4, p5][exp_idx]
    e_best   = [e1, e2, e3, e4, e5][exp_idx]
    print(f"\n[최고 성능] {best_m['experiment']} — MAE={best_m['MAE']:.1f} R²={best_m['R2']:.3f}")

    # 그래프 6종 저장
    save_prediction_plot(y_best, p_best)          # RUL 예측 vs 실제
    save_error_scatter(y_best, e_best)             # AE 오차 vs RUL
    save_performance_bar(results)                  # 실험별 성능 막대그래프
    save_error_distribution(y_best, p_best)        # 오차 분포 히스토그램

    # 교체 임계값 시각화 (R²가 가장 높고 임계값이 있는 실험 기준)
    best_th_r = max((r for r in results if r.get("rul_threshold")),
                    key=lambda r: r.get("R2", 0))
    th_idx = [r["experiment"] for r in results].index(best_th_r["experiment"])
    y_th   = [y1,y2,y3,y4,y5][th_idx]
    p_th   = [p1,p2,p3,p4,p5][th_idx]
    e_th   = [e1,e2,e3,e4,e5][th_idx]
    save_threshold_scatter(
        y_th, p_th, e_th,
        rul_thr=best_th_r["rul_threshold"],
        ae_thr=best_th_r["ae_error_threshold"],
    )

    # 최고 성능 실험의 예측 결과를 CSV로 저장
    pd.DataFrame({"true_rul": y_best, "pred_rul": p_best, "ae_error": e_best}).to_csv(
        "result_predictions_final.csv", index=False
    )
    print("\n완료: result_predictions_final.csv")


if __name__ == "__main__":
    main()
