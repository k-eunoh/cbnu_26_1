import os
import glob
import numpy as np
import pandas as pd
import librosa
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score
import joblib

# 1. 주파수 스펙트럼 추출 함수 정의
def mk_Frequency(y, sr):
    fft = np.fft.fft(y)
    magnitude = np.abs(fft)
    fre = np.linspace(0, sr, len(magnitude))
    
    haf_spectrum = magnitude[:int(len(magnitude)/2)]
    haf_fre = fre[:int(len(magnitude)/2)]
    return haf_spectrum, haf_fre

# 2. 데이터 경로 설정 및 특성 추출 (EDA 단계와 동일)
ok_path = 'FAN_sound_OK/*'
err_path = 'FAN_sound_error/*'

ok_files = glob.glob(ok_path)
err_files = glob.glob(err_path)

spectrum_mins, spectrum_maxs, mfcc_mins, mfcc_maxs, labels = [], [], [], [], []

print("데이터 특성 추출을 시작합니다...")
# (학생들에게는 이전에 작성한 반복문 코드가 이 자리에 들어간다고 설명해주시면 됩니다)
for path in ok_files:
    y, sr = librosa.load(path, sr=100)
    haf_spectrum, _ = mk_Frequency(y, sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_fft=2048, hop_length=512, n_mfcc=13)
    spectrum_mins.append(np.min(haf_spectrum)); spectrum_maxs.append(np.max(haf_spectrum))
    mfcc_mins.append(np.min(mfcc)); mfcc_maxs.append(np.max(mfcc))
    labels.append(0)

for path in err_files:
    y, sr = librosa.load(path, sr=100)
    haf_spectrum, _ = mk_Frequency(y, sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_fft=2048, hop_length=512, n_mfcc=13)
    spectrum_mins.append(np.min(haf_spectrum)); spectrum_maxs.append(np.max(haf_spectrum))
    mfcc_mins.append(np.min(mfcc)); mfcc_maxs.append(np.max(mfcc))
    labels.append(1)

df_sound = pd.DataFrame({
    'mfcc_min': mfcc_mins, 'mfcc_max': mfcc_maxs,
    'spectrum_min': spectrum_mins, 'spectrum_max': spectrum_maxs,
    'NG': labels,
    'filepath': ok_files + err_files
})

# 3. 데이터 분리 및 저장
feature_columns = ['mfcc_min', 'mfcc_max', 'spectrum_min', 'spectrum_max']

data = df_sound[feature_columns + ['filepath']]
target = df_sound['NG']

X_train, X_test, y_train, y_test = train_test_split(
    data, target, test_size=0.3, shuffle=True, stratify=target, random_state=34
)

# 파일 경로는 학습에 사용되지 않으므로 따로 분리합니다.
test_filepaths = X_test['filepath']
X_train = X_train.drop(columns=['filepath'])
X_test = X_test.drop(columns=['filepath'])

# 차후 평가 파일에서 사용하기 위해 테스트 데이터를 CSV로 저장합니다.
X_test.to_csv('X_test.csv', index=False)
y_test.to_csv('y_test.csv', index=False)
test_filepaths.to_csv('test_filepaths.csv', index=False)
print("테스트 데이터(X_test.csv, y_test.csv, test_filepaths.csv)를 성공적으로 저장했습니다.")

# 4. 모델링 및 학습
print("여러 모델을 학습하고 F1-Score 기준으로 비교합니다...")

models = {
    'DecisionTree_depth3': DecisionTreeClassifier(
        criterion='entropy',
        max_depth=3,
        random_state=0
    ),
    'DecisionTree_depth5': DecisionTreeClassifier(
        criterion='entropy',
        max_depth=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=0
    ),
    'DecisionTree_depth7': DecisionTreeClassifier(
        criterion='entropy',
        max_depth=7,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=0
    ),
    'RandomForest': RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        class_weight='balanced',
        random_state=0
    )
}

results = []
best_model = None
best_model_name = None
best_f1 = -1

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    results.append({
        'model': name,
        'accuracy': acc,
        'recall': recall,
        'precision': precision,
        'f1_score': f1
    })

    print(f"\n[{name}]")
    print(f"Accuracy : {acc:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"F1-Score : {f1:.4f}")

    if f1 > best_f1:
        best_f1 = f1
        best_model = model
        best_model_name = name

result_df = pd.DataFrame(results)
result_df.to_csv('model_comparison.csv', index=False)

joblib.dump(best_model, 'dtc_sound_model.pkl')

print("\n===================================")
print(f"최종 선택 모델: {best_model_name}")
print(f"최고 F1-Score: {best_f1:.4f}")
print("비교 결과는 model_comparison.csv에 저장되었습니다.")
print("최종 모델은 dtc_sound_model.pkl로 저장되었습니다.")
print("===================================")

# 5. 학습된 모델 저장 (.pkl 형식)
joblib.dump(Dtc, 'dtc_sound_model.pkl')
print("모델이 'dtc_sound_model.pkl' 이름으로 성공적으로 저장되었습니다!")