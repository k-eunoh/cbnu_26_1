# Linux OS — System

> Linux 시스템 관리 문서

## 사용자 관리

```bash
useradd -m -s /bin/bash username
passwd username
usermod -aG sudo username
userdel -r username
```

## 권한 관리

```bash
chmod 755 file.sh        # rwxr-xr-x
chmod 644 file.txt       # rw-r--r--
chown user:group file
```

## 서비스 관리 (systemd)

```bash
systemctl status nginx
systemctl start nginx
systemctl enable nginx
journalctl -u nginx -f   # 실시간 로그
```

## 패키지 관리

```bash
# Ubuntu/Debian
apt update && apt upgrade -y
apt install <package>

# CentOS/RHEL
dnf update -y
dnf install <package>
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381379a27c1c54b4cb703)
