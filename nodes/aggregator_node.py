"""
nodes/aggregator_node.py
元数据聚合注入节点 (MetaAggregatorInjector)。
支持单输入端口接收 STAGE_META 或 STRING，自动清洗空分支并支持双通道持久化。
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional, Tuple

from ..core.types import ANY_FLOW_TYPE, AnyType
from ..utils.parser import parse_key_value_pairs
from ..utils.serializer import safe_json_dumps, sanitize_for_json

META_INPUT_TYPE = AnyType("STAGE_META")


class MetaAggregatorInjectorNode:
    """
    通用元数据聚合注入节点：
    单一输入端口接收多阶段时序账单，注入 extra_pnginfo 文本块，并输出纯净 JSON 字符串。
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "flow": (ANY_FLOW_TYPE, {}),
            },
            "optional": {
                "stage_meta": (META_INPUT_TYPE, {}),
                "custom_metadata": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": '{\n  "project": "Demo",\n  "version": "1.0"\n}\n或者 key:value 格式',
                    },
                ),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = (ANY_FLOW_TYPE, "STRING")
    RETURN_NAMES = ("flow", "metadata_json")
    FUNCTION = "aggregate_and_inject"
    CATEGORY = "DataflowProbe"

    def _normalize_stages(self, item: Any) -> List[Dict[str, Any]]:
        """
        安全解析并清洗各阶段元数据，兼容字符串输入并过滤空值。
        """
        if item is None:
            return []

        if isinstance(item, str):
            clean_str = item.strip()
            if not clean_str:
                return []
            try:
                parsed = json.loads(clean_str)
                return self._normalize_stages(parsed)
            except Exception:
                return []

        if isinstance(item, list):
            result: List[Dict[str, Any]] = []
            for sub in item:
                result.extend(self._normalize_stages(sub))
            return result

        if isinstance(item, dict) and item:
            return [copy.deepcopy(item)]

        return []

    def aggregate_and_inject(
        self,
        flow: Any,
        stage_meta: Any = None,
        custom_metadata: str = "",
        extra_pnginfo: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, str]:
        # 1. 规整多阶段列表并清洗无效分支与空串
        stages: List[Dict[str, Any]] = self._normalize_stages(stage_meta)

        # 2. 解析全局自定义附加信息
        custom_dict: Dict[str, Any] = {}
        if custom_metadata.strip():
            raw_text = custom_metadata.strip()
            try:
                parsed_json = json.loads(raw_text)
                if isinstance(parsed_json, dict):
                    custom_dict = parsed_json
            except Exception:
                custom_dict = parse_key_value_pairs(raw_text)

        # 3. 组装标准 Payload
        payload: Dict[str, Any] = {
            "schema_version": "3.0",
            "stage_count": len(stages),
            "stages": sanitize_for_json(stages),
            "custom": sanitize_for_json(custom_dict),
        }

        # 4. 隐式注入 extra_pnginfo (供 SaveImage 原生持久化)
        if extra_pnginfo is not None and isinstance(extra_pnginfo, dict):
            extra_pnginfo["dataflow_lineage"] = payload

        # 5. 输出格式化 JSON 字符串
        json_output = safe_json_dumps(payload, indent=2)

        return flow, json_output
