from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any

@dataclass
class CodeSymbol:
    """代码符号（函数、类、变量等）"""
    name: str
    symbol_type: str  # 'function', 'class', 'variable', 'import'
    file_path: str
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str]
    parent: Optional[str]  # 父级符号（如类中的方法）
    calls: Set[str] = field(default_factory=set)  # 调用的其他符号
    called_by: Set[str] = field(default_factory=set)  # 被哪些符号调用
    dependencies: Set[str] = field(default_factory=set)  # 依赖的模块
    semantic_hash: Optional[str] = None  # 语义哈希
    complexity_score: int = 0

@dataclass
class CodeModule:
    """代码模块"""
    file_path: str
    symbols: List[CodeSymbol]
    imports: Set[str]
    exports: Set[str]
    ast_hash: str
    last_modified: float
    language: str