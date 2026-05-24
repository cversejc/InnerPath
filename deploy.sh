#!/bin/bash

# InnerSeek 一键部署脚本
# 用于将项目部署到远程服务器

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_HOST="${REMOTE_HOST}"
REMOTE_DIR="${REMOTE_DIR:-/opt/innerseek}"
REMOTE_PORT="${REMOTE_PORT:-22}"

# 检查必要的环境变量
if [ -z "$REMOTE_HOST" ]; then
    echo -e "${RED}错误: 请设置 REMOTE_HOST 环境变量${NC}"
    echo "示例: export REMOTE_HOST=your.server.com"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}InnerSeek 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "目标服务器: ${YELLOW}${REMOTE_USER}@${REMOTE_HOST}${NC}"
echo -e "部署目录: ${YELLOW}${REMOTE_DIR}${NC}"
echo ""

# 确认部署
read -p "确认部署? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}部署已取消${NC}"
    exit 0
fi

echo -e "${GREEN}[1/6] 检查本地文件...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: docker-compose.yml 不存在${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，将使用 .env.example${NC}"
    if [ ! -f ".env.example" ]; then
        echo -e "${RED}错误: .env.example 也不存在${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}[2/6] 创建部署包...${NC}"
DEPLOY_PACKAGE="innerseek-deploy-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$DEPLOY_PACKAGE" \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='backend/logs' \
    --exclude='*.log' \
    --exclude='.env' \
    --exclude='docs/archive' \
    --exclude='innerseek-deploy-*.tar.gz' \
    --exclude='innerseek-update-*.tar.gz' \
    --exclude='test-package-*.tar.gz' \
    . 2>/dev/null

# 检查打包是否成功
if [ ! -f "$DEPLOY_PACKAGE" ]; then
    echo -e "${RED}错误: 打包失败${NC}"
    exit 1
fi

PACKAGE_SIZE=$(du -h "$DEPLOY_PACKAGE" | cut -f1)
echo -e "${GREEN}✓ 打包完成: ${DEPLOY_PACKAGE} (${PACKAGE_SIZE})${NC}"
echo ""

echo -e "${GREEN}[3/6] 上传到服务器...${NC}"
echo "文件大小: ${PACKAGE_SIZE}"
echo "目标: ${REMOTE_USER}@${REMOTE_HOST}:/tmp/"
echo ""

# 尝试上传，最多重试 3 次
UPLOAD_SUCCESS=false
for i in {1..3}; do
    if [ $i -gt 1 ]; then
        echo -e "${YELLOW}重试上传 (${i}/3)...${NC}"
    fi

    if command -v rsync &> /dev/null; then
        echo "使用 rsync 上传..."
        rsync -avz --progress --partial \
            -e "ssh -p ${REMOTE_PORT}" \
            "$DEPLOY_PACKAGE" \
            "${REMOTE_USER}@${REMOTE_HOST}:/tmp/" && UPLOAD_SUCCESS=true && break
    else
        echo "使用 scp 上传..."
        scp -C -P "$REMOTE_PORT" "$DEPLOY_PACKAGE" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/" && UPLOAD_SUCCESS=true && break
    fi

    if [ $i -lt 3 ]; then
        echo -e "${YELLOW}上传失败，等待 5 秒后重试...${NC}"
        sleep 5
    fi
done

if [ "$UPLOAD_SUCCESS" = false ]; then
    echo -e "${RED}错误: 上传失败，已重试 3 次${NC}"
    rm -f "$DEPLOY_PACKAGE"
    exit 1
fi

echo -e "${GREEN}✓ 上传完成${NC}"
echo ""

echo -e "${GREEN}[4/6] 在服务器上解压...${NC}"
ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" << ENDSSH
set -e

# 创建部署目录
mkdir -p ${REMOTE_DIR}
cd ${REMOTE_DIR}

# 备份旧版本
if [ -d "current" ]; then
    echo "备份当前版本..."
    BACKUP_DIR="backup-\$(date +%Y%m%d-%H%M%S)"
    mv current "\$BACKUP_DIR"
    echo "备份完成: \$BACKUP_DIR"
fi

# 解压新版本
mkdir -p current
tar -xzf /tmp/${DEPLOY_PACKAGE} -C current/
rm /tmp/${DEPLOY_PACKAGE}

cd current

# 检查 .env 文件
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "复制 .env.example 到 .env"
        cp .env.example .env
        echo "警告: 请编辑 .env 文件，填入正确的配置"
    else
        echo "错误: 缺少 .env 文件"
        exit 1
    fi
fi

echo "部署文件准备完成"
ENDSSH

echo -e "${GREEN}[5/6] 启动 Docker 服务...${NC}"
ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" << ENDSSH
set -e
cd ${REMOTE_DIR}/current

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

# 停止旧容器
echo "停止旧容器..."
docker compose down || true

# 构建并启动新容器
echo "构建并启动容器..."
docker compose up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker compose ps

echo "部署完成！"
ENDSSH

echo -e "${GREEN}[6/6] 清理本地部署包...${NC}"
rm "$DEPLOY_PACKAGE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${YELLOW}http://${REMOTE_HOST}${NC}"
echo ""
echo -e "查看日志:"
echo -e "  ${YELLOW}ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR}/current && docker compose logs -f'${NC}"
echo ""
echo -e "重启服务:"
echo -e "  ${YELLOW}ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR}/current && docker compose restart'${NC}"
echo ""
