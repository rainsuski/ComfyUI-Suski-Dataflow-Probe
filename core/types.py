"""
core/types.py
定义通配数据类型与元数据载荷结构。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


class AnyType(str):
    """
    通配类型 (Wildcard Type)
    重写 __ne__ 与 __eq__，使 ComfyUI 前端与后端类型校验时始终判定为匹配，
    从而允许 flow 端口原样透传 IMAGE, LATENT, MODEL, VIDEO, AUDIO 等任意数据流。
    """

    def __ne__(self, __value: object) -> bool:
        return False

    def __eq__(self, __value: object) -> bool:
        return True


# 实例化全局通配符常量
ANY_FLOW_TYPE = AnyType("*")


@dataclass
class StageSnapshot:
    """
    单阶段元数据快照
    """

    stage_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    node_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "params": self.params,
            "node_id": self.node_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageSnapshot:
        return cls(
            stage_name=data.get("stage_name", "Unknown_Stage"),
            params=data.get("params", {}),
            node_id=data.get("node_id"),
            timestamp=data.get("timestamp", time.time()),
        )


# STAGE_META 支持单快照对象或多快照列表传递
StageMetaPayload = Union[
    StageSnapshot, List[StageSnapshot], Dict[str, Any], List[Dict[str, Any]]
]
