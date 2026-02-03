# Linux 部署指南

本指南将帮助您在 Linux 服务器（如 Ubuntu/CentOS）上部署本项目。

## 1. 环境准备

### 安装 Python 3 和 pip
```bash
# Ubuntu
sudo apt update
sudo apt install python3 python3-pip python3-venv

# CentOS
sudo yum install python3 python3-pip
```

### 安装 Node.js (用于构建前端)
推荐使用 nvm 安装 Node.js LTS 版本：
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install --lts
```

### 安装 Nginx (Web 服务器)
```bash
# Ubuntu
sudo apt install nginx

# CentOS
sudo yum install nginx
```

## 2. 部署后端 (FastAPI)

1. **上传代码**: 将项目代码上传到服务器，例如 `/var/www/trce_jxyc`。

2. **创建虚拟环境并安装依赖**:
   ```bash
   cd /var/www/trce_jxyc
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   pip install gunicorn
   ```

3. **使用 Systemd 管理进程**:
   创建一个服务文件 `/etc/systemd/system/trce_backend.service`:
   ```ini
   [Unit]
   Description=Gunicorn instance to serve FastAPI
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/trce_jxyc
   Environment="PATH=/var/www/trce_jxyc/venv/bin"
   ExecStart=/var/www/trce_jxyc/venv/bin/uvicorn backend.main:app --workers 4 --host 127.0.0.1 --port 8000

   [Install]
   WantedBy=multi-user.target
   ```

4. **启动服务**:
   ```bash
   sudo systemctl start trce_backend
   sudo systemctl enable trce_backend
   ```

## 3. 部署前端 (Vue)

1. **构建生产版本**:
   在本地或服务器上执行构建：
   ```bash
   cd frontend
   npm install
   npm run build
   ```
   构建完成后，会生成 `dist` 目录。

2. **移动静态文件**:
   将 `dist` 目录下的所有文件复制到 Nginx 的 Web 目录，例如 `/var/www/trce_jxyc/frontend/dist`。

## 4. 配置 Nginx

编辑 Nginx 配置文件 `/etc/nginx/sites-available/default` (Ubuntu) 或 `/etc/nginx/nginx.conf` (CentOS):

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    # 前端静态文件
    location / {
        root /var/www/trce_jxyc/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 5. 重启 Nginx

```bash
sudo nginx -t  # 检查配置语法
sudo systemctl restart nginx
```

部署完成！现在您可以通过浏览器访问服务器 IP 来使用系统。
