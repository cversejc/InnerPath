#!/bin/bash
# 离火引网站快速更新脚本（Docker 版本）
# 用法: ./update.sh

# 配置
SERVER="${REMOTE_HOST:-8.135.25.206}"
USER="${REMOTE_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/innerseek}"
REMOTE_PORT="${REMOTE_PORT:-22}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 错误处理函数
error_exit() {
    echo -e "${RED}错误: $1${NC}" >&2
    if [ -n "$PACKAGE_NAME" ] && [ -f "$PACKAGE_NAME" ]; then
        rm -f "$PACKAGE_NAME"
        echo "已清理临时文件"
    fi
    exit 1
}

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}离火引网站 - Docker 快速更新${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "目标服务器: ${YELLOW}${USER}@${SERVER}${NC}"
echo -e "部署目录: ${YELLOW}${REMOTE_DIR}${NC}"
echo ""

# 确认更新
read -p "确认更新? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}更新已取消${NC}"
    exit 0
fi

# 1. 检查本地文件
echo -e "${GREEN}[1/5] 检查本地文件...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: docker-compose.yml 不存在${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，将使用服务器上的配置${NC}"
fi

# 2. 打包项目
echo -e "${GREEN}[2/5] 打包项目文件...${NC}"
PACKAGE_NAME="innerseek-update-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$PACKAGE_NAME" \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='backend/logs' \
    --exclude='*.log' \
    --exclude='docs/archive' \
    --exclude='innerseek-update-*.tar.gz' \
    --exclude='test-package-*.tar.gz' \
    . 2>/dev/null

# 检查打包是否成功（忽略 "file changed as we read it" 警告）
if [ ! -f "$PACKAGE_NAME" ]; then
    error_exit "打包失败"
fi

echo -e "${GREEN}✓ 打包完成: ${PACKAGE_NAME}${NC}"
echo ""

# 3. 上传到服务器
echo -e "${GREEN}[3/5] 上传到服务器...${NC}"
PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "文件大小: ${PACKAGE_SIZE}"
echo "目标: ${USER}@${SERVER}:/tmp/"
echo ""

# 尝试上传，最多重试 3 次
UPLOAD_SUCCESS=false
for i in {1..3}; do
    if [ $i -gt 1 ]; then
        echo -e "${YELLOW}重试上传 (${i}/3)...${NC}"
    fi

    # 使用 rsync 替代 scp，支持断点续传和进度显示
    if command -v rsync &> /dev/null; then
        echo "使用 rsync 上传（支持断点续传）..."
        rsync -avz --progress --partial \
            -e "ssh -p ${REMOTE_PORT}" \
            "$PACKAGE_NAME" \
            "${USER}@${SERVER}:/tmp/" && UPLOAD_SUCCESS=true && break
    else
        echo "使用 scp 上传..."
        # -C 启用压缩，-v 显示详细信息
        scp -C -v -P "$REMOTE_PORT" "$PACKAGE_NAME" "${USER}@${SERVER}:/tmp/" && UPLOAD_SUCCESS=true && break
    fi

    if [ $i -lt 3 ]; then
        echo -e "${YELLOW}上传失败，等待 5 秒后重试...${NC}"
        sleep 5
    fi
done

if [ "$UPLOAD_SUCCESS" = false ]; then
    error_exit "上传失败，已重试 3 次"
fi

# 验证上传的文件
echo ""
echo "验证上传的文件..."
REMOTE_SIZE=$(ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" "du -h /tmp/${PACKAGE_NAME} 2>/dev/null | cut -f1" || echo "")
if [ -z "$REMOTE_SIZE" ]; then
    error_exit "无法验证上传的文件"
fi
echo "远程文件大小: ${REMOTE_SIZE}"

echo -e "${GREEN}✓ 上传完成并验证成功${NC}"
echo ""

# 4. 在服务器上更新
echo -e "${GREEN}[4/5] 在服务器上更新...${NC}"
ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" bash << ENDSSH
cd ${REMOTE_DIR}/current || exit 1

# 备份当前 .env 文件
if [ -f ".env" ]; then
    echo "备份 .env 文件..."
    cp .env /tmp/.env.backup || echo "警告: .env 备份失败"
fi

# 解压新文件
echo "解压更新文件..."
tar -xzf /tmp/${PACKAGE_NAME} || exit 1
rm /tmp/${PACKAGE_NAME}

# 恢复 .env 文件
if [ -f "/tmp/.env.backup" ]; then
    echo "恢复 .env 文件..."
    mv /tmp/.env.backup .env
fi

echo "✓ 文件更新完成"
ENDSSH

if [ $? -ne 0 ]; then
    error_exit "服务器文件更新失败"
fi
echo ""

# 5. 重启 Docker 服务
echo -e "${GREEN}[5/5] 重启 Docker 服务...${NC}"
echo "注意: Docker 构建将在后台运行，可能需要 3-5 分钟"

# 使用单独的 SSH 命令，避免长时间连接超时
ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" "cd ${REMOTE_DIR}/current && docker compose down 2>/dev/null || true"
echo "✓ 已停止旧服务"

# 启动后台构建
ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" "cd ${REMOTE_DIR}/current && nohup docker compose up -d --build > /tmp/docker-build.log 2>&1 &"
echo "✓ Docker 构建已在后台启动"

# 等待并检查构建状态
echo "等待服务启动（最多等待 5 分钟）..."
for i in {1..30}; do
    sleep 10

    # 检查容器是否运行
    RUNNING=$(ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" "docker compose -f ${REMOTE_DIR}/current/docker-compose.yml ps --format json 2>/dev/null | grep -c '\"State\":\"running\"' || echo 0")

    if [ "$RUNNING" -ge 2 ]; then
        echo -e "${GREEN}✓ 服务已成功启动${NC}"

        # 显示服务状态
        echo ""
        echo "服务状态:"
        ssh -p "$REMOTE_PORT" "${USER}@${SERVER}" "cd ${REMOTE_DIR}/current && docker compose ps"

        SUCCESS=true
        break
    else
        echo -n "."
    fi
done

if [ "$SUCCESS" != true ]; then
    echo ""
    echo -e "${YELLOW}警告: 服务启动超时，请手动检查${NC}"
    echo "查看构建日志: ssh ${USER}@${SERVER} 'cat /tmp/docker-build.log'"
    echo "查看服务状态: ssh ${USER}@${SERVER} 'cd ${REMOTE_DIR}/current && docker compose ps'"
    exit 1
fi

if [ $? -eq 0 ] || [ "$SUCCESS" = true ]; then
    echo ""
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}🎉 更新成功！${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo -e "网站地址: ${YELLOW}http://${SERVER}${NC}"
    echo ""
    echo -e "查看日志:"
    echo -e "  ${YELLOW}ssh ${USER}@${SERVER} 'cd ${REMOTE_DIR}/current && docker compose logs -f'${NC}"
    echo ""

    # 清理本地打包文件
    rm -f "$PACKAGE_NAME"
else
    error_exit "Docker 服务重启失败"
fi
