# VMware ESXi

> VMware ESXi 설정 및 운영 기술문서

## 주요 구성 요소

| 구성요소 | 설명 |
|----------|------|
| Datastore | VM 파일 저장소 (VMFS / NFS / iSCSI) |
| vSwitch | 가상 네트워크 스위치 |
| VMkernel | 관리 / vMotion / iSCSI 트래픽 |
| Snapshot | VM 상태 저장 및 롤백 |
| OVF/OVA | VM 템플릿 포맷 |

## ESXi Shell 기본 명령어

```bash
# 네트워크 설정
esxcli network ip interface ipv4 set \
  --interface-name=vmk0 \
  --ipv4=192.168.1.100 \
  --netmask=255.255.255.0 \
  --type=static

# 게이트웨이 설정
esxcli network ip route ipv4 add \
  --network=default \
  --gateway=192.168.1.1

# VM 목록
esxcli vm process list

# 서비스 재시작
/etc/init.d/hostd restart
```

> 🔗 [Notion 원본](https://www.notion.so/22b5e60c6bd3803ba7bde861dcedf373)
