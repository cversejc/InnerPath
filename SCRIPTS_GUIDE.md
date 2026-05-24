# 部署脚本使用指南

本文档说明项目中各个部署脚本的用途和使用方法。

## 脚本概览

| 脚本 | 用途 | 适用场景 |
|------|------|----------|
| `build.sh` | 本地构建和测试 | 本地开发环境 |
| `deploy.bat` | Windows 本地部署 | Windows 开发环境 |
| `deploy.sh` | 远程服务器首次部署 | 生产环境首次部署 |
| `update.sh` | 远程服务器快速更新 | 生产环境代码更新 |
| `update.bat` | Windows 远程更新 | Windows 环境代码更新 |

---

## 本地开发

### build.sh - 本地构建和测试

**用途**: 在本地使用 Docker 启动完整的开发环境

**使用方法**:
```bash
# Linux/Mac
chmod +x build.sh
./build.sh
```

**功能**:
- 检查 .env 文件
- 停止现有容器
- 构建 Docker 镜像
- 启动所有服务（PostgreSQL, Redis, Backend, Frontend）

**访问地址**:
- 前端: http://localhost
- 后端: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

### deploy.bat - Windows 本地部署

**用途**: Windows 用户的本地部署脚本

**使用方法**:
```bash
deploy.bat
```

**功能**: 与 `build.sh` 相同，但适配 Windows 环境

---

## 远程部署

### deploy.sh - 首次部署到远程服务器

**用途**: 第一次将项目部署到远程服务器

**前置条件**:
- 远程服务器已安装 Docker 和 Docker Compose
- 已配置 SSH 密钥或密码登录
- 服务器防火墙已开放 80/443 端口

**使用方法**:
```bash
# 1. 配置服务器信息
export REMOTE_HOST=8.135.25.206
export REMOTE_USER=root
export REMOTE_DIR=/opt/innerseek
export REMOTE_PORT=22

# 2. 执行部署
chmod +x deploy.sh
./deploy.sh
```

**功能**:
1. 检查本地文件完整性
2. 创建部署包（排除 node_modules, .git 等）
3. 上传到服务器 /tmp/
4. 在服务器上创建部署目录
5. 备份旧版本（如果存在）
6. 解压新版本
7. 检查/创建 .env 文件
8. 构建并启动 Docker 容器
9. 显示服务状态

**部署目录结构**:
```
/opt/innerseek/
├── current/              # 当前运行版本
├── backup-20260524-123456/  # 自动备份
└── backup-20260523-101010/  # 历史备份
```

---

### update.sh - 快速更新远程服务器

**用途**: 已部署后的代码快速更新（不会备份旧版本）

**使用场景**:
- 修复 bug
- 添加新功能
- 更新配置

**使用方法**:
```bash
# Linux/Mac
chmod +x update.sh
./update.sh

# 或指定服务器
export REMOTE_HOST=your.server.com
./update.sh
```

**功能**:
1. 检查本地文件
2. 打包项目（带时间戳）
3. 上传到服务器
4. **备份并保留 .env 文件**（重要！）
5. 解压新文件
6. 恢复 .env 文件
7. 重新构建 Docker 镜像（--no-cache）
8. 重启服务
9. 检查服务状态

**与 deploy.sh 的区别**:
- ✅ 更快（不创建完整备份）
- ✅ 保留 .env 配置
- ✅ 强制重新构建镜像
- ❌ 不备份旧版本（如需回滚，使用 deploy.sh 的备份目录）

---

### update.bat - Windows 快速更新

**用途**: Windows 用户的快速更新脚本

**使用方法**:
```bash
update.bat
```

**功能**: 与 `update.sh` 相同，但适配 Windows 环境

---

## 使用场景示例

### 场景 1: 本地开发测试

```bash
# 1. 配置环境变量
cp .env.example .env
vim .env  # 填入 DeepSeek API Key

# 2. 启动服务
./build.sh

# 3. 访问应用
# 前端: http://localhost
# 后端: http://localhost:8000
```

### 场景 2: 首次部署到生产服务器

```bash
# 1. 确保服务器已安装 Docker
ssh root@8.135.25.206 "docker --version && docker-compose --version"

# 2. 配置部署参数
export REMOTE_HOST=8.135.25.206
export REMOTE_USER=root
export REMOTE_DIR=/opt/innerseek

# 3. 执行部署
./deploy.sh

# 4. 访问网站
# http://8.135.25.206
```

### 场景 3: 修复 bug 后快速更新

```bash
# 1. 本地修改代码
vim src/views/Assessment.vue

# 2. 本地测试
./build.sh
# 测试功能是否正常

# 3. 快速更新到生产环境
./update.sh

# 4. 验证更新
curl http://8.135.25.206/health
```

### 场景 4: 回滚到旧版本

```bash
# 1. SSH 登录服务器
ssh root@8.135.25.206

# 2. 查看备份
cd /opt/innerseek
ls -la

# 3. 停止当前服务
cd current
docker-compose down

# 4. 切换到备份版本
cd ..
rm -rf current
cp -r backup-20260524-123456 current

# 5. 启动服务
cd current
docker-compose up -d
```

---

## 常见问题

### Q: deploy.sh 和 update.sh 有什么区别？

**deploy.sh**:
- 首次部署使用
- 会创建完整备份
- 适合大版本更新

**update.sh**:
- 日常更新使用
- 不创建备份（更快）
- 保留 .env 配置
- 强制重新构建镜像

### Q: 如何查看远程服务器日志？

```bash
# 实时查看所有日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f"

# 查看后端日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f backend"

# 查看最近 100 行日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs --tail=100"
```

### Q: 更新失败如何处理？

1. **查看错误日志**:
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs"
```

2. **检查服务状态**:
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose ps"
```

3. **重启服务**:
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose restart"
```

4. **完全重建**:
```bash
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose down && docker-compose up -d --build"
```

### Q: 如何修改服务器上的 .env 配置？

```bash
# 1. SSH 登录
ssh root@8.135.25.206

# 2. 编辑 .env
cd /opt/innerseek/current
vim .env

# 3. 重启服务使配置生效
docker-compose restart
```

### Q: 端口被占用怎么办？

修改 `docker-compose.yml`:
```yaml
services:
  frontend:
    ports:
      - "3000:80"  # 改为其他端口
  
  backend:
    ports:
      - "8001:8000"  # 改为其他端口
```

---

## 最佳实践

### 1. 部署前检查清单

- [ ] 本地测试通过
- [ ] .env 配置正确
- [ ] 数据库迁移脚本已准备
- [ ] 备份重要数据
- [ ] 通知用户维护时间

### 2. 部署流程

```bash
# 1. 本地测试
./build.sh
# 测试所有功能

# 2. 提交代码
git add .
git commit -m "feat: 添加新功能"
git push

# 3. 部署到生产
./update.sh

# 4. 验证部署
curl http://your-server.com/health
# 手动测试关键功能

# 5. 监控日志
ssh root@your-server.com "cd /opt/innerseek/current && docker-compose logs -f"
```

### 3. 安全建议

- 使用 SSH 密钥而非密码登录
- 定期更新 Docker 镜像
- 配置 HTTPS（Let's Encrypt）
- 设置防火墙规则
- 定期备份数据库

---

## 脚本维护

如需修改脚本，注意：

1. **保持向后兼容**: 不要破坏现有部署
2. **添加错误处理**: 使用 `set -e` 和错误检查
3. **提供清晰输出**: 使用颜色和进度提示
4. **文档同步更新**: 修改脚本后更新本文档

---

## 联系支持

如有问题：
- GitHub Issues: https://github.com/yourusername/innerseek/issues
- 邮箱: hello@innerseek.me
- 微信: innerseek2026
