# Complete Streamlit Deployment Guide with Nginx

## Overview
This guide covers deploying a Python Streamlit app from GitHub to a server with Nginx reverse proxy and SSL.

**Repository**: https://github.com/kw-andy/stat-ageca  
**Domain**: stat.just-go.dev  
**Location**: /var/www/html/stat-ageca

---

## Pre-Deployment Setup
- [ ] Subdomain configured: stat.just-go.dev
- [ ] Nginx installed and running
- [ ] Repository available: https://github.com/kw-andy/stat-ageca

## 1. Repository Setup
- [ ] SSH into your server
- [ ] Navigate to web directory: `cd /var/www/html`
- [ ] Clone repository: `sudo git clone https://github.com/kw-andy/stat-ageca.git`
- [ ] Enter project directory: `cd stat-ageca`
- [ ] Check what Python files exist: `ls *.py`
- [ ] Identify your main Streamlit file (app.py, main.py, etc.)

## 2. Create and Setup Virtual Environment
- [ ] Create virtual environment: `sudo python3 -m venv .venv`
- [ ] Check if requirements.txt exists: `ls requirements.txt`
- [ ] **If requirements.txt exists:**
  - [ ] Install dependencies: `sudo .venv/bin/pip install -r requirements.txt`
- [ ] **If no requirements.txt:**
  - [ ] Install Streamlit: `sudo .venv/bin/pip install streamlit`
- [ ] Set proper permissions: `sudo chown -R www-data:www-data /var/www/html/stat-ageca`

## 3. Test the Application
- [ ] Test run: `sudo -u www-data /var/www/html/stat-ageca/.venv/bin/streamlit run app.py`
- [ ] Check if app starts without errors
- [ ] Note the port it's running on (usually 8501)
- [ ] Stop the test: `Ctrl+C`

## 4. Create System Service
- [ ] Create service file: `sudo nano /etc/systemd/system/stat-ageca.service`
- [ ] Add service configuration (replace `app.py` with your main file):

```ini
[Unit]
Description=Streamlit App - Stat Ageca
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/html/stat-ageca
Environment=PATH=/var/www/html/stat-ageca/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/var/www/html/stat-ageca/.venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

- [ ] Save and close the file
- [ ] Reload systemd: `sudo systemctl daemon-reload`
- [ ] Enable service: `sudo systemctl enable stat-ageca`
- [ ] Start service: `sudo systemctl start stat-ageca`
- [ ] Check service status: `sudo systemctl status stat-ageca`

## 5. Configure Nginx Reverse Proxy
- [ ] Edit Nginx site config: `sudo nano /etc/nginx/sites-available/stat.just-go.dev`
- [ ] Replace content with:

```nginx
# /etc/nginx/sites-available/stat.just-go.dev
server {
    listen 80;
    listen [::]:80;
    server_name stat.just-go.dev;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name stat.just-go.dev;

    # SSL configuration
    ssl_certificate     /etc/letsencrypt/live/stat.just-go.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stat.just-go.dev/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Proxy to Streamlit app
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
        
        # Important for Streamlit WebSocket connections
        proxy_buffering off;
    }
}
```

- [ ] Save and close the file
- [ ] Test Nginx config: `sudo nginx -t`
- [ ] Reload Nginx: `sudo systemctl reload nginx`

## 6. Final Testing & Verification
- [ ] Check service is running: `sudo systemctl status stat-ageca`
- [ ] Check service logs: `sudo journalctl -u stat-ageca -f` (Ctrl+C to exit)
- [ ] Test local connection: `curl -I http://127.0.0.1:8501`
- [ ] Test domain: `curl -I https://stat.just-go.dev`
- [ ] Visit in browser: https://stat.just-go.dev
- [ ] Verify app loads correctly with SSL

---

## Useful Commands for Management

### Service Management
```bash
sudo systemctl restart stat-ageca    # Restart app
sudo systemctl stop stat-ageca       # Stop app
sudo systemctl start stat-ageca      # Start app
sudo journalctl -u stat-ageca -f     # View live logs
sudo systemctl status stat-ageca     # Check service status
```

### Updates
```bash
cd /var/www/html/stat-ageca
sudo git pull origin main
sudo .venv/bin/pip install -r requirements.txt  # Update dependencies if needed
sudo systemctl restart stat-ageca
```

### Nginx Management
```bash
sudo nginx -t                        # Test config
sudo systemctl reload nginx          # Reload config
sudo systemctl restart nginx         # Restart nginx
sudo tail -f /var/log/nginx/error.log # View error logs
```

---

## Troubleshooting Checklist

If something doesn't work, check:

### Service Issues
- [ ] Service status: `sudo systemctl status stat-ageca`
- [ ] Service logs: `sudo journalctl -u stat-ageca -n 50`
- [ ] Port 8501 is listening: `sudo netstat -tlnp | grep 8501`
- [ ] Virtual environment exists: `ls -la /var/www/html/stat-ageca/.venv/bin/`
- [ ] Streamlit is installed in venv: `/var/www/html/stat-ageca/.venv/bin/pip show streamlit`
- [ ] File permissions are correct: `ls -la /var/www/html/stat-ageca/`

### Network Issues
- [ ] DNS resolves: `nslookup stat.just-go.dev`
- [ ] Firewall allows HTTP/HTTPS: `sudo ufw status`
- [ ] Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
- [ ] SSL certificate is valid: `sudo certbot certificates`

### Common Error Codes
- **203/EXEC**: File doesn't exist or isn't executable
- **Connection refused**: Service not running or wrong port
- **502 Bad Gateway**: Nginx can't connect to Streamlit app
- **SSL errors**: Certificate issues or wrong paths

---

## File Structure
```
/var/www/html/stat-ageca/
├── .venv/
│   └── bin/
│       └── streamlit
├── app.py                 # Your main Streamlit file
├── requirements.txt       # Python dependencies
└── ... (other project files)

/etc/systemd/system/
└── stat-ageca.service     # Systemd service file

/etc/nginx/sites-available/
└── stat.just-go.dev       # Nginx configuration
```

---

## Notes
- Replace `app.py` with your actual main Python file name throughout
- Ensure all paths match your actual directory structure
- The service runs as `www-data` user for security
- Streamlit runs on localhost:8501 and Nginx proxies to it
- SSL is handled by Nginx with Let's Encrypt certificates