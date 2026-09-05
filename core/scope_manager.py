"""
core/scope_manager.py
槽位语义白名单映射与模型血统边界阻断管理器。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class LineageScopeManager:
    BOUNDARY_BLOCK_TYPES: Set[str] = {
        "clip",
        "model",
        "vae",
        "checkpoint",
        "lora_stack",
        "control_net",
        "ipadapter",
    }

    ALLOWED_SCOPE_TARGET_KEYS: Set[str] = {
        "text",
        "prompt",
        "value",
        "string",
        "prefix_prompt",
        "wildcard_text",
        "conditioning_text",
    }

    CANONICAL_ALIASES: Dict[str, str] = {
        "clip_name1": "clip_name",
        "clip_name2": "clip_name",
    }

    def __init__(self, rules: List[Tuple[str, str, str]]):
        self.rules = rules

    def is_boundary_connection(self, slot_name: str) -> bool:
        clean_name = str(slot_name).strip().lower()
        return clean_name in self.BOUNDARY_BLOCK_TYPES

    def normalize_key(self, raw_key: str, class_type: str = "") -> str:
        """
        结合节点类型智能归一化键名。
        """
        clean = raw_key.strip().lower()
        cls_clean = class_type.strip().lower()

        # 智能区分 unet_name 与 ckpt_name
        if clean == "model_name":
            if any(k in cls_clean for k in ["unet", "diffusion", "booster", "anima"]):
                return "unet_name"
            return "ckpt_name"

        return self.CANONICAL_ALIASES.get(clean, raw_key.strip())

    def transform_key_by_scope(
        self, current_scope: Optional[str], raw_key: str, class_type: str = ""
    ) -> str:
        clean_raw_key = raw_key.strip().lower()
        norm_key = self.normalize_key(raw_key, class_type=class_type)

        if not current_scope:
            return norm_key

        if clean_raw_key in self.ALLOWED_SCOPE_TARGET_KEYS:
            for slot_name, src_key, dst_key in self.rules:
                if current_scope.lower() == slot_name.lower():
                    if clean_raw_key in {
                        src_key.lower(),
                        "value",
                        "string",
                        "prefix_prompt",
                    }:
                        return dst_key

            return f"{current_scope}_prompt"

        return norm_key
