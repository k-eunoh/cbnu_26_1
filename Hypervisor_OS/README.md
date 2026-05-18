# 🔮 Hypervisor OS

> 가상화 플랫폼 기술문서 — VMware ESXi, Proxmox VE, BIOS 설정

---

## 📂 하위 문서

| 폴더 | 플랫폼 | 설명 |
|------|--------|------|
| [ESXI](./ESXI/) | VMware ESXi | 엔터프라이즈 하이퍼바이저 설정 및 운영 |
| [Proxmox](./Proxmox/) | Proxmox VE | 오픈소스 가상화 플랫폼 (KVM + LXC) |
| [BIOS](./BIOS/) | 하드웨어 BIOS | 서버 BIOS 가상화 옵션 설정 |

---

## 개념 비교

| 항목 | VMware ESXi | Proxmox VE |
|------|-------------|------------|
| 타입 | Type-1 Hypervisor | Type-1 Hypervisor |
| 라이선스 | 상용 (무료 버전 있음) | 오픈소스 (무료) |
| VM 엔진 | VMware 독자 | KVM |
| 컨테이너 | 미지원 | LXC 지원 |
| 관리 UI | vSphere Client | Web UI |
| 클러스터링 | vCenter 필요 | 내장 클러스터 |
| 주요 용도 | 엔터프라이즈 환경 | SMB, 홈랩, 교육 |

---

## ESXi 주요 구성 요소

- **Datastore**: VM 파일 저장소 (VMFS, NFS, iSCSI)
- **vSwitch**: 가상 네트워크 스위치
- **Port Group**: VM 네트워크 그룹
- **VMkernel**: 관리/vMotion/iSCSI 트래픽 처리
- **Snapshot**: VM 상태 저장 (롤백 가능)

---

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd3810bae6ae421ccc03e5c)
