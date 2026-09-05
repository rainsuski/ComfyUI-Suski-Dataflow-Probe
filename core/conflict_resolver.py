"""
core/conflict_resolver.py
多阶段或同链路中同名键值的解决策略。
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


class ConflictResolver:
    """
    支持 Last, First, List, Index, Auto-Rename 五种冲突解决策略。
    内置对容器型字段 (如 loras) 的集合保护机制。
    """

    # 容器型字段：本身代表多项叠加，绝不受 Last/First 策略的单项截断影响
    COLLECTION_KEYS: Set[str] = {
        "loras",
        "lora_stack",
    }

    @classmethod
    def resolve(
        cls,
        collected_values: Dict[str, List[Any]],
        strategy: str = "Last",
        strategy_index: int = 0,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        strategy = strategy.strip().lower()

        for key, val_list in collected_values.items():
            if not val_list:
                continue

            clean_key = key.strip().lower()

            # 1. 容器型字段特殊保护：保持全量列表，绝不截断为单元素
            if clean_key in cls.COLLECTION_KEYS:
                result[key] = val_list
                continue

            # 2. 常规标量字段的冲突解决策略
            if strategy == "last":
                result[key] = val_list[0]
            elif strategy == "first":
                result[key] = val_list[-1]
            elif strategy == "list":
                result[key] = val_list if len(val_list) > 1 else val_list[0]
            elif strategy == "index":
                idx = max(0, min(strategy_index, len(val_list) - 1))
                result[key] = val_list[idx]
            elif strategy == "auto-rename":
                if len(val_list) == 1:
                    result[key] = val_list[0]
                else:
                    for i, val in enumerate(val_list):
                        result[f"{key}_{i + 1}"] = val
            else:
                result[key] = val_list[0]

        return result
