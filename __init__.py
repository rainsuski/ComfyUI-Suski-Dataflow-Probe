"""
__init__.py
ComfyUI-DataflowProbe 插件根入口。
采用安全的包内相对引用与动态导出机制，防止用户改动目录名导致命名空间污染。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("ComfyUI-DataflowProbe")

try:
    from .nodes import NODE_CLASSES, NODE_DISPLAY_NAMES

    NODE_CLASS_MAPPINGS: Dict[str, Any] = NODE_CLASSES
    NODE_DISPLAY_NAME_MAPPINGS: Dict[str, str] = NODE_DISPLAY_NAMES
except Exception:
    logger.exception("Failed to load nodes:")
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

# 声明支持 Web UI 扩展目录
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
