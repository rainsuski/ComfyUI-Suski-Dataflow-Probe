"""
core/__init__.py
导出核心 AST 回溯引擎、缓存穿透器与数据流类型。
"""

from __future__ import annotations

from .ast_tracer import DataflowASTTracer
from .cache_accessor import RuntimeCacheAccessor
from .conflict_resolver import ConflictResolver
from .scope_manager import LineageScopeManager
from .types import ANY_FLOW_TYPE, AnyType, StageMetaPayload, StageSnapshot

__all__ = [
    "ANY_FLOW_TYPE",
    "AnyType",
    "StageSnapshot",
    "StageMetaPayload",
    "RuntimeCacheAccessor",
    "LineageScopeManager",
    "ConflictResolver",
    "DataflowASTTracer",
]
