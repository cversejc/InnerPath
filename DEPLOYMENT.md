# 离火引 InnerSeek 部署指南

本文档提供基于 Docker 的完整部署指南。

## 目录
- [Docker 部署](#docker-部署)
- [本地开发部署](#本地开发部署)
- [远程服务器部署](#远程服务器部署)
- [环境配置](#环境配置)
- [故障排查](#故障排查)

---

## Docker 部署

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+
- DeepSeek API Key

### 本地部署

#### Windows 用户

1. **配置环境变量**
```bash
copy .env.example .env
```
编辑 `.env` 文件，填入你的 DeepSeek API Key：
```
DEEPSEEK_API_KEY=sk-your-api-key-here
```

2. **启动服务**
```bash
deploy.bat
```

#### Linux/Mac 用户

1. **配置环境变量**
```bash
cp .env.example .env
```
编辑 `.env` 文件，填入你的 DeepSeek API Key

2. **启动服务**
```bash
chmod +x build.sh
./build.sh
```

### 访问服务

启动成功后，访问：
- **前端**: http://localhost
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### Docker 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重新构建并启动
docker-compose up -d --build
```

---

## 远程服务器部署

### 方法一：使用部署脚本（推荐）

**首次部署**

1. **配置服务器信息**
```bash
export REMOTE_HOST=your.server.com
export REMOTE_USER=root
export REMOTE_DIR=/opt/innerseek
```

2. **执行部署**
```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
- 打包项目文件
- 上传到服务器
- 备份旧版本
- 构建并启动 Docker 容器

**快速更新（已部署后）**

当代码有更新时，使用快速更新脚本：

```bash
# Linux/Mac
chmod +x update.sh
./update.sh

# Windows
update.bat
```

快速更新脚本会：
- 打包最新代码
- 上传到服务器
- 保留 .env 配置
- 重新构建 Docker 镜像
- 重启服务

### 方法二：手动部署

1. **在服务器上安装 Docker**
```bash
# CentOS/RHEL
yum install -y docker docker-compose
systemctl start docker
systemctl enable docker

# Ubuntu/Debian
apt update
apt install -y docker.io docker-compose
systemctl start docker
systemctl enable docker
```

2. **上传项目文件**
```bash
# 打包项目（排除不必要的文件）
tar -czf innerseek.tar.gz \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='backend/logs' \
    --exclude='*.log' \
    .

# 上传到服务器
scp innerseek.tar.gz root@your.server.com:/tmp/
```

3. **在服务器上解压并启动**
```bash
ssh root@your.server.com

# 创建部署目录
mkdir -p /opt/innerseek
cd /opt/innerseek

# 解压文件
tar -xzf /tmp/innerseek.tar.gz
rm /tmp/innerseek.tar.gz

# 配置环境变量
cp .env.example .env
vim .env  # 填入正确的配置

# 启动服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

4. **配置防火墙**
```bash
# CentOS/RHEL
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# Ubuntu/Debian
ufw allow 80
ufw allow 443
```

---

## 环境配置

### .env 文件说明

```bash
# DeepSeek API Key（必填）
DEEPSEEK_API_KEY=sk-your-api-key-here

# 数据库配置（生产环境请修改密码）
POSTGRES_DB=innerseek
POSTGRES_USER=innerseek
POSTGRES_PASSWORD=your_secure_password_here

# Redis 配置
REDIS_URL=redis://redis:6379/0

# CORS 配置（生产环境请修改为实际域名）
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# 调试模式
DEBUG=False
LOG_LEVEL=INFO
```

### 生产环境配置建议

1. **修改数据库密码**
```bash
POSTGRES_PASSWORD=使用强密码
```

2. **配置 CORS**
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

3. **关闭调试模式**
```bash
DEBUG=False
LOG_LEVEL=WARNING
```

4. **配置 HTTPS**（推荐使用 Let's Encrypt）
```bash
# 安装 certbot
apt install certbot python3-certbot-nginx

# 获取证书
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
certbot renew --dry-run
```

---

## 本地开发部署

如果不使用 Docker，可以手动启动各个服务。

### 后端开发

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件
```

3. **启动数据库和 Redis**
```bash
# 使用 Docker 启动
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_DB=innerseek \
  -e POSTGRES_USER=innerseek \
  -e POSTGRES_PASSWORD=innerseek123 \
  postgres:15

docker run -d --name redis -p 6379:6379 redis:7-alpine
```

4. **启动后端服务**
```bash
uvicorn app.main:app --reload --port 8000
```

### 前端开发

1. **安装依赖**
```bash
npm install
```

2. **启动开发服务器**
```bash
npm run dev
```

访问 http://localhost:5173

---

## 故障排查

### 服务无法启动

1. **检查端口占用**
```bash
# Windows
netstat -ano | findstr :80
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :80
lsof -i :8000
```

2. **检查 Docker 服务**
```bash
docker ps
docker-compose ps
```

3. **查看日志**
```bash
docker-compose logs backend
docker-compose logs frontend
```

### 数据库连接失败

1. **检查数据库容器**
```bash
docker-compose ps postgres
docker-compose logs postgres
```

2. **检查环境变量**
```bash
# 确认 .env 文件中的数据库配置正确
cat .env | grep POSTGRES
```

3. **手动连接测试**
```bash
docker-compose exec postgres psql -U innerseek -d innerseek
```

### AI 报告生成失败

1. **检查 API Key**
```bash
# 确认 DeepSeek API Key 正确
cat .env | grep DEEPSEEK_API_KEY
```

2. **查看后端日志**
```bash
docker-compose logs -f backend | grep "DeepSeek"
```

3. **测试 API 连接**
```bash
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### 前端显示空白

1. **检查浏览器控制台**
   - 打开开发者工具（F12）
   - 查看 Console 和 Network 标签

2. **检查 API 连接**
```bash
# 测试后端 API
curl http://localhost:8000/api/v1/health
```

3. **清除缓存**
   - 清除浏览器缓存
   - 清除 localStorage

### 查看详细日志

```bash
# 后端日志文件
docker-compose exec backend ls -la logs/

# 查看特定日志
docker-compose exec backend tail -f logs/all.log
docker-compose exec backend tail -f logs/error.log
docker-compose exec backend tail -f logs/api.log
```

---

## 性能优化

### 数据库优化

1. **配置连接池**
```python
# backend/app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

2. **添加索引**
```sql
CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_reports_created_at ON reports(created_at);
```

### Redis 缓存优化

1. **配置持久化**
```bash
# docker-compose.yml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

2. **设置合理的过期时间**
```python
# 游客报告缓存 1 小时
await cache_set(key, value, expire=3600)
```

### Nginx 优化

1. **启用 Gzip 压缩**（已配置）
2. **配置静态资源缓存**（已配置）
3. **启用 HTTP/2**
```nginx
listen 443 ssl http2;
```

---

## 监控和维护

### 健康检查

```bash
# 前端健康检查
curl http://localhost/health

# 后端健康检查
curl http://localhost:8000/api/v1/health
```

### 日志轮转

```bash
# 配置 logrotate
cat > /etc/logrotate.d/innerseek << EOF
/opt/innerseek/backend/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 备份

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U innerseek innerseek > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U innerseek innerseek < backup.sql
```

---

## 联系支持

如有问题，请查看：
- GitHub Issues: https://github.com/yourusername/innerseek/issues
- 邮箱: hello@innerseek.me
- 微信: innerseek2026
