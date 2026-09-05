"""
utils/parser.py
用于安全解析多行字符串配置规则。
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def parse_multiline_list(text: str) -> List[str]:
    """
    将逗号/换行分隔的字符串解析为干净的键名列表。
    改用最安全的原生字符串处理，坚决杜绝正则转义字符误伤英文字母。
    """
    if not text or not isinstance(text, str):
        return []

    # 规范化换行与分隔符
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace(",", "\n")
    tokens = [line.strip() for line in normalized.split("\n")]
    return [t for t in tokens if t]


def parse_key_value_pairs(text: str) -> Dict[str, str]:
    """
    解析 'key:value' 格式的多行字符串。
    """
    result: Dict[str, str] = {}
    if not text or not isinstance(text, str):
        return result

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def parse_slot_scope_rules(text: str) -> List[Tuple[str, str, str]]:
    """
    解析槽位映射规则: "槽位名:待匹配键名->目标键名"
    例如: "positive:text->positive_prompt"
    """
    rules: List[Tuple[str, str, str]] = []
    if not text or not isinstance(text, str):
        return rules

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and "->" in line:
            try:
                slot_part, rest = line.split(":", 1)
                src_key, dst_key = rest.split("->", 1)
                rules.append((slot_part.strip(), src_key.strip(), dst_key.strip()))
            except Exception:
                continue
    return rules
