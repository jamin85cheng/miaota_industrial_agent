"""
API依赖注入模块

提供认证、权限、数据库连接等依赖
"""

from functools import wraps
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

from src.config.config_manager import ConfigManager
from src.utils.connection_pool import connection_pool
from src.utils.thread_safe import ThreadSafeDict

# JWT配置
SECRET_KEY = ConfigManager.get_config().get('security', {}).get('jwt_secret', 'your-secret-key')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 安全方案
security = HTTPBearer(auto_error=False)


class UserContext:
    """用户上下文"""
    
    def __init__(self, user_id: str, username: str, roles: List[str], 
                 tenant_id: Optional[str] = None, permissions: List[str] = None):
        self.user_id = user_id
        self.username = username
        self.roles = roles or []
        self.tenant_id = tenant_id
        self.permissions = permissions or []
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions or 'admin' in self.roles
    
    def has_role(self, role: str) -> bool:
        """检查是否有指定角色"""
        return role in self.roles


# 内存中的用户存储（生产环境应使用数据库）
_users = ThreadSafeDict()
_tokens = ThreadSafeDict()


def create_access_token(user_id: str, username: str, roles: List[str], 
                        tenant_id: Optional[str] = None) -> str:
    """创建访问令牌"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "tenant_id": tenant_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


def init_default_users():
    """初始化默认用户"""
    default_users = [
        {
            "user_id": "admin",
            "username": "admin",
            "password": "admin123",  # 生产环境应使用哈希
            "roles": ["admin"],
            "tenant_id": "default",
            "permissions": ["*"]
        },
        {
            "user_id": "operator",
            "username": "operator",
            "password": "operator123",
            "roles": ["operator"],
            "tenant_id": "default",
            "permissions": [
                "device:read", "device:write",
                "data:read",
                "alert:read", "alert:acknowledge",
                "report:read", "report:export"
            ]
        },
        {
            "user_id": "viewer",
            "username": "viewer",
            "password": "viewer123",
            "roles": ["viewer"],
            "tenant_id": "default",
            "permissions": [
                "device:read",
                "data:read",
                "alert:read",
                "report:read"
            ]
        }
    ]
    
    for user in default_users:
        _users.set(user["user_id"], user)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_data = _users.get(payload["sub"])
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    return UserContext(
        user_id=payload["sub"],
        username=payload["username"],
        roles=payload.get("roles", []),
        tenant_id=payload.get("tenant_id"),
        permissions=user_data.get("permissions", [])
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserContext]:
    """可选用户认证"""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_permissions(*permissions: str):
    """权限检查装饰器"""
    async def permission_checker(user: UserContext = Depends(get_current_user)):
        missing = [p for p in permissions if not user.has_permission(p)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}"
            )
        return user
    return permission_checker


def require_roles(*roles: str):
    """角色检查装饰器"""
    async def role_checker(user: UserContext = Depends(get_current_user)):
        if not any(user.has_role(r) for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {', '.join(roles)}"
            )
        return user
    return role_checker


async def get_db_connection():
    """获取数据库连接"""
    conn = None
    try:
        conn = connection_pool.get_connection()
        yield conn
    finally:
        if conn:
            connection_pool.release_connection(conn)


async def get_tenant_id(
    user: UserContext = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None)
) -> str:
    """获取租户ID（支持多租户）"""
    # 如果用户有固定租户，使用用户租户
    if user.tenant_id:
        return user.tenant_id
    
    # 否则从请求头获取
    return x_tenant_id or "default"


class TenantContext:
    """租户上下文"""
    
    def __init__(self, tenant_id: str, db_connection=None):
        self.tenant_id = tenant_id
        self.db_connection = db_connection
    
    def apply_tenant_filter(self, query: str) -> str:
        """为查询添加租户过滤"""
        # 简化实现，实际应根据数据库类型处理
        if "WHERE" in query.upper():
            return f"{query} AND tenant_id = '{self.tenant_id}'"
        else:
            return f"{query} WHERE tenant_id = '{self.tenant_id}'"


async def get_tenant_context(
    tenant_id: str = Depends(get_tenant_id),
    db = Depends(get_db_connection)
) -> TenantContext:
    """获取租户上下文"""
    return TenantContext(tenant_id, db)


# API密钥验证
async def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> Optional[UserContext]:
    """验证API密钥"""
    if not x_api_key:
        return None
    
    # 简化的API密钥验证（生产环境应使用数据库存储）
    api_keys = {
        "demo-key-001": {
            "user_id": "api_user_001",
            "username": "api_user",
            "roles": ["operator"],
            "tenant_id": "default"
        }
    }
    
    key_data = api_keys.get(x_api_key)
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥"
        )
    
    return UserContext(
        user_id=key_data["user_id"],
        username=key_data["username"],
        roles=key_data["roles"],
        tenant_id=key_data["tenant_id"]
    )


# 组合认证（支持JWT或API Key）
async def get_current_user_or_api_key(
    user: Optional[UserContext] = Depends(get_optional_user),
    api_user: Optional[UserContext] = Depends(verify_api_key)
) -> UserContext:
    """获取当前用户（JWT或API Key）"""
    if user:
        return user
    if api_user:
        return api_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要提供认证信息"
    )


# 请求日志
def log_request(request: Request, user: UserContext = None):
    """记录请求日志"""
    from src.utils.structured_logging import get_logger
    logger = get_logger("api.access")
    
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_id": user.user_id if user else None,
            "user_agent": request.headers.get("user-agent")
        }
    )
