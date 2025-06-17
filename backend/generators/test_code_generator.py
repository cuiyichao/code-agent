"""
智能测试代码生成器
根据代码变更自动生成测试建议
"""

import logging
from typing import List, Dict, Any, Optional
from ..models.code_symbol import CodeSymbol, ChangeAnalysis

class TestCodeGenerator:
    """智能测试代码生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_test_suggestions(self, changed_symbols: List[CodeSymbol], 
                                      analysis: ChangeAnalysis) -> List[Dict[str, Any]]:
        """
        根据变更的符号生成测试建议
        
        Args:
            changed_symbols: 变更的符号列表
            analysis: 变更分析结果
            
        Returns:
            测试建议列表
        """
        test_suggestions = []
        
        try:
            for symbol in changed_symbols:
                suggestions = self._generate_symbol_tests(symbol, analysis)
                test_suggestions.extend(suggestions)
            
            # 按优先级排序
            test_suggestions.sort(key=lambda x: self._get_priority_score(x['priority']), reverse=True)
            
            self.logger.info(f"生成了 {len(test_suggestions)} 个测试建议")
            return test_suggestions
            
        except Exception as e:
            self.logger.error(f"生成测试建议失败: {str(e)}")
            return []
    
    def _generate_symbol_tests(self, symbol: CodeSymbol, analysis: ChangeAnalysis) -> List[Dict[str, Any]]:
        """为单个符号生成测试建议"""
        suggestions = []
        
        if symbol.symbol_type == 'function':
            suggestions.extend(self._generate_function_tests(symbol, analysis))
        elif symbol.symbol_type == 'class':
            suggestions.extend(self._generate_class_tests(symbol, analysis))
        elif symbol.symbol_type == 'variable':
            suggestions.extend(self._generate_variable_tests(symbol, analysis))
        
        return suggestions
    
    def _generate_function_tests(self, symbol: CodeSymbol, analysis: ChangeAnalysis) -> List[Dict[str, Any]]:
        """生成函数测试建议"""
        suggestions = []
        
        # 基础单元测试
        suggestions.append({
            'type': 'unit_test',
            'target': symbol.name,
            'priority': self._calculate_test_priority(symbol, analysis),
            'reason': f"函数 {symbol.name} 发生变更，需要验证基本功能",
            'suggested_test_cases': self._generate_function_test_cases(symbol)
        })
        
        # 如果是高复杂度函数，建议更全面的测试
        if symbol.complexity > 5:
            suggestions.append({
                'type': 'integration_test',
                'target': symbol.name,
                'priority': 'high',
                'reason': f"函数 {symbol.name} 复杂度较高 ({symbol.complexity})，建议集成测试",
                'suggested_test_cases': [
                    "测试函数与其他模块的集成",
                    "测试异常处理路径",
                    "测试边界条件"
                ]
            })
        
        # 如果函数有参数，建议参数测试
        if symbol.parameters:
            suggestions.append({
                'type': 'parameter_test',
                'target': symbol.name,
                'priority': 'medium',
                'reason': f"函数 {symbol.name} 有 {len(symbol.parameters)} 个参数，需要参数验证测试",
                'suggested_test_cases': self._generate_parameter_test_cases(symbol)
            })
        
        return suggestions
    
    def _generate_class_tests(self, symbol: CodeSymbol, analysis: ChangeAnalysis) -> List[Dict[str, Any]]:
        """生成类测试建议"""
        suggestions = []
        
        # 类实例化测试
        suggestions.append({
            'type': 'unit_test',
            'target': symbol.name,
            'priority': self._calculate_test_priority(symbol, analysis),
            'reason': f"类 {symbol.name} 发生变更，需要测试实例化和基本方法",
            'suggested_test_cases': [
                f"测试 {symbol.name} 的实例化",
                f"测试 {symbol.name} 的基本方法调用",
                f"测试 {symbol.name} 的属性访问"
            ]
        })
        
        # 如果是关键业务类，建议更全面的测试
        if self._is_business_critical(symbol):
            suggestions.append({
                'type': 'integration_test',
                'target': symbol.name,
                'priority': 'high',
                'reason': f"类 {symbol.name} 是核心业务类，需要全面测试",
                'suggested_test_cases': [
                    "测试类的生命周期",
                    "测试类与数据库的交互",
                    "测试类的错误处理"
                ]
            })
        
        return suggestions
    
    def _generate_variable_tests(self, symbol: CodeSymbol, analysis: ChangeAnalysis) -> List[Dict[str, Any]]:
        """生成变量测试建议"""
        suggestions = []
        
        # 如果是配置变量或常量
        if self._is_config_variable(symbol):
            suggestions.append({
                'type': 'configuration_test',
                'target': symbol.name,
                'priority': 'medium',
                'reason': f"配置变量 {symbol.name} 发生变更，需要验证配置正确性",
                'suggested_test_cases': [
                    f"测试 {symbol.name} 的默认值",
                    f"测试 {symbol.name} 的有效性验证",
                    f"测试使用 {symbol.name} 的功能"
                ]
            })
        
        return suggestions
    
    def _generate_function_test_cases(self, symbol: CodeSymbol) -> List[str]:
        """生成函数测试用例"""
        test_cases = []
        
        # 基础测试用例
        test_cases.append(f"测试 {symbol.name} 的正常执行路径")
        
        # 参数测试
        if symbol.parameters:
            test_cases.append(f"测试 {symbol.name} 的参数验证")
            test_cases.append(f"测试 {symbol.name} 的边界参数")
        
        # 返回值测试
        if symbol.return_type:
            test_cases.append(f"测试 {symbol.name} 的返回值类型")
        
        # 异常测试
        test_cases.append(f"测试 {symbol.name} 的异常处理")
        
        return test_cases
    
    def _generate_parameter_test_cases(self, symbol: CodeSymbol) -> List[str]:
        """生成参数测试用例"""
        test_cases = []
        
        for param in symbol.parameters:
            test_cases.append(f"测试参数 {param} 的有效值")
            test_cases.append(f"测试参数 {param} 的无效值")
            test_cases.append(f"测试参数 {param} 的边界值")
        
        # 参数组合测试
        if len(symbol.parameters) > 1:
            test_cases.append("测试参数组合的有效性")
        
        return test_cases
    
    def _calculate_test_priority(self, symbol: CodeSymbol, analysis: ChangeAnalysis) -> str:
        """计算测试优先级"""
        priority_score = 0
        
        # 复杂度影响
        priority_score += min(symbol.complexity, 10)
        
        # 影响范围
        if hasattr(analysis, 'direct_impacts'):
            priority_score += len(analysis.direct_impacts) * 2
        if hasattr(analysis, 'indirect_impacts'):
            priority_score += len(analysis.indirect_impacts)
        
        # 符号类型权重
        type_weights = {
            'function': 3,
            'class': 4,
            'variable': 1,
            'import': 2
        }
        priority_score += type_weights.get(symbol.symbol_type, 1)
        
        # 业务关键性
        if self._is_business_critical(symbol):
            priority_score += 5
        
        # 转换为优先级标签
        if priority_score >= 15:
            return 'critical'
        elif priority_score >= 10:
            return 'high'
        elif priority_score >= 5:
            return 'medium'
        else:
            return 'low'
    
    def _is_business_critical(self, symbol: CodeSymbol) -> bool:
        """判断是否是业务关键符号"""
        critical_keywords = [
            'auth', 'login', 'user', 'payment', 'order', 'transaction',
            'security', 'password', 'token', 'api', 'database', 'data',
            'main', 'core', 'service', 'controller', 'model'
        ]
        
        symbol_name_lower = symbol.name.lower()
        file_path_lower = symbol.file_path.lower()
        
        return any(keyword in symbol_name_lower or keyword in file_path_lower 
                  for keyword in critical_keywords)
    
    def _is_config_variable(self, symbol: CodeSymbol) -> bool:
        """判断是否是配置变量"""
        config_indicators = [
            'config', 'setting', 'constant', 'default', 'option',
            'parameter', 'env', 'environment'
        ]
        
        symbol_name_lower = symbol.name.lower()
        return (symbol.name.isupper() or  # 全大写常量
                any(indicator in symbol_name_lower for indicator in config_indicators))
    
    def _get_priority_score(self, priority: str) -> int:
        """获取优先级数值分数"""
        priority_scores = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_scores.get(priority, 1)
