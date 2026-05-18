# Flask REST Stateless API

> Flask를 이용한 Stateless REST API 설계 및 구현 문서

---

## 📖 개요 — REST API란?

- **API** = Application Programming Interface
- 다른 애플리케이션이 우리 애플리케이션과 소통하게 하는 Software Interface
- **REST** = Representational State Transfer
  - 서버-클라이언트 간 리소스 표현을 JSON/XML로 전송
  - 각 요청은 작업 완료에 필요한 모든 정보를 포함 (Self-Contained)
- REST API는 HTTP 메서드를 사용해 애플리케이션 간 정보를 검색·전송

---

## 🔄 HTTP 메서드

| 메서드 | 동작 |
|--------|------|
| `GET` | 지정된 리소스 조회 (Read-only) |
| `POST` | 데이터 제출 / 새 리소스 생성 |
| `PUT` | 기존 리소스 업데이트 (전체 교체) |
| `DELETE` | 지정된 리소스 삭제 |

---

## ✅ RESTful API 6가지 제약 조건

| 제약 조건 | 설명 |
|-----------|------|
| **클라이언트-서버** | 클라이언트와 서버는 독립적. 요청-응답으로 상호작용 |
| **Stateless** | 서버는 이전 요청 상태를 저장하지 않음 |
| **캐시 가능** | 응답에 버전 번호 포함 → 캐시 재사용 여부 결정 |
| **균일한 인터페이스** | URI 식별, 표현을 통한 조작, 자체 설명 메시지, HATEOAS |
| **계층화된 시스템** | API/DB/로드밸런서를 다른 서버에 분리 배포 가능 |
| **Code on Demand** | (선택) 서버가 실행 가능한 코드를 클라이언트에 전송 |

---

## 📂 하위 문서 목록

| 문서 | 설명 |
|------|------|
| [Flask_Introduction](./Flask_Introduction.md) | Flask 기초 및 REST API 개념 |
| [Flask_API_Routing_Configuration](./Flask_API_Routing_Configuration.md) | URL 라우팅 설정 |
| [Flask_API_Render_Template_Configuration](./Flask_API_Render_Template_Configuration.md) | 템플릿 렌더링 |
| [Flask_API_HTTP_Methods_Configuration](./Flask_API_HTTP_Methods_Configuration.md) | HTTP 메서드 처리 |
| [Flask_API_Http_Status_Code](./Flask_API_Http_Status_Code.md) | HTTP 상태 코드 |
| [Flask_API_Abort_Configuration](./Flask_API_Abort_Configuration.md) | 에러 처리 (Abort) |
| [Flask_API_HTTPS_Configuration](./Flask_API_HTTPS_Configuration.md) | HTTPS 설정 |
| [Flask_API_Logging_Configuration](./Flask_API_Logging_Configuration.md) | 로깅 설정 |
| [Flask_API_Jsonify](./Flask_API_Jsonify_How_to_Use_Configuration.md) | Jsonify 사용법 |
| [Flask_API_Parameter_Configuration](./Flask_API_Parameter_Configuration.md) | 파라미터 처리 |
| [Flask_API_Disabled_Ascii](./Flask_API_Disabled_Acscii.md) | ASCII 비활성화 (한글 처리) |
| [Flask_API_Requests](./Flask_API_Requests.md) | Requests 라이브러리 |
| [Flask_Jinja2_Configuration](./Flask_Jinja2_Configuration.md) | Jinja2 템플릿 엔진 |

---

## 🔗 참고

- [Notion 원본 문서](https://www.notion.so/fff5e60c6bd3818483e5c3fbb15cdb95)
- 상위: [API](../README.md) > [Docs](../../README.md)
