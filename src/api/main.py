"""
API主入口

FastAPI应用主文件
"""

import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.utils.structured_logging import get_logger, configure_logging
from src.utils.graceful_shutdown import shutdown_manager
from src.api.dependencies import init_default_users
from src.api.routers import health, devices, collection, alerts, analysis, knowledge, diagnosis_v2

# 配置日志
configure_logging()
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("API服务启动中...")
    
    # 初始化默认用户
    init_default_users()
    logger.info("默认用户初始化完成")
    
    yield
    
    # 关闭时
    logger.info("API服务关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="Miaota Industrial Agent API",
    description="""
    工业智能监控与诊断系统API
    
    ## 功能模块
    - **数据采集**: PLC数据采集与管理
    - **设备管理**: 设备状态监控与配置
    - **告警管理**: 告警规则与通知
    - **数据分析**: 异常检测与趋势分析
    - **知识库**: 故障诊断与知识检索
    - **智能诊断V2**: 基于MiroFish的多智能体协同诊断
    
    ## V2 新特性 (v1.0.0-beta2)
    - **多智能体协同诊断**: 5位领域专家Agent协作
    - **GraphRAG知识图谱**: 图结构知识检索增强
    - **CAMEL框架集成**: 多智能体社会协作
    - **任务追踪系统**: 长时诊断任务管理
    
    ## 认证方式
    - Bearer Token (JWT)
    - API Key (请求头: X-API-Key)
    """,
    "version="v1.0.0-beta2""}]}
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 记录请求开始
    logger.info(
        f"请求开始: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    try:
        response = await call_next(request)
        
        # 计算耗时
        process_time = time.time() - start_time
        
        # 记录请求完成
        logger.info(
            f"请求完成: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2)
            }
        )
        
        # 添加耗时头
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"请求错误: {request.method} {request.url.path} - {str(e)}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time_ms": round(process_time * 1000, 2)
            }
        )
        raise


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(
        f"未捕获的异常: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"path": request.url.path}
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.warning(
        f"HTTP异常: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            }
        }
    )


# 注册路由
app.include_router(health.router)
app.include_router(devices.router)
app.include_router(collection.router)
app.include_router(alerts.router)
app.include_router(analysis.router)
app.include_router(knowledge.router)
app.include_router(diagnosis_v2.router)


# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Miaota Industrial Agent API",
        "version": "v1.0.0-beta2",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "multi-agent-diagnosis",
            "graph-rag",
            "camel-integration",
            "task-tracking"
        ]
    }


# 认证相关端点
@app.post("/auth/login")
async def login(credentials: dict):
    """
    用户登录
    
    获取访问令牌
    """
    from src.api.dependencies import _users, create_access_token
    
    username = credentials.get("username")
    password = credentials.get("password")
    
    # 查找用户
    user = None
    for user_id, user_data in _users._data.items():
        if user_data.get("username") == username:
            user = user_data
            break
    
    if not user or user.get("password") != password:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    # 创建令牌
    token = create_access_token(
        user_id=user["user_id"],
        username=user["username"],
        roles=user.get("roles", []),
        tenant_id=user.get("tenant_id")
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "roles": user.get("roles", [])
        }
    }


@app.get("/auth/me")
async def get_current_user_info(
    user = Depends(lambda: None)  # 简化版，实际需要验证
):
    """获取当前用户信息"""
    return {
        "user_id": "demo_user",
        "username": "demo",
        "roles": ["operator"],
        "permissions": ["device:read", "data:read"]
    }


# 版本信息
@app.get("/version")
async def get_version():
    """获取版本信息"""
    return {
        "version": "v1.0.0-beta2",
        "codename": "MiroFish",
        "build_time": "2024-01-15",
        "git_commit": "mirofish-integration",
        "python_version": "3.11",
        "changelog": [
            "集成MiroFish多智能体诊断引擎",
            "新增GraphRAG知识图谱系统",
            "新增CAMEL框架智能体协作",
            "新增长时任务追踪系统"
        ]
    }


# 启动函数
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
