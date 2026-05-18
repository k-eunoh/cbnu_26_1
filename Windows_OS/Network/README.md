# Windows OS — Network

> Windows Server 네트워크 설정 문서

## PowerShell로 IP 설정

```powershell
New-NetIPAddress -InterfaceAlias "Ethernet" `
  -IPAddress 192.168.1.10 `
  -PrefixLength 24 `
  -DefaultGateway 192.168.1.1

Set-DnsClientServerAddress -InterfaceAlias "Ethernet" `
  -ServerAddresses 8.8.8.8, 8.8.4.4
```

## 방화벽 규칙

```powershell
New-NetFirewallRule -DisplayName "Allow RDP" `
  -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow

Get-NetFirewallRule | Where-Object Enabled -eq True
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd3818cb3fef23a8d308162)
