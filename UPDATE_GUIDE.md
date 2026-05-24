# 更新脚本使用指南

## 快速开始

### 1. 测试脚本（推荐先执行）

```bash
# 快速检查环境
./test-update.sh

# 完整模拟测试（不连接真实服务器）
./test-update-full.sh
```

### 2. 执行更新

```bash
# 使用默认配置（8.135.25.206）
./update.sh

# 或自定义服务器
export REMOTE_HOST=your.server.com
export REMOTE_USER=root
export REMOTE_DIR=/opt/innerseek
./update.sh
```

## 脚本说明

### update.sh - 快速更新脚本

**功能**：
- 打包最新代码
- 上传到远程服务器
- 保留 .env 配置
- 重新构建 Docker 镜像
- 重启所有服务

**执行步骤**：
1. [1/5] 检查本地文件
2. [2/5] 打包项目文件（~112M）
3. [3/5] 上传到服务器
4. [4/5] 在服务器上更新
5. [5/5] 重启 Docker 服务

**预计耗时**：5-10 分钟（取决于网络速度）

### test-update.sh - 快速测试

**功能**：
- 检查脚本语法
- 检查必要文件
- 测试打包功能
- 检查环境变量

**执行时间**：~30 秒

### test-update-full.sh - 完整模拟测试

**功能**：
- 模拟完整更新流程
- 不连接真实服务器
- 验证所有命令正确性

**执行时间**：~1 分钟

## 已修复的问题

### 问题 1: 脚本中途退出
**原因**：heredoc 使用单引号导致变量无法展开
**修复**：移除单引号，使用 `<< ENDSSH` 而不是 `<< 'ENDSSH'`

### 问题 2: tar 打包失败
**原因**：tar 警告 "file changed as we read it" 被当作错误
**修复**：
- 重定向 stderr 到 /dev/null
- 排除 tar 包本身
- 检查文件是否存在而不是依赖退出码

### 问题 3: 意外退出
**原因**：全局 `set -e` 导致任何命令失败都退出
**修复**：移除 `set -e`，使用显式错误检查和容错机制

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| REMOTE_HOST | 8.135.25.206 | 远程服务器地址 |
| REMOTE_USER | root | SSH 用户名 |
| REMOTE_DIR | /opt/innerseek | 部署目录 |
| REMOTE_PORT | 22 | SSH 端口 |

## 使用示例

### 示例 1: 更新到默认服务器

```bash
./update.sh
```

输出：
```
==========================================
离火引网站 - Docker 快速更新
==========================================

目标服务器: root@8.135.25.206
部署目录: /opt/innerseek

确认更新? (y/n) y

[1/5] 检查本地文件...
[2/5] 打包项目文件...
✓ 打包完成: innerseek-update-20260524-143811.tar.gz

[3/5] 上传到服务器...
✓ 上传完成

[4/5] 在服务器上更新...
备份 .env 文件...
解压更新文件...
恢复 .env 文件...
✓ 文件更新完成

[5/5] 重启 Docker 服务...
重新构建 Docker 镜像...
停止旧服务...
启动新服务...
等待服务启动...
检查服务状态...
✓ 服务重启完成

==========================================
🎉 更新成功！
==========================================

网站地址: http://8.135.25.206

查看日志:
  ssh root@8.135.25.206 'cd /opt/innerseek/current && docker-compose logs -f'
```

### 示例 2: 更新到自定义服务器

```bash
export REMOTE_HOST=your.server.com
export REMOTE_USER=admin
export REMOTE_DIR=/home/admin/innerseek
./update.sh
```

### 示例 3: 先测试再更新

```bash
# 1. 快速测试
./test-update.sh

# 2. 完整模拟测试
./test-update-full.sh

# 3. 确认无误后执行更新
./update.sh
```

## 故障排查

### 问题：上传失败

```bash
# 检查 SSH 连接
ssh root@8.135.25.206 "echo OK"

# 检查 /tmp 目录权限
ssh root@8.135.25.206 "ls -la /tmp"
```

### 问题：Docker 构建失败

```bash
# 查看 Docker 日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs"

# 清理 Docker 缓存
ssh root@8.135.25.206 "docker system prune -a"
```

### 问题：服务无法启动

```bash
# 检查服务状态
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose ps"

# 查看详细日志
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f"

# 重启服务
ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose restart"
```

### 问题：.env 文件丢失

```bash
# 手动恢复
scp .env root@8.135.25.206:/opt/innerseek/current/

# 或在服务器上重新创建
ssh root@8.135.25.206
cd /opt/innerseek/current
cp .env.example .env
vim .env  # 填入正确配置
docker-compose restart
```

## 回滚

如果更新后出现问题，使用 deploy.sh 创建的备份回滚：

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

## 最佳实践

1. **更新前备份**
   ```bash
   ssh root@8.135.25.206 "cd /opt/innerseek && cp -r current backup-manual-$(date +%Y%m%d-%H%M%S)"
   ```

2. **本地测试**
   ```bash
   ./build.sh
   # 测试所有功能
   ```

3. **先测试脚本**
   ```bash
   ./test-update-full.sh
   ```

4. **监控更新过程**
   ```bash
   # 在另一个终端监控日志
   ssh root@8.135.25.206 "cd /opt/innerseek/current && docker-compose logs -f"
   ```

5. **验证更新结果**
   ```bash
   curl http://8.135.25.206/health
   # 手动测试关键功能
   ```

## 与 deploy.sh 的区别

| 特性 | deploy.sh | update.sh |
|------|-----------|-----------|
| 用途 | 首次部署 | 日常更新 |
| 备份 | 创建完整备份 | 不创建备份 |
| 速度 | 较慢 | 较快 |
| .env | 检查/创建 | 保留现有 |
| 适用场景 | 大版本更新 | bug 修复、小更新 |

## 联系支持

如有问题：
- 查看 TROUBLESHOOTING.md
- GitHub Issues: https://github.com/yourusername/innerseek/issues
- 邮箱: hello@innerseek.me
- 微信: innerseek2026
