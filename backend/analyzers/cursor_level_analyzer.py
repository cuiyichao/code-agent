import os
import logging
import json
from typing import List, Dict, Optional, Tuple
from git import Repo, GitCommandError
from ..indexers.codebase_indexer import CodebaseIndexer
from ..models.semantic_change import SemanticChange
from ..models.code_symbol import CodeSymbol
from backend.clients.ai_client import AIClient
import numpy as np
from sentence_transformers import SentenceTransformer

class CursorLevelAnalyzer:
    """代码变更分析器，用于分析代码变更的语义影响和风险评估"""
    def __init__(self, codebase_path: str, index_dir: str = ".code_index"):
        self.logger = logging.getLogger(__name__)
        self.codebase_path = codebase_path
        self.indexer = CodebaseIndexer(index_dir)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.ai_client = AIClient()
        self.change_types = {
            'semantic_change': '语义变更',
            'signature_change': '签名变更',
            'logic_change': '逻辑变更',
            'new_feature': '新增功能',
            'refactoring': '重构',
            'bug_fix': '错误修复'
        }

    async def analyze_code_changes(self, commit_hash: Optional[str] = None) -> List[SemanticChange]:
        """分析代码变更并返回语义变更列表"""
        self.logger.info(f"Starting code change analysis for commit: {commit_hash or 'latest'}")

        # 获取Git变更
        changes = self._get_git_changes(commit_hash)
        if not changes:
            self.logger.info("No code changes found")
            return []

        # 确保索引是最新的
        if not self.indexer.load_index():
            self.logger.info("Index not found, building new index")
            self.indexer.build_index(self.codebase_path)

        # 分析每个变更文件
        semantic_changes = []
        for file_path, (old_content, new_content) in changes.items():
            if not self._is_supported_file(file_path):
                continue

            change = await self._analyze_semantic_change(file_path, old_content, new_content)
            if change:
                semantic_changes.append(change)

        # 分析影响传播
        for change in semantic_changes:
            impact_chain = self._analyze_impact_propagation(change)
            change.business_impact = f"影响传播链: {impact_chain}"

            # 生成测试建议
            change.suggested_tests = await self._generate_intelligent_tests(change)

            # 风险评估
            change.risk_factors = self._identify_risk_factors(change, impact_chain)

        return semantic_changes

    def _get_git_changes(self, commit_hash: Optional[str] = None) -> Dict[str, Tuple[bytes, bytes]]:
        """获取Git提交中的文件变更"""
        try:
            repo = Repo(self.codebase_path)
            if commit_hash:
                # 比较指定提交与上一个提交
                commit = repo.commit(commit_hash)
                parent_commit = commit.parents[0] if commit.parents else None
                if not parent_commit:
                    self.logger.warning("No parent commit found, cannot compare")
                    return {}
                diffs = parent_commit.diff(commit)
            else:
                # 获取工作区未提交的变更
                diffs = repo.index.diff(None)
                # 添加已暂存但未提交的变更
                diffs += repo.index.diff('HEAD')

            changes = {}
            for diff in diffs:
                if diff.deleted_file:
                    continue

                file_path = os.path.join(self.codebase_path, diff.a_path)
                old_content = b''
                new_content = b''

                if diff.new_file:
                    with open(file_path, 'rb') as f:
                        new_content = f.read()
                else:
                    old_content = diff.a_blob.data_stream.read() if diff.a_blob else b''
                    new_content = diff.b_blob.data_stream.read() if diff.b_blob else b''

                changes[file_path] = (old_content, new_content)

            return changes

        except GitCommandError as e:
            self.logger.error(f"Git command error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error getting git changes: {str(e)}")
        return {}

    async def _analyze_semantic_change(self, file_path: str, old_content: bytes, new_content: bytes) -> Optional[SemanticChange]:
        """分析单个文件的语义变更"""
        language = self.indexer.parser.get_language(file_path)
        if not language:
            return None

        # 解析新旧代码
        old_root = self.indexer.parser.parse_code(old_content, language) if old_content else None
        new_root = self.indexer.parser.parse_code(new_content, language) if new_content else None

        # 提取新旧符号
        old_symbols = self.indexer.parser.extract_symbols(old_root, old_content, file_path) if old_root else []
        new_symbols = self.indexer.parser.extract_symbols(new_root, new_content, file_path) if new_root else []

        # 找出变更的符号
        changed_symbols = self._find_changed_symbols(old_symbols, new_symbols, old_content, new_content)
        if not changed_symbols:
            return None

        # 计算语义相似度
        similarity = self._calculate_semantic_similarity(old_content, new_content)

        # 分类变更类型
        change_type = self._classify_change_type(old_symbols, new_symbols, changed_symbols)

        # AI增强分析
        ai_analysis = await self.ai_client.analyze_code_change(
            old_content.decode('utf-8', errors='ignore'),
            new_content.decode('utf-8', errors='ignore')
        )
        if ai_analysis:
            # 使用AI结果覆盖分类
            if 'change_type' in ai_analysis:
                change_type = ai_analysis['change_type']
            # 合并风险因素
            if 'risks' in ai_analysis:
                risk_factors = ai_analysis['risks']

        # 分析业务影响
        business_impact = self._analyze_business_impact(changed_symbols, file_path)
        if ai_analysis and 'business_impact' in ai_analysis:
            business_impact += f"; AI分析: {ai_analysis['business_impact']}"

        return SemanticChange(
            file_path=file_path,
            change_type=change_type,
            affected_symbols=changed_symbols,
            semantic_similarity=similarity,
            business_impact=business_impact,
            risk_factors=[],
            suggested_tests=[]
        )

    def _find_changed_symbols(self, old_symbols: List[CodeSymbol], new_symbols: List[CodeSymbol], old_content: bytes, new_content: bytes) -> List[CodeSymbol]:
        """找出变更的符号"""
        # 简单实现：比较符号名称和位置
        changed_symbols = []

        # 查找新增和修改的符号
        for new_sym in new_symbols:
            old_sym = next((s for s in old_symbols if s.name == new_sym.name and s.symbol_type == new_sym.symbol_type), None)
            if not old_sym:
                changed_symbols.append(new_sym)
            else:
                # 检查符号是否有变化
                if not self._symbols_are_equal(old_sym, new_sym, old_content, new_content):
                    changed_symbols.append(new_sym)

        return changed_symbols

    def _symbols_are_equal(self, old_sym: CodeSymbol, new_sym: CodeSymbol, old_content: bytes, new_content: bytes) -> bool:
        """判断两个符号是否相等"""
        # 简单实现：比较位置和参数
        if old_sym.start_line != new_sym.start_line or old_sym.end_line != new_sym.end_line:
            return False

        if old_sym.parameters != new_sym.parameters:
            return False

        return True

    def _calculate_semantic_similarity(self, old_content: bytes, new_content: bytes) -> float:
        """计算新旧代码的语义相似度"""
        if not old_content or not new_content:
            return 0.0

        try:
            old_text = old_content.decode('utf-8')
            new_text = new_content.decode('utf-8')

            # 生成嵌入
            old_embedding = self.embedding_model.encode([old_text])[0]
            new_embedding = self.embedding_model.encode([new_text])[0]

            # 计算余弦相似度
            similarity = np.dot(old_embedding, new_embedding) / (
                np.linalg.norm(old_embedding) * np.linalg.norm(new_embedding)
            )
            return float(similarity)
        except Exception as e:
            self.logger.error(f"Error calculating semantic similarity: {str(e)}")
            return 0.0

    def _classify_change_type(self, old_symbols: List[CodeSymbol], new_symbols: List[CodeSymbol], changed_symbols: List[CodeSymbol]) -> str:
        """分类变更类型"""
        # 简单实现：基于符号变化数量和类型
        if len(new_symbols) > len(old_symbols) and len(changed_symbols) == len(new_symbols) - len(old_symbols):
            return 'new_feature'
        elif any(s.symbol_type == 'function' and s.parameters for s in changed_symbols):
            return 'signature_change'
        else:
            return 'semantic_change'

    def _analyze_business_impact(self, changed_symbols: List[CodeSymbol], file_path: str) -> str:
        """分析业务影响"""
        # 简单实现：基于符号类型和文件路径
        impact_level = '低'
        if 'service' in file_path.lower() or 'api' in file_path.lower():
            impact_level = '高'
        elif 'utils' in file_path.lower() or 'helpers' in file_path.lower():
            impact_level = '中'

        return f"变更影响级别: {impact_level}, 影响符号数量: {len(changed_symbols)}"

    def _identify_risk_factors(self, change: SemanticChange, impact_chain: List[str]) -> List[str]:
        """识别风险因素"""
        risk_factors = []

        # 基于变更类型的风险
        if change.change_type in ['signature_change', 'logic_change']:
            risk_factors.append(f"{self.change_types[change.change_type]}可能导致调用方错误")

        # 基于影响范围的风险
        if len(impact_chain) > 3:
            risk_factors.append(f"影响范围广，传播链长度: {len(impact_chain)}")

        # 基于语义相似度的风险
        if change.semantic_similarity < 0.5:
            risk_factors.append(f"语义变化大，相似度: {change.semantic_similarity:.2f}")

        return risk_factors

    def _analyze_impact_propagation(self, change: SemanticChange) -> List[str]:
        """分析影响传播链"""
        # 简单实现：基于导入图查找直接依赖
        impact_chain = []
        module_path = self.indexer._get_module_path(change.file_path, self.codebase_path)

        # 查找依赖当前模块的其他模块
        for dep_module, imports in self.indexer.import_graph.items():
            if any(module_path in imp for imp in imports.get('imports', [])):
                impact_chain.append(dep_module)

        return impact_chain[:5]  # 限制返回前5个依赖模块

    async def _generate_intelligent_tests(self, change: SemanticChange) -> List[Dict]:
        """生成智能测试建议"""
        tests = []
        from backend.utils.common import extract_function_code

        for symbol in change.affected_symbols:
            test_type = '单元测试'
            if symbol.symbol_type == 'class':
                test_type = '集成测试'

            # 提取函数代码
            function_code = extract_function_code(new_content.decode('utf-8'), symbol)
            if function_code:
                # AI生成测试用例
                test_code = await self.ai_client.generate_test_case(function_code)
            else:
                test_code = None

            tests.append({
                'test_type': test_type,
                'target': f"{symbol.name}",
                'focus_areas': self._determine_test_focus_areas(symbol, change.change_type),
                'ai_generated_test': test_code
            })

        return tests

    def _determine_test_focus_areas(self, symbol: CodeSymbol, change_type: str) -> List[str]:
        """确定测试重点领域"""
        if change_type == 'signature_change':
            return ['参数验证', '返回值类型检查', '异常处理']
        elif change_type == 'logic_change':
            return ['边界条件测试', '业务规则验证', '性能测试']
        elif change_type == 'new_feature':
            return ['功能验证', '兼容性测试', '用户场景测试']
        else:
            return ['基本功能验证', '回归测试']

    def _is_supported_file(self, file_path: str) -> bool:
        """检查文件是否为支持的类型"""
        return self.indexer._is_supported_file(file_path)

    def rebuild_index(self) -> Dict:
        """重建代码库索引"""
        return self.indexer.build_index(self.codebase_path)

    def analyze_symbol_usage_patterns(self, symbol_name: str) -> Dict:
        """分析符号使用模式"""
        # 查找相似符号
        similar_symbols = self.indexer.find_similar_symbols(symbol_name)

        # 分析使用模式
        usage_patterns = {
            'parameter_types': [],
            'return_types': [],
            'call_contexts': []
        }

        # 简单实现：从相似符号中提取模式
        for item in similar_symbols:
            symbol = item['symbol']
            if symbol.parameters:
                usage_patterns['parameter_types'].extend(symbol.parameters)
            if symbol.return_type:
                usage_patterns['return_types'].append(symbol.return_type)

        # 统计频率
        usage_patterns['parameter_types'] = self._count_frequency(usage_patterns['parameter_types'])
        usage_patterns['return_types'] = self._count_frequency(usage_patterns['return_types'])

        return {
            'symbol_name': symbol_name,
            'similar_symbols_count': len(similar_symbols),
            'usage_patterns': usage_patterns
        }

    def _count_frequency(self, items: List[str]) -> Dict[str, int]:
        """统计项目频率"""
        frequency = {}
        for item in items:
            frequency[item] = frequency.get(item, 0) + 1
        # 按频率排序
        return dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))

    def calculate_analysis_confidence(self, change: SemanticChange) -> float:
        """计算分析置信度"""
        # 基于多个因素计算置信度
        factors = []

        # 语义相似度因素
        factors.append(change.semantic_similarity)

        # 符号数量因素
        symbol_factor = min(len(change.affected_symbols) / 10, 1.0)
        factors.append(symbol_factor)

        # 综合计算置信度
        confidence = sum(factors) / len(factors)
        return float(confidence)

    def call_ai_api(self, prompt: str) -> Optional[str]:
        """调用AI API进行辅助分析"""
        # 实际实现需要集成AI API
        self.logger.warning("AI API call not implemented")
        return None