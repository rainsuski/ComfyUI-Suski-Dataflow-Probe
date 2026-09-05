"""
core/cache_accessor.py
运行时执行缓存穿透访问器。
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ComfyUI-DataflowProbe")


class RuntimeCacheAccessor:
    """
    负责在节点执行周期内，安全嗅探已执行完成节点的真实产物。
    """

    @staticmethod
    def get_runtime_outputs_cache() -> Tuple[Optional[Dict[str, List[Any]]], str]:
        """
        全景式栈帧回溯，精准穿透 ComfyUI 执行器缓存 outputs。
        """
        try:
            current_frame = sys._getframe()
            depth = 0
            stack_trace_summary: List[str] = []

            while current_frame is not None:
                depth += 1
                func_name = current_frame.f_code.co_name
                file_name = current_frame.f_code.co_filename.split("/")[-1].split("\\")[
                    -1
                ]
                frame_locals = current_frame.f_locals
                stack_trace_summary.append(f"#{depth} {func_name} ({file_name})")

                # 检查 locals 中的变量
                for var_name, var_val in frame_locals.items():
                    if var_val is None:
                        continue

                    # 检查对象属性 outputs
                    if hasattr(var_val, "outputs"):
                        target_outputs = getattr(var_val, "outputs", None)
                        if isinstance(target_outputs, dict):
                            return (
                                target_outputs,
                                f"Found {var_name}.outputs (depth={depth}, count={len(target_outputs)})",
                            )

                    # 检查直接叫 outputs 的字典
                    if (
                        "outputs" in var_name
                        and isinstance(var_val, dict)
                        and len(var_val) > 0
                    ):
                        return (
                            var_val,
                            f"Found local '{var_name}' (depth={depth}, count={len(var_val)})",
                        )

                current_frame = current_frame.f_back

            summary_str = " -> ".join(stack_trace_summary[:8])
            return None, f"Stack exhausted (depth={depth}). Top frames: {summary_str}"
        except Exception as e:
            return None, f"Exception during cache trace: {e}"

    @classmethod
    def resolve_dynamic_output(
        cls,
        upstream_node_id: str,
        slot_index: int,
        mock_cache: Optional[Dict[str, List[Any]]] = None,
    ) -> Tuple[bool, Any, str]:
        if mock_cache is not None:
            cache = mock_cache
            cache_info = "MockCache"
        else:
            cache, cache_info = cls.get_runtime_outputs_cache()

        if cache is None:
            return False, None, f"Cache unavailable ({cache_info})"

        str_node_id = str(upstream_node_id)
        if str_node_id not in cache:
            return False, None, f"Node {str_node_id} not in cache"

        node_outputs = cache[str_node_id]
        if not isinstance(node_outputs, (list, tuple)):
            return False, None, f"Node {str_node_id} output invalid"

        if not (0 <= slot_index < len(node_outputs)):
            return False, None, f"Slot {slot_index} out of bounds"

        output_val = node_outputs[slot_index]
        if isinstance(output_val, (list, tuple)) and len(output_val) == 1:
            return True, output_val[0], "Hit (unwrapped)"
        return True, output_val, "Hit (raw)"
