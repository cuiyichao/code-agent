import tree_sitter
from tree_sitter import Language, Parser
from typing import List, Dict, Optional
from backend.models.code_symbol import CodeSymbol, CodeModule
import logging

class TreeSitterAnalyzer:
    """使用TreeSitter进行代码解析和符号提取的分析器"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_language_definitions()
        self.parsers = self._initialize_parsers()

    def _load_language_definitions(self):
        """加载TreeSitter语言定义"""
        # 实际实现中需要编译或加载语言定义
        self.LANGUAGES = {
            'python': Language('build/my-languages.so', 'python'),
            'javascript': Language('build/my-languages.so', 'javascript'),
            'java': Language('build/my-languages.so', 'java'),
            'cpp': Language('build/my-languages.so', 'cpp'),
            'go': Language('build/my-languages.so', 'go')
        }

    def _initialize_parsers(self) -> Dict[str, Parser]:
        """初始化不同语言的解析器"""
        parsers = {}
        for lang_name, lang in self.LANGUAGES.items():
            parser = Parser()
            parser.set_language(lang)
            parsers[lang_name] = parser
        return parsers

    def get_language(self, file_path: str) -> Optional[str]:
        """根据文件路径判断编程语言"""
        ext = file_path.split('.')[-1].lower()
        ext_map = {
            'py': 'python',
            'js': 'javascript',
            'java': 'java',
            'cpp': 'cpp',
            'hpp': 'cpp',
            'c': 'cpp',
            'h': 'cpp',
            'go': 'go'
        }
        return ext_map.get(ext)

    def parse_code(self, code: bytes, language: str) -> Optional[tree_sitter.Node]:
        """解析代码并返回AST根节点"""
        if language not in self.parsers:
            self.logger.warning(f"Unsupported language: {language}")
            return None
        try:
            tree = self.parsers[language].parse(code)
            return tree.root_node
        except Exception as e:
            self.logger.error(f"Error parsing code: {str(e)}")
            return None

    def extract_symbols(self, root_node: tree_sitter.Node, code: bytes, file_path: str) -> List[CodeSymbol]:
        """从AST中提取符号信息"""
        symbols = []
        # 实际实现需要根据不同语言的语法树结构递归提取符号
        # 这里仅提供Python的基础实现示例
        self._traverse_python_ast(root_node, code, file_path, symbols)
        return symbols

    def _traverse_python_ast(self, node: tree_sitter.Node, code: bytes, file_path: str, symbols: List[CodeSymbol]):
        """递归遍历Python AST提取符号"""
        if node.type == 'function_definition':
            func_name = self._get_node_text(node.child_by_field_name('name'), code)
            if func_name:
                symbol = CodeSymbol(
                    name=func_name,
                    symbol_type='function',
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_char=node.start_point[1],
                    end_char=node.end_point[1],
                    parameters=self._extract_parameters(node, code),
                    return_type=None
                )
                symbols.append(symbol)
        elif node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            if class_name:
                symbol = CodeSymbol(
                    name=class_name,
                    symbol_type='class',
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_char=node.start_point[1],
                    end_char=node.end_point[1]
                )
                symbols.append(symbol)

        # 递归遍历子节点
        for child in node.children:
            self._traverse_python_ast(child, code, file_path, symbols)

    def _get_node_text(self, node: Optional[tree_sitter.Node], code: bytes) -> Optional[str]:
        """获取节点文本内容"""
        if node is None:
            return None
        return code[node.start_byte:node.end_byte].decode('utf-8')

    def _extract_parameters(self, func_node: tree_sitter.Node, code: bytes) -> List[str]:
        """提取函数参数"""
        params = []
        param_list = func_node.child_by_field_name('parameters')
        if param_list:
            for param in param_list.children:
                if param.type == 'identifier':
                    param_name = self._get_node_text(param, code)
                    if param_name:
                        params.append(param_name)
        return params

    def build_ast(self, code: bytes, language: str) -> Dict:
        """构建AST的字典表示"""
        root_node = self.parse_code(code, language)
        if not root_node:
            return {}
        return self._node_to_dict(root_node, code)

    def _node_to_dict(self, node: tree_sitter.Node, code: bytes) -> Dict:
        """将节点转换为字典表示"""
        return {
            'type': node.type,
            'text': self._get_node_text(node, code),
            'start_line': node.start_point[0] + 1,
            'end_line': node.end_point[0] + 1,
            'start_char': node.start_point[1],
            'end_char': node.end_point[1],
            'children': [self._node_to_dict(child, code) for child in node.children]
        }