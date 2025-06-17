#!/usr/bin/env python3
"""
智能测试用例生成器
支持多种编程语言和测试框架，自动生成高质量的测试用例
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from ..models.test_models import TestType, Priority, FunctionInfo, TestScenario, GeneratedTest
from .test_data_generator import TestDataGenerator
from .test_code_generator import TestCodeGenerator
from ..parsers.test_parser import TestLanguageParser

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentTestGenerator:
    """智能测试用例生成器"""
    
    def __init__(self):
        self.parser = TestLanguageParser()
        self.data_generator = TestDataGenerator()
        self.code_generator = TestCodeGenerator()
    
    def generate_comprehensive_tests(self, change: Dict, impact_analysis: Dict) -> List[GeneratedTest]:
        """生成全面的测试用例"""
        tests = []
        
        # 获取变更信息
        file_path = change.get('file_path', '')
        old_content = change.get('old_content', '')
        new_content = change.get('new_content', '')
        affected_functions = change.get('affected_functions', [])
        
        # 检测语言
        language = self.parser.detect_language(file_path)
        if not language:
            logger.warning(f"无法识别文件 {file_path} 的编程语言")
            return []
        
        # 为每个受影响的函数生成单元测试
        for func_name in affected_functions:
            function_tests = self._generate_function_tests(
                func_name=func_name,
                content=new_content,
                file_path=file_path,
                language=language
            )
            tests.extend(function_tests)
        
        # 生成集成测试
        if impact_analysis and 'direct_impacts' in impact_analysis:
            integration_tests = self._generate_integration_tests(
                change=change,
                impacts=impact_analysis.get('direct_impacts', []),
                language=language
            )
            tests.extend(integration_tests)
        
        # 根据风险等级生成性能测试
        if change.get('risk_level') in ['medium', 'high']:
            performance_tests = self._generate_performance_tests(
                change=change,
                language=language
            )
            tests.extend(performance_tests)
        
        # 如果涉及安全敏感操作，生成安全测试
        if self._involves_security(change):
            security_tests = self._generate_security_tests(
                change=change,
                language=language
            )
            tests.extend(security_tests)
        
        # 如果有业务影响，生成端到端测试
        if change.get('business_impact'):
            e2e_tests = self._generate_e2e_tests(
                change=change,
                language=language
            )
            tests.extend(e2e_tests)
        
        # 优先级排序和去重
        return self._prioritize_and_deduplicate_tests(tests)
    
    def _generate_function_tests(self, func_name: str, content: str, 
                            file_path: str, language: str) -> List[GeneratedTest]:
        """为单个函数生成测试用例"""
        tests = []
        
        # 解析函数信息
        func_info = self.parser.parse_function_info(content, func_name, language)
        if not func_info:
            logger.warning(f"无法解析函数 {func_name}")
            return []
        
        # 生成测试场景
        scenarios = self.data_generator.generate_test_scenarios(func_info)
        
        # 为每个场景生成测试代码
        for scenario in scenarios:
            test_code = self.code_generator.generate_test_code(func_info, scenario, file_path)
            
            test = GeneratedTest(
                name=f"test_{self._sanitize_name(scenario.name)}",
                test_type=scenario.test_type.value,
                priority=scenario.priority.value,
                target_function=func_name,
                scenario=scenario.description,
                test_code=test_code,
                language=language,
                framework=self._get_test_framework(language),
                dependencies=self._extract_dependencies(content, language)
            )
            tests.append(test)
        
        return tests
    
    def _generate_integration_tests(self, change: Dict, impacts: List[str], 
                               language: str) -> List[GeneratedTest]:
        """生成集成测试"""
        tests = []
        
        for impact in impacts[:3]:  # 限制为前3个影响
            test_code = self._generate_integration_test_code(change, impact, language)
            
            test = GeneratedTest(
                name=f"integration_test_{self._sanitize_name(change.get('file_path', ''))}_{self._sanitize_name(impact)}",
                test_type=TestType.INTEGRATION.value,
                priority=Priority.MEDIUM.value,
                target_function=", ".join(change.get('affected_functions', [])),
                scenario=f"测试 {change.get('file_path', '')} 与 {impact} 的集成",
                test_code=test_code,
                language=language,
                framework=self._get_test_framework(language),
                dependencies=[]
            )
            tests.append(test)
        
        return tests
    
    def _generate_performance_tests(self, change: Dict, language: str) -> List[GeneratedTest]:
        """生成性能测试"""
        file_path = change.get('file_path', '')
        affected_functions = change.get('affected_functions', [])
        
        if not affected_functions:
            return []
        
        test_code = self._generate_performance_test_code(change, language)
        
        test = GeneratedTest(
            name=f"performance_test_{self._sanitize_name(file_path)}",
            test_type=TestType.PERFORMANCE.value,
            priority=Priority.LOW.value,
            target_function=", ".join(affected_functions),
            scenario=f"测试 {file_path} 中函数的性能",
            test_code=test_code,
            language=language,
            framework=self._get_performance_framework(language),
            dependencies=self._get_performance_dependencies(language)
        )
        
        return [test]
    
    def _generate_security_tests(self, change: Dict, language: str) -> List[GeneratedTest]:
        """生成安全测试"""
        file_path = change.get('file_path', '')
        affected_functions = change.get('affected_functions', [])
        
        if not affected_functions:
            return []
        
        test_code = self._generate_security_test_code(change, language)
        
        test = GeneratedTest(
            name=f"security_test_{self._sanitize_name(file_path)}",
            test_type=TestType.SECURITY.value,
            priority=Priority.HIGH.value,
            target_function=", ".join(affected_functions),
            scenario=f"测试 {file_path} 中函数的安全性",
            test_code=test_code,
            language=language,
            framework=self._get_test_framework(language),
            dependencies=self._get_security_dependencies(language)
        )
        
        return [test]
    
    def _generate_e2e_tests(self, change: Dict, language: str) -> List[GeneratedTest]:
        """生成端到端测试"""
        file_path = change.get('file_path', '')
        business_impacts = change.get('business_impact', [])
        
        if not business_impacts:
            return []
        
        tests = []
        for i, impact in enumerate(business_impacts[:2]):  # 限制为前2个业务影响
            test_code = self._generate_e2e_test_code(change, impact, language)
            
            test = GeneratedTest(
                name=f"e2e_test_{self._sanitize_name(file_path)}_{i+1}",
                test_type=TestType.E2E.value,
                priority=Priority.MEDIUM.value,
                target_function="",  # 端到端测试不针对特定函数
                scenario=f"测试业务流程: {impact}",
                test_code=test_code,
                language=language,
                framework=self._get_e2e_framework(language),
                dependencies=self._get_e2e_dependencies(language)
            )
            tests.append(test)
        
        return tests
    
    # 其他辅助方法的实现
    def _involves_security(self, change: Dict) -> bool:
        """判断变更是否涉及安全敏感操作"""
        security_keywords = [
            'password', 'auth', 'token', 'secret', 'crypt', 'hash', 'security', 
            'permission', 'access', 'login', 'user', 'admin', 'role', 'privilege',
            'oauth', 'jwt', 'cert', 'ssl', 'tls', 'https', 'encrypt', 'decrypt'
        ]
        
        # 检查文件路径
        file_path = change.get('file_path', '').lower()
        if any(keyword in file_path for keyword in security_keywords):
            return True
        
        # 检查函数名
        for func in change.get('affected_functions', []):
            if any(keyword in func.lower() for keyword in security_keywords):
                return True
        
        return False
    
    def _prioritize_and_deduplicate_tests(self, tests: List[GeneratedTest]) -> List[GeneratedTest]:
        """优先级排序和去重"""
        # 按优先级排序
        sorted_tests = sorted(tests, key=lambda t: t.priority, reverse=True)
        
        # 去重 (基于测试名称)
        unique_tests = []
        test_names = set()
        
        for test in sorted_tests:
            if test.name not in test_names:
                unique_tests.append(test)
                test_names.add(test.name)
        
        return unique_tests
    
    def _sanitize_name(self, name: str) -> str:
        """净化名称，使其适合作为测试函数名"""
        # 替换非字母数字字符为下划线
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # 确保不以数字开头
        if sanitized and sanitized[0].isdigit():
            sanitized = 'test_' + sanitized
        # 避免名称过长
        if len(sanitized) > 40:
            sanitized = sanitized[:40]
        return sanitized
    
    # 框架和依赖相关方法
    def _get_test_framework(self, language: str) -> str:
        """获取测试框架名称"""
        frameworks = {
            'python': 'pytest',
            'javascript': 'jest',
            'typescript': 'jest',
            'java': 'junit5',
            'go': 'go test',
            'rust': 'cargo test',
            'csharp': 'xunit',
            'php': 'phpunit',
            'ruby': 'rspec'
        }
        return frameworks.get(language, 'generic')
    
    def _get_performance_framework(self, language: str) -> str:
        """获取性能测试框架"""
        frameworks = {
            'python': 'pytest-benchmark',
            'javascript': 'benchmark.js',
            'typescript': 'benchmark.js',
            'java': 'JMH',
            'go': 'testing.B',
            'rust': 'criterion',
            'csharp': 'BenchmarkDotNet',
            'php': 'PHPBench',
            'ruby': 'benchmark-ips'
        }
        return frameworks.get(language, 'generic')
    
    def _get_e2e_framework(self, language: str) -> str:
        """获取端到端测试框架"""
        frameworks = {
            'python': 'pytest + selenium',
            'javascript': 'cypress',
            'typescript': 'cypress',
            'java': 'selenium',
            'go': 'godog',
            'rust': 'cucumber-rs',
            'csharp': 'SpecFlow',
            'php': 'Behat',
            'ruby': 'Cucumber'
        }
        return frameworks.get(language, 'generic')
    
    def _get_performance_dependencies(self, language: str) -> List[str]:
        """获取性能测试依赖"""
        dependencies = {
            'python': ['pytest-benchmark'],
            'javascript': ['benchmark'],
            'typescript': ['benchmark', '@types/benchmark'],
            'java': ['org.openjdk.jmh:jmh-core', 'org.openjdk.jmh:jmh-generator-annprocess'],
            'go': [],  # Go内置了性能测试支持
            'rust': ['criterion'],
            'csharp': ['BenchmarkDotNet'],
            'php': ['phpbench/phpbench'],
            'ruby': ['benchmark-ips']
        }
        return dependencies.get(language, [])
    
    def _get_security_dependencies(self, language: str) -> List[str]:
        """获取安全测试依赖"""
        dependencies = {
            'python': ['pytest-security', 'bandit'],
            'javascript': ['jest', 'eslint-plugin-security'],
            'typescript': ['jest', 'eslint-plugin-security', '@types/jest'],
            'java': ['org.owasp:dependency-check-maven', 'com.github.spotbugs:spotbugs'],
            'go': ['github.com/securego/gosec/v2/cmd/gosec'],
            'rust': ['cargo-audit'],
            'csharp': ['SecurityCodeScan.VS2019'],
            'php': ['roave/security-advisories'],
            'ruby': ['bundler-audit']
        }
        return dependencies.get(language, [])
    
    def _get_e2e_dependencies(self, language: str) -> List[str]:
        """获取端到端测试依赖"""
        dependencies = {
            'python': ['pytest', 'selenium', 'webdriver-manager'],
            'javascript': ['cypress', '@cypress/code-coverage'],
            'typescript': ['cypress', '@cypress/code-coverage', '@types/cypress'],
            'java': ['org.seleniumhq.selenium:selenium-java', 'io.cucumber:cucumber-java'],
            'go': ['github.com/cucumber/godog'],
            'rust': ['cucumber_rust'],
            'csharp': ['SpecFlow', 'SpecFlow.Tools.MsBuild.Generation', 'SpecFlow.xUnit'],
            'php': ['behat/behat', 'behat/mink-extension'],
            'ruby': ['cucumber', 'capybara', 'selenium-webdriver']
        }
        return dependencies.get(language, [])
    
    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """从代码内容中提取依赖"""
        if not content:
            return []
            
        dependencies = []
        
        if language == 'python':
            # 提取Python导入
            import re
            import_patterns = [
                r'import\s+([\w.]+)',
                r'from\s+([\w.]+)\s+import'
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend([m.split('.')[0] for m in matches if m])
                
        elif language in ['javascript', 'typescript']:
            # 提取JS/TS导入
            import re
            import_patterns = [
                r'import.*?from\s+[\'"]([^\'".]+)[\'"]',
                r'require\s*\(\s*[\'"]([^\'".]+)[\'"]\s*\)'
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend([m.split('/')[0] for m in matches if m and not m.startswith('.')])
        
        # 去重
        return list(set(dependencies))
    
    # 测试代码生成方法
    def _generate_integration_test_code(self, change: Dict, impact: str, language: str) -> str:
        """生成集成测试代码"""
        # 这里简化实现，实际应根据语言生成更详细的测试代码
        if language == 'python':
            return f"""
import pytest
from unittest.mock import patch, MagicMock

def test_integration_{self._sanitize_name(change.get('file_path', ''))}_{self._sanitize_name(impact)}():
    \"\"\"
    集成测试: 测试 {change.get('file_path', '')} 与 {impact} 的集成
    \"\"\"
    # 准备测试数据
    test_data = {{
        # 这里应该包含实际的测试数据
    }}
    
    # 模拟依赖
    with patch('{impact}') as mock_dependency:
        mock_dependency.return_value = MagicMock()
        
        # 调用被测函数
        # from module import function
        # result = function(test_data)
        
        # 验证结果
        # assert result is not None
        # assert mock_dependency.called
"""
        elif language in ['javascript', 'typescript']:
            return f"""
import {{ jest }} from '@jest/globals';

describe('Integration test for {change.get('file_path', '')} with {impact}', () => {{
  test('should correctly integrate with {impact}', async () => {{
    // 模拟依赖
    jest.mock('{impact}', () => {{
      return {{
        // 模拟方法和返回值
      }};
    }});
    
    // 导入被测函数
    // const {{ function }} = require('../path/to/module');
    
    // 准备测试数据
    const testData = {{
      // 这里应该包含实际的测试数据
    }};
    
    // 调用被测函数
    // const result = await function(testData);
    
    // 验证结果
    // expect(result).toBeDefined();
  }});
}});
"""
        else:
            # 对于其他语言，返回通用模板
            return f"// 集成测试: {change.get('file_path', '')} 与 {impact} 的集成\n// 请根据项目实际情况实现测试代码"
    
    def _generate_performance_test_code(self, change: Dict, language: str) -> str:
        """生成性能测试代码"""
        # 这里简化实现，实际应根据语言生成更详细的测试代码
        if language == 'python':
            return f"""
import pytest

def test_performance_{self._sanitize_name(change.get('file_path', ''))}(benchmark):
    \"\"\"
    性能测试: 测试 {change.get('file_path', '')} 中函数的性能
    \"\"\"
    # 准备测试数据
    test_data = {{
        # 这里应该包含实际的测试数据
    }}
    
    # 使用benchmark运行被测函数
    # from module import function
    # result = benchmark(function, test_data)
    
    # 验证结果
    # assert result is not None
    
    # 可以设置性能预期
    # assert benchmark.stats.stats.mean < 0.001  # 平均执行时间小于1毫秒
"""
        elif language in ['javascript', 'typescript']:
            return f"""
import Benchmark from 'benchmark';

describe('Performance test for {change.get('file_path', '')}', () => {{
  test('should perform efficiently', () => {{
    const suite = new Benchmark.Suite;
    
    // 准备测试数据
    const testData = {{
      // 这里应该包含实际的测试数据
    }};
    
    // 导入被测函数
    // const {{ function }} = require('../path/to/module');
    
    // 添加测试
    suite.add('测试函数性能', function() {{
      // function(testData);
    }})
    .on('cycle', function(event) {{
      console.log(String(event.target));
    }})
    .on('complete', function() {{
      console.log('Fastest is ' + this.filter('fastest').map('name'));
      // 验证性能符合预期
      expect(this[0].hz).toBeGreaterThan(100); // 每秒执行次数大于100
    }})
    .run({{ 'async': false }});
  }});
}});
"""
        else:
            # 对于其他语言，返回通用模板
            return f"// 性能测试: {change.get('file_path', '')}\n// 请根据项目实际情况实现测试代码"
    
    def _generate_security_test_code(self, change: Dict, language: str) -> str:
        """生成安全测试代码"""
        # 这里简化实现，实际应根据语言生成更详细的测试代码
        if language == 'python':
            return f"""
import pytest
import re
import subprocess

def test_security_{self._sanitize_name(change.get('file_path', ''))}():
    \"\"\"
    安全测试: 测试 {change.get('file_path', '')} 中函数的安全性
    \"\"\"
    # 使用bandit进行静态安全分析
    result = subprocess.run(['bandit', '-r', '{change.get('file_path', '')}'], 
                           capture_output=True, text=True)
    
    # 检查是否有高危安全问题
    high_severity_issues = re.findall(r'Issue: \\[High\\]', result.stdout)
    assert len(high_severity_issues) == 0, f"发现高危安全问题: {{result.stdout}}"
    
    # 针对特定安全问题的测试
    # from module import function
    # 测试SQL注入防护
    # malicious_input = "'; DROP TABLE users; --"
    # result = function(malicious_input)
    # assert result is None or not isinstance(result, list), "可能存在SQL注入漏洞"
    
    # 测试XSS防护
    # xss_input = "<script>alert('XSS')</script>"
    # result = function(xss_input)
    # assert "<script>" not in str(result), "可能存在XSS漏洞"
"""
        elif language in ['javascript', 'typescript']:
            return f"""
import {{ jest }} from '@jest/globals';
const { execSync } = require('child_process');

describe('Security test for {change.get('file_path', '')}', () => {{
  test('should not have security vulnerabilities', () => {{
    // 使用eslint-plugin-security进行静态安全分析
    try {{
      execSync('npx eslint --plugin security {change.get('file_path', '')}');
    }} catch (error) {{
      // 检查是否有安全问题
      const output = error.stdout.toString();
      const securityIssues = output.match(/security\\/[a-z-]+/g);
      expect(securityIssues).toBeNull();
    }}
    
    // 针对特定安全问题的测试
    // const {{ function }} = require('../path/to/module');
    
    // 测试SQL注入防护
    // const maliciousInput = "'; DROP TABLE users; --";
    // expect(() => function(maliciousInput)).not.toThrow();
    
    // 测试XSS防护
    // const xssInput = "<script>alert('XSS')</script>";
    // const result = function(xssInput);
    // expect(result).not.toMatch(/<script>/);
  }});
}});
"""
        else:
            # 对于其他语言，返回通用模板
            return f"// 安全测试: {change.get('file_path', '')}\n// 请根据项目实际情况实现测试代码"
    
    def _generate_e2e_test_code(self, change: Dict, business_area: str, language: str) -> str:
        """生成端到端测试代码"""
        # 这里简化实现，实际应根据语言生成更详细的测试代码
        if language == 'python':
            return f"""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture
def browser():
    \"\"\"设置浏览器\"\"\"
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    yield driver
    driver.quit()

def test_e2e_{self._sanitize_name(business_area)}(browser):
    \"\"\"
    端到端测试: {business_area}
    \"\"\"
    # 访问应用
    browser.get('http://localhost:3000')  # 替换为实际URL
    
    # 登录 (如需要)
    # browser.find_element(By.ID, 'username').send_keys('test_user')
    # browser.find_element(By.ID, 'password').send_keys('test_password')
    # browser.find_element(By.ID, 'login-button').click()
    
    # 执行业务流程
    # 例如: 创建新项目
    # browser.find_element(By.ID, 'new-project-button').click()
    # browser.find_element(By.ID, 'project-name').send_keys('Test Project')
    # browser.find_element(By.ID, 'create-button').click()
    
    # 验证结果
    # assert browser.find_element(By.ID, 'project-title').text == 'Test Project'
    # assert browser.find_element(By.CLASS_NAME, 'success-message').is_displayed()
"""
        elif language in ['javascript', 'typescript']:
            return f"""
// cypress/integration/e2e_{self._sanitize_name(business_area)}.spec.js
describe('E2E Test: {business_area}', () => {{
  beforeEach(() => {{
    // 访问应用
    cy.visit('/')
    
    // 登录 (如需要)
    // cy.get('#username').type('test_user')
    // cy.get('#password').type('test_password')
    // cy.get('#login-button').click()
  }})
  
  it('should complete the business process successfully', () => {{
    // 执行业务流程
    // 例如: 创建新项目
    // cy.get('#new-project-button').click()
    // cy.get('#project-name').type('Test Project')
    // cy.get('#create-button').click()
    
    // 验证结果
    // cy.get('#project-title').should('have.text', 'Test Project')
    // cy.get('.success-message').should('be.visible')
  }})
}})
"""
        else:
            # 对于其他语言，返回通用模板
            return f"// 端到端测试: {business_area}\n// 请根据项目实际情况实现测试代码" 