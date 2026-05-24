# 快速开始指南

5 分钟快速启动 InnerSeek 项目。

## 前置要求

- Docker 和 Docker Compose
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/)）

## 快速启动

### Windows 用户

```bash
# 1. 配置环境变量
copy .env.example .env

# 2. 编辑 .env 文件，填入你的 API Key
notepad .env

# 3. 启动服务
deploy.bat
```

### Linux/Mac 用户

```bash
# 1. 配置环境变量
cp .env.example .env

# 2. 编辑 .env 文件，填入你的 API Key
vim .env

# 3. 启动服务
chmod +x build.sh
./build.sh
```

## 访问服务

启动成功后，在浏览器中访问：

- **前端应用**: http://localhost
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 测试功能

1. 打开 http://localhost
2. 点击"开始探索"
3. 填写测评信息（可以使用测试数据）
4. 等待 AI 生成报告（约 30 秒）
5. 查看完整的个人成长报告

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

## 故障排查

### 端口被占用

如果 80 或 8000 端口被占用，修改 `docker-compose.yml`：

```yaml
services:
  frontend:
    ports:
      - "3000:80"  # 改为 3000 端口
  
  backend:
    ports:
      - "8001:8000"  # 改为 8001 端口
```

### API Key 无效

确认 `.env` 文件中的 API Key 格式正确：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 服务无法启动

查看详细日志：

```bash
docker-compose logs backend
docker-compose logs frontend
```

## 下一步

- 查看 [README.md](./README.md) 了解项目详情
- 查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 了解部署指南
- 查看 API 文档: http://localhost:8000/docs

## 需要帮助？

- GitHub Issues: https://github.com/yourusername/innerseek/issues
- 邮箱: hello@innerseek.me
- 微信: innerseek2026
