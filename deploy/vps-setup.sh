#!/bin/bash
# One-time VPS setup for Monty + shared nginx proxy
# Run this ON the VPS (ssh in first), or pipe via: ssh user@vps 'bash -s' < deploy/vps-setup.sh
#
# What this does:
#   1. Creates shared Docker network
#   2. Sets up DuckDNS for montyops.duckdns.org
#   3. Sets up shared nginx reverse proxy
#   4. Gets SSL certs via Let's Encrypt
#   5. Reconfigures agenticeda to use the shared proxy

set -e

echo "=== Step 1: Create shared Docker network ==="
docker network create web 2>/dev/null || echo "Network 'web' already exists"

echo "=== Step 2: Set up DuckDNS ==="
echo "Point montyops.duckdns.org to 64.62.164.6"
echo "Go to https://www.duckdns.org and:"
echo "  1. Log in"
echo "  2. Add subdomain 'montyops'"
echo "  3. Set IP to: 64.62.164.6"
echo ""
read -p "Press Enter once DuckDNS is configured..."

# Verify DNS
echo "Verifying DNS..."
RESOLVED=$(dig +short montyops.duckdns.org 2>/dev/null || nslookup montyops.duckdns.org 2>/dev/null | tail -1)
echo "montyops.duckdns.org resolves to: $RESOLVED"

echo "=== Step 3: Stop existing nginx (agenticeda) from binding ports 80/443 ==="
echo ""
echo "Your existing agenticeda app binds ports 80/443 directly."
echo "We need to change it to use the shared proxy instead."
echo ""
echo "You need to:"
echo "  1. Edit agenticeda's docker-compose.yml"
echo "  2. Remove the 'ports: 80:80, 443:443' from its nginx service"
echo "  3. Add it to the 'web' network"
echo "  4. Give its nginx container the name 'agenticeda-nginx'"
echo ""
echo "Example changes to agenticeda's docker-compose.yml:"
echo "  nginx:"
echo "    container_name: agenticeda-nginx  # ADD this"
echo "    # ports:                          # REMOVE these"
echo "    #   - 80:80                       # REMOVE"
echo "    #   - 443:443                     # REMOVE"
echo "    networks:                         # ADD this"
echo "      - web                           # ADD this"
echo ""
echo "  networks:                           # ADD this block"
echo "    web:                              # ADD"
echo "      external: true                  # ADD"
echo ""
read -p "Press Enter once agenticeda is updated and restarted..."

echo "=== Step 4: Set up shared reverse proxy ==="
mkdir -p ~/proxy
cat > ~/proxy/docker-compose.yml << 'PROXYEOF'
services:
  nginx-proxy:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/www/certbot
    networks:
      - web

  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    networks:
      - web

volumes:
  certbot-etc:
  certbot-var:

networks:
  web:
    external: true
PROXYEOF

# Temporary nginx config (HTTP only, for cert issuance)
cat > ~/proxy/nginx.conf << 'NGINXEOF'
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name montyops.duckdns.org agenticeda.duckdns.org;
        location /.well-known/acme-challenge/ { root /var/www/certbot; }
        location / { return 200 'waiting for SSL setup'; }
    }
}
NGINXEOF

echo "Starting temporary proxy for cert issuance..."
cd ~/proxy && docker compose up -d nginx-proxy
sleep 2

echo "=== Step 5: Get SSL certificates ==="
# Monty cert
docker run --rm \
    -v "$(docker volume inspect proxy_certbot-etc -f '{{.Mountpoint}}'):/etc/letsencrypt" \
    -v "$(docker volume inspect proxy_certbot-var -f '{{.Mountpoint}}'):/var/www/certbot" \
    certbot/certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email indro@example.com --agree-tos --no-eff-email \
    -d montyops.duckdns.org

# AgenticEDA cert (if not already present)
docker run --rm \
    -v "$(docker volume inspect proxy_certbot-etc -f '{{.Mountpoint}}'):/etc/letsencrypt" \
    -v "$(docker volume inspect proxy_certbot-var -f '{{.Mountpoint}}'):/var/www/certbot" \
    certbot/certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email indro@example.com --agree-tos --no-eff-email \
    -d agenticeda.duckdns.org \
    --keep-existing

echo "=== Step 6: Install full nginx config ==="
# Now install the real nginx config with SSL
cat > ~/proxy/nginx.conf << 'FULLNGINX'
events { worker_connections 1024; }
http {
    client_max_body_size 10M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 10s;

    # ── montyops.duckdns.org ──
    server {
        listen 80;
        server_name montyops.duckdns.org;
        location /.well-known/acme-challenge/ { root /var/www/certbot; }
        location / { return 301 https://$host$request_uri; }
    }
    server {
        listen 443 ssl;
        server_name montyops.duckdns.org;
        ssl_certificate /etc/letsencrypt/live/montyops.duckdns.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/montyops.duckdns.org/privkey.pem;

        location / {
            proxy_pass http://monty:3200;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        location /api/ {
            proxy_pass http://monty:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_buffering off;
            proxy_cache off;
        }
    }

    # ── agenticeda.duckdns.org ──
    server {
        listen 80;
        server_name agenticeda.duckdns.org;
        location /.well-known/acme-challenge/ { root /var/www/certbot; }
        location / { return 301 https://$host$request_uri; }
    }
    server {
        listen 443 ssl;
        server_name agenticeda.duckdns.org;
        ssl_certificate /etc/letsencrypt/live/agenticeda.duckdns.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/agenticeda.duckdns.org/privkey.pem;
        location / {
            proxy_pass http://agenticeda-nginx:80;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Catch-all
    server {
        listen 80 default_server;
        return 444;
    }
}
FULLNGINX

echo "Reloading nginx with full config..."
cd ~/proxy && docker compose restart nginx-proxy

echo "=== Step 7: Create Monty directory ==="
mkdir -p ~/monty/data ~/monty/wiki

echo ""
echo "============================================"
echo "  VPS setup complete!"
echo "============================================"
echo ""
echo "  Now deploy Monty from your local machine:"
echo "    cd /path/to/monty"
echo "    ./deploy/deploy.sh"
echo ""
echo "  To purge and redeploy:"
echo "    ./deploy/deploy.sh --purge"
echo ""
echo "  URLs:"
echo "    https://montyops.duckdns.org"
echo "    https://agenticeda.duckdns.org"
echo ""
