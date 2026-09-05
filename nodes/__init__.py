"""
nodes/__init__.py
统一导出节点类映射。
"""

from .aggregator_node import MetaAggregatorInjectorNode
from .combine_node import MetaCombineNode
from .empty_node import EmptyStageMetaNode
from .probe_node import DataflowProbeNode
from .transformer_node import MetaTransformerNode

NODE_CLASSES = {
    "DataflowProbe": DataflowProbeNode,
    "MetaCombine": MetaCombineNode,
    "MetaTransformer": MetaTransformerNode,
    "MetaAggregatorInjector": MetaAggregatorInjectorNode,
    "EmptyStageMeta": EmptyStageMetaNode,
}

NODE_DISPLAY_NAMES = {
    "DataflowProbe": "🔍 Dataflow Lineage Probe",
    "MetaCombine": "🔗 Meta Cascade Combine",
    "MetaTransformer": "🛠️ Meta Transformer",
    "MetaAggregatorInjector": "📦 Meta Aggregator & Injector",
    "EmptyStageMeta": "⚪ Empty Stage Meta (Placeholder)",
}

__all__ = ["NODE_CLASSES", "NODE_DISPLAY_NAMES"]
