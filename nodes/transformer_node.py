"""
nodes/transformer_node.py
元数据中继编辑节点 (MetaTransformer)。
支持接收标准 STAGE_META、原生字符串或 JSON 字符串。
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Tuple

from ..core.types import AnyType
from ..utils.parser import parse_key_value_pairs, parse_multiline_list

META_INPUT_TYPE = AnyType("STAGE_META")


class MetaTransformerNode:
    """
    元数据中继节点：
    提供中间件式的数据清洗、键名替换、标签手动注入与黑名单剔除。
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "stage_meta": (META_INPUT_TYPE, {}),
            },
            "optional": {
                "rename_rules": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "old_key:new_key",
                    },
                ),
                "override_values": (
                    "STRING",
                    {"default": "", "multiline": True, "placeholder": "key:value"},
                ),
                "drop_keys": (
                    "STRING",
                    {"default": "", "multiline": False, "placeholder": "key1, key2"},
                ),
            },
        }

    RETURN_TYPES = ("STAGE_META",)
    RETURN_NAMES = ("stage_meta",)
    FUNCTION = "transform_meta"
    CATEGORY = "DataflowProbe"

    def _normalize_input(self, item: Any) -> List[Dict[str, Any]]:
        """
        统一将输入规整为 Dict 列表。
        """
        if item is None:
            return []

        if isinstance(item, str):
            clean_str = item.strip()
            if not clean_str:
                return []
            try:
                parsed = json.loads(clean_str)
                return self._normalize_input(parsed)
            except Exception:
                return []

        if isinstance(item, list):
            result: List[Dict[str, Any]] = []
            for sub in item:
                if isinstance(sub, dict) and sub:
                    result.append(copy.deepcopy(sub))
            return result

        if isinstance(item, dict) and item:
            return [copy.deepcopy(item)]

        return []

    def transform_meta(
        self,
        stage_meta: Any,
        rename_rules: str = "",
        override_values: str = "",
        drop_keys: str = "",
    ) -> Tuple[List[Dict[str, Any]]]:
        stages = self._normalize_input(stage_meta)

        rename_map = parse_key_value_pairs(rename_rules)
        overrides = parse_key_value_pairs(override_values)
        drops = set(parse_multiline_list(drop_keys))

        for stage in stages:
            if not isinstance(stage, dict) or "params" not in stage:
                continue

            params: Dict[str, Any] = stage["params"]

            # 1. 执行黑名单剔除
            for k in list(params.keys()):
                if k in drops:
                    del params[k]

            # 2. 执行键名重命名
            for old_k, new_k in rename_map.items():
                if old_k in params:
                    params[new_k] = params.pop(old_k)

            # 3. 执行值覆写或新标签追加
            for k, v in overrides.items():
                try:
                    params[k] = json.loads(v)
                except Exception:
                    params[k] = v

        return (stages,)
