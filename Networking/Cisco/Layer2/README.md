# Cisco Layer 2

> VLAN, STP, EtherChannel, VTP 설정

## VLAN 설정

```
vlan 10
 name Management
vlan 20
 name Server
vlan 30
 name User

interface GigabitEthernet0/1
 switchport mode access
 switchport access vlan 10

interface GigabitEthernet0/24
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
```

## STP (Rapid-PVST)

```
spanning-tree mode rapid-pvst
spanning-tree vlan 10 root primary
spanning-tree vlan 20 root secondary
```

## EtherChannel (LACP)

```
interface range GigabitEthernet0/1-2
 channel-group 1 mode active
interface Port-channel1
 switchport mode trunk
```

## VTP

```
vtp mode server
vtp domain LAB
vtp password cisco123
vtp version 2
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381b5aa06e9659901724c)
