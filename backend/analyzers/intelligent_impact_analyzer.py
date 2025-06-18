import os
import logging
import json
from typing import Dict, List, Any
from dataclasses import dataclass
import time
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 修复导入路径问题
try:
    from backend.indexers.codebase_indexer import CodebaseIndexer
    from backend.models.code_symbol import CodeSymbol
    from backend.utils.git_utils import GitUtils
    from backend.clients.ai_client import AIClient
except ImportError:
    try:
        from indexers.codebase_indexer import CodebaseIndexer
        from models.code_symbol import CodeSymbol
        from utils.git_utils import GitUtils
        from clients.ai_client import AIClient
    except ImportError:
        # 创建回退类
        class CodebaseIndexer:
            def __init__(self, *args, **kwargs):
                self.symbol_index = {}
                self.module_index = {}
                
            def build_index(self, path):
                return {'symbol_count': 0, 'module_count': 0}
                
            def find_similar_symbols(self, query, top_k=5):
                return []
        
        class CodeSymbol:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class GitUtils:
            def __init__(self, *args, **kwargs):
                pass
                
            def get_diff(self, *args, **kwargs):
                return ""
                
            def get_changed_files(self, *args, **kwargs):
                return []
        
        class AIClient:
            def __init__(self, *args, **kwargs):
                pass
                
            async def analyze_code_change(self, *args, **kwargs):
                return None

@dataclass
class ChangeImpact:
    """代码变更影响分析结果"""
    symbol_name: str
    file_path: str
    change_type: str  # addition, deletion, modification
    impact_level: str  # high, medium, low
    affected_areas: List[str]
    risk_factors: List[str]
    dependency_chain: List[str]
    business_impact: str
    test_priority: int

@dataclass
class ImpactScope:
    """影响范围分析"""
    affected_modules: List[str]
    affected_business_domains: Dict[str, List[str]]
    integration_points: List[str]
    external_dependencies: List[str]
    user_facing_changes: List[str]

class IntelligentImpactAnalyzer:
    """基于代码索引和AI的智能影响分析器"""
    
    def __init__(self, project_path: str):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🤖 初始化智能影响分析器 - 项目路径: {project_path}")
        
        self.project_path = project_path
        self.git_utils = GitUtils()
        self.indexer = CodebaseIndexer(index_dir=os.path.join(project_path, ".code_index"))
        
        # 强制设置环境变量（在AI客户端初始化之前）
        os.environ['AI_PROVIDER'] = 'qwen'
        os.environ['DASHSCOPE_API_KEY'] = 'sk-f7c7af7a5ff14c1cb6a05d6f979a8c63'
        os.environ['AI_MODEL'] = 'qwen-turbo-2025-04-28'
        
        self.ai_client = AIClient()  # 添加AI客户端
        self.symbol_index = {}
        self.dependency_graph = {}
        
        # 日志AI配置信息
        self.logger.info(f"🔧 AI客户端配置 - 提供商: {getattr(self.ai_client, 'provider', 'unknown')}")
        self.logger.info(f"📋 AI模型: {getattr(self.ai_client, 'model', 'unknown')}")
        
    def analyze_code_changes(self, commit_hash=None, base_commit=None):
        """分析代码变更的智能影响"""
        try:
            self.logger.info("🚀 开始智能影响分析")
            self.logger.info(f"📍 提交哈希: {commit_hash}, 基准提交: {base_commit}")
            
            # 1. 构建代码索引
            self.logger.info("📊 构建代码索引...")
            index_stats = self.indexer.build_index(self.project_path)
            self.symbol_index = self.indexer.symbol_index.copy()
            self.logger.info(f"✅ 索引构建完成 - 符号数: {index_stats.get('symbol_count', 0)}, 模块数: {index_stats.get('module_count', 0)}")
            
            # 2. 获取代码变更
            self.logger.info("🔍 分析代码变更...")
            code_changes = self._analyze_git_changes(commit_hash, base_commit)
            self.logger.info(f"📝 变更分析完成 - 总文件数: {code_changes.get('total_files', 0)}, 已分析: {code_changes.get('analyzed_files', 0)}")
            
            # 3. 构建依赖关系图
            self.logger.info("🔗 构建依赖关系...")
            self._build_dependency_graph()
            self.logger.info(f"🌐 依赖图构建完成 - 依赖关系数: {len(self.dependency_graph)}")
            
            # 4. 分析变更影响
            self.logger.info("⚡ 分析变更影响...")
            change_impacts = self._analyze_change_impacts(code_changes)
            self.logger.info(f"📈 影响分析完成 - 影响项数: {len(change_impacts)}")
            
            # 5. 计算影响范围
            self.logger.info("📏 计算影响范围...")
            impact_scope = self._calculate_impact_scope(change_impacts)
            self.logger.info(f"🎯 影响范围计算完成 - 受影响模块: {len(impact_scope.affected_modules)}")
            
            # 6. 生成功能用例建议（不包含测试代码）
            self.logger.info("💡 生成功能用例建议...")
            functional_recommendations = self._generate_functional_recommendations(change_impacts, impact_scope)
            self.logger.info(f"📋 功能用例生成完成 - 建议数: {len(functional_recommendations.get('functional_cases', []))}")
            
            # 7. 风险评估
            self.logger.info("⚠️ 进行风险评估...")
            risk_assessment = self._assess_risks(change_impacts, impact_scope)
            self.logger.info(f"🛡️ 风险评估完成 - 风险级别: {risk_assessment.get('risk_level', 'unknown')}")
            
            result = {
                "analysis_timestamp": time.time(),
                "commit_hash": commit_hash,
                "base_commit": base_commit,
                "index_stats": index_stats,
                "code_changes": code_changes,
                "change_impacts": [impact.__dict__ for impact in change_impacts],
                "impact_scope": impact_scope.__dict__,
                "functional_recommendations": functional_recommendations,
                "risk_assessment": risk_assessment,
                "summary": self._generate_summary(change_impacts, impact_scope, functional_recommendations)
            }
            
            self.logger.info("🎉 智能影响分析完成")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 智能影响分析失败: {e}", exc_info=True)
            return self._generate_fallback_result()
    
    async def _analyze_with_ai_model(self, change_info):
        """使用AI模型分析代码变更"""
        self.logger.info(f"🤖 调用AI模型分析代码变更: {change_info.get('file_path', 'unknown')}")
        
        try:
            # 构建AI分析提示
            old_code = change_info.get('old_code', '')
            new_code = change_info.get('new_code', '')
            
            self.logger.info(f"📤 发送AI分析请求 - 旧代码长度: {len(old_code)}, 新代码长度: {len(new_code)}")
            
            # 调用AI客户端
            ai_result = await self.ai_client.analyze_code_change(old_code, new_code)
            
            if ai_result:
                self.logger.info(f"✅ AI分析成功 - 变更类型: {ai_result.get('change_type', 'unknown')}")
                self.logger.info(f"🔍 AI置信度: {ai_result.get('confidence_score', 0)}%")
                return ai_result
            else:
                self.logger.warning("⚠️ AI分析返回空结果")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ AI模型分析失败: {e}")
            return None

    def _analyze_git_changes(self, commit_hash=None, base_commit=None):
        """分析Git变更"""
        try:
            # 获取变更的文件列表
            changed_files = self.git_utils.get_changed_files(commit_hash, base_commit)
            
            changes = []
            for file_path in changed_files[:15]:  # 限制分析的文件数量
                try:
                    # 获取文件的diff内容
                    diff_content = self.git_utils.get_file_diff(file_path, commit_hash, base_commit)
                    
                    # 分析文件中的符号变更
                    symbol_changes = self._analyze_file_symbol_changes(file_path, diff_content)
                    
                    change_info = {
                        "file_path": file_path,
                        "diff_content": diff_content[:1500] if diff_content else "",
                        "lines_added": diff_content.count('\n+') if diff_content else 0,
                        "lines_removed": diff_content.count('\n-') if diff_content else 0,
                        "symbol_changes": symbol_changes,
                        "change_magnitude": self._assess_change_magnitude(diff_content)
                    }
                    changes.append(change_info)
                    
                except Exception as e:
                    self.logger.warning(f"分析文件{file_path}失败: {e}")
            
            return {
                "total_files": len(changed_files),
                "analyzed_files": len(changes),
                "changes": changes
            }
            
        except Exception as e:
            self.logger.warning(f"Git变更分析失败: {e}")
            return {"total_files": 0, "analyzed_files": 0, "changes": []}
    
    def _analyze_file_symbol_changes(self, file_path, diff_content):
        """分析文件中的符号变更"""
        symbol_changes = []
        
        # 获取该文件中的所有符号
        file_symbols = []
        for symbol_id, symbol_info in self.symbol_index.items():
            if file_path in symbol_info.get("file_path", "") or symbol_info.get("file_path", "").endswith(file_path):
                file_symbols.append(symbol_info["symbol"])
        
        # 分析每个符号的可能变更
        for symbol in file_symbols:
            change_type = self._detect_symbol_change_type(symbol, diff_content)
            if change_type != "unchanged":
                symbol_changes.append({
                    "symbol_name": symbol.name,
                    "symbol_type": symbol.symbol_type,
                    "change_type": change_type,
                    "complexity": getattr(symbol, 'complexity', 1),
                    "signature": getattr(symbol, 'signature', ''),
                    "line_number": getattr(symbol, 'start_line', 0)
                })
        
        return symbol_changes
    
    def _detect_symbol_change_type(self, symbol, diff_content):
        """检测符号的变更类型"""
        if not diff_content:
            return "unchanged"
        
        symbol_name = symbol.name
        
        # 检查是否有与符号相关的变更
        if f"def {symbol_name}" in diff_content or f"class {symbol_name}" in diff_content:
            if f"+def {symbol_name}" in diff_content or f"+class {symbol_name}" in diff_content:
                return "addition"
            elif f"-def {symbol_name}" in diff_content or f"-class {symbol_name}" in diff_content:
                return "deletion"
            else:
                return "modification"
        elif symbol_name in diff_content:
            return "reference_change"
        else:
            return "unchanged"
    
    def _assess_change_magnitude(self, diff_content):
        """评估变更幅度"""
        if not diff_content:
            return "none"
        
        lines_changed = diff_content.count('\n+') + diff_content.count('\n-')
        
        if lines_changed > 100:
            return "major"
        elif lines_changed > 20:
            return "significant"
        elif lines_changed > 5:
            return "moderate"
        else:
            return "minor"
    
    def _build_dependency_graph(self):
        """构建符号依赖关系图"""
        self.dependency_graph = {}
        
        for symbol_id, symbol_info in self.symbol_index.items():
            symbol = symbol_info["symbol"]
            dependencies = []
            
            # 简化的依赖分析：基于符号内容和导入
            symbol_content = getattr(symbol, 'content', '') or getattr(symbol, 'signature', '')
            
            # 查找对其他符号的引用
            for other_id, other_info in self.symbol_index.items():
                if other_id != symbol_id:
                    other_symbol = other_info["symbol"]
                    if other_symbol.name in symbol_content:
                        dependencies.append(other_symbol.name)
            
            self.dependency_graph[symbol.name] = dependencies[:10]  # 限制依赖数量
    
    def _analyze_change_impacts(self, code_changes):
        """分析变更影响"""
        impacts = []
        
        for change in code_changes.get("changes", []):
            file_path = change["file_path"]
            symbol_changes = change["symbol_changes"]
            
            for symbol_change in symbol_changes:
                impact = self._analyze_single_symbol_impact(symbol_change, file_path, change)
                impacts.append(impact)
        
        return impacts
    
    def _analyze_single_symbol_impact(self, symbol_change, file_path, file_change):
        """分析单个符号变更的影响"""
        symbol_name = symbol_change["symbol_name"]
        change_type = symbol_change["change_type"]
        
        # 计算影响级别
        impact_level = self._calculate_impact_level(symbol_change, file_change)
        
        # 识别受影响的区域
        affected_areas = self._identify_affected_areas(symbol_name, file_path, change_type)
        
        # 识别风险因素
        risk_factors = self._identify_risk_factors(symbol_change, file_change)
        
        # 分析依赖链
        dependency_chain = self._trace_dependency_chain(symbol_name)
        
        # 评估业务影响
        business_impact = self._assess_business_impact(affected_areas, impact_level)
        
        # 计算测试优先级
        test_priority = self._calculate_test_priority(impact_level, risk_factors, dependency_chain)
        
        return ChangeImpact(
            symbol_name=symbol_name,
            file_path=file_path,
            change_type=change_type,
            impact_level=impact_level,
            affected_areas=affected_areas,
            risk_factors=risk_factors,
            dependency_chain=dependency_chain,
            business_impact=business_impact,
            test_priority=test_priority
        )
    
    def _calculate_impact_level(self, symbol_change, file_change):
        """计算影响级别"""
        base_score = 1
        
        # 根据变更类型
        if symbol_change["change_type"] == "deletion":
            base_score += 3
        elif symbol_change["change_type"] == "addition":
            base_score += 2
        elif symbol_change["change_type"] == "modification":
            base_score += 2
        
        # 根据符号复杂度
        complexity = symbol_change.get("complexity", 1)
        if complexity > 5:
            base_score += 2
        elif complexity > 3:
            base_score += 1
        
        # 根据文件变更幅度
        magnitude = file_change.get("change_magnitude", "minor")
        if magnitude == "major":
            base_score += 2
        elif magnitude == "significant":
            base_score += 1
        
        # 根据符号类型
        if symbol_change["symbol_type"] == "class":
            base_score += 1
        
        # 转换为级别
        if base_score >= 6:
            return "high"
        elif base_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _identify_affected_areas(self, symbol_name, file_path, change_type):
        """识别受影响的区域"""
        areas = set()
        
        # 基于文件路径
        path_lower = file_path.lower()
        if "api" in path_lower or "route" in path_lower:
            areas.update(["API接口层", "外部服务集成", "请求响应处理"])
        if "model" in path_lower or "database" in path_lower:
            areas.update(["数据模型层", "数据持久化", "数据一致性"])
        if "service" in path_lower or "business" in path_lower:
            areas.update(["业务逻辑层", "业务流程", "业务规则"])
        if "component" in path_lower or "view" in path_lower:
            areas.update(["用户界面层", "用户体验", "界面交互"])
        if "util" in path_lower or "helper" in path_lower:
            areas.update(["工具函数层", "通用功能", "辅助服务"])
        
        # 基于符号名称
        name_lower = symbol_name.lower()
        if "auth" in name_lower or "login" in name_lower:
            areas.update(["用户认证", "安全验证", "权限控制"])
        if "validate" in name_lower or "check" in name_lower:
            areas.update(["数据验证", "业务规则验证", "输入检查"])
        if "process" in name_lower or "handle" in name_lower:
            areas.update(["数据处理", "事件处理", "流程控制"])
        if "config" in name_lower or "setting" in name_lower:
            areas.update(["系统配置", "环境设置", "参数管理"])
        
        return list(areas) if areas else ["核心功能模块"]
    
    def _identify_risk_factors(self, symbol_change, file_change):
        """识别风险因素"""
        risks = []
        
        change_type = symbol_change["change_type"]
        if change_type == "deletion":
            risks.append("功能缺失风险")
        if change_type == "addition":
            risks.append("新功能集成风险")
        
        complexity = symbol_change.get("complexity", 1)
        if complexity > 5:
            risks.append("高复杂度风险")
        
        magnitude = file_change.get("change_magnitude", "minor")
        if magnitude in ["major", "significant"]:
            risks.append("大范围变更风险")
        
        symbol_type = symbol_change["symbol_type"]
        if symbol_type == "class":
            risks.append("对象状态风险")
        
        return risks if risks else ["一般功能风险"]
    
    def _trace_dependency_chain(self, symbol_name):
        """追踪依赖链"""
        chain = []
        visited = set()
        
        def trace_recursive(name, depth=0):
            if depth > 3 or name in visited:  # 限制深度和避免循环
                return
            visited.add(name)
            
            dependencies = self.dependency_graph.get(name, [])
            for dep in dependencies[:5]:  # 限制每层的依赖数量
                chain.append(dep)
                trace_recursive(dep, depth + 1)
        
        trace_recursive(symbol_name)
        return list(set(chain))[:10]  # 去重并限制总数
    
    def _assess_business_impact(self, affected_areas, impact_level):
        """评估业务影响"""
        critical_areas = ["API接口层", "用户认证", "数据持久化", "业务逻辑层"]
        
        has_critical_impact = any(area in critical_areas for area in affected_areas)
        
        if impact_level == "high" and has_critical_impact:
            return "严重业务影响"
        elif impact_level == "high" or has_critical_impact:
            return "重要业务影响"
        elif impact_level == "medium":
            return "中等业务影响"
        else:
            return "轻微业务影响"
    
    def _calculate_test_priority(self, impact_level, risk_factors, dependency_chain):
        """计算测试优先级"""
        priority = 1
        
        if impact_level == "high":
            priority += 3
        elif impact_level == "medium":
            priority += 2
        
        priority += len(risk_factors)
        priority += min(len(dependency_chain) // 2, 2)
        
        return min(priority, 10)  # 最高优先级为10
    
    def _calculate_impact_scope(self, change_impacts):
        """计算影响范围"""
        affected_modules = set()
        affected_business_domains = {}
        integration_points = []
        external_dependencies = []
        user_facing_changes = []
        
        for impact in change_impacts:
            # 收集受影响的模块
            module = os.path.dirname(impact.file_path)
            affected_modules.add(module)
            
            # 按业务域分类
            for area in impact.affected_areas:
                domain = self._classify_business_domain(area)
                if domain not in affected_business_domains:
                    affected_business_domains[domain] = []
                affected_business_domains[domain].append(area)
            
            # 识别集成点
            if "API接口层" in impact.affected_areas:
                integration_points.append(f"{impact.symbol_name} API集成点")
            
            # 识别外部依赖
            if len(impact.dependency_chain) > 5:
                external_dependencies.append(f"{impact.symbol_name} 依赖链")
            
            # 识别用户可见变更
            if "用户界面层" in impact.affected_areas or "用户体验" in impact.affected_areas:
                user_facing_changes.append(f"{impact.symbol_name} 用户界面变更")
        
        return ImpactScope(
            affected_modules=list(affected_modules),
            affected_business_domains=affected_business_domains,
            integration_points=integration_points,
            external_dependencies=external_dependencies,
            user_facing_changes=user_facing_changes
        )
    
    def _classify_business_domain(self, area):
        """分类业务域"""
        domain_mapping = {
            "API接口层": "接口服务",
            "数据模型层": "数据服务",
            "业务逻辑层": "业务服务",
            "用户界面层": "前端服务",
            "用户认证": "安全服务",
            "系统配置": "基础服务"
        }
        
        for key, domain in domain_mapping.items():
            if key in area:
                return domain
        return "通用服务"
    
    def _generate_functional_recommendations(self, change_impacts, impact_scope):
        """生成功能用例建议"""
        functional_cases = []
        
        # 按影响级别排序
        sorted_impacts = sorted(change_impacts, key=lambda x: x.test_priority, reverse=True)
        
        for impact in sorted_impacts[:10]:  # 限制功能用例数量
            case = {
                "name": f"变更影响功能用例 - {impact.symbol_name}",
                "description": f"验证{impact.symbol_name}的{impact.change_type}对{impact.business_impact}的影响",
                "change_analysis": {
                    "changed_symbol": impact.symbol_name,
                    "change_type": impact.change_type,
                    "impact_level": impact.impact_level,
                    "business_impact": impact.business_impact
                },
                "impact_scope": {
                    "affected_areas": impact.affected_areas,
                    "dependency_chain": impact.dependency_chain[:5],
                    "risk_factors": impact.risk_factors
                },
                "test_scenarios": self._generate_functional_test_scenarios(impact),
                "test_data_requirements": self._generate_functional_test_data(impact),
                "expected_outcomes": self._generate_functional_expected_outcomes(impact),
                "priority": impact.impact_level,
                "estimated_time": self._estimate_functional_test_time(impact),
                "test_strategy": self._determine_functional_test_strategy(impact)
            }
            functional_cases.append(case)
        
        return {
            "functional_cases": functional_cases,
            "total_estimated_time": sum(case.get("estimated_time", 15) for case in functional_cases),
            "test_coverage_analysis": self._analyze_test_coverage(functional_cases, impact_scope),
            "testing_strategy": "基于代码变更影响的智能功能用例策略"
        }
    
    def _generate_functional_test_scenarios(self, impact):
        """生成功能用例场景"""
        scenarios = []
        
        # 基于变更类型生成场景
        if impact.change_type == "addition":
            scenarios.extend([
                f"验证新增的{impact.symbol_name}功能按预期工作",
                f"测试{impact.symbol_name}与现有系统的集成",
                f"确认{impact.symbol_name}不会影响现有功能"
            ])
        elif impact.change_type == "deletion":
            scenarios.extend([
                f"确认{impact.symbol_name}的移除不破坏依赖功能",
                f"验证替代方案或错误处理机制",
                f"测试相关业务流程的完整性"
            ])
        elif impact.change_type == "modification":
            scenarios.extend([
                f"验证修改后的{impact.symbol_name}保持预期行为",
                f"测试变更对依赖模块的影响",
                f"确认性能和稳定性没有退化"
            ])
        
        # 基于受影响区域生成场景
        for area in impact.affected_areas:
            if "API接口" in area:
                scenarios.append(f"测试{area}的请求响应正确性")
            elif "数据" in area:
                scenarios.append(f"验证{area}的数据完整性和一致性")
            elif "业务" in area:
                scenarios.append(f"测试{area}的业务逻辑正确性")
            elif "用户" in area:
                scenarios.append(f"验证{area}的用户体验和交互")
        
        return scenarios[:6]  # 限制场景数量
    
    def _generate_functional_test_data(self, impact):
        """生成功能用例数据需求"""
        data_requirements = []
        
        # 基于受影响区域确定数据需求
        for area in impact.affected_areas:
            if "API接口" in area:
                data_requirements.extend(["API请求测试数据", "各种HTTP状态码场景", "边界值请求数据"])
            elif "数据模型" in area or "数据持久化" in area:
                data_requirements.extend(["数据库测试数据集", "数据完整性测试数据", "并发访问测试数据"])
            elif "业务逻辑" in area:
                data_requirements.extend(["业务场景测试数据", "业务规则验证数据", "异常业务流程数据"])
            elif "用户界面" in area:
                data_requirements.extend(["UI交互测试数据", "用户行为模拟数据", "跨浏览器测试环境"])
            elif "用户认证" in area:
                data_requirements.extend(["用户权限测试数据", "安全测试数据", "认证失败场景数据"])
        
        # 基于风险因素添加特殊数据需求
        for risk in impact.risk_factors:
            if "复杂度" in risk:
                data_requirements.append("复杂场景测试数据")
            if "集成" in risk:
                data_requirements.append("系统集成测试数据")
            if "性能" in risk:
                data_requirements.append("性能压力测试数据")
        
        return list(set(data_requirements))[:8]  # 去重并限制数量
    
    def _generate_functional_expected_outcomes(self, impact):
        """生成功能用例预期结果"""
        outcomes = []
        
        # 基于业务影响生成预期结果
        if "严重" in impact.business_impact:
            outcomes.extend([
                f"{impact.symbol_name}的变更不应影响关键业务流程",
                "系统应保持高可用性和稳定性",
                "关键功能应通过所有测试场景"
            ])
        elif "重要" in impact.business_impact:
            outcomes.extend([
                f"{impact.symbol_name}应按预期功能正常工作",
                "相关业务功能应保持正常运行",
                "系统性能应在可接受范围内"
            ])
        else:
            outcomes.extend([
                f"{impact.symbol_name}应实现预期的功能变更",
                "不应对其他功能产生负面影响"
            ])
        
        # 基于受影响区域生成具体预期
        for area in impact.affected_areas:
            if "API" in area:
                outcomes.append(f"{area}应返回正确的响应格式和状态码")
            elif "数据" in area:
                outcomes.append(f"{area}应保持数据的准确性和完整性")
            elif "用户" in area:
                outcomes.append(f"{area}应提供良好的用户体验")
        
        return outcomes[:5]  # 限制数量
    
    def _estimate_functional_test_time(self, impact):
        """估算功能用例测试时间"""
        base_time = 10
        
        # 根据影响级别调整
        if impact.impact_level == "high":
            base_time += 20
        elif impact.impact_level == "medium":
            base_time += 10
        
        # 根据受影响区域数量调整
        base_time += len(impact.affected_areas) * 5
        
        # 根据依赖链长度调整
        base_time += min(len(impact.dependency_chain) * 2, 15)
        
        # 根据风险因素调整
        base_time += len(impact.risk_factors) * 3
        
        # 根据测试优先级调整
        base_time += impact.test_priority * 2
        
        return min(base_time, 60)  # 最大60分钟
    
    def _determine_functional_test_strategy(self, impact):
        """确定功能用例测试策略"""
        if impact.impact_level == "high":
            return "全面回归测试 + 专项功能测试"
        elif impact.impact_level == "medium":
            return "重点功能测试 + 集成测试"
        else:
            return "基础功能验证测试"
    
    def _analyze_test_coverage(self, functional_cases, impact_scope):
        """分析测试覆盖率"""
        covered_areas = set()
        covered_domains = set()
        
        for case in functional_cases:
            covered_areas.update(case.get("impact_scope", {}).get("affected_areas", []))
            
        for domain in impact_scope.affected_business_domains:
            if any(area in covered_areas for area in impact_scope.affected_business_domains[domain]):
                covered_domains.add(domain)
        
        return {
            "covered_business_domains": list(covered_domains),
            "total_business_domains": len(impact_scope.affected_business_domains),
            "coverage_percentage": len(covered_domains) / max(len(impact_scope.affected_business_domains), 1) * 100,
            "uncovered_areas": list(set(impact_scope.affected_business_domains.keys()) - covered_domains)
        }
    
    def _assess_risks(self, change_impacts, impact_scope):
        """评估风险"""
        high_risk_count = sum(1 for impact in change_impacts if impact.impact_level == "high")
        medium_risk_count = sum(1 for impact in change_impacts if impact.impact_level == "medium")
        total_impacts = len(change_impacts)
        
        risk_score = (high_risk_count * 3 + medium_risk_count * 2) / max(total_impacts, 1)
        
        if risk_score >= 2.5:
            risk_level = "high"
            recommendations = [
                "建议进行全面的回归测试",
                "考虑分阶段发布以降低风险",
                "加强生产环境监控",
                "准备快速回滚方案"
            ]
        elif risk_score >= 1.5:
            risk_level = "medium"
            recommendations = [
                "进行重点功能测试",
                "关注关键业务流程",
                "进行性能基准测试"
            ]
        else:
            risk_level = "low"
            recommendations = [
                "进行基础功能验证",
                "执行标准回归测试"
            ]
        
        return {
            "overall_risk_score": risk_score,
            "risk_level": risk_level,
            "high_risk_changes": high_risk_count,
            "medium_risk_changes": medium_risk_count,
            "low_risk_changes": total_impacts - high_risk_count - medium_risk_count,
            "total_changes": total_impacts,
            "risk_distribution": {
                "high": high_risk_count,
                "medium": medium_risk_count,
                "low": total_impacts - high_risk_count - medium_risk_count
            },
            "recommended_actions": recommendations,
            "critical_areas": self._identify_critical_areas(change_impacts, impact_scope)
        }
    
    def _identify_critical_areas(self, change_impacts, impact_scope):
        """识别关键区域"""
        critical_areas = []
        
        # 识别高风险变更的区域
        for impact in change_impacts:
            if impact.impact_level == "high":
                critical_areas.extend(impact.affected_areas)
        
        # 识别用户可见的变更
        critical_areas.extend(impact_scope.user_facing_changes)
        
        # 识别集成点
        critical_areas.extend(impact_scope.integration_points)
        
        return list(set(critical_areas))[:10]  # 去重并限制数量
    
    def _generate_summary(self, change_impacts, impact_scope, functional_recommendations):
        """生成分析摘要"""
        high_impact_changes = [i for i in change_impacts if i.impact_level == "high"]
        medium_impact_changes = [i for i in change_impacts if i.impact_level == "medium"]
        
        return {
            "total_changes_analyzed": len(change_impacts),
            "high_impact_changes": len(high_impact_changes),
            "medium_impact_changes": len(medium_impact_changes),
            "affected_business_domains": len(impact_scope.affected_business_domains),
            "generated_functional_cases": len(functional_recommendations.get("functional_cases", [])),
            "estimated_test_time": functional_recommendations.get("total_estimated_time", 0),
            "key_findings": [
                f"分析了{len(change_impacts)}个代码变更的智能影响",
                f"识别了{len(high_impact_changes)}个高影响变更",
                f"涉及{len(impact_scope.affected_business_domains)}个业务域",
                f"生成了{len(functional_recommendations.get('functional_cases', []))}个智能功能用例"
            ],
            "recommendations": [
                "优先测试高影响级别的变更",
                "关注跨模块的集成影响",
                "验证业务流程的完整性",
                "确保用户体验不受负面影响"
            ],
            "analysis_method": "基于代码索引、依赖分析和AI智能影响评估"
        }
    
    def _generate_fallback_result(self):
        """生成回退结果"""
        return {
            "analysis_timestamp": time.time(),
            "error": "智能影响分析失败，使用基础分析",
            "functional_recommendations": {
                "functional_cases": [
                    {
                        "name": "基础功能回归测试",
                        "description": "验证系统基础功能的正常运行",
                        "change_analysis": {
                            "changed_symbol": "unknown",
                            "change_type": "unknown",
                            "impact_level": "medium",
                            "business_impact": "需要手动评估"
                        },
                        "test_scenarios": ["测试核心功能", "验证基础业务流程"],
                        "test_data_requirements": ["基础测试数据"],
                        "expected_outcomes": ["系统功能正常运行"],
                        "priority": "high",
                        "estimated_time": 30
                    }
                ],
                "total_estimated_time": 30
            },
            "summary": {
                "analysis_method": "回退分析模式",
                "recommendations": ["建议手动分析代码变更影响"]
            }
        } 