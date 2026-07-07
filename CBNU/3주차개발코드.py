import argparse
import ipaddress
from pathlib import Path

import numpy as np
import pandas as pd


# ==============================
# 유틸 함수
# ==============================
def is_valid_ip(value):
    if pd.isna(value):
        return False
    try:
        ipaddress.ip_address(str(value).strip())
        return True
    except ValueError:
        return False


def is_valid_port(value):
    if pd.isna(value):
        return False
    try:
        port = int(float(value))
        return 0 <= port <= 65535
    except (TypeError, ValueError):
        return False


def is_private_ip(value):
    if not is_valid_ip(value):
        return False
    return ipaddress.ip_address(str(value).strip()).is_private


# ==============================
# 핵심 전처리 함수
# ==============================
def build_traffic_dataset(input_path: str, output_clean: str, output_model: str):
    df = pd.read_csv(input_path)
    print(f"[최초 데이터 로드] 총 레코드 수: {len(df)}건")
    print(f"[원본 컬럼 수] {df.shape[1]}개\n")

    # 0. 구조 정리
    # 불필요한 Unnamed / 빈 컬럼 제거
    removable_cols = [
        c for c in df.columns
        if str(c).startswith("Unnamed:") or str(c).strip() in ["]", "", " "]
    ]
    df = df.drop(columns=removable_cols, errors="ignore")

    # 중복 의미로 보이는 컬럼명 정리
    if "protocol.1" in df.columns and "protocol" in df.columns:
        same_ratio = (df["protocol"] == df["protocol.1"]).mean()
        print(f"[구조 정리] protocol / protocol.1 일치율: {same_ratio:.2%}")
        if same_ratio >= 0.99:
            df = df.drop(columns=["protocol.1"])
        else:
            df = df.rename(columns={"protocol.1": "protocol_dup"})

    # 문자열 공백 정리
    object_cols = df.select_dtypes(include="object").columns
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # 완전 공백 행 제거
    df = df.dropna(how="all")
    print(f"[구조 정리 후] 레코드 수: {len(df)}건, 컬럼 수: {df.shape[1]}개\n")

    df_clean = df.copy()

    # 1. 유일성 (중복 트래픽 제거)
    print("[1. 유일성 평가]")
    flow_keys = [
        col for col in ["type", "protocol", "sip", "sport", "dip", "dport", "state", "duration"]
        if col in df_clean.columns
    ]
    duplicates = df_clean.duplicated(subset=flow_keys, keep=False)
    print(f" - 중복 Flow 데이터 수: {duplicates.sum()}건 발견")
    df_clean = df_clean.drop_duplicates(subset=flow_keys, keep="first")
    print("중복 데이터 제거 완료\n")

    # 2. 완전성 (핵심 컬럼 결측치 제거)
    print("[2. 완전성 평가]")
    critical_cols = [
        col for col in ["sip", "dip", "sport", "dport", "protocol", "sent_data", "rcvd_data", "duration"]
        if col in df_clean.columns
    ]
    missing_count = df_clean[critical_cols].isnull().any(axis=1).sum()
    print(f" - 핵심 컬럼 결측치 수: {missing_count}건 발견")
    df_clean = df_clean.dropna(subset=critical_cols)
    print("핵심 결측치 제거 완료\n")

    # 3. 유효성 (IP, Port, 숫자 범위 검증)
    print("[3. 유효성 평가]")
    invalid_ip = ~df_clean["sip"].apply(is_valid_ip) | ~df_clean["dip"].apply(is_valid_ip)
    invalid_port = ~df_clean["sport"].apply(is_valid_port) | ~df_clean["dport"].apply(is_valid_port)

    numeric_nonnegative_cols = [
        col for col in ["sent_data", "sent_pk", "rcvd_data", "rcvd_pk", "duration"]
        if col in df_clean.columns
    ]
    invalid_numeric = pd.Series(False, index=df_clean.index)
    for col in numeric_nonnegative_cols:
        invalid_numeric = invalid_numeric | (pd.to_numeric(df_clean[col], errors="coerce") < 0)

    print(f" - 비정상 IP 데이터 수: {invalid_ip.sum()}건 발견")
    print(f" - 비정상 Port 데이터 수: {invalid_port.sum()}건 발견")
    print(f" - 음수 트래픽/패킷/지속시간 데이터 수: {invalid_numeric.sum()}건 발견")

    df_clean = df_clean[~invalid_ip]
    df_clean = df_clean[~invalid_port]
    df_clean = df_clean[~invalid_numeric]
    print("유효성 위배 데이터 제거 완료\n")

    # 4. 일관성 (논리 모순 제거)
    print("[4. 일관성 평가]")
    inconsistent = pd.Series(False, index=df_clean.index)

    # 패킷 수가 0인데 바이트 수가 존재하거나, 반대로 패킷 수는 있는데 바이트 수가 음수가 되는 일은 비정상
    if {"sent_data", "sent_pk"}.issubset(df_clean.columns):
        inconsistent = inconsistent | ((df_clean["sent_pk"] == 0) & (df_clean["sent_data"] > 0))
    if {"rcvd_data", "rcvd_pk"}.issubset(df_clean.columns):
        inconsistent = inconsistent | ((df_clean["rcvd_pk"] == 0) & (df_clean["rcvd_data"] > 0))

    # state가 차단(deny/drop/reset 등)인데도 과도한 데이터 전송이 있다면 점검 대상
    if "state" in df_clean.columns:
        blocked_states = {"DROP", "DENY", "RESET", "BLOCK", "REJECT"}
        inconsistent_state = (
            df_clean["state"].astype(str).str.upper().isin(blocked_states)
            & ((df_clean.get("sent_data", 0) > 0) | (df_clean.get("rcvd_data", 0) > 0))
        )
        inconsistent = inconsistent | inconsistent_state

    print(f" - 논리적 모순 데이터 수: {inconsistent.sum()}건 발견")
    df_clean = df_clean[~inconsistent]
    print("일관성 위배 데이터 제거 완료\n")

    # 5. 정확성 (이상치 완화)
    print("[5. 정확성 평가]")
    # 99.5 분위수 기반 극단 이상치 상한 설정
    outlier_cols = [col for col in ["sent_data", "rcvd_data", "duration"] if col in df_clean.columns]
    outlier_mask = pd.Series(False, index=df_clean.index)
    caps = {}
    for col in outlier_cols:
        upper = df_clean[col].quantile(0.995)
        caps[col] = upper
        outlier_mask = outlier_mask | (df_clean[col] > upper)

    print(f" - 극단 이상치 데이터 수(상위 0.5% 기준): {outlier_mask.sum()}건 발견")
    # 완전 삭제 대신 clip 처리
    for col, upper in caps.items():
        df_clean[col] = df_clean[col].clip(upper=upper)
    print("이상치 완화(clip) 완료\n")

    # 6. 파생변수 생성 (모델링용 데이터셋)
    print("[6. 파생변수 생성]")
    df_model = df_clean.copy()

    if {"sent_data", "rcvd_data"}.issubset(df_model.columns):
        df_model["total_bytes"] = df_model["sent_data"] + df_model["rcvd_data"]
    if {"sent_pk", "rcvd_pk"}.issubset(df_model.columns):
        df_model["total_packets"] = df_model["sent_pk"] + df_model["rcvd_pk"]
    if {"total_bytes", "total_packets"}.issubset(df_model.columns):
        df_model["bytes_per_packet"] = np.where(
            df_model["total_packets"] > 0,
            df_model["total_bytes"] / df_model["total_packets"],
            0,
        )
    if {"total_bytes", "duration"}.issubset(df_model.columns):
        df_model["bytes_per_second"] = np.where(
            df_model["duration"] > 0,
            df_model["total_bytes"] / df_model["duration"],
            0,
        )
    if {"sip", "dip"}.issubset(df_model.columns):
        df_model["is_private_to_private"] = (
            df_model["sip"].apply(is_private_ip) & df_model["dip"].apply(is_private_ip)
        ).astype(int)

    # 범주형 결측 보정
    fill_unknown_cols = [
        col for col in ["service", "state", "reason", "tcp_flag", "in_zone", "out_zone"]
        if col in df_model.columns
    ]
    for col in fill_unknown_cols:
        df_model[col] = df_model[col].fillna("Unknown")

    print("파생변수 생성 완료\n")

    # 결과 저장
    Path(output_clean).parent.mkdir(parents=True, exist_ok=True)
    Path(output_model).parent.mkdir(parents=True, exist_ok=True)

    df_clean.to_csv(output_clean, index=False, encoding="utf-8-sig")
    df_model.to_csv(output_model, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("[최종 결과]")
    print(f" - 최초 원본 데이터: {len(df)}건")
    print(f" - 정제 데이터셋: {len(df_clean)}건")
    print(f" - 모델링용 데이터셋: {len(df_model)}건")
    print(f" - 정제 파일 저장 경로: {output_clean}")
    print(f" - 모델링 파일 저장 경로: {output_model}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traffic Sample CSV를 정제하고 모델링용 데이터셋을 생성합니다.")
    parser.add_argument("--input", default="/Users/kimeunoh/Downloads/trafficsample.csv", help="원본 CSV 경로")
    parser.add_argument("--output_clean", default="/Users/kimeunoh/Downloads/trafficsample_clean.csv", help="정제 데이터 저장 경로")
    parser.add_argument("--output_model", default="/Users/kimeunoh/Downloads/trafficsample_model_ready.csv", help="모델링용 데이터 저장 경로")
    args = parser.parse_args()

    build_traffic_dataset(args.input, args.output_clean, args.output_model)
