# Shared location blocks — included by both the HTTP (port 80) and the
# HTTPS (port 443) server blocks in default.conf so the routing rules
# never drift between the two.

# Auth endpoints - stricter than general API, still allows normal flows
location /api/v1/auth/ {
    limit_req zone=auth burst=20 nodelay;

    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Admin docs - gated at app layer; hide them from crawlers.
location ~ ^/api/v1/admin/(docs|openapi\.json)$ {
    limit_req zone=api burst=10 nodelay;
    add_header X-Robots-Tag "noindex, nofollow" always;

    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Celery Flower — gated by HTTP basic auth + noindex. Backing service is
# reachable only through the internal backend_net.
location /flower/ {
    auth_basic "Patinho Celery";
    auth_basic_user_file /etc/nginx/flower.htpasswd;
    add_header X-Robots-Tag "noindex, nofollow" always;

    proxy_pass http://flower:5555;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Payment webhooks - higher rate limit, no buffering
location /api/v1/payments/webhook/ {
    limit_req zone=webhook burst=20 nodelay;

    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_buffering off;
    proxy_request_buffering off;
}

# General API endpoints
location /api/ {
    limit_req zone=api burst=40 nodelay;

    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# WebSocket connections
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}

# Static media files
location /media/ {
    alias /media/;
    expires 7d;
    add_header Cache-Control "public, no-transform";
}

# Frontend SPA catch-all
location / {
    proxy_pass http://frontend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
