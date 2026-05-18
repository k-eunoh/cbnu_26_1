# Windows OS — Service

> Windows Server 주요 서비스 설정 문서

## IIS (웹 서버)

```powershell
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Start-Service -Name W3SVC
```

## Active Directory

```powershell
Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
Install-ADDSForest -DomainName "lab.local"
```

## DNS 서버

```powershell
Install-WindowsFeature DNS -IncludeManagementTools
Add-DnsServerPrimaryZone -Name "lab.local" -ZoneFile "lab.local.dns"
Add-DnsServerResourceRecordA -ZoneName "lab.local" `
  -Name "server1" -IPv4Address "192.168.1.10"
```

## DHCP 서버

```powershell
Install-WindowsFeature DHCP -IncludeManagementTools
Add-DhcpServerV4Scope -Name "LAN" `
  -StartRange 192.168.1.100 -EndRange 192.168.1.200 `
  -SubnetMask 255.255.255.0
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381d699fed5d27af264fa)
