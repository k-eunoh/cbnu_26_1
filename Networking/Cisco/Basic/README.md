# Cisco Basic

> Cisco IOS 초기 설정 및 기본 명령어

## 초기 설정

```
enable
configure terminal

hostname SW1
enable secret cisco123
service password-encryption

line console 0
 password cisco
 login
line vty 0 4
 password cisco
 login
 transport input ssh

ip domain-name lab.local
crypto key generate rsa modulus 2048
ip ssh version 2

banner motd #Authorized Access Only#
end
write memory
```

## 자주 쓰는 Show 명령어

```
show version
show ip interface brief
show interfaces status
show running-config
show mac address-table
show arp
show cdp neighbors
```

> 🔗 [Notion 원본](https://www.notion.so/39dee1296d44413386ea3639cb67f8ab)
