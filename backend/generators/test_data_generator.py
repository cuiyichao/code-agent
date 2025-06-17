import random
import string
import logging
from typing import Dict, List, Optional, Any, Union
import re

from ..models.test_models import FunctionInfo, TestScenario, TestType, Priority

logger = logging.getLogger(__name__)

class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self):
        self.type_generators = {
            'int': self._generate_int_data,
            'float': self._generate_float_data,
            'str': self._generate_string_data,
            'bool': self._generate_bool_data,
            'list': self._generate_list_data,
            'dict': self._generate_dict_data,
            'any': lambda case_type: "test_value"
        }
        
        self.common_param_patterns = {
            'id': r'id|identifier|key',
            'name': r'name|title|label',
            'email': r'email|mail',
            'password': r'password|pwd|pass',
            'date': r'date|time|day|month|year',
            'url': r'url|link|uri',
            'file': r'file|path|filename',
            'count': r'count|num|number|quantity|amount',
            'enabled': r'enabled|active|is_|has_|can_|should_'
        }
    
    def generate_test_scenarios(self, func_info: FunctionInfo) -> List[TestScenario]:
        """生成测试场景"""
        scenarios = []
        
        # 常规测试场景
        normal_data = self._generate_normal_data(func_info)
        scenarios.append(
            TestScenario(
                name=f"{func_info.name}_normal_case",
                description=f"测试 {func_info.name} 函数在正常输入下的行为",
                test_data=normal_data,
                expected_behavior="函数应正确执行并返回预期结果",
                test_type=TestType.UNIT,
                priority=Priority.HIGH
            )
        )
        
        # 边界测试场景
        edge_scenarios = self._generate_edge_scenarios(func_info)
        scenarios.extend(edge_scenarios)
        
        # 错误测试场景
        error_scenarios = self._generate_error_scenarios(func_info)
        scenarios.extend(error_scenarios)
        
        # 如果函数复杂度高，添加性能测试场景
        if func_info.complexity > 5:
            perf_data = self._generate_performance_data(func_info)
            scenarios.append(
                TestScenario(
                    name=f"{func_info.name}_performance_test",
                    description=f"测试 {func_info.name} 函数的性能",
                    test_data=perf_data,
                    expected_behavior="函数应在合理时间内完成执行",
                    test_type=TestType.PERFORMANCE,
                    priority=Priority.MEDIUM
                )
            )
        
        return scenarios
    
    def _generate_normal_data(self, func_info: FunctionInfo) -> Dict[str, Any]:
        """生成正常测试数据"""
        test_data = {}
        
        for param in func_info.parameters:
            param_name = param['name']
            param_type = param.get('type', 'any')
            
            # 跳过self参数
            if param_name == 'self':
                continue
                
            # 跳过*args和**kwargs
            if param_name.startswith('*'):
                continue
            
            # 优先使用默认值
            if param.get('default') is not None and param.get('default') != 'None':
                test_data[param_name] = param['default']
                continue
            
            # 根据参数名称推断合适的测试值
            inferred_value = self._infer_from_name(param_name)
            if inferred_value is not None:
                test_data[param_name] = inferred_value
                continue
            
            # 根据类型生成
            test_data[param_name] = self._generate_value_by_type(param_type, 'normal')
        
        return test_data
    
    def _generate_edge_scenarios(self, func_info: FunctionInfo) -> List[TestScenario]:
        """生成边界测试场景"""
        edge_scenarios = []
        
        for param in func_info.parameters:
            param_name = param['name']
            param_type = param.get('type', 'any')
            
            # 跳过self参数、*args和**kwargs
            if param_name == 'self' or param_name.startswith('*'):
                continue
            
            # 获取该类型的边界情况
            edge_cases = self._get_edge_cases_for_type(param_type)
            
            for i, case in enumerate(edge_cases):
                edge_data = self._generate_normal_data(func_info)  # 先生成正常数据
                edge_data[param_name] = case['value']  # 替换为边界值
                
                edge_scenarios.append(
                    TestScenario(
                        name=f"{func_info.name}_{param_name}_{case['name']}",
                        description=f"测试 {func_info.name} 函数在参数 {param_name} 为{case['description']}时的行为",
                        test_data=edge_data,
                        expected_behavior=case['expected'],
                        test_type=TestType.UNIT,
                        priority=Priority.MEDIUM
                    )
                )
                
                # 限制边界场景数量
                if len(edge_scenarios) >= 5:
                    break
        
        return edge_scenarios[:5]  # 最多返回5个边界场景
    
    def _generate_error_scenarios(self, func_info: FunctionInfo) -> List[TestScenario]:
        """生成错误测试场景"""
        error_scenarios = []
        
        for param in func_info.parameters:
            param_name = param['name']
            param_type = param.get('type', 'any')
            
            # 跳过self参数、*args和**kwargs
            if param_name == 'self' or param_name.startswith('*'):
                continue
            
            # 生成错误类型的数据
            error_data = self._generate_normal_data(func_info)  # 先生成正常数据
            wrong_type_value = self._get_wrong_type_data(param)
            
            if wrong_type_value is not None:
                error_data[param_name] = wrong_type_value
                
                error_scenarios.append(
                    TestScenario(
                        name=f"{func_info.name}_{param_name}_wrong_type",
                        description=f"测试 {func_info.name} 函数在参数 {param_name} 类型错误时的行为",
                        test_data=error_data,
                        expected_behavior="函数应抛出类型错误异常或进行适当的错误处理",
                        test_type=TestType.UNIT,
                        priority=Priority.HIGH
                    )
                )
            
            # 生成空值测试
            null_data = self._generate_normal_data(func_info)
            null_data[param_name] = None
            
            error_scenarios.append(
                TestScenario(
                    name=f"{func_info.name}_{param_name}_null",
                    description=f"测试 {func_info.name} 函数在参数 {param_name} 为空值时的行为",
                    test_data=null_data,
                    expected_behavior="函数应适当处理空值或抛出预期的异常",
                    test_type=TestType.UNIT,
                    priority=Priority.MEDIUM
                )
            )
            
            # 限制错误场景数量
            if len(error_scenarios) >= 3:
                break
        
        return error_scenarios[:3]  # 最多返回3个错误场景
    
    def _generate_performance_data(self, func_info: FunctionInfo) -> Dict[str, Any]:
        """生成性能测试数据"""
        perf_data = {}
        
        for param in func_info.parameters:
            param_name = param['name']
            param_type = param.get('type', 'any')
            
            # 跳过self参数、*args和**kwargs
            if param_name == 'self' or param_name.startswith('*'):
                continue
            
            # 生成大量数据
            if 'list' in param_type.lower() or 'array' in param_type.lower():
                # 生成大型列表
                perf_data[param_name] = [i for i in range(1000)]
            elif 'dict' in param_type.lower() or 'map' in param_type.lower():
                # 生成大型字典
                perf_data[param_name] = {f'key_{i}': f'value_{i}' for i in range(1000)}
            elif 'str' in param_type.lower() or 'string' in param_type.lower():
                # 生成长字符串
                perf_data[param_name] = 'a' * 10000
            else:
                # 使用普通测试数据
                perf_data[param_name] = self._generate_value_by_type(param_type, 'normal')
        
        return perf_data
    
    def _generate_value_by_type(self, param_type: str, case_type: str) -> Any:
        """根据类型生成测试值"""
        # 提取基本类型
        basic_type = param_type.lower().split('[')[0].strip()
        
        # 处理常见类型
        for type_name, generator in self.type_generators.items():
            if type_name in basic_type:
                return generator(case_type)
        
        # 默认返回字符串
        return "test_value"
    
    def _generate_int_data(self, case_type: str) -> Union[int, str]:
        """生成整数测试数据"""
        if case_type == 'normal':
            return random.randint(1, 100)
        else:
            return 42  # 默认值
    
    def _generate_float_data(self, case_type: str) -> Union[float, str]:
        """生成浮点数测试数据"""
        if case_type == 'normal':
            return random.uniform(0.1, 100.0)
        else:
            return 3.14  # 默认值
    
    def _generate_string_data(self, case_type: str) -> Union[str, int]:
        """生成字符串测试数据"""
        if case_type == 'normal':
            return ''.join(random.choices(string.ascii_letters, k=10))
        else:
            return "test_string"  # 默认值
    
    def _generate_bool_data(self, case_type: str) -> Union[bool, str]:
        """生成布尔测试数据"""
        if case_type == 'normal':
            return random.choice([True, False])
        else:
            return True  # 默认值
    
    def _generate_list_data(self, case_type: str) -> Union[List, str]:
        """生成列表测试数据"""
        if case_type == 'normal':
            return [i for i in range(5)]
        else:
            return [1, 2, 3]  # 默认值
    
    def _generate_dict_data(self, case_type: str) -> Union[Dict, str]:
        """生成字典测试数据"""
        if case_type == 'normal':
            return {'key1': 'value1', 'key2': 'value2'}
        else:
            return {'key': 'value'}  # 默认值
    
    def _get_edge_cases_for_type(self, param_type: str) -> List[Dict]:
        """获取特定类型的边界情况"""
        param_type = param_type.lower()
        edge_cases = []
        
        # 整数边界情况
        if 'int' in param_type:
            edge_cases = [
                {
                    'name': 'zero',
                    'description': '零值',
                    'value': 0,
                    'expected': '函数应正确处理零值'
                },
                {
                    'name': 'negative',
                    'description': '负数',
                    'value': -1,
                    'expected': '函数应正确处理负数'
                },
                {
                    'name': 'max',
                    'description': '最大值',
                    'value': 2**31 - 1,
                    'expected': '函数应正确处理最大整数值'
                },
                {
                    'name': 'min',
                    'description': '最小值',
                    'value': -2**31,
                    'expected': '函数应正确处理最小整数值'
                }
            ]
        
        # 浮点数边界情况
        elif 'float' in param_type or 'double' in param_type:
            edge_cases = [
                {
                    'name': 'zero',
                    'description': '零值',
                    'value': 0.0,
                    'expected': '函数应正确处理零值'
                },
                {
                    'name': 'negative',
                    'description': '负数',
                    'value': -0.1,
                    'expected': '函数应正确处理负浮点数'
                },
                {
                    'name': 'very_small',
                    'description': '非常小的值',
                    'value': 1e-10,
                    'expected': '函数应正确处理非常小的浮点数'
                },
                {
                    'name': 'very_large',
                    'description': '非常大的值',
                    'value': 1e10,
                    'expected': '函数应正确处理非常大的浮点数'
                }
            ]
        
        # 字符串边界情况
        elif 'str' in param_type or 'string' in param_type:
            edge_cases = [
                {
                    'name': 'empty',
                    'description': '空字符串',
                    'value': '',
                    'expected': '函数应正确处理空字符串'
                },
                {
                    'name': 'very_long',
                    'description': '非常长的字符串',
                    'value': 'a' * 1000,
                    'expected': '函数应正确处理非常长的字符串'
                },
                {
                    'name': 'special_chars',
                    'description': '包含特殊字符',
                    'value': '!@#$%^&*()',
                    'expected': '函数应正确处理包含特殊字符的字符串'
                },
                {
                    'name': 'unicode',
                    'description': '包含Unicode字符',
                    'value': '你好世界😊',
                    'expected': '函数应正确处理包含Unicode字符的字符串'
                }
            ]
        
        # 列表边界情况
        elif 'list' in param_type or 'array' in param_type:
            edge_cases = [
                {
                    'name': 'empty',
                    'description': '空列表',
                    'value': [],
                    'expected': '函数应正确处理空列表'
                },
                {
                    'name': 'single_item',
                    'description': '单元素列表',
                    'value': [1],
                    'expected': '函数应正确处理单元素列表'
                },
                {
                    'name': 'large',
                    'description': '大型列表',
                    'value': [i for i in range(100)],
                    'expected': '函数应正确处理大型列表'
                }
            ]
        
        # 字典边界情况
        elif 'dict' in param_type or 'map' in param_type:
            edge_cases = [
                {
                    'name': 'empty',
                    'description': '空字典',
                    'value': {},
                    'expected': '函数应正确处理空字典'
                },
                {
                    'name': 'single_item',
                    'description': '单键值对字典',
                    'value': {'key': 'value'},
                    'expected': '函数应正确处理单键值对字典'
                },
                {
                    'name': 'large',
                    'description': '大型字典',
                    'value': {f'key{i}': f'value{i}' for i in range(100)},
                    'expected': '函数应正确处理大型字典'
                }
            ]
        
        # 布尔边界情况
        elif 'bool' in param_type:
            edge_cases = [
                {
                    'name': 'true',
                    'description': 'True值',
                    'value': True,
                    'expected': '函数应正确处理True值'
                },
                {
                    'name': 'false',
                    'description': 'False值',
                    'value': False,
                    'expected': '函数应正确处理False值'
                }
            ]
        
        # 默认边界情况
        else:
            edge_cases = [
                {
                    'name': 'null',
                    'description': '空值',
                    'value': None,
                    'expected': '函数应正确处理空值'
                }
            ]
        
        return edge_cases
    
    def _get_wrong_type_data(self, param: Dict) -> Any:
        """获取错误类型的数据"""
        param_type = param.get('type', 'any').lower()
        
        if 'int' in param_type:
            return "not_an_integer"
        elif 'float' in param_type or 'double' in param_type:
            return "not_a_float"
        elif 'str' in param_type or 'string' in param_type:
            return 123  # 整数而非字符串
        elif 'list' in param_type or 'array' in param_type:
            return "not_a_list"
        elif 'dict' in param_type or 'map' in param_type:
            return "not_a_dict"
        elif 'bool' in param_type:
            return "not_a_boolean"
        else:
            return object()  # 默认使用一个对象
    
    def _infer_from_name(self, param_name: str) -> Any:
        """根据参数名称推断合适的测试值"""
        param_name = param_name.lower()
        
        # 检查是否匹配常见参数模式
        for data_type, pattern in self.common_param_patterns.items():
            if re.search(pattern, param_name):
                if data_type == 'id':
                    return 1
                elif data_type == 'name':
                    return "Test Name"
                elif data_type == 'email':
                    return "test@example.com"
                elif data_type == 'password':
                    return "password123"
                elif data_type == 'date':
                    return "2023-01-01"
                elif data_type == 'url':
                    return "https://example.com"
                elif data_type == 'file':
                    return "test_file.txt"
                elif data_type == 'count':
                    return 10
                elif data_type == 'enabled':
                    return True
        
        # 如果参数名包含特定关键词
        if 'max' in param_name:
            return 100
        elif 'min' in param_name:
            return 0
        elif 'limit' in param_name:
            return 50
        elif 'offset' in param_name:
            return 0
        elif 'page' in param_name:
            return 1
        elif 'size' in param_name:
            return 20
        
        return None  # 无法推断 