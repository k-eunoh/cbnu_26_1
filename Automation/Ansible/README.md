# Ansible

> 에이전트리스 자동화 도구 Ansible을 활용한 인프라 자동화 문서

---

## 📂 하위 문서

| 문서 | 설명 |
|------|------|
| [Global_Configuration](./Global_Configuration.md) | Ansible 전역 설정 (ansible.cfg, inventory) |
| [Linux_Ansible](./Linux_Ansible.md) | Linux 서버 자동화 Playbook |
| [Windows_Ansible](./Windows_Ansible.md) | Windows Server 자동화 Playbook |
| [Cisco_Ansible](./Cisco_Ansible.md) | Cisco 네트워크 장비 자동화 |
| [API_Ansible](./API_Ansible.md) | REST API 연동 자동화 |

---

## 개요

Ansible은 SSH/WinRM 기반 에이전트리스 자동화 도구로, YAML 형식의 Playbook을 통해 다수의 호스트를 일괄 관리한다.

### 기본 구조

```
ansible/
├── ansible.cfg          # 전역 설정
├── inventory/
│   └── hosts            # 관리 대상 호스트 목록
└── playbooks/
    ├── site.yml         # 메인 Playbook
    └── roles/           # Role 기반 모듈화
```

### 주요 모듈

| 모듈 | 대상 | 용도 |
|------|------|------|
| `ansible.builtin.shell` | Linux | 쉘 명령 실행 |
| `ansible.windows.win_command` | Windows | 윈도우 명령 실행 |
| `cisco.ios.ios_command` | Cisco IOS | 장비 명령 실행 |
| `cisco.ios.ios_config` | Cisco IOS | 장비 설정 변경 |
| `ansible.builtin.uri` | All | REST API 호출 |

---

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381a39a88eda565d73804)
