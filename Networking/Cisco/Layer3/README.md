# Cisco Layer 3

> 라우팅 프로토콜 (OSPF, EIGRP), VLAN 간 라우팅, 게이트웨이 이중화

## VLAN 간 라우팅 (Router-on-a-Stick)

```
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0
```

## OSPF

```
router ospf 1
 router-id 1.1.1.1
 network 192.168.10.0 0.0.0.255 area 0
 network 192.168.20.0 0.0.0.255 area 0
 passive-interface GigabitEthernet0/0
```

## HSRP (게이트웨이 이중화)

```
interface GigabitEthernet0/0
 standby 1 ip 192.168.10.254
 standby 1 priority 110
 standby 1 preempt
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd3810cbb4fd66e23fe01c5)
