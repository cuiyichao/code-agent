import os
import logging
from typing import Dict, List
from dataclasses import dataclass
import time
import json

from backend.indexers.codebase_indexer import CodebaseIndexer
from backend.models.code_symbol import CodeSymbol
from backend.utils.git_utils import GitUtils
from backend.generators.test_code_generator import IntelligentTestGenerator

@dataclass
class FunctionImpact:
    function_name: str
    module_path: str
    impact_level: str
    affected_functions: List[str]
    test_priority: int
    estimated_test_time: int
    change_type: str
    complexity_score: float
    risk_factors: List[str]

@dataclass  
class ModuleImpact:
    module_path: str
    impact_level: str
    affected_modules: List[str]
    function_impacts: List[Dict]
    integration_risk: float
    test_coverage_needed: float

class IndexBasedAnalyzer:
    def __init__(self, project_path: str, git_utils=None):
        self.logger = logging.getLogger(__name__)
        self.project_path = project_path
        self.git_utils = git_utils or GitUtils()
        self.indexer = CodebaseIndexer(index_dir=os.path.join(project_path, ".code_index"))
        self.test_generator = IntelligentTestGenerator()
        self.current_index = {}
        
    def analyze_comprehensive_diff(self, commit_hash=None, base_commit=None):
        """基于真实代码变更进行智能影响分析"""
        try:
            # 1. 构建当前代码索引
            current_stats = self.indexer.build_index(self.project_path)
            self.current_index = self.indexer.symbol_index.copy()
            
            # 2. 获取Git变更信息
            git_changes = self._get_git_changes(commit_hash, base_commit)
            
            # 3. 分析代码变更的影响范围
            impact_analysis = self._analyze_change_impacts(git_changes)
            
            # 4. 生成基于影响分析的功能测试
            test_recommendations = self._generate_impact_based_tests(impact_analysis)
            
            # 5. 评估风险和影响范围
            risk_assessment = self._assess_change_risks(impact_analysis)
            impact_scope = self._calculate_impact_scope(impact_analysis)
            
            return {
                "analysis_timestamp": time.time(),
                "commit_hash": commit_hash,
                "base_commit": base_commit,
                "index_stats": current_stats,
                "git_changes": git_changes,
                "change_impact_analysis": impact_analysis,
                "test_recommendations": test_recommendations,
                "risk_assessment": risk_assessment,
                "impact_scope": impact_scope,
                "summary": self._generate_analysis_summary(impact_analysis, test_recommendations)
            }
            
        except Exception as e:
            self.logger.error(f"智能影响分析失败: {str(e)}")
            return self._generate_fallback_analysis()
    
    def _get_git_changes(self, commit_hash=None, base_commit=None):
        """获取Git变更信息"""
        try:
            if not self.git_utils:
                return {"changes": [], "diff_summary": "无Git变更信息"}
            
            # 获取文件变更列表
            changed_files = self.git_utils.get_changed_files(commit_hash, base_commit)
            
            # 获取详细的diff信息
            changes = []
            for file_path in changed_files[:10]:  # 限制分析文件数量
                try:
                    diff_content = self.git_utils.get_file_diff(file_path, commit_hash, base_commit)
                    file_symbols = self._get_file_symbols(file_path)
                    
                    change_info = {
                        "file_path": file_path,
                        "change_type": self._determine_change_type(diff_content),
                        "diff_content": diff_content[:2000],  # 限制diff长度
                        "affected_symbols": file_symbols,
                        "lines_added": diff_content.count('+') if diff_content else 0,
                        "lines_removed": diff_content.count('-') if diff_content else 0
                    }
                    changes.append(change_info)
                except Exception as e:
                    self.logger.warning(f"获取文件{file_path}的变更信息失败: {e}")
            
            return {
                "total_files_changed": len(changed_files),
                "analyzed_files": len(changes),
                "changes": changes,
                "diff_summary": f"共{len(changed_files)}个文件发生变更"
            }
        except Exception as e:
            self.logger.warning(f"获取Git变更失败: {e}")
            return {"changes": [], "diff_summary": "无法获取Git变更信息"}
    
    def _get_file_symbols(self, file_path):
        """获取文件中的符号信息"""
        symbols = []
        for symbol_id, symbol_info in self.current_index.items():
            if symbol_info.get("file_path", "").endswith(file_path) or file_path in symbol_info.get("file_path", ""):
                symbol = symbol_info["symbol"]
                symbols.append({
                    "name": symbol.name,
                    "type": symbol.symbol_type,
                    "signature": getattr(symbol, 'signature', ''),
                    "complexity": getattr(symbol, 'complexity', 1)
                })
        return symbols
    
    def _determine_change_type(self, diff_content):
        """确定变更类型"""
        if not diff_content:
            return "unknown"
        
        added_lines = diff_content.count('\n+')
        removed_lines = diff_content.count('\n-')
        
        if added_lines > removed_lines * 2:
            return "major_addition"
        elif removed_lines > added_lines * 2:
            return "major_deletion"
        elif added_lines > 10 or removed_lines > 10:
            return "significant_modification"
        else:
            return "minor_modification"
    
    def _analyze_change_impacts(self, git_changes):
        """分析代码变更的影响范围"""
        impacts = []
        
        for change in git_changes.get("changes", []):
            file_path = change["file_path"]
            change_type = change["change_type"]
            affected_symbols = change["affected_symbols"]
            
            # 分析每个受影响的符号
            for symbol in affected_symbols:
                impact = self._analyze_symbol_impact(symbol, change_type, file_path)
                impacts.append(impact)
        
        # 分析符号间的依赖关系影响
        dependency_impacts = self._analyze_dependency_impacts(impacts)
        impacts.extend(dependency_impacts)
        
        return {
            "direct_impacts": impacts,
            "dependency_impacts": dependency_impacts,
            "total_affected_symbols": len(impacts),
            "impact_levels": self._categorize_impacts(impacts)
        }
    
    def _analyze_symbol_impact(self, symbol, change_type, file_path):
        """分析单个符号的影响"""
        # 基于符号类型和变更类型分析影响
        impact_level = self._calculate_impact_level(symbol, change_type)
        affected_areas = self._identify_affected_areas(symbol, file_path)
        risk_factors = self._identify_risk_factors(symbol, change_type)
        
        return {
            "symbol_name": symbol["name"],
            "symbol_type": symbol["type"],
            "file_path": file_path,
            "change_type": change_type,
            "impact_level": impact_level,
            "affected_areas": affected_areas,
            "risk_factors": risk_factors,
            "complexity_score": symbol.get("complexity", 1),
            "estimated_impact_scope": len(affected_areas)
        }
    
    def _calculate_impact_level(self, symbol, change_type):
        """计算影响级别"""
        base_score = 1
        
        # 根据符号类型调整
        if symbol["type"] == "function":
            if "api" in symbol["name"].lower() or "route" in symbol["name"].lower():
                base_score += 2  # API函数影响更大
            elif "test" in symbol["name"].lower():
                base_score -= 1  # 测试函数影响较小
        elif symbol["type"] == "class":
            base_score += 1  # 类的影响通常较大
        
        # 根据变更类型调整
        if change_type == "major_addition":
            base_score += 1
        elif change_type == "major_deletion":
            base_score += 2
        elif change_type == "significant_modification":
            base_score += 1
        
        # 根据复杂度调整
        complexity = symbol.get("complexity", 1)
        if complexity > 5:
            base_score += 1
        
        # 转换为级别
        if base_score >= 4:
            return "high"
        elif base_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _identify_affected_areas(self, symbol, file_path):
        """识别受影响的区域"""
        areas = []
        
        # 基于文件路径识别
        if "api" in file_path.lower() or "route" in file_path.lower():
            areas.extend(["API接口", "请求处理", "响应格式"])
        if "model" in file_path.lower() or "database" in file_path.lower():
            areas.extend(["数据模型", "数据库操作", "数据完整性"])
        if "service" in file_path.lower() or "business" in file_path.lower():
            areas.extend(["业务逻辑", "业务流程", "业务规则"])
        if "component" in file_path.lower() or "view" in file_path.lower():
            areas.extend(["用户界面", "用户交互", "界面渲染"])
        if "util" in file_path.lower() or "helper" in file_path.lower():
            areas.extend(["工具函数", "辅助功能", "通用逻辑"])
        
        # 基于符号名称识别
        symbol_name = symbol["name"].lower()
        if "auth" in symbol_name or "login" in symbol_name:
            areas.extend(["用户认证", "权限验证", "安全控制"])
        if "validate" in symbol_name or "check" in symbol_name:
            areas.extend(["数据验证", "输入检查", "业务规则验证"])
        if "process" in symbol_name or "handle" in symbol_name:
            areas.extend(["数据处理", "业务处理", "流程控制"])
        
        return list(set(areas)) if areas else ["核心功能"]
    
    def _identify_risk_factors(self, symbol, change_type):
        """识别风险因素"""
        risks = []
        
        if change_type == "major_deletion":
            risks.append("功能缺失风险")
        if change_type == "major_addition":
            risks.append("新功能集成风险")
        if symbol.get("complexity", 1) > 5:
            risks.append("复杂度风险")
        if "critical" in symbol["name"].lower() or "important" in symbol["name"].lower():
            risks.append("关键功能风险")
        if symbol["type"] == "class":
            risks.append("对象状态风险")
        
        return risks if risks else ["一般功能风险"]
    
    def _analyze_dependency_impacts(self, direct_impacts):
        """分析依赖关系影响"""
        dependency_impacts = []
        
        # 简化的依赖分析：基于符号名称匹配
        for impact in direct_impacts:
            symbol_name = impact["symbol_name"]
            
            # 查找可能依赖此符号的其他符号
            for symbol_id, symbol_info in self.current_index.items():
                symbol = symbol_info["symbol"]
                if symbol.name != symbol_name and symbol_name.lower() in symbol.name.lower():
                    dependency_impact = {
                        "symbol_name": symbol.name,
                        "symbol_type": symbol.symbol_type,
                        "file_path": symbol_info.get("file_path", ""),
                        "change_type": "dependency_change",
                        "impact_level": "medium",
                        "affected_areas": ["依赖关系", "功能集成"],
                        "risk_factors": ["依赖变更风险"],
                        "dependency_source": symbol_name
                    }
                    dependency_impacts.append(dependency_impact)
        
        return dependency_impacts[:5]  # 限制依赖影响数量
    
    def _categorize_impacts(self, impacts):
        """分类影响级别"""
        categories = {"high": 0, "medium": 0, "low": 0}
        for impact in impacts:
            level = impact.get("impact_level", "low")
            categories[level] = categories.get(level, 0) + 1
        return categories
    
    def _generate_impact_based_tests(self, impact_analysis):
        """基于影响分析生成功能测试"""
        functional_tests = []
        direct_impacts = impact_analysis.get("direct_impacts", [])
        
        for impact in direct_impacts[:8]:  # 限制测试用例数量
            test_case = {
                "name": f"影响测试 - {impact['symbol_name']}变更影响",
                "description": f"验证{impact['symbol_name']}的{impact['change_type']}对{', '.join(impact['affected_areas'])}的影响",
                "test_scenarios": self._generate_impact_test_scenarios(impact),
                "test_data_requirements": self._generate_impact_test_data(impact),
                "expected_outcomes": self._generate_impact_expected_outcomes(impact),
                "priority": impact["impact_level"],
                "estimated_time": self._estimate_impact_test_time(impact),
                "impact_scope": impact["affected_areas"],
                "risk_factors": impact["risk_factors"],
                "change_type": impact["change_type"]
            }
            functional_tests.append(test_case)
        
        total_time = sum(test.get("estimated_time", 15) for test in functional_tests)
        
        return {
            "functional_tests": functional_tests,
            "total_estimated_time": total_time,
            "test_strategy": "基于代码变更影响的智能测试策略",
            "coverage_areas": list(set(area for test in functional_tests for area in test.get("impact_scope", [])))
        }
    
    def _generate_impact_test_scenarios(self, impact):
        """生成基于影响的测试场景"""
        scenarios = []
        change_type = impact["change_type"]
        affected_areas = impact["affected_areas"]
        
        if change_type == "major_addition":
            scenarios.extend([
                f"验证新增的{impact['symbol_name']}功能是否正常工作",
                f"测试新功能与现有{', '.join(affected_areas)}的集成",
                f"验证新功能不会破坏现有业务流程"
            ])
        elif change_type == "major_deletion":
            scenarios.extend([
                f"确认{impact['symbol_name']}功能的移除不影响核心业务",
                f"验证依赖此功能的{', '.join(affected_areas)}有替代方案",
                f"测试相关错误处理和用户提示"
            ])
        elif change_type == "significant_modification":
            scenarios.extend([
                f"验证修改后的{impact['symbol_name']}保持原有功能",
                f"测试修改对{', '.join(affected_areas)}的影响范围",
                f"确认性能和稳定性没有退化"
            ])
        else:
            scenarios.extend([
                f"验证{impact['symbol_name']}的基本功能完整性",
                f"测试与{', '.join(affected_areas)}的正常交互",
                f"确认变更没有引入新的问题"
            ])
        
        return scenarios
    
    def _generate_impact_test_data(self, impact):
        """生成基于影响的测试数据需求"""
        data_requirements = ["基础功能测试数据"]
        
        affected_areas = impact["affected_areas"]
        if "API接口" in affected_areas:
            data_requirements.extend(["API请求测试数据", "各种HTTP状态码场景"])
        if "数据库操作" in affected_areas:
            data_requirements.extend(["数据库测试数据集", "边界值数据", "异常数据"])
        if "用户界面" in affected_areas:
            data_requirements.extend(["UI交互测试数据", "不同设备和浏览器环境"])
        if "业务逻辑" in affected_areas:
            data_requirements.extend(["业务场景测试数据", "规则验证数据"])
        if "用户认证" in affected_areas:
            data_requirements.extend(["用户权限测试数据", "安全测试数据"])
        
        return list(set(data_requirements))
    
    def _generate_impact_expected_outcomes(self, impact):
        """生成基于影响的预期结果"""
        outcomes = []
        change_type = impact["change_type"]
        affected_areas = impact["affected_areas"]
        
        if change_type == "major_addition":
            outcomes.append(f"新功能{impact['symbol_name']}应该按预期工作")
            outcomes.append(f"不应影响现有{', '.join(affected_areas)}的稳定性")
        elif change_type == "major_deletion":
            outcomes.append(f"系统应该优雅地处理{impact['symbol_name']}功能的缺失")
            outcomes.append(f"相关{', '.join(affected_areas)}应该有适当的错误处理")
        else:
            outcomes.append(f"{impact['symbol_name']}应该保持预期的功能行为")
            outcomes.append(f"所有{', '.join(affected_areas)}应该正常运行")
        
        outcomes.append("系统整体稳定性和性能不应受到负面影响")
        return outcomes
    
    def _estimate_impact_test_time(self, impact):
        """估算影响测试时间"""
        base_time = 10
        
        # 根据影响级别调整
        if impact["impact_level"] == "high":
            base_time += 15
        elif impact["impact_level"] == "medium":
            base_time += 10
        
        # 根据受影响区域数量调整
        base_time += len(impact["affected_areas"]) * 5
        
        # 根据风险因素调整
        base_time += len(impact["risk_factors"]) * 3
        
        return min(base_time, 45)  # 最大45分钟
    
    def _assess_change_risks(self, impact_analysis):
        """评估变更风险"""
        direct_impacts = impact_analysis.get("direct_impacts", [])
        impact_levels = impact_analysis.get("impact_levels", {})
        
        high_risk_count = impact_levels.get("high", 0)
        medium_risk_count = impact_levels.get("medium", 0)
        total_impacts = len(direct_impacts)
        
        # 计算整体风险分数
        risk_score = (high_risk_count * 3 + medium_risk_count * 2) / max(total_impacts, 1)
        
        if risk_score >= 2.5:
            risk_level = "high"
            recommendations = ["建议进行全面测试", "考虑分阶段发布", "加强监控"]
        elif risk_score >= 1.5:
            risk_level = "medium"
            recommendations = ["进行重点功能测试", "关注核心业务流程"]
        else:
            risk_level = "low"
            recommendations = ["进行基础回归测试"]
        
        return {
            "overall_risk_score": risk_score,
            "risk_level": risk_level,
            "high_risk_changes": high_risk_count,
            "medium_risk_changes": medium_risk_count,
            "total_changes": total_impacts,
            "recommended_actions": recommendations,
            "risk_factors_summary": self._summarize_risk_factors(direct_impacts)
        }
    
    def _summarize_risk_factors(self, impacts):
        """汇总风险因素"""
        all_risks = []
        for impact in impacts:
            all_risks.extend(impact.get("risk_factors", []))
        
        risk_counts = {}
        for risk in all_risks:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        return sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def _calculate_impact_scope(self, impact_analysis):
        """计算影响范围"""
        direct_impacts = impact_analysis.get("direct_impacts", [])
        
        affected_files = set()
        affected_areas = set()
        business_domains = {}
        
        for impact in direct_impacts:
            affected_files.add(impact["file_path"])
            affected_areas.update(impact["affected_areas"])
            
            # 按业务域分类
            for area in impact["affected_areas"]:
                domain = self._classify_business_domain(area)
                if domain not in business_domains:
                    business_domains[domain] = {"areas": set(), "risk_level": "low", "impact_count": 0}
                business_domains[domain]["areas"].add(area)
                business_domains[domain]["impact_count"] += 1
                
                # 更新风险级别
                if impact["impact_level"] == "high":
                    business_domains[domain]["risk_level"] = "high"
                elif impact["impact_level"] == "medium" and business_domains[domain]["risk_level"] != "high":
                    business_domains[domain]["risk_level"] = "medium"
        
        return {
            "affected_files_count": len(affected_files),
            "affected_areas_count": len(affected_areas),
            "affected_areas": list(affected_areas),
            "business_domains": {
                domain: {
                    "areas": list(info["areas"]),
                    "risk_level": info["risk_level"],
                    "impact_count": info["impact_count"]
                } for domain, info in business_domains.items()
            },
            "impact_distribution": impact_analysis.get("impact_levels", {}),
            "scope_assessment": self._assess_scope_size(len(affected_files), len(affected_areas))
        }
    
    def _classify_business_domain(self, area):
        """将影响区域分类到业务域"""
        if area in ["API接口", "请求处理", "响应格式"]:
            return "接口服务"
        elif area in ["数据模型", "数据库操作", "数据完整性"]:
            return "数据层"
        elif area in ["业务逻辑", "业务流程", "业务规则"]:
            return "业务层"
        elif area in ["用户界面", "用户交互", "界面渲染"]:
            return "用户界面"
        elif area in ["用户认证", "权限验证", "安全控制"]:
            return "安全模块"
        else:
            return "通用功能"
    
    def _assess_scope_size(self, file_count, area_count):
        """评估影响范围大小"""
        if file_count >= 10 or area_count >= 8:
            return "large"
        elif file_count >= 5 or area_count >= 4:
            return "medium"
        else:
            return "small"
    
    def _generate_analysis_summary(self, impact_analysis, test_recommendations):
        """生成分析摘要"""
        direct_impacts = impact_analysis.get("direct_impacts", [])
        functional_tests = test_recommendations.get("functional_tests", [])
        
        return {
            "total_changes_analyzed": len(direct_impacts),
            "functional_tests_generated": len(functional_tests),
            "estimated_total_test_time": test_recommendations.get("total_estimated_time", 0),
            "key_findings": [
                f"分析了{len(direct_impacts)}个代码变更的影响",
                f"识别了{len(set(area for impact in direct_impacts for area in impact['affected_areas']))}个受影响区域",
                f"生成了{len(functional_tests)}个针对性功能测试用例"
            ],
            "recommendations": [
                "重点关注高风险变更的测试覆盖",
                "验证关键业务流程的完整性",
                "确保变更不会影响系统稳定性"
            ],
            "analysis_method": "基于代码索引和变更影响的智能分析"
        }
    
    def _generate_fallback_analysis(self):
        """生成回退分析结果"""
        return {
            "analysis_timestamp": time.time(),
            "error": "无法进行完整的影响分析",
            "test_recommendations": {
                "functional_tests": [
                    {
                        "name": "基础功能验证测试",
                        "description": "验证系统核心功能的基本运行状态",
                        "test_scenarios": ["测试主要功能模块", "验证基础业务流程"],
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
                "recommendations": ["建议手动检查代码变更影响"]
            }
        } 