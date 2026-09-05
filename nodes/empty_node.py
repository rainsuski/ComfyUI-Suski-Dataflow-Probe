"""
nodes/empty_node.py
空阶段元数据发生器 (EmptyStageMeta)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class EmptyStageMetaNode:
    """
    专门为 Switch 旁路、条件分支占位提供合法的空元数据输入，彻底规避类型与空值报错。
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {"required": {}}

    RETURN_TYPES = ("STAGE_META",)
    RETURN_NAMES = ("stage_meta",)
    FUNCTION = "generate_empty_meta"
    CATEGORY = "DataflowProbe"

    def generate_empty_meta(self) -> Tuple[List[Dict[str, Any]]]:
        return ([],)
