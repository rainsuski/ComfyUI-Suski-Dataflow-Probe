"""
core/ast_tracer.py
DAG 拓扑反向血统追踪核心引擎。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Union

from .cache_accessor import RuntimeCacheAccessor
from .conflict_resolver import ConflictResolver
from .scope_manager import LineageScopeManager

logger = logging.getLogger("ComfyUI-DataflowProbe")


class DataflowASTTracer:
    PRIMITIVE_CLASS_TYPES: Set[str] = {
        "primitiveint",
        "primitivefloat",
        "primitivestring",
        "primitivestringmultiline",
        "primitivenode",
    }

    CANONICAL_TARGET_MAP: Dict[str, str] = {
        "model_name": "unet_name",
        "unet_name": "unet_name",
        "ckpt_name": "ckpt_name",
        "clip_name": "clip_name",
        "clip_name1": "clip_name",
        "clip_name2": "clip_name",
        "lora_name": "lora_name",
        "loras": "loras",
    }

    def __init__(
        self,
        prompt: Dict[str, Any],
        sniff_keys: Union[List[str], str],
        scope_manager: LineageScopeManager,
        conflict_strategy: str = "Last",
        strategy_index: int = 0,
        mock_cache: Optional[Dict[str, List[Any]]] = None,
    ):
        self.prompt = prompt or {}
        if isinstance(sniff_keys, str):
            from ..utils.parser import parse_multiline_list

            self.sniff_keys = [k.lower() for k in parse_multiline_list(sniff_keys)]
        else:
            self.sniff_keys = [k.strip().lower() for k in sniff_keys if k and k.strip()]

        for alias_k, canonical_k in self.CANONICAL_TARGET_MAP.items():
            if canonical_k in self.sniff_keys and alias_k not in self.sniff_keys:
                self.sniff_keys.append(alias_k)

        self.scope_manager = scope_manager
        self.conflict_strategy = conflict_strategy
        self.strategy_index = strategy_index
        self.mock_cache = mock_cache
        self.visited_nodes: Set[str] = set()

    def trace_lineage(self, start_node_id: str) -> Dict[str, Any]:
        self.visited_nodes.clear()
        collected_values: Dict[str, List[Any]] = defaultdict(list)

        self._traverse_node(
            node_id=str(start_node_id),
            current_scope=None,
            is_model_branch=False,
            inherited_slot_name=None,
            collected=collected_values,
            depth=0,
        )

        # 正向与负向提示词去重自然拼接
        for prompt_key in ["positive_prompt", "negative_prompt"]:
            if prompt_key in collected_values and len(collected_values[prompt_key]) > 1:
                raw_segments = [
                    str(s).strip()
                    for s in reversed(collected_values[prompt_key])
                    if str(s).strip()
                ]
                unique_segments: List[str] = []
                for seg in raw_segments:
                    if seg not in unique_segments:
                        unique_segments.append(seg)
                if unique_segments:
                    collected_values[prompt_key] = [", ".join(unique_segments)]

        final_res = ConflictResolver.resolve(
            collected_values=collected_values,
            strategy=self.conflict_strategy,
            strategy_index=self.strategy_index,
        )

        logger.debug(
            f"[DataflowProbe] 回溯完成: 节点 [{start_node_id}] 提取到 {len(final_res)} 个有效参数"
        )
        return final_res

    def _clean_lora_payload(self, raw_val: Any) -> Optional[List[Dict[str, Any]]]:
        """
        清洗各第三方 LoRA 节点的非标列表载荷。
        """
        if not isinstance(raw_val, list):
            return None

        clean_loras: List[Dict[str, Any]] = []
        for item in raw_val:
            if isinstance(item, dict):
                name = item.get("name") or item.get("lora_name")
                strength = item.get("strength", 1.0)
                if name:
                    clean_loras.append({"lora_name": name, "strength": strength})
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                clean_loras.append(
                    {"lora_name": str(item[0]), "strength": float(item[1])}
                )

        return clean_loras if clean_loras else None

    def _traverse_node(
        self,
        node_id: str,
        current_scope: Optional[str],
        is_model_branch: bool,
        inherited_slot_name: Optional[str],
        collected: Dict[str, List[Any]],
        depth: int = 0,
    ) -> None:
        if node_id in self.visited_nodes or node_id not in self.prompt:
            return

        self.visited_nodes.add(node_id)
        node_info = self.prompt[node_id]
        class_type = str(node_info.get("class_type", "Unknown")).strip()
        class_type_lower = class_type.lower()
        inputs: Dict[str, Any] = node_info.get("inputs", {})

        for input_key, input_val in inputs.items():
            clean_input_key = input_key.strip().lower()

            # 1. 作用域判定
            next_scope = current_scope
            branch_is_model = is_model_branch

            if any(
                k in clean_input_key
                for k in ["positive", "pos_cond", "positive_prompt", "pos"]
            ):
                next_scope = "positive"
                branch_is_model = False
            elif any(
                k in clean_input_key
                for k in ["negative", "neg_cond", "negative_prompt", "neg"]
            ):
                next_scope = "negative"
                branch_is_model = False
            elif clean_input_key in {"model", "unet"}:
                branch_is_model = True

            # 2. 如果输入是连线指针 [upstream_id, slot_idx]
            if isinstance(input_val, (list, tuple)) and len(input_val) == 2:
                upstream_id = str(input_val[0])
                slot_idx = int(input_val[1])
                is_boundary = self.scope_manager.is_boundary_connection(clean_input_key)
                pass_scope = None if is_boundary else next_scope

                # 穿透读取动态输出
                hit, runtime_val = RuntimeCacheAccessor.resolve_dynamic_output(
                    upstream_node_id=upstream_id,
                    slot_index=slot_idx,
                    mock_cache=self.mock_cache,
                )

                if hit and isinstance(runtime_val, (str, int, float, bool)):
                    if not (branch_is_model and isinstance(runtime_val, str)):
                        effective_key = inherited_slot_name or input_key
                        mapped_key = self.scope_manager.transform_key_by_scope(
                            pass_scope, effective_key, class_type
                        )
                        if self._is_target_key(mapped_key):
                            collected[mapped_key].append(runtime_val)
                        elif self._is_target_key(effective_key):
                            collected[effective_key].append(runtime_val)

                if clean_input_key in self.sniff_keys:
                    pass_inherited = clean_input_key
                elif clean_input_key in {
                    "string_a",
                    "string_b",
                    "prefix_prompt",
                    "text",
                    "prompt",
                }:
                    pass_inherited = "text"
                else:
                    pass_inherited = inherited_slot_name

                self._traverse_node(
                    node_id=upstream_id,
                    current_scope=pass_scope,
                    is_model_branch=branch_is_model,
                    inherited_slot_name=pass_inherited,
                    collected=collected,
                    depth=depth + 1,
                )

            # 3. 如果是字面量 (int, float, str, bool)
            elif isinstance(input_val, (int, float, str, bool)):
                if (
                    class_type_lower in self.PRIMITIVE_CLASS_TYPES
                    and inherited_slot_name
                ):
                    actual_key = inherited_slot_name
                elif clean_input_key in {
                    "orinalmessage",
                    "original_message",
                    "prefix_prompt",
                }:
                    actual_key = "text"
                else:
                    actual_key = input_key

                if branch_is_model and actual_key.lower() == "text":
                    continue

                mapped_key = self.scope_manager.transform_key_by_scope(
                    next_scope, actual_key, class_type
                )
                norm_key = self.scope_manager.normalize_key(actual_key, class_type)

                if isinstance(input_val, str) and not input_val.strip():
                    continue

                if self._is_target_key(mapped_key):
                    collected[mapped_key].append(input_val)
                elif self._is_target_key(norm_key):
                    collected[norm_key].append(input_val)
                elif self._is_target_key(actual_key):
                    collected[actual_key].append(input_val)

            # 4. 针对 LoRA 列表槽位 (loras, lora_stack) 的特殊解析
            elif isinstance(input_val, list) and clean_input_key in {
                "loras",
                "lora_stack",
                "lora",
            }:
                parsed_loras = self._clean_lora_payload(input_val)
                if parsed_loras and (
                    self._is_target_key("loras") or self._is_target_key("lora_name")
                ):
                    collected["loras"].extend(parsed_loras)

    def _is_target_key(self, key_name: str) -> bool:
        clean = key_name.strip().lower()
        if clean in self.sniff_keys:
            return True
        for target in self.sniff_keys:
            if clean == f"positive_{target}" or clean == f"negative_{target}":
                return True
        return False
