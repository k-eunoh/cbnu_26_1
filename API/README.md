# 📁 API

> Flask 및 RESTCONF를 활용한 REST API 개발 기술문서

---

## 📂 하위 문서

| 폴더 | 설명 |
|------|------|
| [Flask_REST_Stateless](./Flask_REST_Stateless/) | Flask 기반 Stateless REST API — 라우팅, HTTP 메서드, HTTPS, 로깅 등 |
| [Flask_REST_Stateful](./Flask_REST_Stateful/) | Flask 기반 Stateful REST API — 세션, 인증, DB 연동 |
| [RESTCONF](./RESTCONF/) | RESTCONF 프로토콜을 이용한 네트워크 장비 제어 |

---

## 핵심 개념

- REST API는 HTTP 프로토콜 기반으로 동작하며 GET / POST / PUT / DELETE 메서드를 사용
- **Stateless**: 각 요청이 독립적 — 서버가 이전 상태를 기억하지 않음
- **Stateful**: 세션/쿠키 등으로 클라이언트 상태를 서버가 유지
- **RESTCONF**: RFC 8040 기반, YANG 모델을 HTTP로 조작하는 네트워크 자동화 프로토콜

---

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381879a3bc022fb94047b)
