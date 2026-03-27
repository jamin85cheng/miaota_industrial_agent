"""
认证路由

作者: Security Team
职责: 用户登录、登出、Token刷新
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.core.security import AuthService, TokenData
from api.core.config import settings


router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserProfile(BaseModel):
    """用户资料"""
    user_id: str
    username: str
    email: str
    role: str
    permissions: list


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 JWT Token，用于后续 API 认证
    """
    # 验证用户
    user = AuthService.authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建 Token
    access_token_expires = timedelta(hours=settings.JWT_EXPIRE_HOURS)
    
    access_token = AuthService.create_access_token(
        data={
            "sub": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "permissions": user["permissions"]
        },
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_HOURS * 3600,
        user={
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user(token_data: TokenData = Depends(AuthService())):
    """获取当前登录用户信息"""
    user = AuthService.USERS_DB.get(token_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserProfile(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        permissions=user["permissions"]
    )


@router.post("/logout")
async def logout():
    """
    用户登出
    
    注意：JWT 是无状态的，服务端无法真正"注销"一个 Token。
    实际应用中应该将 Token 加入黑名单（Redis）。
    """
    # TODO: 将 Token 加入黑名单
    return {"message": "登出成功"}
