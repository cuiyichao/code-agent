from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .code_symbol import CodeSymbol

@dataclass
class SemanticChange:
    """语义级代码变更"""
    file_path: str
    change_type: str  # 'semantic_change', 'signature_change', 'logic_change', 'new_feature'
    affected_symbols: List[CodeSymbol]
    semantic_similarity: float  # 与原代码的语义相似度
    business_impact: str  # 业务影响描述
    risk_factors: List[str]
    suggested_tests: List[Dict]