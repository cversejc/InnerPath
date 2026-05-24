# InnerSeek 后端部署指南

## 服务器要求

- **操作系统**: Ubuntu 20.04+ / CentOS 7+
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Nginx**: 1.18+
- **内存**: 最低2GB，推荐4GB+
- **磁盘**: 最低10GB

## 部署步骤

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql-15 redis-server nginx supervisor git

# CentOS/RHEL
sudo yum install -y python311 python311-pip postgresql15-server redis nginx supervisor git
```

### 2. 配置PostgreSQL

```bash
# 启动PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE innerseek;
CREATE USER innerseek WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE innerseek TO innerseek;
\q
EOF

# 配置PostgreSQL允许本地连接
sudo nano /etc/postgresql/15/main/pg_hba.conf
# 添加: local   innerseek   innerseek   md5

# 重启PostgreSQL
sudo systemctl restart postgresql
```

### 3. 配置Redis

```bash
# 启动Redis
sudo systemctl start redis
sudo systemctl enable redis

# 测试连接
redis-cli ping
# 应返回: PONG
```

### 4. 部署后端代码

```bash
# 创建部署目录
sudo mkdir -p /var/www/innerseek/backend
sudo chown -R $USER:$USER /var/www/innerseek

# 上传代码（使用git或scp）
cd /var/www/innerseek
git clone <your-repo-url> backend
# 或使用scp上传

cd backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
nano .env
```

**重要配置项**:
```bash
# 应用配置
ENVIRONMENT=production
DEBUG=False

# 数据库
DATABASE_URL=postgresql+asyncpg://innerseek:your_secure_password@localhost:5432/innerseek

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT密钥（生成随机密钥）
SECRET_KEY=$(openssl rand -hex 32)

# DeepSeek API
DEEPSEEK_API_KEY=sk-your-actual-api-key

# CORS（前端域名）
CORS_ORIGINS=http://8.135.25.206

# 短信服务（如果使用）
SMS_ACCESS_KEY=your_access_key
SMS_SECRET_KEY=your_secret_key
```

### 6. 运行数据库迁移

```bash
source venv/bin/activate
alembic upgrade head
```

### 7. 配置Nginx

```bash
# 复制Nginx配置
sudo cp deployment/nginx.conf /etc/nginx/sites-available/innerseek

# 创建软链接
sudo ln -s /etc/nginx/sites-available/innerseek /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8. 配置Supervisor

```bash
# 创建日志目录
sudo mkdir -p /var/log/innerseek
sudo chown -R www-data:www-data /var/log/innerseek

# 复制Supervisor配置
sudo cp deployment/supervisor.conf /etc/supervisor/conf.d/innerseek.conf

# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start innerseek:*

# 查看状态
sudo supervisorctl status
```

### 9. 验证部署

```bash
# 检查API健康状态
curl http://localhost:8000/health

# 检查Swagger文档
curl http://localhost:8000/docs

# 检查Celery worker
sudo supervisorctl status innerseek-celery

# 查看日志
sudo tail -f /var/log/innerseek/api.log
sudo tail -f /var/log/innerseek/celery.log
```

## 常用管理命令

### Supervisor管理

```bash
# 查看所有服务状态
sudo supervisorctl status

# 启动所有服务
sudo supervisorctl start innerseek:*

# 停止所有服务
sudo supervisorctl stop innerseek:*

# 重启所有服务
sudo supervisorctl restart innerseek:*

# 重启单个服务
sudo supervisorctl restart innerseek-api

# 查看日志
sudo supervisorctl tail -f innerseek-api
```

### 数据库管理

```bash
# 备份数据库
pg_dump -U innerseek innerseek > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U innerseek innerseek < backup_20260524.sql

# 运行迁移
cd /var/www/innerseek/backend
source venv/bin/activate
alembic upgrade head
```

### 日志查看

```bash
# API日志
sudo tail -f /var/log/innerseek/api.log

# Celery日志
sudo tail -f /var/log/innerseek/celery.log

# Nginx访问日志
sudo tail -f /var/log/nginx/innerseek_access.log

# Nginx错误日志
sudo tail -f /var/log/nginx/innerseek_error.log
```

## 更新部署

```bash
# 1. 拉取最新代码
cd /var/www/innerseek/backend
git pull origin main

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 更新依赖
pip install -r requirements.txt

# 4. 运行数据库迁移
alembic upgrade head

# 5. 重启服务
sudo supervisorctl restart innerseek:*

# 6. 验证
curl http://localhost:8000/health
```

## 监控和维护

### 性能监控

```bash
# 查看系统资源
htop

# 查看PostgreSQL连接
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# 查看Redis内存使用
redis-cli info memory

# 查看Celery任务队列
cd /var/www/innerseek/backend
source venv/bin/activate
celery -A app.tasks.celery_app inspect active
```

### 日志轮转

创建 `/etc/logrotate.d/innerseek`:
```
/var/log/innerseek/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        supervisorctl restart innerseek:*
    endscript
}
```

### 定期备份

创建备份脚本 `/usr/local/bin/backup-innerseek.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/innerseek"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U innerseek innerseek | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 删除30天前的备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

添加到crontab:
```bash
# 每天凌晨2点备份
0 2 * * * /usr/local/bin/backup-innerseek.sh
```

## 安全加固

### 1. 配置防火墙

```bash
# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许SSH（如果需要）
sudo ufw allow 22/tcp

# 启用防火墙
sudo ufw enable
```

### 2. 配置HTTPS（推荐）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 限制数据库访问

编辑 `/etc/postgresql/15/main/pg_hba.conf`:
```
# 只允许本地连接
local   innerseek   innerseek   md5
host    innerseek   innerseek   127.0.0.1/32   md5
```

### 4. 配置Redis密码

编辑 `/etc/redis/redis.conf`:
```
requirepass your_redis_password
```

更新 `.env`:
```
REDIS_URL=redis://:your_redis_password@localhost:6379/0
```

## 故障排查

### API无法启动

```bash
# 查看详细日志
sudo supervisorctl tail -f innerseek-api stderr

# 检查端口占用
sudo netstat -tlnp | grep 8000

# 手动启动测试
cd /var/www/innerseek/backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Celery任务不执行

```bash
# 查看Celery日志
sudo supervisorctl tail -f innerseek-celery

# 检查Redis连接
redis-cli ping

# 手动启动Celery测试
cd /var/www/innerseek/backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=debug
```

### 数据库连接失败

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 测试连接
psql -U innerseek -d innerseek -h localhost

# 查看PostgreSQL日志
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

## 性能优化

### 1. PostgreSQL优化

编辑 `/etc/postgresql/15/main/postgresql.conf`:
```
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### 2. Nginx优化

编辑 `/etc/nginx/nginx.conf`:
```
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
client_max_body_size 10M;
```

### 3. Uvicorn workers

根据CPU核心数调整workers:
```bash
# 在supervisor.conf中
command=/var/www/innerseek/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

## 联系支持

如遇到问题，请查看：
- API文档: http://your-domain/docs
- 项目仓库: https://github.com/your-org/innerseek
- 问题反馈: https://github.com/your-org/innerseek/issues
