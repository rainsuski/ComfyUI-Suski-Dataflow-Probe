"""
utils/__init__.py
导出通用规则解析器与安全 JSON 序列化工具。
"""

from __future__ import annotations

from .parser import (
    parse_key_value_pairs,
    parse_multiline_list,
    parse_slot_scope_rules,
)
from .serializer import (
    safe_json_dumps,
    sanitize_for_json,
)

__all__ = [
    "parse_multiline_list",
    "parse_key_value_pairs",
    "parse_slot_scope_rules",
    "sanitize_for_json",
    "safe_json_dumps",
]
