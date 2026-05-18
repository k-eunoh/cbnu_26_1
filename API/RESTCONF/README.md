# RESTCONF

> RFC 8040 기반 RESTCONF 프로토콜을 이용한 네트워크 장비 제어

## 개요

- HTTP 기반으로 YANG 모델 데이터를 읽고 쓰는 프로토콜
- Cisco IOS-XE 16.6+ 지원
- JSON / XML 데이터 포맷 지원

## RESTCONF 활성화 (Cisco IOS-XE)

```
ip http server
ip http secure-server
restconf
```

## 기본 사용법 (Python requests)

```python
import requests
import json

url = "https://192.168.1.1/restconf/data/ietf-interfaces:interfaces"
headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

response = requests.get(
    url,
    headers=headers,
    auth=("admin", "password"),
    verify=False
)

data = response.json()
print(json.dumps(data, indent=2))
```

## 주요 RESTCONF URI

| 동작 | Method | URI |
|------|--------|-----|
| 인터페이스 조회 | GET | `/restconf/data/ietf-interfaces:interfaces` |
| 인터페이스 설정 | PUT | `/restconf/data/ietf-interfaces:interfaces/interface={name}` |
| 라우팅 테이블 조회 | GET | `/restconf/data/ietf-routing:routing` |
| Hostname 변경 | PATCH | `/restconf/data/Cisco-IOS-XE-native:native/hostname` |

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381988895fbfca7631e69)
