# Proxmox VE

> Proxmox Virtual Environment — 오픈소스 가상화 플랫폼

## 특징

- KVM 기반 완전 가상화 + LXC 컨테이너 지원
- 웹 UI 기반 관리 (포트 8006)
- 클러스터링 내장 지원
- 무료 오픈소스

## 설치 후 기본 설정

```bash
# 무료 저장소로 변경
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  > /etc/apt/sources.list.d/pve-install-repo.list
apt update && apt upgrade -y
```

## 네트워크 브리지 설정 (/etc/network/interfaces)

```
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
```

## ESXi vs Proxmox 비교

| 항목 | VMware ESXi | Proxmox VE |
|------|-------------|------------|
| 라이선스 | 상용 | 오픈소스 |
| VM 엔진 | 독자 | KVM |
| 컨테이너 | 미지원 | LXC 지원 |
| 관리 UI | vSphere Client | Web UI |
| 주요 용도 | 엔터프라이즈 | SMB / 홈랩 / 교육 |

> 🔗 [Notion 원본](https://www.notion.so/22b5e60c6bd380a8a589d5202c2fd4cb)
