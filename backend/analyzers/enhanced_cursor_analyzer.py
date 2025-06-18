import os
import sys
import hashlib
import logging
import json
import re
import networkx as nx
from collections import defaultdict, deque
from git import Repo, GitCommandError
from typing import List, Dict, Optional, Tuple, Set, Any, Union
from pathlib import Path

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

try:
    from parsers.language_parser import MultiLanguageParser
    from indexers.codebase_indexer import CodebaseIndexer
    from generators.test_code_generator import TestCodeGenerator
    from models.code_symbol import CodeSymbol
    from utils.git_utils import GitUtils
    from clients.ai_client import AIClient
    from analyzers.ai_service_integrator import AIServiceIntegrator
    from models.code_models import (
        CodeChange, TestCase, ImpactAnalysis, 
        AnalysisResult, TestStrategy, AnalysisSummary,
        RepositoryAnalysisResult
    )
except ImportError as e:
    print(f"导入模块失败: {e}")
    # 创建简单的替代类
    class MultiLanguageParser:
        def __init__(self):
            pass
        
        def get_language_from_file(self, file_path):
            ext = os.path.splitext(file_path)[1]
            lang_map = {'.py': 'python', '.js': 'javascript', '.vue': 'vue', '.ts': 'typescript'}
            return lang_map.get(ext)
        
        def extract_functions_and_classes(self, content, language):
            return [], []
        
        def calculate_complexity(self, content, language):
            return 1
        
        def extract_imports(self, content, language):
            return []
    
    class CodebaseIndexer:
        def __init__(self):
            pass
    
    class TestCodeGenerator:
        def __init__(self):
            pass
    
    class CodeSymbol:
        def __init__(self):
            pass
    
    class GitUtils:
        def __init__(self):
            pass
    
    class AIClient:
        def __init__(self):
            pass
    
    class AIServiceIntegrator:
        def __init__(self, config):
            pass
    
    class CodeChange:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TestCase:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ImpactAnalysis:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class AnalysisResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TestStrategy:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class AnalysisSummary:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class RepositoryAnalysisResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)


class EnhancedCursorAnalyzer:
    """增强版代码变更分析器 - 实现类似Cursor的智能分析"""
    
    def __init__(self, repo_path: str, config: Optional[Dict] = None):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化组件
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            self.logger.warning("sentence-transformers库未安装，将减少一些分析能力")
            self.embedding_model = None
        
        self.dependency_graph = nx.DiGraph()
        self.function_call_graph = nx.DiGraph()
        self.import_graph = defaultdict(set)
        
        # 多语言解析器
        self.parser = MultiLanguageParser()
        
        # AI服务集成
        self.ai_integrator = AIServiceIntegrator(self.config)
        
        # 缓存
        self._ast_cache = {}
        self._function_cache = {}
        
    async def analyze_repository_changes(self, commit_hash: Optional[str] = None) -> RepositoryAnalysisResult:
        """分析仓库变更的完整流程"""
        try:
            # 1. 获取变更
            changes = self._get_detailed_changes(commit_hash)
            if not changes:
                return RepositoryAnalysisResult(status="no_changes", message="未检测到代码变更")
            
            # 2. 构建依赖图
            self._build_dependency_graphs()
            
            # 3. 分析每个变更
            analysis_results = []
            for change in changes:
                impact = await self._analyze_change_impact(change)
                analysis_results.append(AnalysisResult(change=change, impact=impact))
            
            # 4. 生成全局测试策略
            global_test_strategy = self._generate_global_test_strategy(analysis_results)
            
            # 5. 生成分析摘要
            summary = self._generate_analysis_summary(analysis_results)
            
            return RepositoryAnalysisResult(
                status="success",
                changes_count=len(changes),
                analysis_results=analysis_results,
                global_test_strategy=global_test_strategy,
                summary=summary
            )
            
        except Exception as e:
            self.logger.error(f"分析过程出错: {str(e)}", exc_info=True)
            return RepositoryAnalysisResult(status="error", message=str(e))
    
    def _get_detailed_changes(self, commit_hash: Optional[str] = None) -> List[CodeChange]:
        """获取详细的代码变更信息"""
        changes = []
        
        try:
            if commit_hash:
                commit = self.repo.commit(commit_hash)
                parent = commit.parents[0] if commit.parents else None
                if not parent:
                    return changes
                diffs = parent.diff(commit)
            else:
                # 获取工作区变更
                diffs = self.repo.index.diff(None)
                diffs += self.repo.index.diff('HEAD')
            
            for diff in diffs:
                if not self._is_code_file(diff.a_path or diff.b_path):
                    continue
                
                change = self._create_code_change(diff)
                if change:
                    changes.append(change)
                    
        except Exception as e:
            self.logger.error(f"获取变更失败: {str(e)}")
        
        return changes
    
    def _create_code_change(self, diff) -> Optional[CodeChange]:
        """创建代码变更对象"""
        try:
            file_path = diff.a_path or diff.b_path
            language = self.parser.get_language_from_file(file_path)
            
            if not language:
                return None
            
            # 获取变更类型
            if diff.new_file:
                change_type = "added"
                old_content = ""
                new_content = self._read_file_content(file_path)
            elif diff.deleted_file:
                change_type = "deleted"
                old_content = diff.a_blob.data_stream.read().decode('utf-8', errors='ignore')
                new_content = ""
            else:
                change_type = "modified"
                old_content = diff.a_blob.data_stream.read().decode('utf-8', errors='ignore') if diff.a_blob else ""
                new_content = diff.b_blob.data_stream.read().decode('utf-8', errors='ignore') if diff.b_blob else ""
            
            # 分析受影响的函数和类
            old_functions, old_classes = self.parser.extract_functions_and_classes(old_content, language)
            new_functions, new_classes = self.parser.extract_functions_and_classes(new_content, language)
            
            affected_functions = list(set(new_functions) - set(old_functions)) + \
                               [f for f in new_functions if f in old_functions and 
                                self._function_changed(f, old_content, new_content)]
                                
            affected_classes = list(set(new_classes) - set(old_classes)) + \
                              [c for c in new_classes if c in old_classes and 
                               self._class_changed(c, old_content, new_content)]
            
            # 计算复杂度变化
            old_complexity = self.parser.calculate_complexity(old_content, language)
            new_complexity = self.parser.calculate_complexity(new_content, language)
            complexity_delta = new_complexity - old_complexity
            
            # 评估风险等级
            risk_level = self._assess_risk_level(file_path, affected_functions, affected_classes, complexity_delta)
            
            # 分析业务影响
            business_impact = self._analyze_business_impact(file_path, affected_functions, affected_classes, language)
            
            return CodeChange(
                file_path=file_path,
                change_type=change_type,
                old_content=old_content,
                new_content=new_content,
                affected_functions=affected_functions,
                affected_classes=affected_classes,
                complexity_delta=complexity_delta,
                risk_level=risk_level,
                business_impact=business_impact
            )
            
        except Exception as e:
            self.logger.error(f"创建变更对象失败: {str(e)}")
            return None
    
    def _build_dependency_graphs(self):
        """构建依赖关系图"""
        try:
            # 遍历所有代码文件
            for root, dirs, files in os.walk(self.repo_path):
                # 跳过.git等隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_code_file(file_path):
                        self._analyze_file_dependencies(file_path)
                        
        except Exception as e:
            self.logger.error(f"构建依赖图失败: {str(e)}")
    
    def _analyze_file_dependencies(self, file_path: str):
        """分析单个文件的依赖关系"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            language = self.parser.get_language_from_file(file_path)
            if not language:
                return
            
            module_name = self._get_module_name(file_path)
            
            # 提取导入语句
            imports = self.parser.extract_imports(content, language)
            
            for import_name in imports:
                self.import_graph[module_name].add(import_name)
                self.dependency_graph.add_edge(module_name, import_name)
            
            # 分析函数调用关系（简化版）
            functions, _ = self.parser.extract_functions_and_classes(content, language)
            for func in functions:
                full_func_name = f"{module_name}.{func}"
                self.function_call_graph.add_node(full_func_name)
                        
        except Exception as e:
            self.logger.debug(f"分析文件依赖失败 {file_path}: {str(e)}")
    
    async def _analyze_change_impact(self, change: CodeChange) -> ImpactAnalysis:
        """深度分析代码变更的影响"""
        try:
            # 1. 直接影响分析
            direct_impacts = self._find_direct_impacts(change)
            
            # 2. 间接影响分析
            indirect_impacts = self._find_indirect_impacts(change, direct_impacts)
            
            # 3. 风险因子识别
            risk_factors = self._identify_comprehensive_risks(change, direct_impacts, indirect_impacts)
            
            # 4. AI增强分析
            ai_analysis = None
            if self.ai_integrator.providers:
                language = self.parser.get_language_from_file(change.file_path)
                ai_analysis = await self.ai_integrator.analyze_code_change(
                    change.old_content, 
                    change.new_content, 
                    language or 'unknown'
                )
                
                if ai_analysis:
                    # 合并AI分析结果
                    if 'risks' in ai_analysis:
                        risk_factors.extend(ai_analysis['risks'])
            
            # 5. 智能测试用例生成
            suggested_tests = await self._generate_intelligent_tests(change, direct_impacts, indirect_impacts)
            
            # 6. 计算置信度
            confidence_score = self._calculate_confidence(change, direct_impacts, indirect_impacts, ai_analysis)
            
            return ImpactAnalysis(
                direct_impacts=direct_impacts,
                indirect_impacts=indirect_impacts,
                risk_factors=list(set(risk_factors)),  # 去重
                suggested_tests=suggested_tests,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            self.logger.error(f"影响分析失败: {str(e)}")
            return ImpactAnalysis([], [], [], [], 0.0)
    
    def _find_direct_impacts(self, change: CodeChange) -> List[str]:
        """查找直接影响"""
        impacts = []
        module_name = self._get_module_name(change.file_path)
        
        # 查找直接依赖此模块的其他模块
        for dependent_module, imports in self.import_graph.items():
            if module_name in imports or any(imp.startswith(module_name) for imp in imports):
                impacts.append(f"模块依赖: {dependent_module}")
        
        # 查找调用了变更函数的其他函数
        for func in change.affected_functions:
            full_func_name = f"{module_name}.{func}"
            if full_func_name in self.function_call_graph:
                callers = list(self.function_call_graph.predecessors(full_func_name))
                impacts.extend([f"函数调用: {caller}" for caller in callers])
        
        return impacts
    
    def _find_indirect_impacts(self, change: CodeChange, direct_impacts: List[str]) -> List[str]:
        """查找间接影响（影响传播）"""
        indirect_impacts = []
        visited = set()
        
        # 使用BFS进行影响传播分析
        queue = deque(direct_impacts)
        depth = 0
        max_depth = self.config.get('max_analysis_depth', 3)
        
        while queue and depth < max_depth:
            level_size = len(queue)
            depth += 1
            
            for _ in range(level_size):
                impact = queue.popleft()
                if impact in visited:
                    continue
                visited.add(impact)
                
                # 从影响中提取模块名
                if ":" in impact:
                    affected_module = impact.split(":")[1].strip()
                    
                    # 查找进一步的依赖
                    for dependent_module, imports in self.import_graph.items():
                        if affected_module in imports:
                            new_impact = f"间接影响(深度{depth}): {dependent_module}"
                            if new_impact not in indirect_impacts:
                                indirect_impacts.append(new_impact)
                                queue.append(new_impact)
        
        return indirect_impacts
    
    def _identify_comprehensive_risks(self, change: CodeChange, direct_impacts: List[str], 
                                    indirect_impacts: List[str]) -> List[str]:
        """识别综合风险因素"""
        risk_factors = []
        
        # 基于变更类型的风险
        if change.change_type == "added":
            risk_factors.append("新增代码可能引入未知缺陷")
        elif change.change_type == "deleted":
            risk_factors.append("删除代码可能影响依赖模块")
        elif change.change_type == "modified":
            if change.complexity_delta > 3:
                risk_factors.append(f"复杂度显著增加: +{change.complexity_delta:.1f}")
        
        # 基于影响范围的风险
        total_impacts = len(direct_impacts) + len(indirect_impacts)
        if total_impacts > 5:
            risk_factors.append(f"影响范围广泛: {total_impacts} 个模块")
        
        # 基于业务影响的风险
        critical_areas = ['payment', 'auth', 'security', 'user', 'order']
        for area in critical_areas:
            if any(area in impact.lower() for impact in change.business_impact):
                risk_factors.append(f"涉及关键业务领域: {area}")
        
        # 基于文件路径的风险
        if any(keyword in change.file_path.lower() for keyword in ['core', 'main', 'service', 'api']):
            risk_factors.append("修改核心组件")
        
        return risk_factors
    
    async def _generate_intelligent_tests(self, change: CodeChange, direct_impacts: List[str], 
                                        indirect_impacts: List[str]) -> List[TestCase]:
        """生成智能测试用例"""
        tests = []
        language = self.parser.get_language_from_file(change.file_path)
        
        # 为变更的每个函数生成测试
        for func_name in change.affected_functions:
            # AI生成测试用例
            ai_test_code = None
            if self.ai_integrator.providers:
                func_code = self._extract_function_code(change.new_content, func_name, language)
                if func_code:
                    ai_test_code = await self.ai_integrator.generate_test_cases(func_code, language or 'unknown')
            
            test = TestCase(
                name=f"test_{func_name}",
                test_type="unit",
                target_function=func_name,
                test_code=ai_test_code or self._generate_default_test_code(func_name, language),
                priority="high" if change.risk_level == "high" else "medium",
                coverage_areas=self._determine_coverage_areas(func_name, change.change_type),
                dependencies=[]
            )
            tests.append(test)
        
        # 为高风险变更生成集成测试
        if change.risk_level == "high" and direct_impacts:
            integration_test = TestCase(
                name=f"test_integration_{os.path.basename(change.file_path).replace('.', '_')}",
                test_type="integration",
                target_function="integration_scenario",
                test_code=self._generate_integration_test_code(change, direct_impacts, language),
                priority="high",
                coverage_areas=["模块交互", "数据流验证"],
                dependencies=direct_impacts[:3]  # 限制依赖数量
            )
            tests.append(integration_test)
        
        return tests
    
    def _extract_function_code(self, content: str, function_name: str, language: Optional[str]) -> Optional[str]:
        """提取函数代码"""
        if not language or not content:
            return None
        
        # 简化的函数提取逻辑
        lines = content.split('\n')
        func_lines = []
        in_function = False
        indent_level = 0
        
        for line in lines:
            if language == 'python':
                if f'def {function_name}(' in line or f'async def {function_name}(' in line:
                    in_function = True
                    indent_level = len(line) - len(line.lstrip())
                    func_lines.append(line)
                elif in_function:
                    if line.strip() == '':
                        func_lines.append(line)
                    elif len(line) - len(line.lstrip()) > indent_level:
                        func_lines.append(line)
                    else:
                        break
            elif language in ['javascript', 'typescript']:
                if f'function {function_name}(' in line or f'{function_name} = ' in line:
                    in_function = True
                    func_lines.append(line)
                    brace_count = line.count('{') - line.count('}')
                elif in_function:
                    func_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count == 0:
                        break
            # 可以继续添加其他语言的处理逻辑
        
        return '\n'.join(func_lines) if func_lines else None
    
    def _generate_default_test_code(self, func_name: str, language: Optional[str]) -> str:
        """生成默认测试代码"""
        if language == 'python':
            return f"""
import pytest

def test_{func_name}():
    '''测试 {func_name} 函数'''
    # TODO: 添加具体的测试逻辑
    assert True  # 占位符
    
def test_{func_name}_edge_cases():
    '''测试 {func_name} 边界条件'''
    # TODO: 添加边界条件测试
    pass
    
def test_{func_name}_error_handling():
    '''测试 {func_name} 异常处理'''
    # TODO: 添加异常处理测试
    pass
"""
        elif language in ['javascript', 'typescript']:
            return f"""
describe('{func_name}', () => {{
    test('should work correctly', () => {{
        // TODO: 添加具体的测试逻辑
        expect(true).toBe(true);
    }});
    
    test('should handle edge cases', () => {{
        // TODO: 添加边界条件测试
    }});
    
    test('should handle errors', () => {{
        // TODO: 添加异常处理测试
    }});
}});
"""
        else:
            return f"// TODO: 为 {func_name} 添加测试用例"
    
    def _generate_integration_test_code(self, change: CodeChange, impacts: List[str], language: Optional[str]) -> str:
        """生成集成测试代码"""
        if language == 'python':
            return f"""
import pytest
from unittest.mock import Mock, patch

class TestIntegration{os.path.basename(change.file_path).replace('.py', '').title()}:
    '''集成测试 - 验证模块交互'''
    
    def test_module_integration(self):
        '''测试模块集成'''
        # TODO: 实现集成测试逻辑
        # 验证与依赖模块的交互
        pass
    
    def test_data_flow(self):
        '''测试数据流'''
        # TODO: 验证数据在模块间的流转
        pass
"""
        else:
            return "// TODO: 添加集成测试"
    
    def _determine_coverage_areas(self, func_name: str, change_type: str) -> List[str]:
        """确定测试覆盖区域"""
        areas = ["基本功能验证"]
        
        if change_type == "added":
            areas.extend(["新功能测试", "兼容性验证"])
        elif change_type == "modified":
            areas.extend(["回归测试", "边界条件测试"])
        
        # 基于函数名推断测试重点
        if 'create' in func_name.lower():
            areas.append("数据创建验证")
        elif 'update' in func_name.lower():
            areas.append("数据更新验证")
        elif 'delete' in func_name.lower():
            areas.append("数据删除验证")
        elif 'validate' in func_name.lower():
            areas.append("输入验证测试")
        
        return areas
    
    def _calculate_confidence(self, change: CodeChange, direct_impacts: List[str], 
                            indirect_impacts: List[str], ai_analysis: Optional[Dict]) -> float:
        """计算分析置信度"""
        factors = []
        
        # 基于变更大小的置信度
        if change.complexity_delta < 2:
            factors.append(0.9)  # 小变更，置信度高
        elif change.complexity_delta < 5:
            factors.append(0.7)  # 中等变更
        else:
            factors.append(0.5)  # 大变更，置信度较低
        
        # 基于影响范围的置信度
        total_impacts = len(direct_impacts) + len(indirect_impacts)
        if total_impacts < 3:
            factors.append(0.8)
        elif total_impacts < 8:
            factors.append(0.6)
        else:
            factors.append(0.4)
        
        # 基于AI分析的置信度
        if ai_analysis:
            factors.append(0.9)  # 有AI分析支持
        else:
            factors.append(0.6)  # 仅基于规则分析
        
        # 基于语言支持的置信度
        language = self.parser.get_language_from_file(change.file_path)
        if language in ['python', 'javascript', 'typescript']:
            factors.append(0.9)  # 主要支持的语言
        elif language:
            factors.append(0.7)  # 部分支持的语言
        else:
            factors.append(0.3)  # 不支持的语言
        
        return sum(factors) / len(factors)
    
    def _generate_global_test_strategy(self, analysis_results: List[AnalysisResult]) -> TestStrategy:
        """生成全局测试策略"""
        
        high_risk_changes = sum(1 for result in analysis_results if result.change.risk_level == "high")
        medium_risk_changes = sum(1 for result in analysis_results if result.change.risk_level == "medium")
        low_risk_changes = len(analysis_results) - high_risk_changes - medium_risk_changes
        
        # 推荐测试类型
        recommended_test_types = []
        if high_risk_changes > 0:
            recommended_test_types.extend(["unit", "integration", "e2e", "performance"])
        elif medium_risk_changes > 0:
            recommended_test_types.extend(["unit", "integration"])
        else:
            recommended_test_types.extend(["unit"])
        
        # 生成测试优先级
        testing_priority = []
        for result in analysis_results:
            change = result.change
            if change.risk_level == "high":
                testing_priority.append({
                    "file": change.file_path,
                    "priority": "高",
                    "reason": "高风险变更，需要全面测试",
                    "suggested_tests": len(result.impact.suggested_tests)
                })
            elif change.risk_level == "medium":
                testing_priority.append({
                    "file": change.file_path,
                    "priority": "中",
                    "reason": "中等风险变更，建议重点测试",
                    "suggested_tests": len(result.impact.suggested_tests)
                })
        
        # 覆盖率建议
        coverage_recommendations = []
        total_functions = sum(len(result.change.affected_functions) for result in analysis_results)
        if total_functions > 10:
            coverage_recommendations.append("建议代码覆盖率达到90%以上")
        elif total_functions > 5:
            coverage_recommendations.append("建议代码覆盖率达到80%以上")
        else:
            coverage_recommendations.append("建议代码覆盖率达到70%以上")
        
        # 自动化建议
        automation_suggestions = []
        if high_risk_changes > 0:
            automation_suggestions.extend([
                "集成到CI/CD流程中",
                "添加性能测试监控",
                "设置自动化回归测试"
            ])
        
        # 估算测试时间
        test_time = high_risk_changes * 2 + medium_risk_changes * 1 + low_risk_changes * 0.5
        
        return TestStrategy(
            total_changes=len(analysis_results),
            high_risk_changes=high_risk_changes,
            medium_risk_changes=medium_risk_changes,
            low_risk_changes=low_risk_changes,
            recommended_test_types=list(set(recommended_test_types)),
            testing_priority=testing_priority,
            coverage_recommendations=coverage_recommendations,
            automation_suggestions=automation_suggestions,
            estimated_test_time=f"{test_time:.1f} hours"
        )
    
    def _generate_analysis_summary(self, analysis_results: List[AnalysisResult]) -> AnalysisSummary:
        """生成分析摘要"""
        total_changes = len(analysis_results)
        high_risk_count = sum(1 for result in analysis_results 
                             if result.change.risk_level == "high")
        medium_risk_count = sum(1 for result in analysis_results 
                               if result.change.risk_level == "medium")
        
        total_tests = sum(len(result.impact.suggested_tests) 
                         for result in analysis_results)
        
        avg_confidence = sum(result.impact.confidence_score 
                           for result in analysis_results) / total_changes if total_changes > 0 else 0
        
        # 统计涉及的业务领域
        business_areas = set()
        for result in analysis_results:
            business_areas.update(result.change.business_impact)
        
        # 统计编程语言
        languages = set()
        for result in analysis_results:
            file_path = result.change.file_path
            language = self.parser.get_language_from_file(file_path)
            if language:
                languages.add(language)
        
        return AnalysisSummary(
            total_changes=total_changes,
            high_risk_changes=high_risk_count,
            medium_risk_changes=medium_risk_count,
            low_risk_changes=total_changes - high_risk_count - medium_risk_count,
            total_suggested_tests=total_tests,
            average_confidence=round(avg_confidence, 2),
            affected_business_areas=list(business_areas),
            programming_languages=list(languages),
            recommendation=self._get_overall_recommendation(high_risk_count, medium_risk_count, total_changes)
        )
    
    def _get_overall_recommendation(self, high_risk_count: int, medium_risk_count: int, total_changes: int) -> str:
        """获取总体建议"""
        if high_risk_count > 0:
            return f"检测到 {high_risk_count} 个高风险变更，建议进行全面测试和代码审查后再部署"
        elif medium_risk_count > total_changes // 2:
            return "中等风险变更较多，建议重点测试核心功能"
        elif total_changes > 10:
            return "变更数量较多，建议分批测试和部署"
        else:
            return "变更风险可控，可以进行常规测试流程"
    
    # 辅助方法
    def _is_code_file(self, file_path: str) -> bool:
        """判断是否为代码文件"""
        if not file_path:
            return False
        return self.parser.get_language_from_file(file_path) is not None
    
    def _read_file_content(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            full_path = os.path.join(self.repo_path, file_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
    
    def _get_module_name(self, file_path: str) -> str:
        """获取模块名"""
        rel_path = os.path.relpath(file_path, self.repo_path)
        return rel_path.replace(os.path.sep, '.').rsplit('.', 1)[0]
    
    def _function_changed(self, func_name: str, old_content: str, new_content: str) -> bool:
        """检查函数是否发生变化"""
        old_func = self._extract_function_content(old_content, func_name)
        new_func = self._extract_function_content(new_content, func_name)
        return hashlib.md5(old_func.encode()).hexdigest() != hashlib.md5(new_func.encode()).hexdigest()
    
    def _class_changed(self, class_name: str, old_content: str, new_content: str) -> bool:
        """检查类是否发生变化"""
        old_class = self._extract_class_content(old_content, class_name)
        new_class = self._extract_class_content(new_content, class_name)
        return hashlib.md5(old_class.encode()).hexdigest() != hashlib.md5(new_class.encode()).hexdigest()
    
    def _extract_function_content(self, content: str, func_name: str) -> str:
        """提取函数内容"""
        # 简化实现
        lines = content.split('\n')
        func_lines = []
        in_function = False
        indent_level = 0
        
        for line in lines:
            if f'def {func_name}(' in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                func_lines.append(line)
            elif in_function:
                if line.strip() == '':
                    func_lines.append(line)
                elif len(line) - len(line.lstrip()) > indent_level:
                    func_lines.append(line)
                else:
                    break
        
        return '\n'.join(func_lines)
    
    def _extract_class_content(self, content: str, class_name: str) -> str:
        """提取类内容"""
        # 类似函数提取的逻辑
        lines = content.split('\n')
        class_lines = []
        in_class = False
        indent_level = 0
        
        for line in lines:
            if f'class {class_name}' in line:
                in_class = True
                indent_level = len(line) - len(line.lstrip())
                class_lines.append(line)
            elif in_class:
                if line.strip() == '':
                    class_lines.append(line)
                elif len(line) - len(line.lstrip()) > indent_level:
                    class_lines.append(line)
                else:
                    break
        
        return '\n'.join(class_lines)
    
    def _assess_risk_level(self, file_path: str, affected_functions: List[str], 
                          affected_classes: List[str], complexity_delta: float) -> str:
        """评估风险等级"""
        risk_score = 0
        
        # 基于文件路径的风险
        if any(keyword in file_path.lower() for keyword in ['core', 'main', 'service', 'api']):
            risk_score += 3
        elif any(keyword in file_path.lower() for keyword in ['util', 'helper', 'tool']):
            risk_score += 1
        
        # 基于变更范围的风险
        risk_score += len(affected_functions) * 0.5
        risk_score += len(affected_classes) * 1
        
        # 基于复杂度变化的风险
        if complexity_delta > 5:
            risk_score += 3
        elif complexity_delta > 2:
            risk_score += 1
        
        # 风险等级判定
        if risk_score >= 5:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _analyze_business_impact(self, file_path: str, affected_functions: List[str], 
                               affected_classes: List[str], language: Optional[str]) -> List[str]:
        """分析业务影响"""
        impacts = []
        
        # 基于文件路径推断业务领域
        path_keywords = {
            'user': '用户管理',
            'order': '订单处理',
            'payment': '支付系统',
            'auth': '身份认证',
            'product': '产品管理',
            'inventory': '库存管理',
            'notification': '通知系统',
            'report': '报表系统',
            'admin': '管理后台',
            'api': 'API接口',
            'service': '业务服务',
            'model': '数据模型',
            'controller': '控制器',
            'view': '视图层'
        }
        
        for keyword, business_area in path_keywords.items():
            if keyword in file_path.lower():
                impacts.append(business_area)
        
        # 基于函数名推断业务功能
        function_keywords = {
            'create': '数据创建',
            'update': '数据更新',
            'delete': '数据删除',
            'validate': '数据验证',
            'process': '业务处理',
            'calculate': '计算逻辑',
            'generate': '数据生成',
            'send': '消息发送',
            'notify': '通知推送',
            'login': '用户登录',
            'logout': '用户登出',
            'register': '用户注册',
            'encrypt': '数据加密',
            'decrypt': '数据解密',
            'backup': '数据备份',
            'restore': '数据恢复'
        }
        
        for func in affected_functions:
            for keyword, business_func in function_keywords.items():
                if keyword in func.lower():
                    impacts.append(business_func)
        
        # 基于类名推断业务实体
        class_keywords = {
            'user': '用户实体',
            'order': '订单实体',
            'product': '产品实体',
            'payment': '支付实体',
            'account': '账户实体',
            'session': '会话管理',
            'cache': '缓存系统',
            'database': '数据库操作',
            'queue': '队列系统',
            'scheduler': '调度系统'
        }
        
        for cls in affected_classes:
            for keyword, business_entity in class_keywords.items():
                if keyword in cls.lower():
                    impacts.append(business_entity)
        
        return list(set(impacts)) if impacts else ['通用功能'] 