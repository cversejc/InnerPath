# 更新脚本故障排查指南

本文档帮助你解决 `update.sh` 脚本执行过程中可能遇到的问题。

## 快速诊断

运行测试脚本检查本地环境：
```bash
./test-update.sh
```

## 常见问题

### 1. 脚本执行到一半退出

**症状**: 脚本运行到某个步骤后突然退出，没有完成所有步骤

**可能原因**:

#### A. SSH 连接中断
```bash
# 检查 SSH 连接
ssh root@8.135.25.206 "echo 'SSH 连接正常'"

# 如果超时，检查网络
ping 8.135.25.206
```

**解决方案**:
- 检查网络连接
- 增加 SSH 超时时间：在 `~/.ssh/config` 添加
  ```
  Host 8.135.25.206
      ServerAliveInterval 60
      ServerAliveCountMax 3
  ```

#### B. 远程目录不存在
```bash
# 检查远程目录
ssh root@8.135.25.206 "ls -la /opt/innerseek/current"
```

**解决方案**:
- 如果目录不存在，先使用 `deploy.sh` 进行首次部署
- 或手动创建目录：
  ```bash
  ssh root@8.135.25.206 "mkdir -p /opt/innerseek/current"
  ```

#### C. Docker 构建失败
```bash
# 查看 Docker 日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs"
```

**解决方案**:
- 检查 Dockerfile 语法
- 检查网络连接（Docker 需要下载镜像）
- 清理 Docker 缓存：
  ```bash
  ssh root@8.135.25.206 "docker system prune -a"
  ```

#### D. 磁盘空间不足
```bash
# 检查磁盘空间
ssh root@8.135.25.206 "df -h"
```

**解决方案**:
- 清理 Docker 镜像和容器：
  ```bash
  ssh root@8.135.25.206 "docker system prune -a --volumes"
  ```
- 清理旧的备份：
  ```bash
  ssh root@8.135.25.206 "cd /opt/innerseek && ls -la"
  ssh root@8.135.25.206 "rm -rf /opt/innerseek/backup-*"
  ```

### 2. 上传失败

**症状**: `[3/5] 上传到服务器...` 步骤失败

**检查**:
```bash
# 测试 SCP 连接
scp test-update.sh root@8.135.25.206:/tmp/
```

**解决方案**:
- 检查 SSH 密钥或密码
- 检查服务器 /tmp 目录权限
- 检查网络带宽（大文件上传可能超时）

### 3. .env 文件丢失

**症状**: 更新后服务无法启动，提示缺少环境变量

**检查**:
```bash
# 查看远程 .env 文件
ssh root@8.135.25.206 "cat /opt/innerseek/current/.env"
```

**解决方案**:
- 手动恢复 .env 文件：
  ```bash
  scp .env root@8.135.25.206:/opt/innerseek/current/
  ```
- 或在服务器上重新创建：
  ```bash
  ssh root@8.135.25.206
  cd /opt/innerseek/current
  cp .env.example .env
  vim .env  # 填入正确配置
  docker-compose restart
  ```

### 4. Docker 服务无法启动

**症状**: `[5/5] 重启 Docker 服务...` 步骤失败

**检查**:
```bash
# 查看 Docker 状态
ssh root@8.135.25.206 "docker ps -a"

# 查看服务日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs"
```

**解决方案**:

#### A. 端口被占用
```bash
# 检查端口占用
ssh root@8.135.25.206 "netstat -tlnp | grep -E ':(80|8000|5432|6379)'"
```

修改 `docker-compose.yml` 使用其他端口：
```yaml
services:
  frontend:
    ports:
      - "3000:80"  # 改为 3000
```

#### B. 数据库连接失败
```bash
# 检查 PostgreSQL 容器
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs postgres"
```

重启数据库：
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose restart postgres"
```

#### C. Redis 连接失败
```bash
# 检查 Redis 容器
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs redis"
```

重启 Redis：
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose restart redis"
```

### 5. 权限问题

**症状**: 提示 "Permission denied"

**解决方案**:
```bash
# 修复文件权限
ssh root@8.135.25.206 "chmod -R 755 /opt/innerseek/current"

# 修复 Docker socket 权限
ssh root@8.135.25.206 "chmod 666 /var/run/docker.sock"
```

## 手动恢复步骤

如果自动更新失败，可以手动执行以下步骤：

### 1. 登录服务器
```bash
ssh root@8.135.25.206
```

### 2. 进入项目目录
```bash
cd /opt/innerseek/current
```

### 3. 查看当前状态
```bash
docker-compose ps
docker-compose logs --tail=50
```

### 4. 停止服务
```bash
docker-compose down
```

### 5. 备份 .env
```bash
cp .env /tmp/.env.backup
```

### 6. 上传新代码（在本地执行）
```bash
# 打包
tar -czf update.tar.gz \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.git' \
    .

# 上传
scp update.tar.gz root@8.135.25.206:/tmp/
```

### 7. 解压新代码（在服务器上）
```bash
cd /opt/innerseek/current
tar -xzf /tmp/update.tar.gz
rm /tmp/update.tar.gz
```

### 8. 恢复 .env
```bash
cp /tmp/.env.backup .env
```

### 9. 重新构建
```bash
docker-compose build
```

### 10. 启动服务
```bash
docker-compose up -d
```

### 11. 检查状态
```bash
docker-compose ps
docker-compose logs -f
```

## 回滚到旧版本

如果更新后出现问题，可以回滚：

```bash
# 1. 登录服务器
ssh root@8.135.25.206

# 2. 查看备份
cd /opt/innerseek
ls -la

# 3. 停止当前服务
cd current
docker-compose down

# 4. 切换到备份版本
cd ..
mv current current-broken
cp -r backup-20260524-123456 current

# 5. 启动服务
cd current
docker-compose up -d
```

## 日志查看

### 实时查看所有日志
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f"
```

### 查看特定服务日志
```bash
# 后端日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f backend"

# 前端日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f frontend"

# 数据库日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f postgres"
```

### 查看最近 N 行日志
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs --tail=100"
```

### 查看后端应用日志
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose exec backend ls -la logs/"
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose exec backend tail -f logs/all.log"
```

## 性能优化

### 加速 Docker 构建

1. **使用构建缓存**（去掉 --no-cache）
   
   编辑 `update.sh`，将：
   ```bash
   docker-compose build --no-cache
   ```
   改为：
   ```bash
   docker-compose build
   ```

2. **使用 Docker BuildKit**
   ```bash
   export DOCKER_BUILDKIT=1
   docker-compose build
   ```

### 减少上传时间

1. **排除更多不必要的文件**
   
   编辑 `update.sh`，在 tar 命令中添加更多排除项：
   ```bash
   tar -czf "$PACKAGE_NAME" \
       --exclude='node_modules' \
       --exclude='dist' \
       --exclude='.git' \
       --exclude='*.md' \
       --exclude='docs' \
       .
   ```

2. **使用增量更新**（仅上传变更的文件）
   ```bash
   rsync -avz --exclude='node_modules' --exclude='.git' \
       ./ root@8.135.25.206:/opt/innerseek/current/
   ```

## 预防措施

### 1. 更新前备份
```bash
ssh root@8.135.25.206 "cd /opt/innerseek && cp -r current backup-manual-$(date +%Y%m%d-%H%M%S)"
```

### 2. 本地测试
```bash
# 在本地 Docker 环境测试
./build.sh
# 测试所有功能
```

### 3. 分步更新
不要一次性更新所有内容，可以分步进行：
- 先更新前端
- 再更新后端
- 最后更新配置

### 4. 监控服务状态
设置监控脚本，定期检查服务状态：
```bash
#!/bin/bash
while true; do
    curl -s http://8.135.25.206/health || echo "服务异常"
    sleep 60
done
```

## 联系支持

如果以上方法都无法解决问题：

1. 收集以下信息：
   - 错误信息截图
   - `docker-compose logs` 输出
   - `docker-compose ps` 输出
   - 服务器系统信息：`uname -a`

2. 联系支持：
   - GitHub Issues: https://github.com/yourusername/innerseek/issues
   - 邮箱: hello@innerseek.me
   - 微信: innerseek2026
