"""
core/conflict_resolver.py
多阶段或同链路中同名键值的解决策略。
"""

from __future__ import annotations

from typing import Any, Dict, List


class ConflictResolver:
    """
    支持 Last, First, List, Index, Auto-Rename 五种冲突解决策略。
    """

    @staticmethod
    def resolve(
        collected_values: Dict[str, List[Any]],
        strategy: str = "Last",
        strategy_index: int = 0,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        strategy = strategy.strip().lower()

        for key, val_list in collected_values.items():
            if not val_list:
                continue

            if strategy == "last":
                # 取遍历中最靠近探针（最新）的值
                result[key] = val_list[0]
            elif strategy == "first":
                # 取溯源到最顶层（最源头）的值
                result[key] = val_list[-1]
            elif strategy == "list":
                # 保留所有值构成的列表
                result[key] = val_list if len(val_list) > 1 else val_list[0]
            elif strategy == "index":
                # 按照指定索引提取
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
