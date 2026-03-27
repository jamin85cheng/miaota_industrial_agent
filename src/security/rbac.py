"""
RBAC权限管理系统

基于角色的访问控制实现
"""

from enum import Enum, auto
from typing import List, Set, Dict, Optional, Any
from dataclasses import dataclass, field
from functools import wraps
import json

from src.utils.structured_logging import get_logger

logger = get_logger("rbac")


class Permission(Enum):
    """系统权限定义"""
    # 设备权限
    DEVICE_READ = "device:read"
    DEVICE_WRITE = "device:write"
    DEVICE_DELETE = "device:delete"
    DEVICE_ADMIN = "device:admin"
    
    # 数据权限
    DATA_READ = "data:read"
    DATA_EXPORT = "data:export"
    DATA_ADMIN = "data:admin"
    
    # 告警权限
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_CONFIGURE = "alert:configure"
    ALERT_ADMIN = "alert:admin"
    
    # 分析权限
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_EXECUTE = "analysis:execute"
    
    # 知识库权限
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_ADMIN = "knowledge:admin"
    
    # 报表权限
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_ADMIN = "report:admin"
    
    # 系统权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_ADMIN = "user:admin"
    
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"
    
    # 超级权限
    SUPER_ADMIN = "*"


@dataclass
class Role:
    """角色定义"""
    id: str
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: List[str] = field(default_factory=list)
    is_system: bool = False
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否有指定权限"""
        if Permission.SUPER_ADMIN in self.permissions:
            return True
        return permission in self.permissions
    
    def add_permission(self, permission: Permission):
        """添加权限"""
        self.permissions.add(permission)
    
    def remove_permission(self, permission: Permission):
        """移除权限"""
        self.permissions.discard(permission)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "parent_roles": self.parent_roles,
            "is_system": self.is_system
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            permissions={Permission(p) for p in data.get("permissions", [])},
            parent_roles=data.get("parent_roles", []),
            is_system=data.get("is_system", False)
        )


@dataclass
class User:
    """用户定义"""
    id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    tenant_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def has_role(self, role_id: str) -> bool:
        """检查是否有指定角色"""
        return role_id in self.roles
    
    def has_permission(self, permission: Permission, rbac_manager=None) -> bool:
        """检查是否有指定权限"""
        # 直接权限
        if Permission.SUPER_ADMIN in self.permissions:
            return True
        if permission in self.permissions:
            return True
        
        # 角色权限
        if rbac_manager:
            for role_id in self.roles:
                role = rbac_manager.get_role(role_id)
                if role and role.has_permission(permission):
                    return True
        
        return False
    
    def get_all_permissions(self, rbac_manager=None) -> Set[Permission]:
        """获取所有权限（包括角色继承）"""
        all_perms = set(self.permissions)
        
        if rbac_manager:
            for role_id in self.roles:
                role = rbac_manager.get_role(role_id)
                if role:
                    all_perms.update(role.permissions)
        
        return all_perms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": [p.value for p in self.permissions],
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
            "attributes": self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=data["id"],
            username=data["username"],
            email=data.get("email"),
            roles=data.get("roles", []),
            permissions={Permission(p) for p in data.get("permissions", [])},
            is_active=data.get("is_active", True),
            tenant_id=data.get("tenant_id"),
            attributes=data.get("attributes", {})
        )


class RBACManager:
    """RBAC管理器"""
    
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}
        self._init_default_roles()
    
    def _init_default_roles(self):
        """初始化默认角色"""
        default_roles = [
            Role(
                id="admin",
                name="管理员",
                description="系统管理员，拥有所有权限",
                permissions={Permission.SUPER_ADMIN},
                is_system=True
            ),
            Role(
                id="operator",
                name="操作员",
                description="日常操作员",
                permissions={
                    Permission.DEVICE_READ,
                    Permission.DEVICE_WRITE,
                    Permission.DATA_READ,
                    Permission.DATA_EXPORT,
                    Permission.ALERT_READ,
                    Permission.ALERT_ACKNOWLEDGE,
                    Permission.ANALYSIS_READ,
                    Permission.ANALYSIS_EXECUTE,
                    Permission.KNOWLEDGE_READ,
                    Permission.REPORT_READ,
                    Permission.REPORT_CREATE
                },
                is_system=True
            ),
            Role(
                id="viewer",
                name="观察员",
                description="只读用户",
                permissions={
                    Permission.DEVICE_READ,
                    Permission.DATA_READ,
                    Permission.ALERT_READ,
                    Permission.REPORT_READ
                },
                is_system=True
            ),
            Role(
                id="engineer",
                name="工程师",
                description="系统工程师",
                permissions={
                    Permission.DEVICE_READ,
                    Permission.DEVICE_WRITE,
                    Permission.DATA_READ,
                    Permission.DATA_EXPORT,
                    Permission.ALERT_READ,
                    Permission.ALERT_ACKNOWLEDGE,
                    Permission.ALERT_CONFIGURE,
                    Permission.ANALYSIS_READ,
                    Permission.ANALYSIS_EXECUTE,
                    Permission.KNOWLEDGE_READ,
                    Permission.KNOWLEDGE_WRITE,
                    Permission.REPORT_READ,
                    Permission.REPORT_CREATE
                },
                is_system=True
            ),
            Role(
                id="alert_manager",
                name="告警管理员",
                description="负责告警管理",
                permissions={
                    Permission.ALERT_READ,
                    Permission.ALERT_ACKNOWLEDGE,
                    Permission.ALERT_CONFIGURE,
                    Permission.ALERT_ADMIN
                },
                is_system=True
            )
        ]
        
        for role in default_roles:
            self._roles[role.id] = role
        
        logger.info(f"已初始化 {len(default_roles)} 个默认角色")
    
    # 角色管理
    def create_role(self, role: Role) -> Role:
        """创建角色"""
        if role.id in self._roles:
            raise ValueError(f"角色 {role.id} 已存在")
        
        self._roles[role.id] = role
        logger.info(f"角色已创建: {role.id}")
        return role
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(role_id)
    
    def update_role(self, role: Role) -> Role:
        """更新角色"""
        if role.id not in self._roles:
            raise ValueError(f"角色 {role.id} 不存在")
        
        existing = self._roles[role.id]
        if existing.is_system:
            raise ValueError(f"不能修改系统角色 {role.id}")
        
        self._roles[role.id] = role
        logger.info(f"角色已更新: {role.id}")
        return role
    
    def delete_role(self, role_id: str):
        """删除角色"""
        if role_id not in self._roles:
            raise ValueError(f"角色 {role_id} 不存在")
        
        role = self._roles[role_id]
        if role.is_system:
            raise ValueError(f"不能删除系统角色 {role_id}")
        
        # 检查是否有用户使用该角色
        for user in self._users.values():
            if role_id in user.roles:
                raise ValueError(f"角色 {role_id} 正在被用户使用，无法删除")
        
        del self._roles[role_id]
        logger.info(f"角色已删除: {role_id}")
    
    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self._roles.values())
    
    # 用户管理
    def create_user(self, user: User) -> User:
        """创建用户"""
        if user.id in self._users:
            raise ValueError(f"用户 {user.id} 已存在")
        
        self._users[user.id] = user
        logger.info(f"用户已创建: {user.username}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
    
    def update_user(self, user: User) -> User:
        """更新用户"""
        if user.id not in self._users:
            raise ValueError(f"用户 {user.id} 不存在")
        
        self._users[user.id] = user
        logger.info(f"用户已更新: {user.username}")
        return user
    
    def delete_user(self, user_id: str):
        """删除用户"""
        if user_id not in self._users:
            raise ValueError(f"用户 {user_id} 不存在")
        
        user = self._users[user_id]
        del self._users[user_id]
        logger.info(f"用户已删除: {user.username}")
    
    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        """列出用户"""
        users = list(self._users.values())
        if tenant_id:
            users = [u for u in users if u.tenant_id == tenant_id]
        return users
    
    # 权限检查
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查用户权限"""
        user = self.get_user(user_id)
        if not user:
            return False
        if not user.is_active:
            return False
        return user.has_permission(permission, self)
    
    def check_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查是否有任意权限"""
        return any(self.check_permission(user_id, p) for p in permissions)
    
    def check_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查是否有所有权限"""
        return all(self.check_permission(user_id, p) for p in permissions)
    
    def check_role(self, user_id: str, role_id: str) -> bool:
        """检查用户角色"""
        user = self.get_user(user_id)
        if not user:
            return False
        return user.has_role(role_id)
    
    # 用户-角色管理
    def assign_role(self, user_id: str, role_id: str):
        """分配角色给用户"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        if role_id not in self._roles:
            raise ValueError(f"角色 {role_id} 不存在")
        
        if role_id not in user.roles:
            user.roles.append(role_id)
            logger.info(f"角色 {role_id} 已分配给用户 {user_id}")
    
    def revoke_role(self, user_id: str, role_id: str):
        """撤销用户角色"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        if role_id in user.roles:
            user.roles.remove(role_id)
            logger.info(f"角色 {role_id} 已从用户 {user_id} 撤销")
    
    # 导入导出
    def export_roles(self) -> str:
        """导出角色配置"""
        roles_data = [r.to_dict() for r in self._roles.values()]
        return json.dumps(roles_data, indent=2, ensure_ascii=False)
    
    def import_roles(self, json_str: str):
        """导入角色配置"""
        roles_data = json.loads(json_str)
        for role_data in roles_data:
            role = Role.from_dict(role_data)
            if role.id in self._roles:
                self.update_role(role)
            else:
                self.create_role(role)
    
    def export_users(self) -> str:
        """导出用户配置"""
        users_data = [u.to_dict() for u in self._users.values()]
        return json.dumps(users_data, indent=2, ensure_ascii=False)
    
    def import_users(self, json_str: str):
        """导入用户配置"""
        users_data = json.loads(json_str)
        for user_data in users_data:
            user = User.from_dict(user_data)
            if user.id in self._users:
                self.update_user(user)
            else:
                self.create_user(user)


# 全局RBAC管理器实例
rbac_manager = RBACManager()


# 装饰器
def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs获取用户ID
            user_id = kwargs.get("user_id")
            if not user_id:
                raise PermissionError("需要提供用户ID")
            
            if not rbac_manager.check_permission(user_id, permission):
                raise PermissionError(f"缺少权限: {permission.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role_id: str):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            if not user_id:
                raise PermissionError("需要提供用户ID")
            
            if not rbac_manager.check_role(user_id, role_id):
                raise PermissionError(f"需要角色: {role_id}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
