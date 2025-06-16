import os
import json
import logging
from typing import List, Dict, Optional, Set
from sentence_transformers import SentenceTransformer
import numpy as np
from ..models.code_symbol import CodeSymbol, CodeModule
from ..parsers.tree_sitter_analyzer import TreeSitterAnalyzer

class CodebaseIndexer:
    """代码库索引器，用于构建和管理代码符号的向量索引"""
    def __init__(self, index_dir: str = ".code_index"):
        self.logger = logging.getLogger(__name__)
        self.index_dir = index_dir
        self.symbol_index = {}
        self.vector_db = {}
        self.import_graph = {}
        self.module_index = {}
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.parser = TreeSitterAnalyzer()
        self._initialize_index_directory()

    def _initialize_index_directory(self):
        """初始化索引目录"""
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
            self.logger.info(f"Created index directory at {self.index_dir}")

    def build_index(self, codebase_path: str) -> Dict:
        """构建整个代码库的索引"""
        self.logger.info(f"Starting to build index for codebase: {codebase_path}")
        self.symbol_index = {}
        self.vector_db = {}
        self.import_graph = {}
        self.module_index = {}

        # 遍历代码库目录
        for root, _, files in os.walk(codebase_path):
            for file in files:
                if self._is_supported_file(file):
                    file_path = os.path.join(root, file)
                    self._process_file(file_path, codebase_path)

        # 保存索引到磁盘
        self._save_index()
        self.logger.info(f"Successfully built index with {len(self.symbol_index)} symbols")
        return {
            "symbol_count": len(self.symbol_index),
            "module_count": len(self.module_index),
            "index_path": self.index_dir
        }

    def _is_supported_file(self, file_name: str) -> bool:
        """检查文件是否为支持的类型"""
        supported_extensions = {'.py', '.js', '.java', '.cpp', '.h', '.go'}
        ext = os.path.splitext(file_name)[1].lower()
        return ext in supported_extensions

    def _process_file(self, file_path: str, codebase_root: str) -> None:
        """处理单个文件，提取符号并添加到索引"""
        try:
            with open(file_path, 'rb') as f:
                code = f.read()

            # 提取模块信息
            module_path = self._get_module_path(file_path, codebase_root)
            self.logger.debug(f"Processing module: {module_path}")

            # 解析代码并提取符号
            language = self.parser.get_language(file_path)
            if not language:
                return

            root_node = self.parser.parse_code(code, language)
            if not root_node:
                return

            symbols = self.parser.extract_symbols(root_node, code, file_path)
            if not symbols:
                return

            # 创建模块并添加符号
            module = CodeModule(
                path=module_path,
                file_path=file_path,
                symbols=symbols
            )
            self.module_index[module_path] = module

            # 提取导入信息
            imports = self.extract_imports_exports(file_path, code, language)
            self.import_graph[module_path] = imports

            # 为符号创建嵌入并添加到索引
            for symbol in symbols:
                self._add_symbol_to_index(symbol, module_path)

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")

    def _get_module_path(self, file_path: str, codebase_root: str) -> str:
        """获取模块路径"""
        relative_path = os.path.relpath(file_path, codebase_root)
        # 转换为Python风格的模块路径
        if relative_path.endswith('.py'):
            return relative_path[:-3].replace(os.sep, '.')
        return relative_path.replace(os.sep, '.')

    def _add_symbol_to_index(self, symbol: CodeSymbol, module_path: str) -> None:
        """将符号添加到索引并创建嵌入"""
        # 创建符号ID
        symbol_id = f"{module_path}::{symbol.name}::{symbol.symbol_type}"
        self.symbol_index[symbol_id] = {
            "symbol": symbol,
            "module_path": module_path
        }

        # 创建符号嵌入
        symbol_text = self._generate_symbol_text(symbol)
        embedding = self.embedding_model.encode([symbol_text])[0]
        self.vector_db[symbol_id] = embedding.tolist()

    def _generate_symbol_text(self, symbol: CodeSymbol) -> str:
        """生成用于嵌入的符号文本表示"""
        if symbol.symbol_type == 'function':
            params = ', '.join(symbol.parameters) if symbol.parameters else ''
            return f"def {symbol.name}({params}): {symbol.return_type or 'None'}"
        elif symbol.symbol_type == 'class':
            return f"class {symbol.name}"
        return f"{symbol.symbol_type} {symbol.name}"

    def find_similar_symbols(self, query: str, top_k: int = 5) -> List[Dict]:
        """查找语义相似的符号"""
        if not self.vector_db or not self.symbol_index:
            self.logger.warning("Index is empty, cannot find similar symbols")
            return []

        # 生成查询嵌入
        query_embedding = self.embedding_model.encode([query])[0]

        # 计算相似度
        similarities = []
        for symbol_id, embedding in self.vector_db.items():
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            similarities.append((symbol_id, similarity))

        # 按相似度排序并返回前k个结果
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []

        for symbol_id, score in similarities[:top_k]:
            symbol_info = self.symbol_index.get(symbol_id)
            if symbol_info:
                results.append({
                    "symbol": symbol_info["symbol"],
                    "module_path": symbol_info["module_path"],
                    "similarity_score": float(score)
                })

        return results

    def extract_imports_exports(self, file_path: str, code: bytes, language: str) -> Dict:
        """提取文件的导入和导出信息"""
        # 实际实现需要根据不同语言解析导入语句
        # 这里仅提供基础框架
        return {
            "imports": [],
            "exports": []
        }

    def resolve_import_paths(self, module_path: str, import_statement: str) -> Optional[str]:
        """解析导入路径，返回目标模块路径"""
        # 实际实现需要根据不同语言的导入规则解析
        return None

    def _save_index(self):
        """保存索引到磁盘"""
        # 保存符号索引
        with open(os.path.join(self.index_dir, "symbol_index.json"), "w") as f:
            json.dump({
                k: {
                    "symbol": v["symbol"].__dict__,
                    "module_path": v["module_path"]
                } for k, v in self.symbol_index.items()
            }, f, indent=2)

        # 保存向量数据库
        with open(os.path.join(self.index_dir, "vector_db.json"), "w") as f:
            json.dump(self.vector_db, f, indent=2)

        # 保存导入图
        with open(os.path.join(self.index_dir, "import_graph.json"), "w") as f:
            json.dump(self.import_graph, f, indent=2)

        # 保存模块索引
        with open(os.path.join(self.index_dir, "module_index.json"), "w") as f:
            json.dump({
                k: v.__dict__ for k, v in self.module_index.items()
            }, f, indent=2)

    def load_index(self) -> bool:
        """从磁盘加载索引"""
        try:
            # 加载符号索引
            with open(os.path.join(self.index_dir, "symbol_index.json"), "r") as f:
                symbol_data = json.load(f)
                self.symbol_index = {}
                for k, v in symbol_data.items():
                    symbol = CodeSymbol(**v["symbol"])
                    self.symbol_index[k] = {
                        "symbol": symbol,
                        "module_path": v["module_path"]
                    }

            # 加载向量数据库
            with open(os.path.join(self.index_dir, "vector_db.json"), "r") as f:
                self.vector_db = json.load(f)

            # 加载导入图
            with open(os.path.join(self.index_dir, "import_graph.json"), "r") as f:
                self.import_graph = json.load(f)

            # 加载模块索引
            with open(os.path.join(self.index_dir, "module_index.json"), "r") as f:
                module_data = json.load(f)
                self.module_index = {}
                for k, v in module_data.items():
                    symbols = [CodeSymbol(**s) for s in v["symbols"]]
                    module = CodeModule(
                        path=v["path"],
                        file_path=v["file_path"],
                        symbols=symbols
                    )
                    self.module_index[k] = module

            self.logger.info(f"Successfully loaded index with {len(self.symbol_index)} symbols")
            return True
        except Exception as e:
            self.logger.error(f"Error loading index: {str(e)}")
            return False