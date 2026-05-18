# PowerShell Automation

> Windows 환경 PowerShell 자동화 스크립트

## 기본 구조

```powershell
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $Message"
}

Write-Log "스크립트 시작"
```

## 주요 활용

- Windows Server 구성 자동화
- AD 사용자 일괄 관리
- 서비스 모니터링 및 재시작
- 방화벽 규칙 일괄 설정

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381e08d89ff2b4c1bc9b4)
