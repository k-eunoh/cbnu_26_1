# Windows OS — System

> Windows Server 시스템 관리 문서

## 사용자 관리 (PowerShell)

```powershell
# 로컬 사용자 생성
New-LocalUser -Name "username" `
  -Password (ConvertTo-SecureString "P@ssw0rd" -AsPlainText -Force)
Add-LocalGroupMember -Group "Administrators" -Member "username"

# AD 사용자 생성
New-ADUser -Name "홍길동" -SamAccountName "honggd" `
  -UserPrincipalName "honggd@lab.local" -Enabled $true
```

## 서비스 관리

```powershell
Get-Service | Where-Object Status -eq 'Running'
Start-Service -Name "wuauserv"
Stop-Service -Name "wuauserv"
Set-Service -Name "wuauserv" -StartupType Automatic
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd3814aa8f4cbe95a55d07a)
