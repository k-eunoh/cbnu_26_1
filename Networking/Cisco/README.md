# Cisco

> Cisco 네트워크 장비 설정 기술문서 — IOS / IOS-XE

---

## 📂 하위 문서

| 폴더 | 설명 |
|------|------|
| [Basic](./Basic/) | 초기 설정, 기본 명령어, 인터페이스 |
| [Layer2](./Layer2/) | VLAN, STP, EtherChannel, VTP |
| [Layer3](./Layer3/) | 라우팅 (OSPF, EIGRP, BGP), VLAN 간 라우팅 |
| [Network_Services](./Network_Services/) | DHCP, NAT, VPN, ACL, QoS |
| [EEM](./EEM/) | Embedded Event Manager 자동화 |

---

## 주요 프로토콜 요약

### Layer 2
| 프로토콜 | 역할 |
|----------|------|
| **VLAN** | 논리적 네트워크 분리 |
| **STP/RSTP** | 루프 방지 |
| **EtherChannel (LACP/PAgP)** | 링크 집선, 대역폭 증가 |
| **VTP** | VLAN 정보 자동 전파 |

### Layer 3
| 프로토콜 | 역할 |
|----------|------|
| **OSPF** | 링크 상태 기반 내부 라우팅 |
| **EIGRP** | Cisco 전용 하이브리드 라우팅 |
| **BGP** | 외부 라우팅 (ISP 연동) |
| **HSRP/VRRP** | 게이트웨이 이중화 |

### Network Services
| 서비스 | 역할 |
|--------|------|
| **DHCP** | IP 자동 할당 |
| **NAT/PAT** | 사설 IP ↔ 공인 IP 변환 |
| **ACL** | 트래픽 필터링 |
| **IKEv2 VPN** | 사이트 간 암호화 터널 |

---

> 🔗 [Notion 원본](https://www.notion.so/9dddaeb3d3264af888b5245707383991)
