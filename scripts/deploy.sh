#!/bin/bash

# 辰鉴部署脚本
# 支持本地和远程部署，并在远程部署前校验证书和 HTTPS。

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 默认配置
REMOTE_HOST="${REMOTE_HOST:-47.82.81.147}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/innerpath}"
REMOTE_PORT="${REMOTE_PORT:-22}"
DOMAIN="${DOMAIN:-chenvis.com}"
SSL_DIR="${SSL_DIR:-${REMOTE_DIR}/ssl}"
PACKAGE=""

show_usage() {
    echo "辰鉴部署脚本"
    echo ""
    echo "用法:"
    echo "  $0 local              # 本地部署"
    echo "  $0 remote init        # 远程首次部署"
    echo "  $0 remote update      # 远程快速更新"
    echo ""
    echo "环境变量:"
    echo "  REMOTE_HOST          # 远程服务器地址（默认: 47.82.81.147）"
    echo "  REMOTE_USER          # SSH 用户名（默认: root）"
    echo "  REMOTE_DIR           # 部署目录（默认: /opt/innerpath）"
    echo "  REMOTE_PORT          # SSH 端口（默认: 22）"
    echo "  DOMAIN               # HTTPS 域名（默认: chenvis.com）"
    echo "  SSL_DIR              # 服务器证书目录（默认: \${REMOTE_DIR}/ssl）"
    echo ""
    echo "示例:"
    echo "  $0 remote init"
    echo "  REMOTE_HOST=1.2.3.4 DOMAIN=example.com $0 remote update"
}

check_local_files() {
    for file in docker-compose.yml nginx.conf Dockerfile.frontend backend/Dockerfile .env.example; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}错误: 缺少文件 $file${NC}"
            exit 1
        fi
    done
}

create_package() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    PACKAGE="/tmp/innerpath_${timestamp}.tar.gz"
    tar -czf "$PACKAGE" \
        --exclude=node_modules \
        --exclude=.git \
        --exclude=.venv \
        --exclude=__pycache__ \
        --exclude=dist \
        --exclude=logs \
        --exclude=.env \
        .
}

cleanup_package() {
    if [ -n "${PACKAGE}" ]; then
        rm -f "$PACKAGE"
    fi
}

trap cleanup_package EXIT

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

deploy_remote_init() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}辰鉴远程首次部署${NC}"
    echo -e "${GREEN}目标: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}${NC}"
    echo -e "${GREEN}HTTPS: ${DOMAIN}${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    echo -e "${GREEN}[1/8] 检查本地文件...${NC}"
    check_local_files

    echo -e "${GREEN}[2/8] 创建部署包...${NC}"
    create_package

    echo -e "${GREEN}[3/8] 上传到服务器...${NC}"
    scp -P "${REMOTE_PORT}" "$PACKAGE" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/"

    echo -e "${GREEN}[4/8] 校验证书并部署文件...${NC}"
    ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" << EOF
        set -eu

        REMOTE_DIR="${REMOTE_DIR}"
        SSL_DIR="${SSL_DIR}"
        DOMAIN="${DOMAIN}"

        # 首次部署先生成 .env，但不使用占位密钥直接启动生产服务。
        if [ ! -f "\${REMOTE_DIR}/current/.env" ]; then
            mkdir -p "\${REMOTE_DIR}/current"
            tar -xzf /tmp/${PACKAGE} -C "\${REMOTE_DIR}/current"
            cp "\${REMOTE_DIR}/current/.env.example" "\${REMOTE_DIR}/current/.env"
            echo "已创建 \${REMOTE_DIR}/current/.env，请填入生产配置后重新运行部署。"
            exit 2
        fi

        if ! grep -Eq '^SESSION_COOKIE_SECURE=(true|1|yes)$' "\${REMOTE_DIR}/current/.env"; then
            echo "错误: 生产环境必须设置 SESSION_COOKIE_SECURE=true"
            exit 1
        fi
        if ! grep -Fq "https://${DOMAIN}" "\${REMOTE_DIR}/current/.env"; then
            echo "错误: CORS_ORIGINS 必须包含 https://${DOMAIN}"
            exit 1
        fi

        if [ ! -s "\${SSL_DIR}/fullchain.pem" ] || [ ! -s "\${SSL_DIR}/privkey.pem" ]; then
            echo "错误: 缺少 HTTPS 证书或私钥: \${SSL_DIR}"
            exit 1
        fi
        openssl x509 -in "\${SSL_DIR}/fullchain.pem" -noout -checkend 0
        if ! openssl x509 -in "\${SSL_DIR}/fullchain.pem" -noout -ext subjectAltName | grep -Fq "DNS:\${DOMAIN}"; then
            echo "错误: 证书不包含域名 \${DOMAIN}"
            exit 1
        fi
        cert_pub=\$(openssl x509 -in "\${SSL_DIR}/fullchain.pem" -pubkey -noout | openssl pkey -pubin -outform DER | sha256sum | awk '{print \$1}')
        key_pub=\$(openssl pkey -in "\${SSL_DIR}/privkey.pem" -pubout -outform DER | sha256sum | awk '{print \$1}')
        if [ "\${cert_pub}" != "\${key_pub}" ]; then
            echo "错误: 证书与私钥不匹配"
            exit 1
        fi
        chmod 600 "\${SSL_DIR}/privkey.pem"

        ENV_BACKUP="/tmp/innerpath_env_backup_\$\$.env"
        cp "\${REMOTE_DIR}/current/.env" "\${ENV_BACKUP}"

        if [ -d "\${REMOTE_DIR}/current" ] && [ "\$(ls -A "\${REMOTE_DIR}/current")" ]; then
            BACKUP_DIR="\${REMOTE_DIR}/backup_\$(date +%Y%m%d_%H%M%S)"
            echo "备份旧版本到 \${BACKUP_DIR}"
            mv "\${REMOTE_DIR}/current" "\${BACKUP_DIR}"
        fi
        mkdir -p "\${REMOTE_DIR}/current"
        tar -xzf /tmp/${PACKAGE} -C "\${REMOTE_DIR}/current"
        mv "\${ENV_BACKUP}" "\${REMOTE_DIR}/current/.env"
        cd "\${REMOTE_DIR}/current"
        export SSL_DIR

        docker compose config -q
        docker compose down 2>/dev/null || true
        docker compose up -d --build

        for attempt in \$(seq 1 30); do
            if curl --noproxy '*' -ksSf --resolve "\${DOMAIN}:443:127.0.0.1" "https://\${DOMAIN}/health" >/dev/null; then
                docker exec innerpath-frontend nginx -t
                docker compose ps
                rm -f /tmp/${PACKAGE}
                echo "HTTPS 验证通过: https://\${DOMAIN}"
                exit 0
            fi
            sleep 2
        done
        echo "错误: HTTPS 健康检查失败"
        docker compose ps
        exit 1
EOF
    cleanup_package

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 远程部署完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址: ${YELLOW}https://${DOMAIN}${NC}"
    echo -e "证书目录: ${YELLOW}${SSL_DIR}${NC}"
    echo -e "${YELLOW}证书更新后的重载命令: docker exec innerpath-frontend nginx -s reload${NC}"
}

deploy_remote_update() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}辰鉴远程快速更新${NC}"
    echo -e "${GREEN}目标: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}${NC}"
    echo -e "${GREEN}HTTPS: ${DOMAIN}${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    echo -e "${GREEN}[1/6] 检查本地文件...${NC}"
    check_local_files

    echo -e "${GREEN}[2/6] 创建更新包...${NC}"
    create_package

    echo -e "${GREEN}[3/6] 上传到服务器...${NC}"
    scp -P "${REMOTE_PORT}" "$PACKAGE" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/"

    echo -e "${GREEN}[4/6] 校验证书和 Compose 配置...${NC}"
    ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" << EOF
        set -eu

        REMOTE_DIR="${REMOTE_DIR}"
        SSL_DIR="${SSL_DIR}"
        DOMAIN="${DOMAIN}"
        CURRENT_DIR="\${REMOTE_DIR}/current"
        STAGE_DIR="\${REMOTE_DIR}/.deploy_stage_\$(date +%s)"

        if [ ! -f "\${CURRENT_DIR}/.env" ]; then
            echo "错误: \${CURRENT_DIR}/.env 不存在，请先完成首次部署配置。"
            exit 1
        fi
        if ! grep -Eq '^SESSION_COOKIE_SECURE=(true|1|yes)$' "\${CURRENT_DIR}/.env"; then
            echo "错误: 生产环境必须设置 SESSION_COOKIE_SECURE=true"
            exit 1
        fi
        if ! grep -Fq "https://${DOMAIN}" "\${CURRENT_DIR}/.env"; then
            echo "错误: CORS_ORIGINS 必须包含 https://${DOMAIN}"
            exit 1
        fi
        if [ ! -s "\${SSL_DIR}/fullchain.pem" ] || [ ! -s "\${SSL_DIR}/privkey.pem" ]; then
            echo "错误: 缺少 HTTPS 证书或私钥: \${SSL_DIR}"
            exit 1
        fi
        openssl x509 -in "\${SSL_DIR}/fullchain.pem" -noout -checkend 0
        if ! openssl x509 -in "\${SSL_DIR}/fullchain.pem" -noout -ext subjectAltName | grep -Fq "DNS:\${DOMAIN}"; then
            echo "错误: 证书不包含域名 \${DOMAIN}"
            exit 1
        fi
        cert_pub=\$(openssl x509 -in "\${SSL_DIR}/fullchain.pem" -pubkey -noout | openssl pkey -pubin -outform DER | sha256sum | awk '{print \$1}')
        key_pub=\$(openssl pkey -in "\${SSL_DIR}/privkey.pem" -pubout -outform DER | sha256sum | awk '{print \$1}')
        if [ "\${cert_pub}" != "\${key_pub}" ]; then
            echo "错误: 证书与私钥不匹配"
            exit 1
        fi
        chmod 600 "\${SSL_DIR}/privkey.pem"

        mkdir -p "\${STAGE_DIR}"
        tar -xzf /tmp/${PACKAGE} -C "\${STAGE_DIR}"
        cp "\${CURRENT_DIR}/.env" "\${STAGE_DIR}/.env"
        cd "\${STAGE_DIR}"
        export SSL_DIR
        docker compose config -q
        cd "\${CURRENT_DIR}"

        ENV_BACKUP="/tmp/innerpath_env_backup_\$\$.env"
        cp .env "\${ENV_BACKUP}"
        docker compose down
        tar -xzf /tmp/${PACKAGE} -C "\${CURRENT_DIR}"
        mv "\${ENV_BACKUP}" "\${CURRENT_DIR}/.env"
        rm -rf "\${STAGE_DIR}"
        cd "\${CURRENT_DIR}"
        export SSL_DIR

        echo "[5/6] 构建并启动服务..."
        docker compose up -d --build
        for attempt in \$(seq 1 30); do
            if curl --noproxy '*' -ksSf --resolve "\${DOMAIN}:443:127.0.0.1" "https://\${DOMAIN}/health" >/dev/null; then
                docker exec innerpath-frontend nginx -t
                docker compose ps
                rm -f /tmp/${PACKAGE}
                echo "HTTPS 验证通过: https://\${DOMAIN}"
                exit 0
            fi
            sleep 2
        done
        echo "错误: HTTPS 健康检查失败"
        docker compose ps
        exit 1
EOF
    cleanup_package

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 更新完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "访问地址: ${YELLOW}https://${DOMAIN}${NC}"
}

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
