---
name: vps-linux
description: Setting up a VPS Linux server from scratch with Docker, reverse proxy, SSL, and security hardening. Use when provisioning a new server, configuring a production environment on a VPS, or troubleshooting server setup.
---

# VPS Linux Setup — Docker-Based

## 1. Initial Server Access & Hardening

```bash
# Connect as root initially
ssh root@<SERVER_IP>

# Create non-root user
adduser deploy
usermod -aG sudo deploy

# Copy your SSH key
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Disable root SSH login and password auth
nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes

systemctl restart sshd

# Basic firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

## 2. System Update & Essential Packages

```bash
apt update && apt upgrade -y
apt install -y \
    curl \
    wget \
    git \
    htop \
    fail2ban \
    unattended-upgrades
```

## 3. Docker Installation

```bash
# Install Docker (official script — verify at docs.docker.com)
curl -fsSL https://get.docker.com | sh

# Add deploy user to docker group (no sudo needed)
usermod -aG docker deploy

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

## 4. Reverse Proxy — Nginx + SSL (Certbot)

### Install Nginx
```bash
apt install -y nginx certbot python3-certbot-nginx
```

### Nginx Site Config
```nginx
# /etc/nginx/sites-available/myapp
server {
    listen 80;
    server_name myapp.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name myapp.example.com;

    ssl_certificate /etc/letsencrypt/live/myapp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 60s;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Issue SSL certificate
certbot --nginx -d myapp.example.com

# Auto-renew (verify cron is set by certbot)
certbot renew --dry-run
```

## 5. Application Directory Structure

```bash
mkdir -p /opt/myapp
chown deploy:deploy /opt/myapp

# Inside /opt/myapp:
# docker-compose.yml
# .env.production (permissions 600, not committed to git)
# secrets/
```

## 6. Deployment Script

```bash
#!/bin/bash
# /opt/myapp/deploy.sh
set -e

IMAGE_TAG=${1:-latest}

cd /opt/myapp

echo "Pulling image..."
docker compose pull app

echo "Deploying..."
IMAGE_TAG=$IMAGE_TAG docker compose up -d --remove-orphans

echo "Cleaning up old images..."
docker image prune -f

echo "Deployed successfully."
```

## 7. Fail2Ban Configuration

```bash
# Protect SSH and Nginx
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF

systemctl restart fail2ban
```

## 8. Maintenance Checklist

- [ ] Unattended security upgrades enabled (`unattended-upgrades`)
- [ ] Docker auto-prune configured (`docker system prune` via cron)
- [ ] Log rotation configured (`/etc/logrotate.d/`)
- [ ] Backups: database dumps to remote storage (S3, B2, etc.)
- [ ] Monitoring: UptimeRobot, BetterUptime, or self-hosted (Uptime Kuma)
- [ ] Swap configured if RAM < 2GB: `fallocate -l 1G /swapfile`

## Common Issues

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway | App container not running — `docker compose ps` |
| SSL cert expired | `certbot renew` |
| Port already in use | `lsof -i :PORT` to find the process |
| Out of disk space | `docker system prune -a`, check logs |
