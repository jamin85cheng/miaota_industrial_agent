"""
API 路由包
"""

from .auth import router as auth_router
from .data import router as data_router
from .rules import router as rules_router
from .alerts import router as alerts_router
from .diagnosis import router as diagnosis_router
from .dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "data_router",
    "rules_router",
    "alerts_router",
    "diagnosis_router",
    "dashboard_router"
]
