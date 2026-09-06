#!/bin/bash

# 辰鉴部署脚本
# 支持本地和远程部署

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 默认配置
REMOTE_HOST="${REMOTE_HOST:-8.135.25.206}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/innerpath}"
REMOTE_PORT="${REMOTE_PORT:-22}"

# 显示使用说明
show_usage() {
    echo "辰鉴部署脚本"
    echo ""
    echo "用法:"
    echo "  $0 local              # 本地部署（同 dev.sh）"
    echo "  $0 remote init        # 远程首次部署"
    echo "  $0 remote update      # 远程快速更新"
    echo ""
    echo "环境变量:"
    echo "  REMOTE_HOST          # 远程服务器地址（默认: 8.135.25.206）"
    echo "  REMOTE_USER          # SSH 用户名（默认: root）"
    echo "  REMOTE_DIR           # 部署目录（默认: /opt/innerpath）"
    echo "  REMOTE_PORT          # SSH 端口（默认: 22）"
    echo ""
    echo "示例:"
    echo "  $0 remote init                    # 使用默认服务器"
    echo "  export REMOTE_HOST=1.2.3.4        # 或指定其他服务器"
    echo "  $0 remote init"
}

# 本地部署
deploy_local() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}辰鉴本地部署${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  .env 文件不存在，从 .env.example 复制${NC}"
        cp .env.example .env
        echo -e "${RED}请编辑 .env 文件后重新运行${NC}"
        exit 1
    fi

    echo -e "${GREEN}停止现有容器...${NC}"
    docker compose down 2>/dev/null || true

    echo -e "${GREEN}构建并启动服务...${NC}"
    docker compose up -d --build

    echo ""
    echo -e "${GREEN}✅ 部署完成！${NC}"
    echo -e "前端: ${YELLOW}http://localhost${NC}"
    echo -e "后端: ${YELLOW}http://localhost:8000/docs${NC}"
}

# 远程首次部署
deploy_remote_init() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}辰鉴远程首次部署${NC}"
    echo -e "${GREEN}目标: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # 检查必需文件
    echo -e "${GREEN}[1/8] 检查本地文件...${NC}"
    for file in docker-compose.yml Dockerfile.frontend backend/Dockerfile .env.example; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}错误: 缺少文件 $file${NC}"
            exit 1
        fi
    done

    # 创建部署包
    echo -e "${GREEN}[2/8] 创建部署包...${NC}"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    PACKAGE="innerpath_${TIMESTAMP}.tar.gz"
    tar -czf "/tmp/${PACKAGE}" \
        --exclude=node_modules \
        --exclude=.git \
        --exclude=.venv \
        --exclude=__pycache__ \
        --exclude=dist \
        --exclude=logs \
        --exclude=.env \
        .

    # 上传到服务器
    echo -e "${GREEN}[3/8] 上传到服务器...${NC}"
    scp -P ${REMOTE_PORT} "/tmp/${PACKAGE}" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/"

    # 在服务器上部署
    echo -e "${GREEN}[4/8] 解压并部署...${NC}"
    ssh -p ${REMOTE_PORT} "${REMOTE_USER}@${REMOTE_HOST}" << EOF
        set -e

        # 创建部署目录
        mkdir -p ${REMOTE_DIR}/current

        # 备份旧版本
        if [ -d "${REMOTE_DIR}/current" ] && [ "\$(ls -A ${REMOTE_DIR}/current)" ]; then
            BACKUP_DIR="${REMOTE_DIR}/backup_\$(date +%Y%m%d_%H%M%S)"
            echo "备份旧版本到 \${BACKUP_DIR}"
            mv ${REMOTE_DIR}/current \${BACKUP_DIR}
            mkdir -p ${REMOTE_DIR}/current
        fi

        # 解压新版本
        tar -xzf /tmp/${PACKAGE} -C ${REMOTE_DIR}/current
        cd ${REMOTE_DIR}/current

        # 检查 .env 文件
        if [ ! -f ".env" ]; then
            echo "创建 .env 文件（从 .env.example）"
            cp .env.example .env
            echo "⚠️  请编辑 ${REMOTE_DIR}/current/.env 文件"
        fi

        # 启动服务
        docker compose down 2>/dev/null || true
        docker compose up -d --build

        # 清理
        rm -f /tmp/${PACKAGE}

        echo ""
        echo "部署完成！"
        docker compose ps
EOF

    # 清理本地临时文件
    rm -f "/tmp/${PACKAGE}"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 远程部署完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址: ${YELLOW}http://${REMOTE_HOST}${NC}"
    echo -e "API 文档: ${YELLOW}http://${REMOTE_HOST}:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  请登录服务器编辑 .env 文件：${NC}"
    echo -e "ssh ${REMOTE_USER}@${REMOTE_HOST}"
    echo -e "vim ${REMOTE_DIR}/current/.env"
}

# 远程快速更新
deploy_remote_update() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}辰鉴远程快速更新${NC}"
    echo -e "${GREEN}目标: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # 创建更新包
    echo -e "${GREEN}[1/5] 创建更新包...${NC}"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    PACKAGE="innerpath_update_${TIMESTAMP}.tar.gz"
    tar -czf "/tmp/${PACKAGE}" \
        --exclude=node_modules \
        --exclude=.git \
        --exclude=.venv \
        --exclude=__pycache__ \
        --exclude=dist \
        --exclude=logs \
        --exclude=.env \
        .

    # 上传
    echo -e "${GREEN}[2/5] 上传到服务器...${NC}"
    scp -P ${REMOTE_PORT} "/tmp/${PACKAGE}" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/"

    # 更新
    echo -e "${GREEN}[3/5] 更新服务...${NC}"
    ssh -p ${REMOTE_PORT} "${REMOTE_USER}@${REMOTE_HOST}" << EOF
        set -e
        cd ${REMOTE_DIR}/current

        # 备份 .env
        cp .env /tmp/.env.backup

        # 停止服务
        docker compose down

        # 解压新文件
        tar -xzf /tmp/${PACKAGE} -C ${REMOTE_DIR}/current

        # 恢复 .env
        mv /tmp/.env.backup .env

        # 重新构建并启动
        docker compose build --no-cache
        docker compose up -d

        # 清理
        rm -f /tmp/${PACKAGE}

        echo ""
        echo "更新完成！"
        docker compose ps
EOF

    # 清理本地临时文件
    rm -f "/tmp/${PACKAGE}"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 更新完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# 主逻辑
case "${1:-}" in
    local)
        deploy_local
        ;;
    remote)
        case "${2:-}" in
            init)
                deploy_remote_init
                ;;
            update)
                deploy_remote_update
                ;;
            *)
                echo -e "${RED}错误: 未知的远程操作 '${2:-}'${NC}"
                show_usage
                exit 1
                ;;
        esac
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
