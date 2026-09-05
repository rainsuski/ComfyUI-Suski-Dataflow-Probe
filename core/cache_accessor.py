"""
core/cache_accessor.py
运行时执行缓存穿透访问器。
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Tuple


class RuntimeCacheAccessor:
    """
    负责在节点执行周期内，安全嗅探已执行完成节点的真实产物。
    """

    @staticmethod
    def get_runtime_outputs_cache() -> Optional[Dict[str, List[Any]]]:
        """
        全景式栈帧回溯，精准穿透 ComfyUI 执行器缓存 outputs。
        """
        try:
            current_frame = sys._getframe()
            while current_frame is not None:
                frame_locals = current_frame.f_locals

                # 扫描局部变量中持有 outputs 字典的执行器实例
                for var_name, var_val in frame_locals.items():
                    if var_val is None:
                        continue

                    # 匹配持有 outputs 属性的对象 (如 PromptExecutor)
                    if hasattr(var_val, "outputs"):
                        target_outputs = getattr(var_val, "outputs", None)
                        if isinstance(target_outputs, dict):
                            return target_outputs

                    # 匹配局部命名直接为 outputs 的字典
                    if (
                        "outputs" in var_name
                        and isinstance(var_val, dict)
                        and len(var_val) > 0
                    ):
                        return var_val

                current_frame = current_frame.f_back
            return None
        except Exception:
            return None

    @classmethod
    def resolve_dynamic_output(
        cls,
        upstream_node_id: str,
        slot_index: int,
        mock_cache: Optional[Dict[str, List[Any]]] = None,
    ) -> Tuple[bool, Any]:
        """
        尝试从运行时缓存中提取指定节点的输出槽值。
        """
        cache = (
            mock_cache if mock_cache is not None else cls.get_runtime_outputs_cache()
        )
        if cache is None:
            return False, None

        str_node_id = str(upstream_node_id)
        if str_node_id not in cache:
            return False, None

        node_outputs = cache[str_node_id]
        if not isinstance(node_outputs, (list, tuple)):
            return False, None

        if not (0 <= slot_index < len(node_outputs)):
            return False, None

        output_val = node_outputs[slot_index]
        if isinstance(output_val, (list, tuple)) and len(output_val) == 1:
            return True, output_val[0]
        return True, output_val
