# Python Automation

> Python을 활용한 네트워크 인프라 자동화

## 주요 라이브러리

| 라이브러리 | 용도 |
|-----------|------|
| `netmiko` | SSH 기반 네트워크 장비 제어 |
| `paramiko` | SSH 클라이언트 |
| `napalm` | 멀티벤더 네트워크 추상화 |
| `requests` | REST API 호출 |
| `nornir` | 병렬 네트워크 자동화 프레임워크 |

## 기본 패턴 (Netmiko)

```python
from netmiko import ConnectHandler

device = {
    'device_type': 'cisco_ios',
    'host': '192.168.1.1',
    'username': 'admin',
    'password': 'password',
}

with ConnectHandler(**device) as conn:
    output = conn.send_command('show ip interface brief')
    print(output)
```

## 다중 장비 자동화 패턴

```python
devices = [
    {'device_type': 'cisco_ios', 'host': '10.0.0.1', ...},
    {'device_type': 'cisco_ios', 'host': '10.0.0.2', ...},
]

for device in devices:
    with ConnectHandler(**device) as conn:
        output = conn.send_command('show version')
        print(f"[{device['host']}] {output}")
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd38167b933ec69d9ce90af)
