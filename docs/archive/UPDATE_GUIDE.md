# 离火引网站 - 更新部署指南

## 🚀 快速更新方法

修改代码后，使用以下脚本一键更新到服务器：

### 方法1：使用 update.sh（推荐）

**Git Bash / Linux / Mac:**
```bash
./update.sh
```

**PowerShell:**
```powershell
.\update.ps1
```

**功能：**
- ✅ 自动构建项目
- ✅ 自动打包文件
- ✅ 自动上传到服务器
- ✅ 自动部署更新

**使用步骤：**
1. 修改代码
2. 运行脚本
3. 输入密码（两次）
4. 完成！

---

### 方法2：使用 sync.sh（更快）

如果你的系统支持 rsync：

```bash
./sync.sh
```

**优势：**
- ⚡ 只传输变化的文件，速度更快
- 🔄 增量同步，节省带宽
- 🗑️ 自动删除服务器上多余的文件

---

## 📝 手动更新步骤

如果脚本无法使用，可以手动执行：

```bash
# 1. 构建
npm run build

# 2. 打包
cd dist && tar -czf ../dist.tar.gz . && cd ..

# 3. 上传
scp dist.tar.gz root@8.135.25.206:/tmp/

# 4. 部署
ssh root@8.135.25.206
cd /var/www/innerseek
tar -xzf /tmp/dist.tar.gz
rm /tmp/dist.tar.gz
exit
```

---

## 🔧 常见问题

### Q: 每次都要输入两次密码？
**A:** 可以配置 SSH 密钥免密登录：

```bash
# 1. 生成密钥（如果还没有）
ssh-keygen -t rsa -b 4096

# 2. 复制公钥到服务器
ssh-copy-id root@8.135.25.206

# 3. 之后就不需要输入密码了
```

### Q: 如何查看网站是否更新成功？
**A:** 
1. 访问 http://8.135.25.206
2. 按 Ctrl+F5 强制刷新浏览器缓存
3. 检查修改的内容是否生效

### Q: 更新后网站显示异常？
**A:** 
```bash
# 登录服务器检查
ssh root@8.135.25.206

# 查看文件是否正确
ls -la /var/www/innerseek

# 查看 Nginx 日志
tail -f /var/log/nginx/error.log

# 重启 Nginx
systemctl restart nginx
```

---

## 🎯 开发工作流

推荐的开发流程：

```bash
# 1. 本地开发
npm run dev

# 2. 修改代码并测试
# 在浏览器中访问 http://localhost:3000

# 3. 确认无误后更新到服务器
./update.sh  # 或 .\update.ps1

# 4. 验证线上效果
# 访问 http://8.135.25.206
```

---

## 📊 脚本对比

| 特性 | update.sh | sync.sh | 手动更新 |
|------|-----------|---------|----------|
| 速度 | 中等 | 快 | 慢 |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 依赖 | SSH/SCP | rsync | SSH/SCP |
| 推荐度 | ✅ 推荐 | ✅ 高级用户 | ⚠️ 备用 |

---

## 💡 提示

- 首次部署使用 `deploy-interactive.sh`
- 日常更新使用 `update.sh` 或 `update.ps1`
- 频繁更新使用 `sync.sh`（需要 rsync）
- 配置 SSH 密钥后，更新速度会更快

---

## 🔐 配置 SSH 密钥（可选但推荐）

**Windows (Git Bash):**
```bash
# 生成密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 复制公钥到服务器
cat ~/.ssh/id_rsa.pub | ssh root@8.135.25.206 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# 测试
ssh root@8.135.25.206  # 应该不需要密码了
```

配置后，所有脚本都不需要输入密码！

---

## 📞 需要帮助？

如果遇到问题：
1. 检查网络连接
2. 确认服务器 IP 和密码正确
3. 查看脚本输出的错误信息
4. 检查服务器磁盘空间：`df -h`
