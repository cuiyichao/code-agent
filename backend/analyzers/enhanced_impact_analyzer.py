"""
增强版影响分析器
提供更准确、详细的代码变更影响分析和功能测试用例生成
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import networkx as nx

from .intelligent_impact_analyzer import IntelligentImpactAnalyzer
from ..generators.enhanced_test_generator import EnhancedTestGenerator
from ..models.code_symbol import CodeSymbol
from ..models.semantic_change import SemanticChange

logger = logging.getLogger(__name__)

class EnhancedImpactAnalyzer:
    """增强版影响分析器"""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client
        self.base_analyzer = IntelligentImpactAnalyzer(ai_client)
        self.test_generator = EnhancedTestGenerator()
        self.dependency_graph = nx.DiGraph()
        
    def analyze_code_changes_comprehensive(self, 
                                         project_path: str, 
                                         changes: List[Dict],
                                         analysis_config: Dict = None) -> Dict:
        """
        综合分析代码变更影响
        
        Args:
            project_path: 项目路径
            changes: 代码变更列表
            analysis_config: 分析配置
            
        Returns:
            详细的影响分析结果
        """
        logger.info(f"开始综合影响分析，项目路径: {project_path}")
        
        try:
            # 1. 基础影响分析
            base_analysis = self.base_analyzer.analyze_impact(project_path, changes)
            
            # 2. 增强业务域分析
            business_analysis = self._analyze_business_domains(changes, project_path)
            
            # 3. 生成详细的功能测试用例
            functional_tests = self._generate_comprehensive_functional_tests(
                base_analysis, business_analysis
            )
            
            # 4. 风险评估和缓解建议
            risk_assessment = self._comprehensive_risk_assessment(
                base_analysis, business_analysis
            )
            
            # 5. 测试策略建议
            test_strategy = self._generate_test_strategy(
                functional_tests, risk_assessment
            )
            
            # 6. 生成最终报告
            comprehensive_result = {
                "analysis_metadata": {
                    "analysis_time": datetime.now().isoformat(),
                    "project_path": project_path,
                    "changes_count": len(changes),
                    "analyzer_version": "enhanced_v2.0"
                },
                
                "impact_summary": {
                    "total_changes": len(changes),
                    "high_risk_changes": len([c for c in changes if self._assess_change_risk(c) == "high"]),
                    "medium_risk_changes": len([c for c in changes if self._assess_change_risk(c) == "medium"]),
                    "low_risk_changes": len([c for c in changes if self._assess_change_risk(c) == "low"]),
                    "affected_business_domains": len(business_analysis.get("domains", {})),
                    "recommended_test_cases": len(functional_tests.get("test_cases", []))
                },
                
                "business_domain_analysis": business_analysis,
                "functional_test_recommendations": functional_tests,
                "risk_assessment": risk_assessment,
                "test_strategy": test_strategy,
                "detailed_changes": self._format_detailed_changes(changes, base_analysis),
                
                # 原始分析结果（向后兼容）
                "base_analysis": base_analysis
            }
            
            logger.info("综合影响分析完成")
            return comprehensive_result
            
        except Exception as e:
            logger.error(f"综合影响分析失败: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}",
                "analysis_metadata": {
                    "analysis_time": datetime.now().isoformat(),
                    "project_path": project_path,
                    "analyzer_version": "enhanced_v2.0"
                }
            }
    
    def _analyze_business_domains(self, changes: List[Dict], project_path: str) -> Dict:
        """分析业务域影响"""
        domains = {}
        domain_patterns = {
            "用户管理": ["user", "auth", "login", "account", "permission", "role"],
            "项目管理": ["project", "repo", "git", "repository", "workspace"],
            "代码分析": ["analyzer", "parser", "analysis", "code", "ast", "symbol"],
            "API服务": ["api", "route", "endpoint", "service", "controller"],
            "数据管理": ["database", "model", "data", "storage", "db", "sql"],
            "用户界面": ["ui", "view", "component", "frontend", "template", "page"],
            "文件系统": ["file", "path", "directory", "folder", "io"],
            "网络通信": ["http", "websocket", "client", "request", "response"],
            "安全模块": ["security", "encrypt", "decrypt", "hash", "token"],
            "配置管理": ["config", "setting", "environment", "env"]
        }
        
        for change in changes:
            file_path = change.get("file_path", "").lower()
            change_content = str(change).lower()
            
            # 识别变更所属的业务域
            identified_domains = []
            for domain, patterns in domain_patterns.items():
                if any(pattern in file_path or pattern in change_content for pattern in patterns):
                    identified_domains.append(domain)
            
            # 如果没有匹配到特定域，归类为核心服务
            if not identified_domains:
                identified_domains = ["核心服务"]
            
            # 将变更分配到相应的业务域
            for domain in identified_domains:
                if domain not in domains:
                    domains[domain] = {
                        "changes": [],
                        "risk_level": "low",
                        "impact_score": 0,
                        "test_priority": "medium"
                    }
                
                domains[domain]["changes"].append(change)
                
                # 更新域的风险级别和影响分数
                change_risk = self._assess_change_risk(change)
                if change_risk == "high":
                    domains[domain]["impact_score"] += 3
                    domains[domain]["risk_level"] = "high"
                elif change_risk == "medium":
                    domains[domain]["impact_score"] += 2
                    if domains[domain]["risk_level"] != "high":
                        domains[domain]["risk_level"] = "medium"
                else:
                    domains[domain]["impact_score"] += 1
        
        # 确定测试优先级
        for domain, info in domains.items():
            if info["impact_score"] >= 6:
                info["test_priority"] = "high"
            elif info["impact_score"] >= 3:
                info["test_priority"] = "medium"
            else:
                info["test_priority"] = "low"
        
        return {
            "domains": domains,
            "domain_count": len(domains),
            "high_priority_domains": [d for d, info in domains.items() if info["test_priority"] == "high"],
            "coverage_analysis": self._analyze_domain_coverage(domains)
        }
    
    def _assess_change_risk(self, change: Dict) -> str:
        """评估单个变更的风险级别"""
        risk_score = 0
        
        # 基于变更类型
        change_type = change.get("type", "").lower()
        if change_type in ["deletion", "major_modification"]:
            risk_score += 3
        elif change_type in ["modification", "refactor"]:
            risk_score += 2
        elif change_type in ["addition", "minor_modification"]:
            risk_score += 1
        
        # 基于文件路径
        file_path = change.get("file_path", "").lower()
        if any(keyword in file_path for keyword in ["core", "main", "index", "app"]):
            risk_score += 2
        if any(keyword in file_path for keyword in ["auth", "security", "database"]):
            risk_score += 2
        if any(keyword in file_path for keyword in ["api", "route", "controller"]):
            risk_score += 1
        
        # 基于变更大小
        lines_changed = change.get("lines_changed", 0)
        if lines_changed > 100:
            risk_score += 2
        elif lines_changed > 50:
            risk_score += 1
        
        # 确定风险级别
        if risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _generate_comprehensive_functional_tests(self, 
                                               base_analysis: Dict, 
                                               business_analysis: Dict) -> Dict:
        """生成综合功能测试用例"""
        test_cases = []
        
        # 基于业务域生成测试用例
        domains = business_analysis.get("domains", {})
        
        for domain_name, domain_info in domains.items():
            domain_changes = domain_info.get("changes", [])
            
            for change in domain_changes:
                # 为每个变更生成详细的测试用例
                test_case = self._generate_domain_specific_test_case(
                    domain_name, change, domain_info
                )
                test_cases.append(test_case)
        
        # 生成集成测试用例
        integration_tests = self._generate_integration_test_cases(domains)
        
        # 生成回归测试建议
        regression_tests = self._generate_regression_test_recommendations(base_analysis)
        
        return {
            "test_cases": test_cases,
            "integration_tests": integration_tests,
            "regression_tests": regression_tests,
            "test_summary": {
                "total_test_cases": len(test_cases),
                "high_priority_tests": len([t for t in test_cases if t.get("priority") == "high"]),
                "estimated_total_time": sum([t.get("estimated_time", 30) for t in test_cases]),
                "automation_feasible": len([t for t in test_cases if "高" in t.get("automation_feasibility", "")])
            }
        }

    def _generate_domain_specific_test_case(self,
                                          domain_name: str,
                                          change: Dict,
                                          domain_info: Dict) -> Dict:
        """生成特定业务域的测试用例"""
        change_type = change.get("type", "modification")
        file_path = change.get("file_path", "")
        symbol_name = change.get("symbol_name", "unknown_symbol")

        test_case = {
            "id": f"test_{domain_name}_{abs(hash(file_path + symbol_name)) % 100000}",
            "name": f"{domain_name}功能测试 - {symbol_name}",
            "description": f"验证{symbol_name}在{change_type}变更后的{domain_name}功能完整性",
            "business_domain": domain_name,
            "priority": domain_info.get("test_priority", "medium"),
            "change_info": {
                "file_path": file_path,
                "symbol_name": symbol_name,
                "change_type": change_type,
                "risk_level": self._assess_change_risk(change)
            },
            "test_scenarios": self._generate_domain_test_scenarios(domain_name, change),
            "test_data_requirements": self._generate_domain_test_data(domain_name),
            "expected_outcomes": self._generate_domain_expected_outcomes(domain_name, change),
            "verification_points": self._generate_domain_verification_points(domain_name),
            "estimated_time": self._estimate_domain_test_time(domain_name, change),
            "automation_feasibility": self._assess_domain_automation(domain_name, change),
            "test_environment": self._determine_domain_test_environment(domain_name),
            "prerequisites": self._generate_domain_prerequisites(domain_name),
            "acceptance_criteria": self._generate_domain_acceptance_criteria(domain_name, change)
        }

        return test_case

    def _generate_domain_test_scenarios(self, domain_name: str, change: Dict) -> List[str]:
        """生成业务域特定的测试场景"""
        scenarios = []
        symbol_name = change.get("symbol_name", "功能")
        change_type = change.get("change_type", change.get("type", "修改"))

        domain_scenarios = {
            "用户管理": [
                f"验证{symbol_name}的用户注册流程",
                f"测试{symbol_name}的用户登录认证",
                f"验证{symbol_name}的权限控制机制",
                f"测试{symbol_name}的用户数据安全性",
                f"验证{symbol_name}的会话管理功能"
            ],
            "项目管理": [
                f"验证{symbol_name}的项目创建功能",
                f"测试{symbol_name}的项目配置管理",
                f"验证{symbol_name}的项目权限控制",
                f"测试{symbol_name}的项目状态管理",
                f"验证{symbol_name}的项目数据一致性"
            ],
            "代码分析": [
                f"验证{symbol_name}的代码解析准确性",
                f"测试{symbol_name}的分析结果完整性",
                f"验证{symbol_name}的分析性能表现",
                f"测试{symbol_name}的错误处理机制",
                f"验证{symbol_name}的多语言支持"
            ],
            "API服务": [
                f"验证{symbol_name}的API接口规范",
                f"测试{symbol_name}的请求响应格式",
                f"验证{symbol_name}的错误处理机制",
                f"测试{symbol_name}的API性能表现",
                f"验证{symbol_name}的并发处理能力"
            ],
            "数据管理": [
                f"验证{symbol_name}的数据存储功能",
                f"测试{symbol_name}的数据查询性能",
                f"验证{symbol_name}的数据完整性约束",
                f"测试{symbol_name}的事务处理机制",
                f"验证{symbol_name}的数据备份恢复"
            ],
            "用户界面": [
                f"验证{symbol_name}的界面显示正确性",
                f"测试{symbol_name}的用户交互响应",
                f"验证{symbol_name}的界面兼容性",
                f"测试{symbol_name}的界面性能表现",
                f"验证{symbol_name}的用户体验流畅性"
            ]
        }

        base_scenarios = domain_scenarios.get(domain_name, [
            f"验证{symbol_name}的基本功能",
            f"测试{symbol_name}的边界条件",
            f"验证{symbol_name}的错误处理",
            f"测试{symbol_name}的性能表现"
        ])

        # 基于变更类型添加特定场景
        if change_type in ["addition", "新增"]:
            scenarios.append(f"验证新增{symbol_name}功能的正确性")
            scenarios.append(f"测试{symbol_name}与现有系统的集成")
        elif change_type in ["modification", "修改"]:
            scenarios.append(f"验证修改后{symbol_name}的向后兼容性")
            scenarios.append(f"测试{symbol_name}功能的完整性保持")
        elif change_type in ["deletion", "删除"]:
            scenarios.append(f"验证删除{symbol_name}后系统的稳定性")
            scenarios.append(f"测试替代方案的有效性")

        scenarios.extend(base_scenarios[:4])  # 添加前4个基础场景
        return scenarios[:6]  # 限制场景数量

    def _generate_domain_test_data(self, domain_name: str) -> List[str]:
        """生成业务域特定的测试数据需求"""
        domain_data = {
            "用户管理": [
                "有效用户账户数据（用户名、邮箱、密码）",
                "无效用户数据（空值、格式错误、重复数据）",
                "权限角色测试数据（管理员、普通用户、访客）",
                "用户行为模拟数据（登录、注销、权限变更）"
            ],
            "项目管理": [
                "项目配置测试数据（名称、描述、Git仓库）",
                "项目状态测试数据（创建中、分析中、完成、错误）",
                "项目权限测试数据（所有者、协作者、只读）",
                "Git仓库测试数据（公开仓库、私有仓库、无效仓库）"
            ],
            "代码分析": [
                "多语言代码样本（Python、JavaScript、Java等）",
                "代码复杂度测试数据（简单、中等、复杂）",
                "语法错误代码样本（用于错误处理测试）",
                "大型代码库测试数据（性能测试用）"
            ],
            "API服务": [
                "有效API请求数据（正确格式、参数）",
                "无效API请求数据（错误格式、缺失参数）",
                "API认证测试数据（有效token、无效token）",
                "并发请求测试数据（多用户同时访问）"
            ],
            "数据管理": [
                "数据库连接测试数据（有效连接、无效连接）",
                "数据CRUD操作测试数据（增删改查）",
                "数据完整性测试数据（约束验证）",
                "数据迁移测试数据（版本升级）"
            ],
            "用户界面": [
                "界面元素测试数据（按钮、表单、列表）",
                "用户交互测试数据（点击、输入、滚动）",
                "响应式设计测试数据（不同屏幕尺寸）",
                "浏览器兼容性测试数据（Chrome、Firefox、Safari）"
            ]
        }

        return domain_data.get(domain_name, [
            "基础功能测试数据",
            "边界条件测试数据",
            "异常情况测试数据",
            "性能测试数据"
        ])

    def _generate_domain_expected_outcomes(self, domain_name: str, change: Dict) -> List[str]:
        """生成业务域特定的预期结果"""
        symbol_name = change.get("symbol_name", "功能")

        domain_outcomes = {
            "用户管理": [
                f"{symbol_name}用户认证流程正常工作",
                f"{symbol_name}权限控制准确执行",
                f"{symbol_name}用户数据安全存储",
                f"{symbol_name}会话管理稳定可靠"
            ],
            "项目管理": [
                f"{symbol_name}项目操作成功执行",
                f"{symbol_name}项目数据保持一致",
                f"{symbol_name}项目权限正确控制",
                f"{symbol_name}项目状态准确反映"
            ],
            "代码分析": [
                f"{symbol_name}代码解析准确无误",
                f"{symbol_name}分析结果完整正确",
                f"{symbol_name}分析性能满足要求",
                f"{symbol_name}错误处理健壮可靠"
            ],
            "API服务": [
                f"{symbol_name}API响应符合规范",
                f"{symbol_name}数据格式正确",
                f"{symbol_name}错误处理完善",
                f"{symbol_name}性能满足要求"
            ],
            "数据管理": [
                f"{symbol_name}数据操作成功执行",
                f"{symbol_name}数据完整性得到保证",
                f"{symbol_name}数据查询性能良好",
                f"{symbol_name}事务处理正确"
            ],
            "用户界面": [
                f"{symbol_name}界面显示正确",
                f"{symbol_name}用户交互响应及时",
                f"{symbol_name}界面兼容性良好",
                f"{symbol_name}用户体验流畅"
            ]
        }

        return domain_outcomes.get(domain_name, [
            f"{symbol_name}功能按预期工作",
            f"{symbol_name}不影响现有功能",
            f"{symbol_name}性能在可接受范围",
            f"{symbol_name}错误处理正确"
        ])

    def _generate_domain_verification_points(self, domain_name: str) -> List[str]:
        """生成业务域特定的验证点"""
        domain_verifications = {
            "用户管理": [
                "用户认证成功率达到100%",
                "权限控制准确无误",
                "用户数据加密存储验证",
                "会话超时机制正常",
                "密码强度验证有效"
            ],
            "项目管理": [
                "项目创建成功率达到100%",
                "项目数据一致性验证",
                "项目权限控制准确",
                "Git集成功能正常",
                "项目状态同步及时"
            ],
            "代码分析": [
                "代码解析准确率 > 95%",
                "分析结果完整性验证",
                "分析性能 < 30秒/MB",
                "错误处理覆盖率 > 90%",
                "多语言支持验证"
            ],
            "API服务": [
                "API响应时间 < 2秒",
                "响应格式符合OpenAPI规范",
                "错误状态码正确返回",
                "并发处理能力 > 100 req/s",
                "API文档与实现一致"
            ],
            "数据管理": [
                "数据完整性约束验证",
                "查询性能 < 1秒",
                "事务ACID特性验证",
                "数据备份恢复成功",
                "并发访问安全性"
            ],
            "用户界面": [
                "界面渲染时间 < 3秒",
                "用户交互响应 < 200ms",
                "跨浏览器兼容性验证",
                "响应式设计适配",
                "无障碍访问支持"
            ]
        }

        return domain_verifications.get(domain_name, [
            "功能正确性验证",
            "性能指标达标",
            "错误处理有效",
            "兼容性验证"
        ])

    def _estimate_domain_test_time(self, domain_name: str, change: Dict) -> int:
        """估算业务域测试时间（分钟）"""
        base_time = 30

        # 基于业务域调整
        domain_multipliers = {
            "用户管理": 1.5,  # 安全性要求高
            "代码分析": 1.3,  # 复杂度高
            "API服务": 1.2,   # 需要集成测试
            "项目管理": 1.1,  # 功能相对复杂
            "数据管理": 1.4,  # 数据一致性要求高
            "用户界面": 1.0   # 相对简单
        }

        base_time *= domain_multipliers.get(domain_name, 1.0)

        # 基于变更风险调整
        risk_level = self._assess_change_risk(change)
        if risk_level == "high":
            base_time *= 1.5
        elif risk_level == "medium":
            base_time *= 1.2

        return min(int(base_time), 120)  # 最大120分钟

    def _assess_domain_automation(self, domain_name: str, change: Dict) -> str:
        """评估业务域自动化可行性"""
        automation_scores = {
            "API服务": 4,     # 高度适合自动化
            "数据管理": 3,    # 适合自动化
            "代码分析": 3,    # 适合自动化
            "项目管理": 2,    # 部分适合自动化
            "用户管理": 2,    # 部分适合自动化（安全考虑）
            "用户界面": 1     # 需要人工验证
        }

        base_score = automation_scores.get(domain_name, 2)

        # 基于变更类型调整
        change_type = change.get("type", "").lower()
        if change_type in ["addition", "modification"]:
            base_score += 1
        elif change_type == "deletion":
            base_score -= 1

        if base_score >= 4:
            return "高 - 完全适合自动化测试"
        elif base_score >= 3:
            return "中 - 大部分可自动化"
        elif base_score >= 2:
            return "中 - 部分可自动化"
        else:
            return "低 - 建议手动测试"

    def _determine_domain_test_environment(self, domain_name: str) -> List[str]:
        """确定业务域测试环境需求"""
        domain_environments = {
            "用户管理": ["开发环境", "测试环境", "安全测试环境"],
            "API服务": ["开发环境", "测试环境", "集成测试环境"],
            "代码分析": ["开发环境", "测试环境", "性能测试环境"],
            "项目管理": ["开发环境", "测试环境"],
            "数据管理": ["开发环境", "测试环境", "数据测试环境"],
            "用户界面": ["开发环境", "测试环境", "兼容性测试环境"]
        }

        return domain_environments.get(domain_name, ["开发环境", "测试环境"])

    def _generate_domain_prerequisites(self, domain_name: str) -> List[str]:
        """生成业务域前置条件"""
        domain_prerequisites = {
            "用户管理": [
                "用户数据库已初始化",
                "认证服务正常运行",
                "权限系统配置完成"
            ],
            "项目管理": [
                "项目数据库已准备",
                "Git服务可访问",
                "文件系统权限正确"
            ],
            "代码分析": [
                "代码解析器已加载",
                "测试代码样本已准备",
                "分析引擎正常运行"
            ],
            "API服务": [
                "API服务已启动",
                "数据库连接正常",
                "认证系统可用"
            ],
            "数据管理": [
                "数据库服务运行",
                "数据连接池配置",
                "备份系统可用"
            ],
            "用户界面": [
                "前端服务已启动",
                "静态资源可访问",
                "浏览器环境准备"
            ]
        }

        return domain_prerequisites.get(domain_name, [
            "测试环境已准备",
            "依赖服务正常",
            "测试数据已加载"
        ])

    def _generate_domain_acceptance_criteria(self, domain_name: str, change: Dict) -> List[str]:
        """生成业务域验收标准"""
        symbol_name = change.get("symbol_name", "功能")

        domain_criteria = {
            "用户管理": [
                f"{symbol_name}通过所有安全性检查",
                f"{symbol_name}用户认证流程无误",
                f"{symbol_name}权限控制准确执行",
                "通过安全合规审查"
            ],
            "项目管理": [
                f"{symbol_name}项目操作成功率100%",
                f"{symbol_name}数据一致性验证通过",
                f"{symbol_name}Git集成功能正常",
                "项目管理流程完整"
            ],
            "代码分析": [
                f"{symbol_name}分析准确率达标",
                f"{symbol_name}性能指标满足要求",
                f"{symbol_name}错误处理健壮",
                "分析结果可重现"
            ],
            "API服务": [
                f"{symbol_name}API规范符合标准",
                f"{symbol_name}响应时间达标",
                f"{symbol_name}错误处理完善",
                "API文档更新完整"
            ],
            "数据管理": [
                f"{symbol_name}数据完整性保证",
                f"{symbol_name}查询性能达标",
                f"{symbol_name}事务处理正确",
                "数据安全性验证通过"
            ],
            "用户界面": [
                f"{symbol_name}界面显示正确",
                f"{symbol_name}用户体验良好",
                f"{symbol_name}兼容性验证通过",
                "界面响应性能达标"
            ]
        }

        return domain_criteria.get(domain_name, [
            f"{symbol_name}功能按设计工作",
            f"{symbol_name}不影响现有功能",
            f"{symbol_name}性能满足要求",
            "通过所有测试用例"
        ])

    def _analyze_domain_coverage(self, domains: Dict) -> Dict:
        """分析业务域覆盖情况"""
        total_domains = len(domains)
        high_risk_domains = len([d for d, info in domains.items() if info["risk_level"] == "high"])
        medium_risk_domains = len([d for d, info in domains.items() if info["risk_level"] == "medium"])

        coverage_analysis = {
            "total_domains_affected": total_domains,
            "high_risk_domains": high_risk_domains,
            "medium_risk_domains": medium_risk_domains,
            "low_risk_domains": total_domains - high_risk_domains - medium_risk_domains,
            "coverage_percentage": min(100, (total_domains / 10) * 100),  # 假设总共10个可能的域
            "risk_distribution": {
                "high": high_risk_domains,
                "medium": medium_risk_domains,
                "low": total_domains - high_risk_domains - medium_risk_domains
            }
        }

        return coverage_analysis

    def _generate_integration_test_cases(self, domains: Dict) -> List[Dict]:
        """生成集成测试用例"""
        integration_tests = []

        # 如果涉及多个业务域，生成跨域集成测试
        if len(domains) > 1:
            domain_names = list(domains.keys())

            # 生成两两集成测试
            for i in range(len(domain_names)):
                for j in range(i + 1, len(domain_names)):
                    domain1, domain2 = domain_names[i], domain_names[j]

                    integration_test = {
                        "id": f"integration_{abs(hash(domain1 + domain2)) % 10000}",
                        "name": f"{domain1}与{domain2}集成测试",
                        "description": f"验证{domain1}和{domain2}之间的集成功能",
                        "involved_domains": [domain1, domain2],
                        "test_scenarios": [
                            f"验证{domain1}到{domain2}的数据流",
                            f"测试{domain2}到{domain1}的响应",
                            f"验证{domain1}和{domain2}的错误处理集成",
                            f"测试{domain1}和{domain2}的性能集成"
                        ],
                        "priority": "high" if any(domains[d]["risk_level"] == "high" for d in [domain1, domain2]) else "medium",
                        "estimated_time": 45,
                        "test_type": "integration"
                    }
                    integration_tests.append(integration_test)

        return integration_tests[:5]  # 限制集成测试数量

    def _generate_regression_test_recommendations(self, base_analysis: Dict) -> List[Dict]:
        """生成回归测试建议"""
        regression_tests = []

        # 基于影响分析生成回归测试
        impact_areas = base_analysis.get("impact_analysis", {}).get("affected_areas", [])

        for area in impact_areas[:5]:  # 限制数量
            regression_test = {
                "id": f"regression_{abs(hash(area)) % 10000}",
                "name": f"{area}回归测试",
                "description": f"确保{area}的现有功能不受变更影响",
                "test_scope": area,
                "test_scenarios": [
                    f"验证{area}的核心功能完整性",
                    f"测试{area}的性能基准",
                    f"验证{area}的数据一致性",
                    f"测试{area}的错误处理"
                ],
                "priority": "high",
                "estimated_time": 30,
                "test_type": "regression",
                "automation_recommended": True
            }
            regression_tests.append(regression_test)

        return regression_tests

    def _comprehensive_risk_assessment(self, base_analysis: Dict, business_analysis: Dict) -> Dict:
        """综合风险评估"""
        domains = business_analysis.get("domains", {})

        # 计算总体风险分数
        total_risk_score = 0
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0

        for domain_name, domain_info in domains.items():
            risk_level = domain_info.get("risk_level", "low")
            if risk_level == "high":
                total_risk_score += 3
                high_risk_count += 1
            elif risk_level == "medium":
                total_risk_score += 2
                medium_risk_count += 1
            else:
                total_risk_score += 1
                low_risk_count += 1

        # 确定总体风险级别
        if total_risk_score >= 8:
            overall_risk = "high"
        elif total_risk_score >= 4:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        # 生成风险缓解建议
        mitigation_strategies = self._generate_risk_mitigation_strategies(domains, overall_risk)

        return {
            "overall_risk_level": overall_risk,
            "total_risk_score": total_risk_score,
            "risk_distribution": {
                "high_risk_domains": high_risk_count,
                "medium_risk_domains": medium_risk_count,
                "low_risk_domains": low_risk_count
            },
            "critical_areas": [name for name, info in domains.items() if info["risk_level"] == "high"],
            "mitigation_strategies": mitigation_strategies,
            "recommended_actions": self._generate_recommended_actions(overall_risk, domains)
        }

    def _generate_risk_mitigation_strategies(self, domains: Dict, overall_risk: str) -> List[str]:
        """生成风险缓解策略"""
        strategies = []

        # 基于总体风险级别
        if overall_risk == "high":
            strategies.extend([
                "执行全面的回归测试套件",
                "增加代码审查流程",
                "实施分阶段部署策略",
                "准备快速回滚方案"
            ])
        elif overall_risk == "medium":
            strategies.extend([
                "执行重点功能测试",
                "加强集成测试覆盖",
                "监控关键性能指标"
            ])
        else:
            strategies.extend([
                "执行基础功能验证",
                "进行标准测试流程"
            ])

        # 基于特定业务域风险
        high_risk_domains = [name for name, info in domains.items() if info["risk_level"] == "high"]
        for domain in high_risk_domains:
            if domain == "用户管理":
                strategies.append("加强安全性测试和权限验证")
            elif domain == "数据管理":
                strategies.append("执行数据完整性和备份验证")
            elif domain == "API服务":
                strategies.append("增加API性能和负载测试")

        return list(set(strategies))  # 去重

    def _generate_recommended_actions(self, overall_risk: str, domains: Dict) -> List[str]:
        """生成推荐行动"""
        actions = []

        if overall_risk == "high":
            actions.extend([
                "立即执行全面测试计划",
                "安排额外的代码审查",
                "准备应急响应计划",
                "通知相关利益相关者"
            ])
        elif overall_risk == "medium":
            actions.extend([
                "执行重点测试计划",
                "监控部署后的系统表现",
                "准备快速修复方案"
            ])
        else:
            actions.extend([
                "执行标准测试流程",
                "进行常规部署监控"
            ])

        # 基于域数量添加建议
        if len(domains) > 3:
            actions.append("考虑分批次部署以降低风险")

        return actions

    def _generate_test_strategy(self, functional_tests: Dict, risk_assessment: Dict) -> Dict:
        """生成测试策略"""
        test_cases = functional_tests.get("test_cases", [])
        overall_risk = risk_assessment.get("overall_risk_level", "medium")

        # 计算测试统计
        high_priority_tests = len([t for t in test_cases if t.get("priority") == "high"])
        total_time = sum([t.get("estimated_time", 30) for t in test_cases])
        automation_feasible = len([t for t in test_cases if "高" in t.get("automation_feasibility", "")])

        # 确定测试策略
        if overall_risk == "high":
            strategy_type = "全面测试策略"
            execution_phases = ["单元测试", "集成测试", "系统测试", "验收测试", "回归测试"]
        elif overall_risk == "medium":
            strategy_type = "重点测试策略"
            execution_phases = ["单元测试", "集成测试", "重点功能测试"]
        else:
            strategy_type = "标准测试策略"
            execution_phases = ["单元测试", "基础功能测试"]

        return {
            "strategy_type": strategy_type,
            "execution_phases": execution_phases,
            "test_statistics": {
                "total_test_cases": len(test_cases),
                "high_priority_tests": high_priority_tests,
                "estimated_total_time_hours": round(total_time / 60, 1),
                "automation_feasible_percentage": round((automation_feasible / len(test_cases)) * 100, 1) if test_cases else 0
            },
            "resource_requirements": self._calculate_resource_requirements(total_time, high_priority_tests),
            "timeline_recommendation": self._generate_timeline_recommendation(total_time, overall_risk),
            "success_criteria": self._generate_success_criteria(overall_risk)
        }

    def _calculate_resource_requirements(self, total_time: int, high_priority_tests: int) -> Dict:
        """计算资源需求"""
        # 假设一个测试人员每天工作8小时
        testing_days = max(1, round(total_time / (8 * 60)))

        if high_priority_tests > 5:
            recommended_testers = 2
        else:
            recommended_testers = 1

        return {
            "recommended_testers": recommended_testers,
            "estimated_testing_days": testing_days,
            "automation_engineer_needed": total_time > 480,  # 超过8小时建议自动化
            "environment_requirements": ["开发环境", "测试环境"]
        }

    def _generate_timeline_recommendation(self, total_time: int, risk_level: str) -> str:
        """生成时间线建议"""
        days = max(1, round(total_time / (8 * 60)))

        if risk_level == "high":
            return f"建议{days + 2}天完成测试，包含2天缓冲时间"
        elif risk_level == "medium":
            return f"建议{days + 1}天完成测试，包含1天缓冲时间"
        else:
            return f"建议{days}天完成测试"

    def _generate_success_criteria(self, risk_level: str) -> List[str]:
        """生成成功标准"""
        if risk_level == "high":
            return [
                "所有高优先级测试用例通过率100%",
                "所有中优先级测试用例通过率95%以上",
                "性能测试通过基准要求",
                "安全测试无严重漏洞",
                "回归测试通过率100%"
            ]
        elif risk_level == "medium":
            return [
                "所有高优先级测试用例通过率100%",
                "所有中优先级测试用例通过率90%以上",
                "核心功能测试通过"
            ]
        else:
            return [
                "所有测试用例通过率90%以上",
                "基础功能验证通过"
            ]

    def _format_detailed_changes(self, changes: List[Dict], base_analysis: Dict) -> List[Dict]:
        """格式化详细变更信息"""
        detailed_changes = []

        for change in changes:
            detailed_change = {
                "file_path": change.get("file_path", ""),
                "symbol_name": change.get("symbol_name", ""),
                "change_type": change.get("type", change.get("change_type", "")),
                "risk_level": self._assess_change_risk(change),
                "business_domain": self._identify_business_domain_for_change(change),
                "impact_analysis": {
                    "lines_changed": change.get("lines_changed", 0),
                    "complexity_impact": self._assess_complexity_impact(change),
                    "dependency_impact": self._assess_dependency_impact(change),
                    "test_impact": self._assess_test_impact(change)
                },
                "recommendations": self._generate_change_recommendations(change)
            }
            detailed_changes.append(detailed_change)

        return detailed_changes

    def _identify_business_domain_for_change(self, change: Dict) -> str:
        """为单个变更识别业务域"""
        file_path = change.get("file_path", "").lower()

        if any(keyword in file_path for keyword in ["user", "auth", "login"]):
            return "用户管理"
        elif any(keyword in file_path for keyword in ["project", "repo", "git"]):
            return "项目管理"
        elif any(keyword in file_path for keyword in ["analyzer", "analysis", "code"]):
            return "代码分析"
        elif any(keyword in file_path for keyword in ["api", "route", "endpoint"]):
            return "API服务"
        elif any(keyword in file_path for keyword in ["database", "model", "data"]):
            return "数据管理"
        elif any(keyword in file_path for keyword in ["ui", "view", "component"]):
            return "用户界面"
        else:
            return "核心服务"

    def _assess_complexity_impact(self, change: Dict) -> str:
        """评估复杂度影响"""
        lines_changed = change.get("lines_changed", 0)

        if lines_changed > 100:
            return "高复杂度影响"
        elif lines_changed > 50:
            return "中等复杂度影响"
        else:
            return "低复杂度影响"

    def _assess_dependency_impact(self, change: Dict) -> str:
        """评估依赖影响"""
        # 这里可以基于实际的依赖分析结果
        file_path = change.get("file_path", "")

        if any(keyword in file_path.lower() for keyword in ["core", "base", "main"]):
            return "高依赖影响"
        elif any(keyword in file_path.lower() for keyword in ["util", "helper", "common"]):
            return "中等依赖影响"
        else:
            return "低依赖影响"

    def _assess_test_impact(self, change: Dict) -> str:
        """评估测试影响"""
        change_type = change.get("type", "").lower()

        if change_type in ["deletion", "major_modification"]:
            return "需要全面测试"
        elif change_type in ["modification", "refactor"]:
            return "需要重点测试"
        else:
            return "需要基础测试"

    def _generate_change_recommendations(self, change: Dict) -> List[str]:
        """生成变更建议"""
        recommendations = []
        risk_level = self._assess_change_risk(change)

        if risk_level == "high":
            recommendations.extend([
                "执行全面的回归测试",
                "增加代码审查",
                "考虑分阶段部署",
                "准备回滚计划"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "执行重点功能测试",
                "进行代码审查",
                "监控部署后表现"
            ])
        else:
            recommendations.extend([
                "执行基础功能验证",
                "进行标准测试"
            ])

        return recommendations
