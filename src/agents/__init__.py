"""
智能体模块

包含CAMEL框架集成、多智能体协调等功能
"""

from .camel_integration import (
    CamelAgent,
    CamelSociety,
    IndustrialDiagnosisSociety,
    AgentMessage,
    AgentRole,
    MessageType,
    Task
)

__all__ = [
    "CamelAgent",
    "CamelSociety",
    "IndustrialDiagnosisSociety",
    "AgentMessage",
    "AgentRole",
    "MessageType",
    "Task"
]
