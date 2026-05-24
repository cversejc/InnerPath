# SSH 免密登录配置指南（Windows）

## 方法一：使用 Git Bash（推荐）

1. 打开 Git Bash

2. 生成密钥：
```bash
ssh-keygen -t rsa -b 4096
```
按三次回车（使用默认设置）

3. 复制公钥到服务器：
```bash
cat ~/.ssh/id_rsa.pub | ssh root@8.135.25.206 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```
输入密码：Cjc123456

4. 测试免密登录：
```bash
ssh root@8.135.25.206
```
应该不需要密码了！

---

## 方法二：手动配置

### 步骤 1：生成密钥

在 PowerShell 中：
```powershell
ssh-keygen -t rsa -b 4096
```
按三次回车

### 步骤 2：查看公钥

```powershell
notepad $env:USERPROFILE\.ssh\id_rsa.pub
```
复制所有内容（Ctrl+A, Ctrl+C）

### 步骤 3：登录服务器

```powershell
ssh root@8.135.25.206
```
输入密码：Cjc123456

### 步骤 4：在服务器上添加公钥

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
```

粘贴刚才复制的公钥内容，保存退出（Ctrl+X, Y, Enter）

```bash
chmod 600 ~/.ssh/authorized_keys
exit
```

### 步骤 5：测试

```powershell
ssh root@8.135.25.206
```
应该不需要密码了！

---

## 验证是否成功

如果配置成功，执行以下命令不需要输入密码：

```bash
ssh root@8.135.25.206 "echo 'Success!'"
```

---

## 配置成功后

以后使用更新脚本就不需要输入密码了：

**Git Bash:**
```bash
./update.sh
```

**PowerShell:**
```powershell
.\update.ps1
```

一键更新，无需密码！🎉
