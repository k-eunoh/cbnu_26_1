# 🪟 Windows OS

> Windows Server 기술문서 — 네트워크, 시스템, 서비스

---

## 📂 하위 문서

| 폴더 | 설명 |
|------|------|
| [Network](./Network/) | IP 설정, DNS, DHCP, 방화벽, 네트워크 어댑터 |
| [System](./System/) | AD, 사용자 관리, 레지스트리, 이벤트 로그 |
| [Service](./Service/) | IIS, RDP, FTP, File Server, Hyper-V |

---

## 자주 사용하는 PowerShell

```powershell
# IP 설정
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.1.10 -PrefixLength 24 -DefaultGateway 192.168.1.1
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 8.8.8.8

# 서비스 관리
Get-Service | Where-Object Status -eq 'Running'
Start-Service -Name <ServiceName>
Stop-Service -Name <ServiceName>

# 방화벽 규칙
New-NetFirewallRule -DisplayName "Allow RDP" -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow
Get-NetFirewallRule | Where-Object Enabled -eq True

# 사용자 관리
New-LocalUser -Name "username" -Password (ConvertTo-SecureString "P@ssw0rd" -AsPlainText -Force)
Add-LocalGroupMember -Group "Administrators" -Member "username"
```

---

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381fc8217ca099cea8559)
