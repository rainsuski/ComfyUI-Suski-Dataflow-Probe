"""
nodes/combine_node.py
元数据级联合并节点 (MetaCombine)。
支持接收标准 STAGE_META、原生字符串、JSON 字符串及空字符串。
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Tuple

from ..core.types import AnyType

# 允许接收 STAGE_META、STRING 等任意连线类型
META_INPUT_TYPE = AnyType("STAGE_META")


class MetaCombineNode:
    """
    元数据级联合并节点：
    接收两个阶段的元数据（支持单字典、列表、JSON 字符串或空串），按时序规整为一个有序列表。
    自动剔除 None 与未选通分支的空数据。
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "meta_a": (META_INPUT_TYPE, {}),
            },
            "optional": {
                "meta_b": (META_INPUT_TYPE, {}),
            },
        }

    RETURN_TYPES = ("STAGE_META",)
    RETURN_NAMES = ("stage_meta",)
    FUNCTION = "combine_meta"
    CATEGORY = "DataflowProbe"

    def _normalize_input(self, item: Any) -> List[Dict[str, Any]]:
        """
        容错解析器：安全吞下 None、空字符串、JSON 字符串、字典或列表。
        """
        if item is None:
            return []

        # 1. 如果是字符串 (例如从通用 Switch 传入的空串或 JSON 文本)
        if isinstance(item, str):
            clean_str = item.strip()
            if not clean_str:
                return []
            try:
                parsed = json.loads(clean_str)
                return self._normalize_input(parsed)
            except Exception:
                return []

        # 2. 如果是列表
        if isinstance(item, (list, tuple)):
            result: List[Dict[str, Any]] = []
            for sub in item:
                result.extend(self._normalize_input(sub))
            return result

        # 3. 如果是字典
        if isinstance(item, dict) and item:
            if "stage_name" in item or "params" in item:
                return [copy.deepcopy(item)]

        return []

    def combine_meta(
        self,
        meta_a: Any,
        meta_b: Any = None,
    ) -> Tuple[List[Dict[str, Any]]]:
        combined_list: List[Dict[str, Any]] = []
        combined_list.extend(self._normalize_input(meta_a))
        combined_list.extend(self._normalize_input(meta_b))
        return (combined_list,)
