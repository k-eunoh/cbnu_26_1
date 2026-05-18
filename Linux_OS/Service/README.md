# Linux OS — Service

> Linux 주요 서비스 설정 문서

## SSH 강화

```bash
# /etc/ssh/sshd_config
Port 2222
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
```

## Nginx

```bash
apt install nginx
systemctl enable --now nginx
# 설정 파일: /etc/nginx/nginx.conf
```

## NFS 서버

```bash
apt install nfs-kernel-server
echo "/data  192.168.1.0/24(rw,sync,no_subtree_check)" >> /etc/exports
exportfs -ra
systemctl enable --now nfs-server
```

## Samba

```bash
apt install samba
# /etc/samba/smb.conf 편집 후
systemctl restart smbd
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381adacfbc6d3b004be0d)
