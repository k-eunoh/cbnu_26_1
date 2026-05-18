# Linux OS — Network

> Linux 네트워크 설정 문서

## Netplan 설정 (Ubuntu 22.04+)

```yaml
# /etc/netplan/00-installer-config.yaml
network:
  version: 2
  ethernets:
    ens33:
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```
```bash
sudo netplan apply
```

## 자주 쓰는 명령어

```bash
ip addr show              # IP 확인
ip route show             # 라우팅 테이블
ss -tuln                  # 열린 포트 확인
ping -c 4 8.8.8.8         # 연결 테스트
traceroute 8.8.8.8        # 경로 추적
```

## 방화벽 (UFW)

```bash
sudo ufw status
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381d69b72da4fbe0942da)
