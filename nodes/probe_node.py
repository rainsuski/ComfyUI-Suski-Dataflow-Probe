"""
nodes/probe_node.py
数据流探针节点 (DataflowProbe)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..core.ast_tracer import DataflowASTTracer
from ..core.scope_manager import LineageScopeManager
from ..core.types import ANY_FLOW_TYPE, StageSnapshot
from ..utils.parser import parse_multiline_list, parse_slot_scope_rules


class DataflowProbeNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "flow": (ANY_FLOW_TYPE, {}),
                "stage_name": ("STRING", {"default": "Stage_1", "multiline": False}),
                "sniff_keys": (
                    "STRING",
                    {
                        "default": (
                            "seed, steps, cfg, sampler_name, scheduler, denoise, "
                            "ckpt_name, model_name, unet_name, clip_name, "
                            "text, prompt, positive_prompt, negative_prompt"
                        ),
                        "multiline": True,
                    },
                ),
                "slot_scope_rules": (
                    "STRING",
                    {
                        "default": (
                            "positive:text->positive_prompt\n"
                            "negative:text->negative_prompt\n"
                            "positive:prompt->positive_prompt\n"
                            "negative:prompt->negative_prompt"
                        ),
                        "multiline": True,
                    },
                ),
                "conflict_strategy": (
                    ["Last", "First", "List", "Index", "Auto-Rename"],
                    {"default": "Last"},
                ),
            },
            "optional": {
                "strategy_index": (
                    "INT",
                    {"default": 0, "min": 0, "max": 99, "step": 1},
                ),
                "key_prefix": ("STRING", {"default": "", "multiline": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = (ANY_FLOW_TYPE, "STAGE_META")
    RETURN_NAMES = ("flow", "stage_meta")
    FUNCTION = "probe_dataflow"
    CATEGORY = "DataflowProbe"

    def probe_dataflow(
        self,
        flow: Any,
        stage_name: str,
        sniff_keys: str,
        slot_scope_rules: str,
        conflict_strategy: str,
        strategy_index: int = 0,
        key_prefix: str = "",
        prompt: Dict[str, Any] = None,
        unique_id: str = None,
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        parsed_keys = parse_multiline_list(sniff_keys)
        parsed_rules = parse_slot_scope_rules(slot_scope_rules)
        scope_manager = LineageScopeManager(rules=parsed_rules)

        tracer = DataflowASTTracer(
            prompt=prompt or {},
            sniff_keys=parsed_keys,
            scope_manager=scope_manager,
            conflict_strategy=conflict_strategy,
            strategy_index=strategy_index,
        )

        # 核心修复 1: 从 flow 输入槽的上游真实业务节点开始追踪，跳过自身
        upstream_start_node = None
        if prompt and str(unique_id) in prompt:
            probe_inputs = prompt[str(unique_id)].get("inputs", {})
            flow_conn = probe_inputs.get("flow")
            if isinstance(flow_conn, (list, tuple)) and len(flow_conn) == 2:
                upstream_start_node = str(flow_conn[0])

        if upstream_start_node:
            extracted_params = tracer.trace_lineage(start_node_id=upstream_start_node)
        else:
            extracted_params = {}

        if key_prefix.strip():
            prefix = key_prefix.strip()
            extracted_params = {f"{prefix}{k}": v for k, v in extracted_params.items()}

        snapshot = StageSnapshot(
            stage_name=stage_name.strip() or "Stage_1",
            params=extracted_params,
            node_id=str(unique_id),
        )

        return flow, [snapshot.to_dict()]
