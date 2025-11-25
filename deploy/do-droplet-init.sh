#!/bin/bash

set -e

DOMAIN="triptools.net"
DOCKER_APP_PORT=8000

echo "Updating system ..."
apt update && apt upgrade -y

echo "Installing Docker ..."
apt install -y docker.io
systemctl enable docker
sudo systemctl start docker

echo "Installing Nginx + Certbot ..."
apt install -y nginx certbot python3-certbot-nginx
systemctl enable nginx
sudo systemctl start nginx

echo "Configuring Nginx reverse proxy ..."

# Suppress existing default config to avoid port conflict
rm -f /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-available/tt <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://localhost:$DOCKER_APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -s /etc/nginx/sites-available/tt /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "Installing MySQL ..."
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql

echo "Installing Redis ..."
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

echo "Installing docker-compose ..."
sudo apt install -y docker-compose

echo "Creating deployment directory ..."
mkdir -p /opt/triptools

# After DNS is set up and pointing to this server, run:
echo "*********"
echo "* NOTICE: Need to run certbot after DNS points here."
echo "* "
echo "*         certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN"
echo "*********"

echo "Ready."
