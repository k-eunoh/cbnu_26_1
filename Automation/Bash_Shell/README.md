# Bash Shell Script

> Linux 환경 Bash 자동화 스크립트

## 기본 구조

```bash
#!/bin/bash
set -e

TARGET_IP="192.168.1.1"
LOG_FILE="/var/log/script.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "스크립트 시작"
ping -c 3 "$TARGET_IP" && log "연결 성공" || log "연결 실패"
```

## 주요 활용

- 서버 모니터링 자동화
- 정기 백업 스크립트
- 네트워크 상태 점검
- 사용자/권한 일괄 관리

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381318c86c2fa0f9e63a6)
