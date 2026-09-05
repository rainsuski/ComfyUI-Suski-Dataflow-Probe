"""
utils/serializer.py
安全 JSON 序列化工具，支持 Tensor、Numpy、非标准类型的无损清洗。
"""

from __future__ import annotations

import json
import math
from typing import Any


def sanitize_for_json(obj: Any) -> Any:
    """
    深度递归清洗数据，使其符合标准 JSON 规范。
    """
    if obj is None:
        return None
    if isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # 尝试处理 PyTorch Tensor
    if hasattr(obj, "detach") and hasattr(obj, "cpu"):
        try:
            tensor_cpu = obj.detach().cpu()
            if tensor_cpu.numel() == 1:
                return sanitize_for_json(tensor_cpu.item())
            return sanitize_for_json(tensor_cpu.tolist())
        except Exception:
            pass

    # 尝试处理 Numpy 数据
    if hasattr(obj, "tolist"):
        try:
            return sanitize_for_json(obj.tolist())
        except Exception:
            pass

    # 降级处理为字符串表现形式
    return str(obj)


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """
    序列化为格式化 JSON 字符串，保证跨平台 UTF-8 兼容。
    """
    sanitized = sanitize_for_json(obj)
    return json.dumps(sanitized, indent=indent, ensure_ascii=False)
