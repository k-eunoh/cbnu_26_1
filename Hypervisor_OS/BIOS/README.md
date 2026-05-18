# BIOS Configuration

> 서버 BIOS 설정 — 가상화 활성화 및 최적화

## 가상화 필수 설정

| 설정 항목 | 권장값 | 설명 |
|-----------|--------|------|
| Intel VT-x / AMD-V | **Enable** | CPU 가상화 기술 |
| VT-d / AMD-Vi | **Enable** | I/O 가상화 (PCI 패스스루) |
| Hyper-Threading | Enable | 논리 코어 수 증가 |
| Secure Boot | Disable | 일부 하이퍼바이저 설치 시 |
| C-State / EIST | Disable | 서버 환경 절전 비활성화 권장 |

## 벤더별 BIOS 진입 키

| 벤더 | 진입 키 |
|------|---------|
| HP/HPE | F9 |
| Dell | F2 |
| Lenovo | F1 |
| 일반 PC | Del / F2 |

> 🔗 [Notion 원본](https://www.notion.so/22b5e60c6bd380908d9dfd820731e953)
