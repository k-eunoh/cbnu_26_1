# EEM — Embedded Event Manager

> Cisco IOS 내장 자동화 엔진 — 이벤트 기반 자동 조치

## 기본 구조

```
event manager applet <이름>
 event <트리거 조건>
 action <번호> <동작>
```

## 예시 — 인터페이스 다운 감지 시 알림

```
event manager applet INTF_DOWN
 event syslog pattern "Interface.*down"
 action 1.0 syslog msg "인터페이스 다운 감지!"
 action 2.0 cli command "enable"
 action 3.0 cli command "show ip interface brief"
```

## 예시 — CPU 과부하 감지

```
event manager applet HIGH_CPU
 event snmp oid 1.3.6.1.4.1.9.9.109.1.1.1.1.3.1 get-type gt entry-val 80 poll-interval 5
 action 1.0 syslog msg "CPU 사용률 80% 초과!"
 action 2.0 cli command "show processes cpu sorted"
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd3818a8009dfcbf8991fdd)
