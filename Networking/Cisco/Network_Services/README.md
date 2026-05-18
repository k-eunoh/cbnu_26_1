# Cisco Network Services

> DHCP, NAT, ACL, IKEv2 VPN 설정

## DHCP

```
ip dhcp pool VLAN10
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
 dns-server 8.8.8.8
 lease 7
ip dhcp excluded-address 192.168.10.1 192.168.10.10
```

## NAT (PAT)

```
ip nat inside source list 1 interface GigabitEthernet0/1 overload
access-list 1 permit 192.168.0.0 0.0.255.255

interface GigabitEthernet0/0
 ip nat inside
interface GigabitEthernet0/1
 ip nat outside
```

## ACL

```
ip access-list extended BLOCK_TELNET
 deny   tcp any any eq 23
 permit ip any any

interface GigabitEthernet0/0
 ip access-group BLOCK_TELNET in
```

## IKEv2 VPN (Site-to-Site)

```
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14

crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
 mode tunnel
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381d8bdaae697e71657c9)
