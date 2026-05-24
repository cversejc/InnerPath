from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.core.cache import init_redis, close_redis
from app.core.logging_config import setup_logging, get_logger
from app.api.v1 import auth, users, reports, bookings, courses
import time

# 初始化日志系统
setup_logging(
    app_name=settings.APP_NAME,
    log_level=settings.LOG_LEVEL,
    log_dir="logs"
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("应用启动中...")
    await init_redis()
    logger.info("Redis 连接已建立")
    logger.info(f"应用启动完成 | 环境: {settings.ENVIRONMENT} | 调试模式: {settings.DEBUG}")
    yield
    # Shutdown
    logger.info("应用关闭中...")
    await close_redis()
    logger.info("应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有 HTTP 请求"""
    request_id = str(time.time())
    start_time = time.time()

    # 记录请求
    logger.info(
        f"请求开始 | {request.method} {request.url.path} | "
        f"客户端: {request.client.host} | ID: {request_id}"
    )

    # 处理请求
    try:
        response = await call_next(request)
        elapsed = (time.time() - start_time) * 1000

        # 记录响应
        logger.info(
            f"请求完成 | {request.method} {request.url.path} | "
            f"状态: {response.status_code} | 耗时: {elapsed:.2f}ms | ID: {request_id}"
        )

        return response
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(
            f"请求失败 | {request.method} {request.url.path} | "
            f"耗时: {elapsed:.2f}ms | 错误: {str(e)} | ID: {request_id}",
            exc_info=True
        )
        raise


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        f"全局异常捕获 | {request.method} {request.url.path} | "
        f"错误类型: {type(exc).__name__} | 错误信息: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to InnerPath API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
