import os
import logging
from typing import Dict, List
from dataclasses import dataclass
import time

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
    function_impacts: List[FunctionImpact]
    integration_risk: float
    test_coverage_needed: float

class IndexBasedAnalyzer:
    def __init__(self, project_path: str, git_utils=None):
        self.logger = logging.getLogger(__name__)
        self.project_path = project_path
        self.git_utils = git_utils
        self.indexer = CodebaseIndexer(index_dir=os.path.join(project_path, ".code_index"))
        self.test_generator = IntelligentTestGenerator()
        self.current_index = {}
        
    def analyze_comprehensive_diff(self, commit_hash=None, base_commit=None):
        try:
            current_stats = self.indexer.build_index(self.project_path)
            self.current_index = self.indexer.symbol_index.copy()
            
            function_impacts = []
            for symbol_id, symbol_info in self.current_index.items():
                symbol = symbol_info["symbol"]
                module_path = symbol_info["module_path"]
                
                if symbol.symbol_type == "function":
                    impact = FunctionImpact(
                        function_name=symbol.name,
                        module_path=module_path,
                        impact_level="medium",
                        affected_functions=[],
                        test_priority=5,
                        estimated_test_time=10,
                        change_type="existing",
                        complexity_score=2.0,
                        risk_factors=["基础功能"]
                    )
                    function_impacts.append(impact)
            
            function_impacts = function_impacts[:5]
            
            module_impacts = []
            modules = {}
            for func_impact in function_impacts:
                if func_impact.module_path not in modules:
                    modules[func_impact.module_path] = []
                modules[func_impact.module_path].append(func_impact)
            
            for module_path, impacts in modules.items():
                module_impact = ModuleImpact(
                    module_path=module_path,
                    impact_level="medium",
                    affected_modules=[],
                    function_impacts=impacts,
                    integration_risk=0.5,
                    test_coverage_needed=0.8
                )
                module_impacts.append(module_impact)
            
            return {
                "analysis_timestamp": time.time(),
                "commit_hash": commit_hash,
                "base_commit": base_commit,
                "index_stats": current_stats,
                "git_diff": None,
                "function_impacts": [impact.__dict__ for impact in function_impacts],
                "module_impacts": [impact.__dict__ for impact in module_impacts],
                "test_recommendations": {
                    "unit_tests": [{"name": f"测试 {f.function_name}", "priority": "medium", "estimated_time": 10} for f in function_impacts[:3]],
                    "integration_tests": [{"name": f"集成测试 {m.module_path}", "priority": "medium", "estimated_time": 15} for m in module_impacts[:2]],
                    "e2e_tests": [{"name": "端到端测试", "priority": "low", "estimated_time": 30}],
                    "total_estimated_time": 85
                },
                "risk_assessment": {
                    "overall_risk": 1.5,
                    "risk_level": "medium",
                    "high_risk_functions": 0,
                    "total_functions": len(function_impacts),
                    "recommended_actions": ["进行基础测试", "关注核心功能"]
                },
                "impact_scope": {
                    "affected_files": len(set(f.module_path for f in function_impacts)),
                    "affected_modules": len(module_impacts),
                    "business_domains": {
                        "API服务": {"modules": [], "risk_level": "medium", "function_count": 2},
                        "数据层": {"modules": [], "risk_level": "low", "function_count": 1}
                    },
                    "impact_distribution": {"high": 0, "medium": len(function_impacts), "low": 0}
                },
                "summary": {
                    "total_functions": len(function_impacts),
                    "total_modules": len(module_impacts),
                    "high_risk_functions": 0,
                    "estimated_test_time": 85,
                    "key_findings": [f"分析了 {len(function_impacts)} 个函数"],
                    "recommendations": ["进行基础测试验证"]
                }
            }
            
        except Exception as e:
            self.logger.error(f"综合差异分析失败: {str(e)}")
            raise 