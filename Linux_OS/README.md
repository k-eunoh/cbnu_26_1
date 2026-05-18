# 🐧 Linux OS

> Linux 운영체제 기술문서 — 네트워크, 시스템, 서비스

---

## 📂 하위 문서

| 폴더 | 설명 |
|------|------|
| [Network](./Network/) | 네트워크 인터페이스, IP 설정, 라우팅, 방화벽 (iptables/nftables) |
| [System](./System/) | 사용자 관리, 권한, 프로세스, 패키지 관리 |
| [Service](./Service/) | SSH, Nginx, Apache, FTP, NFS, Samba, DNS, DHCP 등 |

---

## 자주 사용하는 명령어

### 네트워크

```bash
# IP 확인
ip addr show
ip -br addr

# 라우팅 테이블
ip route show

# 네트워크 인터페이스 설정 (Ubuntu 22.04+ / Netplan)
sudo nano /etc/netplan/00-installer-config.yaml
sudo netplan apply

# 방화벽 (UFW)
sudo ufw status
sudo ufw allow 22/tcp
sudo ufw enable
```

### 시스템

```bash
# 서비스 관리
systemctl status <service>
systemctl start <service>
systemctl enable <service>

# 프로세스 확인
ps aux | grep <process>
top / htop

# 디스크 확인
df -h
lsblk
```

### 패키지 관리

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install <package>

# CentOS/RHEL
sudo dnf update -y
sudo dnf install <package>
```

---

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd38144a28cf3151bdbad04)
