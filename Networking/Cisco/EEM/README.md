# Cisco EEM (Networking)

> Cisco 장비에서 EEM을 활용한 네트워크 이벤트 자동화

## 주요 이벤트 트리거

| 트리거 | 설명 |
|--------|------|
| `event syslog` | syslog 메시지 패턴 감지 |
| `event snmp` | SNMP OID 값 임계치 |
| `event timer` | 타이머 기반 실행 |
| `event cli` | CLI 명령어 입력 감지 |

## 예시 — 인터페이스 복구 자동화

```
event manager applet INTF_RECOVERY
 event syslog pattern "Interface GigabitEthernet.*down"
 action 1.0 cli command "enable"
 action 2.0 cli command "configure terminal"
 action 3.0 cli command "interface GigabitEthernet0/1"
 action 4.0 cli command "shutdown"
 action 5.0 wait 3
 action 6.0 cli command "no shutdown"
 action 7.0 syslog msg "인터페이스 자동 복구 완료"
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381f89d95f294a5f29967)
