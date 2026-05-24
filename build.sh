#!/bin/bash

# InnerSeek 本地构建脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}InnerSeek 本地构建${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，从 .env.example 复制${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}请编辑 .env 文件，填入正确的配置${NC}"
    else
        echo "错误: .env.example 不存在"
        exit 1
    fi
fi

echo -e "${GREEN}[1/3] 停止现有容器...${NC}"
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

echo -e "${GREEN}[2/3] 构建 Docker 镜像...${NC}"
docker-compose build || docker compose build

echo -e "${GREEN}[3/3] 启动服务...${NC}"
docker-compose up -d || docker compose up -d

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}构建完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "前端地址: ${YELLOW}http://localhost${NC}"
echo -e "后端地址: ${YELLOW}http://localhost:8000${NC}"
echo -e "API 文档: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "查看日志: ${YELLOW}docker-compose logs -f${NC}"
echo -e "停止服务: ${YELLOW}docker-compose down${NC}"
echo ""
