#!/usr/bin/env python3
"""
增强的AI客户端 - 优化的Prompt设计
解决三个关键问题：
1. 功能测试用例生成（非单元测试）
2. 全局代码分析能力
3. 更专业准确的Prompt设计
"""

import os
import json
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class CodeContext:
    """代码上下文信息"""
    file_path: str
    function_name: str = ""
    class_name: str = ""
    module_dependencies: List[str] = None
    business_domain: str = ""
    api_endpoints: List[str] = None
    database_tables: List[str] = None

class EnhancedAIClient:
    """增强的AI客户端，专业的Prompt设计"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # AI配置
        self.provider = os.environ.get('AI_PROVIDER', 'qwen')
        self.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-f7c7af7a5ff14c1cb6a05d6f979a8c63')
        self.base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.model = os.environ.get('AI_MODEL', 'qwen-turbo-2025-04-28')
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    async def analyze_code_change_with_global_context(
        self, 
        old_code: str, 
        new_code: str, 
        global_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """基于全局上下文分析代码变更"""
        
        # 构建全局上下文信息
        context_prompt = self._build_global_context_prompt(global_context)
        
        system_prompt = """你是一个资深的软件架构师和代码审查专家，具备以下能力：
1. 深度理解软件系统架构和模块间依赖关系
2. 识别代码变更对整个系统的潜在影响
3. 评估业务风险和技术风险
4. 提供专业的测试策略建议

请基于提供的全局上下文信息，进行深度的代码变更分析。"""

        user_prompt = f"""请基于以下全局上下文信息，深度分析这个代码变更：

=== 全局系统上下文 ===
{context_prompt}

=== 代码变更详情 ===
旧代码:
```
{old_code}
```

新代码:
```
{new_code}
```

=== 分析要求 ===
请从以下维度进行专业分析：

1. **变更分类与影响范围**
   - 变更类型（功能增强/bug修复/重构/性能优化/安全修复）
   - 直接影响的模块和组件
   - 间接影响的系统部分
   - 对外部依赖的影响

2. **业务影响评估**
   - 对用户体验的影响
   - 对业务流程的影响
   - 对数据一致性的影响
   - 对系统可用性的影响

3. **技术风险评估**
   - 兼容性风险
   - 性能影响风险
   - 安全风险
   - 数据风险
   - 集成风险

4. **测试策略建议**
   - 必须的回归测试范围
   - 重点的集成测试场景
   - 性能测试建议
   - 安全测试建议

5. **部署风险控制**
   - 建议的部署策略
   - 监控重点
   - 回滚预案
   - 风险缓解措施

请以JSON格式返回分析结果，包含以下字段：
- change_classification: 变更分类
- impact_scope: 影响范围分析
- business_impact: 业务影响评估
- technical_risks: 技术风险列表
- testing_strategy: 测试策略建议
- deployment_recommendations: 部署建议
- confidence_score: 分析置信度(0-100)
- critical_attention_points: 需要特别关注的要点"""

        return await self._call_ai_api(system_prompt, user_prompt)

    async def generate_comprehensive_functional_tests(self, change_analysis: Dict, system_context: Dict = None) -> Dict:
        """生成全面的功能测试用例"""
        try:
            self.logger.info("🚀 开始生成AI功能测试用例")
            
            # 提取项目信息
            project_path = change_analysis.get('project_path', '')
            project_name = change_analysis.get('project_name', 'Unknown Project')
            project_id = change_analysis.get('project_id', 0)
            
            self.logger.info(f"📋 项目信息 - 名称: {project_name}, 路径: {project_path}, ID: {project_id}")
            
            # 分析项目代码结构和业务逻辑
            self.logger.info("🔍 开始分析项目代码结构...")
            code_analysis = await self._analyze_project_code_structure(project_path)
            self.logger.info(f"📊 代码分析完成 - API端点数: {len(code_analysis.get('api_endpoints', []))}, 模型数: {len(code_analysis.get('database_models', []))}")
            
            business_domains = self._identify_business_domains(code_analysis)
            self.logger.info(f"🏢 识别到 {len(business_domains)} 个业务领域")
            
            # 构建增强的提示词
            prompt = f"""作为专业的软件测试专家，请基于以下项目信息生成具体的功能测试用例。

项目信息：
- 项目名称：{project_name}
- 项目类型：{system_context.get('project_type', 'web_application') if system_context else 'web_application'}
- 技术栈：{', '.join(system_context.get('tech_stack', ['python', 'javascript']) if system_context else ['python', 'javascript'])}

代码结构分析：
{self._format_code_analysis(code_analysis)}

业务领域识别：
{self._format_business_domains(business_domains)}

请生成4个具体的功能测试用例，要求：
1. 每个测试用例必须针对具体的功能模块或业务场景
2. 测试步骤要详细、可执行
3. 包含具体的输入数据和预期输出
4. 覆盖核心业务流程和边界条件
5. 包含用户角色和权限相关的测试

返回格式为JSON：
{{
  "test_plan": [
    {{
      "test_case_name": "具体功能模块 - 详细测试场景",
      "test_type": "functional",
      "business_scenario": "详细的业务场景描述，包含具体的用户操作和业务目标",
      "target_module": "具体的代码模块或功能组件",
      "user_role": "admin|user|guest",
      "test_steps": [
        "1. 具体的操作步骤，包含输入数据",
        "2. 验证中间状态和响应",
        "3. 检查最终结果和副作用"
      ],
      "test_data": {{
        "input": "具体的输入数据示例",
        "expected_output": "预期的输出结果"
      }},
      "expected_result": "详细的预期结果",
      "priority": "high|medium|low",
      "estimated_time": 30,
      "preconditions": "具体的前置条件",
      "affected_components": ["具体的组件或模块列表"],
      "risk_factors": ["潜在的风险点"]
    }}
  ]
}}"""

            self.logger.info("📤 发送AI请求...")
            self.logger.debug(f"🔍 AI提示词长度: {len(prompt)} 字符")
            self.logger.debug(f"🔍 AI提示词内容预览: {prompt[:500]}...")
            
            # 调用AI模型
            response = await self._call_ai_model(prompt)
            
            self.logger.info(f"📥 AI响应接收完成")
            self.logger.debug(f"🔍 AI响应类型: {type(response)}")
            
            if response and isinstance(response, dict):
                self.logger.info("✅ AI响应格式正确，开始处理...")
                self.logger.debug(f"🔍 AI响应键: {list(response.keys())}")
                
                # 增强生成的测试用例
                if 'test_plan' in response:
                    self.logger.info(f"📋 找到测试计划，包含 {len(response['test_plan'])} 个测试用例")
                    enhanced_tests = []
                    for i, test_case in enumerate(response['test_plan']):
                        self.logger.info(f"🔧 增强第 {i+1} 个测试用例: {test_case.get('test_case_name', 'unnamed')}")
                        enhanced_test = self._enhance_test_case_with_context(
                            test_case, 
                            code_analysis, 
                            business_domains,
                            project_name
                        )
                        enhanced_tests.append(enhanced_test)
                    
                    result = {
                        'test_plan': enhanced_tests,
                        'generation_metadata': {
                            'project_analysis': code_analysis,
                            'business_domains': business_domains,
                            'generation_time': datetime.now().isoformat(),
                            'ai_model': self.model,
                            'context_used': True
                        }
                    }
                    
                    self.logger.info(f"✅ AI测试用例生成成功，返回 {len(enhanced_tests)} 个增强测试用例")
                    return result
                else:
                    self.logger.warning("⚠️ AI响应中未找到 'test_plan' 键，返回原始响应")
                    self.logger.debug(f"🔍 AI响应内容: {response}")
                    return response
            else:
                self.logger.warning(f"⚠️ AI响应格式异常: {type(response)}, 使用基于代码分析的回退方案")
                # 回退到基于代码分析的测试生成
                return self._generate_context_based_tests(code_analysis, business_domains, project_name)
                
        except Exception as e:
            self.logger.error(f"❌ 生成功能测试用例失败: {e}")
            import traceback
            self.logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            # 返回基于代码分析的回退测试用例
            return self._generate_fallback_tests_with_context(change_analysis, system_context)
    
    async def _analyze_project_code_structure(self, project_path: str) -> Dict:
        """分析项目代码结构"""
        analysis = {
            'api_endpoints': [],
            'database_models': [],
            'frontend_components': [],
            'business_logic': [],
            'authentication': [],
            'data_processing': [],
            'file_structure': {}
        }
        
        try:
            # 如果是Git URL，先克隆到临时目录
            if project_path.startswith(('http', 'git')):
                import tempfile
                import subprocess
                temp_dir = tempfile.mkdtemp()
                try:
                    subprocess.run(['git', 'clone', project_path, temp_dir], 
                                 capture_output=True, check=True)
                    actual_path = temp_dir
                except:
                    return analysis
            else:
                actual_path = project_path
            
            import os
            if not os.path.exists(actual_path):
                return analysis
            
            # 分析文件结构
            for root, dirs, files in os.walk(actual_path):
                # 跳过常见的非代码目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, actual_path)
                    
                    # 分析API端点
                    if 'api' in rel_path.lower() or 'route' in rel_path.lower():
                        endpoints = self._extract_api_endpoints(file_path)
                        analysis['api_endpoints'].extend(endpoints)
                    
                    # 分析数据模型
                    if 'model' in rel_path.lower() or 'schema' in rel_path.lower():
                        models = self._extract_data_models(file_path)
                        analysis['database_models'].extend(models)
                    
                    # 分析前端组件
                    if file.endswith(('.vue', '.jsx', '.tsx', '.component.js')):
                        components = self._extract_frontend_components(file_path)
                        analysis['frontend_components'].extend(components)
                    
                    # 分析业务逻辑
                    if any(keyword in rel_path.lower() for keyword in ['service', 'business', 'logic', 'manager']):
                        logic = self._extract_business_logic(file_path)
                        analysis['business_logic'].extend(logic)
                    
                    # 分析认证相关
                    if any(keyword in rel_path.lower() for keyword in ['auth', 'login', 'user', 'permission']):
                        auth = self._extract_auth_logic(file_path)
                        analysis['authentication'].extend(auth)
        
        except Exception as e:
            self.logger.warning(f"代码结构分析失败: {e}")
        
        return analysis
    
    def _extract_api_endpoints(self, file_path: str) -> List[Dict]:
        """提取API端点信息"""
        endpoints = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            # 匹配Flask路由
            flask_routes = re.findall(r"@\w+\.route\(['\"]([^'\"]+)['\"].*?methods=\[([^\]]+)\]", content)
            for route, methods in flask_routes:
                endpoints.append({
                    'path': route,
                    'methods': methods.replace("'", "").replace('"', '').split(','),
                    'file': file_path,
                    'type': 'flask_route'
                })
            
            # 匹配函数定义
            functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\):', content)
            for func in functions:
                if any(keyword in func.lower() for keyword in ['create', 'update', 'delete', 'get', 'post', 'login', 'register']):
                    endpoints.append({
                        'function': func,
                        'file': file_path,
                        'type': 'api_function'
                    })
        
        except Exception:
            pass
        
        return endpoints
    
    def _extract_data_models(self, file_path: str) -> List[Dict]:
        """提取数据模型信息"""
        models = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            # 匹配类定义
            classes = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]', content)
            for cls in classes:
                if not cls.lower().endswith('test'):
                    models.append({
                        'name': cls,
                        'file': file_path,
                        'type': 'data_model'
                    })
        
        except Exception:
            pass
        
        return models
    
    def _extract_frontend_components(self, file_path: str) -> List[Dict]:
        """提取前端组件信息"""
        components = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import os
            component_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 分析Vue组件
            if file_path.endswith('.vue'):
                components.append({
                    'name': component_name,
                    'file': file_path,
                    'type': 'vue_component',
                    'has_form': 'form' in content.lower(),
                    'has_table': 'table' in content.lower(),
                    'has_modal': 'modal' in content.lower()
                })
        
        except Exception:
            pass
        
        return components
    
    def _extract_business_logic(self, file_path: str) -> List[Dict]:
        """提取业务逻辑信息"""
        logic = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\):', content)
            for func in functions:
                if any(keyword in func.lower() for keyword in ['process', 'calculate', 'validate', 'generate', 'analyze']):
                    logic.append({
                        'function': func,
                        'file': file_path,
                        'type': 'business_logic'
                    })
        
        except Exception:
            pass
        
        return logic
    
    def _extract_auth_logic(self, file_path: str) -> List[Dict]:
        """提取认证逻辑信息"""
        auth = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\):', content)
            for func in functions:
                if any(keyword in func.lower() for keyword in ['login', 'logout', 'auth', 'verify', 'permission', 'role']):
                    auth.append({
                        'function': func,
                        'file': file_path,
                        'type': 'authentication'
                    })
        
        except Exception:
            pass
        
        return auth
    
    def _identify_business_domains(self, code_analysis: Dict) -> List[Dict]:
        """识别业务领域"""
        domains = []
        
        # 基于API端点识别业务域
        api_patterns = {
            'user_management': ['user', 'profile', 'account', 'register', 'login'],
            'content_management': ['post', 'article', 'content', 'media'],
            'data_analysis': ['analyze', 'report', 'statistics', 'dashboard'],
            'file_management': ['upload', 'download', 'file', 'document'],
            'notification': ['notify', 'message', 'email', 'alert'],
            'payment': ['payment', 'order', 'billing', 'invoice'],
            'admin': ['admin', 'manage', 'config', 'setting']
        }
        
        for domain, keywords in api_patterns.items():
            domain_functions = []
            
            # 检查API端点
            for endpoint in code_analysis.get('api_endpoints', []):
                if any(keyword in str(endpoint).lower() for keyword in keywords):
                    domain_functions.append(endpoint)
            
            # 检查业务逻辑
            for logic in code_analysis.get('business_logic', []):
                if any(keyword in str(logic).lower() for keyword in keywords):
                    domain_functions.append(logic)
            
            if domain_functions:
                domains.append({
                    'domain': domain,
                    'functions': domain_functions,
                    'complexity': len(domain_functions)
                })
        
        return domains
    
    def _format_code_analysis(self, analysis: Dict) -> str:
        """格式化代码分析结果"""
        formatted = []
        
        if analysis.get('api_endpoints'):
            formatted.append(f"API端点: {len(analysis['api_endpoints'])}个")
            for endpoint in analysis['api_endpoints'][:3]:
                formatted.append(f"  - {endpoint.get('path', endpoint.get('function', 'Unknown'))}")
        
        if analysis.get('database_models'):
            formatted.append(f"数据模型: {len(analysis['database_models'])}个")
            for model in analysis['database_models'][:3]:
                formatted.append(f"  - {model.get('name', 'Unknown')}")
        
        if analysis.get('frontend_components'):
            formatted.append(f"前端组件: {len(analysis['frontend_components'])}个")
            for comp in analysis['frontend_components'][:3]:
                formatted.append(f"  - {comp.get('name', 'Unknown')}")
        
        return '\n'.join(formatted) if formatted else "代码结构分析未发现明显模式"
    
    def _format_business_domains(self, domains: List[Dict]) -> str:
        """格式化业务领域"""
        if not domains:
            return "未识别出明确的业务领域"
        
        formatted = []
        for domain in domains:
            formatted.append(f"- {domain['domain']}: {domain['complexity']}个相关功能")
        
        return '\n'.join(formatted)
    
    def _enhance_test_case_with_context(self, test_case: Dict, code_analysis: Dict, 
                                      business_domains: List[Dict], project_name: str) -> Dict:
        """基于上下文增强测试用例"""
        # 添加具体的测试数据
        if 'test_data' not in test_case or not test_case['test_data']:
            test_case['test_data'] = self._generate_realistic_test_data(test_case, code_analysis)
        
        # 添加相关组件
        if 'affected_components' not in test_case:
            test_case['affected_components'] = self._identify_affected_components(test_case, code_analysis)
        
        # 添加风险因素
        if 'risk_factors' not in test_case:
            test_case['risk_factors'] = self._identify_risk_factors(test_case, business_domains)
        
        # 添加验证点
        if 'validation_points' not in test_case:
            test_case['validation_points'] = self._generate_validation_points(test_case)
        
        return test_case
    
    def _generate_realistic_test_data(self, test_case: Dict, code_analysis: Dict) -> Dict:
        """生成真实的测试数据"""
        test_type = test_case.get('test_type', 'functional')
        target_module = test_case.get('target_module', '')
        
        # 基于模块类型生成相应的测试数据
        if 'user' in target_module.lower() or 'auth' in target_module.lower():
            return {
                'input': {
                    'username': 'test_user_001',
                    'password': 'SecurePass123!',
                    'email': 'test@example.com'
                },
                'expected_output': {
                    'status': 'success',
                    'user_id': 'generated_id',
                    'token': 'jwt_token_string'
                },
                'boundary_conditions': {
                    'empty_username': '',
                    'invalid_email': 'invalid-email',
                    'weak_password': '123'
                }
            }
        elif 'data' in target_module.lower() or 'process' in target_module.lower():
            return {
                'input': {
                    'data_file': 'sample_data.csv',
                    'parameters': {'threshold': 0.8, 'method': 'standard'}
                },
                'expected_output': {
                    'processed_records': 1000,
                    'success_rate': 0.95,
                    'output_file': 'processed_data.json'
                },
                'boundary_conditions': {
                    'empty_file': '',
                    'large_dataset': '10GB_file.csv',
                    'invalid_format': 'corrupted_data.txt'
                }
            }
        else:
            return {
                'input': 'standard_test_input',
                'expected_output': 'expected_result',
                'boundary_conditions': 'edge_case_data'
            }
    
    def _identify_affected_components(self, test_case: Dict, code_analysis: Dict) -> List[str]:
        """识别受影响的组件"""
        components = []
        target_module = test_case.get('target_module', '').lower()
        
        # 基于目标模块识别相关组件
        if 'api' in target_module:
            components.extend(['API接口', '数据验证', '错误处理'])
        if 'user' in target_module:
            components.extend(['用户管理', '权限控制', '会话管理'])
        if 'data' in target_module:
            components.extend(['数据处理', '数据存储', '数据验证'])
        if 'frontend' in target_module or 'ui' in target_module:
            components.extend(['用户界面', '交互逻辑', '状态管理'])
        
        return list(set(components)) if components else ['核心功能模块']
    
    def _identify_risk_factors(self, test_case: Dict, business_domains: List[Dict]) -> List[str]:
        """识别风险因素"""
        risks = []
        test_type = test_case.get('test_type', '')
        target_module = test_case.get('target_module', '').lower()
        
        # 基于测试类型和目标模块识别风险
        if 'auth' in target_module:
            risks.extend(['安全漏洞', '权限绕过', '会话劫持'])
        if 'data' in target_module:
            risks.extend(['数据丢失', '数据泄露', '性能问题'])
        if 'payment' in target_module:
            risks.extend(['交易安全', '数据一致性', '合规问题'])
        if test_type == 'integration':
            risks.extend(['接口兼容性', '数据同步问题'])
        if test_type == 'e2e':
            risks.extend(['用户体验影响', '业务流程中断'])
        
        return risks if risks else ['功能异常', '性能下降']
    
    def _generate_validation_points(self, test_case: Dict) -> List[str]:
        """生成验证点"""
        points = []
        test_type = test_case.get('test_type', '')
        target_module = test_case.get('target_module', '').lower()
        
        # 基本验证点
        points.extend(['功能正确性', '输入验证', '输出格式'])
        
        # 特定验证点
        if 'auth' in target_module:
            points.extend(['权限检查', '令牌有效性', '登录状态'])
        if 'data' in target_module:
            points.extend(['数据完整性', '处理准确性', '存储一致性'])
        if test_type == 'e2e':
            points.extend(['用户流程完整性', '界面响应性'])
        
        return points
    
    def _generate_context_based_tests(self, code_analysis: Dict, business_domains: List[Dict], project_name: str) -> Dict:
        """基于上下文生成测试用例"""
        tests = []
        
        # 为每个业务域生成测试用例
        for domain in business_domains[:5]:  # 限制为前5个域
            domain_name = domain['domain']
            functions = domain['functions']
            
            test_case = {
                'test_case_name': f'{project_name} - {domain_name.replace("_", " ").title()}功能验证',
                'test_type': 'functional',
                'business_scenario': f'验证{domain_name.replace("_", " ")}相关功能的完整性和正确性',
                'target_module': domain_name,
                'user_role': self._determine_user_role(domain_name),
                'test_steps': self._generate_domain_test_steps(domain_name, functions),
                'test_data': self._generate_realistic_test_data({'target_module': domain_name}, code_analysis),
                'expected_result': f'{domain_name.replace("_", " ")}功能应正常工作，满足业务需求',
                'priority': 'high' if domain['complexity'] > 3 else 'medium',
                'estimated_time': min(30 + domain['complexity'] * 5, 60),
                'preconditions': f'{domain_name.replace("_", " ")}模块已正确配置',
                'affected_components': [domain_name.replace("_", " ").title()],
                'risk_factors': self._identify_risk_factors({'target_module': domain_name}, business_domains),
                'validation_points': self._generate_validation_points({'target_module': domain_name})
            }
            
            tests.append(test_case)
        
        return {'test_plan': tests}
    
    def _determine_user_role(self, domain_name: str) -> str:
        """确定用户角色"""
        if 'admin' in domain_name:
            return 'admin'
        elif 'user' in domain_name:
            return 'user'
        elif 'payment' in domain_name:
            return 'customer'
        else:
            return 'user'
    
    def _generate_domain_test_steps(self, domain_name: str, functions: List[Dict]) -> List[str]:
        """为业务域生成测试步骤"""
        steps = [
            f'1. 准备{domain_name.replace("_", " ")}测试环境和数据',
            f'2. 执行{domain_name.replace("_", " ")}核心功能操作'
        ]
        
        # 基于功能添加具体步骤
        if functions:
            for i, func in enumerate(functions[:3], 3):
                func_name = func.get('function', func.get('path', 'Unknown'))
                steps.append(f'{i}. 测试{func_name}功能的正确性')
        
        steps.extend([
            f'{len(steps)+1}. 验证{domain_name.replace("_", " ")}输出结果',
            f'{len(steps)+2}. 检查系统状态和副作用'
        ])
        
        return steps
    
    def _generate_fallback_tests_with_context(self, change_analysis: Dict, system_context: Dict) -> Dict:
        """生成基于上下文的回退测试用例"""
        project_name = change_analysis.get('project_name', 'Unknown Project')
        
        return {
            'test_plan': [
                {
                    'test_case_name': f'{project_name} - 用户认证与权限管理验证',
                    'test_type': 'functional',
                    'business_scenario': '验证用户登录、注册、权限控制等认证相关功能的完整性',
                    'target_module': 'authentication',
                    'user_role': 'user',
                    'test_steps': [
                        '1. 使用有效凭据进行用户登录',
                        '2. 验证登录后的权限分配',
                        '3. 测试无效凭据的错误处理',
                        '4. 验证会话管理和超时机制',
                        '5. 测试权限边界和访问控制'
                    ],
                    'test_data': {
                        'input': {'username': 'test_user', 'password': 'SecurePass123!'},
                        'expected_output': {'status': 'success', 'token': 'valid_jwt_token'},
                        'boundary_conditions': {'invalid_password': 'wrong_pass', 'empty_username': ''}
                    },
                    'expected_result': '用户应能成功登录并获得相应权限，无效操作应被正确阻止',
                    'priority': 'high',
                    'estimated_time': 25,
                    'preconditions': '用户账户已创建，认证服务正常运行',
                    'affected_components': ['用户管理', '权限控制', '会话管理'],
                    'risk_factors': ['安全漏洞', '权限绕过', '会话劫持'],
                    'validation_points': ['登录成功率', '权限准确性', '错误处理']
                },
                {
                    'test_case_name': f'{project_name} - 数据处理与存储完整性验证',
                    'test_type': 'integration',
                    'business_scenario': '验证数据输入、处理、存储和检索的完整流程',
                    'target_module': 'data_processing',
                    'user_role': 'user',
                    'test_steps': [
                        '1. 准备多种格式的测试数据',
                        '2. 执行数据导入和验证流程',
                        '3. 验证数据处理逻辑的正确性',
                        '4. 检查数据存储的完整性',
                        '5. 测试数据检索和导出功能'
                    ],
                    'test_data': {
                        'input': {'data_file': 'test_data.csv', 'format': 'CSV'},
                        'expected_output': {'processed_records': 1000, 'success_rate': 0.95},
                        'boundary_conditions': {'large_file': '10MB_data.csv', 'empty_file': 'empty.csv'}
                    },
                    'expected_result': '数据应被正确处理和存储，保持完整性和一致性',
                    'priority': 'high',
                    'estimated_time': 35,
                    'preconditions': '数据库连接正常，存储空间充足',
                    'affected_components': ['数据处理', '数据存储', '数据验证'],
                    'risk_factors': ['数据丢失', '数据损坏', '性能问题'],
                    'validation_points': ['数据完整性', '处理准确性', '存储一致性']
                },
                {
                    'test_case_name': f'{project_name} - 用户界面交互与响应验证',
                    'test_type': 'e2e',
                    'business_scenario': '验证用户界面的交互功能和用户体验',
                    'target_module': 'frontend_ui',
                    'user_role': 'user',
                    'test_steps': [
                        '1. 加载主要用户界面页面',
                        '2. 测试表单输入和验证',
                        '3. 验证按钮和链接的响应性',
                        '4. 检查数据展示和更新',
                        '5. 测试错误提示和用户反馈'
                    ],
                    'test_data': {
                        'input': {'form_data': {'name': 'Test User', 'email': 'test@example.com'}},
                        'expected_output': {'ui_response': 'success', 'data_updated': True},
                        'boundary_conditions': {'invalid_email': 'invalid@', 'empty_form': {}}
                    },
                    'expected_result': '界面应响应流畅，提供清晰的用户反馈和错误提示',
                    'priority': 'medium',
                    'estimated_time': 20,
                    'preconditions': '前端应用已部署，浏览器环境正常',
                    'affected_components': ['用户界面', '交互逻辑', '状态管理'],
                    'risk_factors': ['用户体验问题', '界面错误', '响应延迟'],
                    'validation_points': ['界面加载速度', '交互响应性', '错误处理']
                }
            ]
        }

    def _build_global_context_prompt(self, global_context: Dict[str, Any]) -> str:
        """构建全局上下文提示"""
        context_parts = []
        
        if 'system_architecture' in global_context:
            arch = global_context['system_architecture']
            context_parts.append(f"系统架构: {arch.get('type', 'unknown')}")
            context_parts.append(f"主要组件: {', '.join(arch.get('components', []))}")
        
        if 'business_domain' in global_context:
            context_parts.append(f"业务领域: {global_context['business_domain']}")
        
        if 'api_endpoints' in global_context:
            endpoints = global_context['api_endpoints'][:5]  # 取前5个
            context_parts.append(f"相关API: {', '.join(endpoints)}")
        
        if 'database_schema' in global_context:
            tables = global_context['database_schema'][:5]  # 取前5个
            context_parts.append(f"相关数据表: {', '.join(tables)}")
        
        if 'dependencies' in global_context:
            deps = global_context['dependencies'][:10]  # 取前10个
            context_parts.append(f"系统依赖: {', '.join(deps)}")
        
        return '\n'.join(context_parts)

    def _extract_change_summary(self, change_analysis: Dict[str, Any]) -> str:
        """提取变更摘要"""
        summary_parts = []
        
        if 'code_changes' in change_analysis:
            changes = change_analysis['code_changes']
            summary_parts.append(f"变更文件数: {changes.get('total_files', 0)}")
            summary_parts.append(f"分析文件数: {changes.get('analyzed_files', 0)}")
        
        if 'change_impacts' in change_analysis:
            impacts = change_analysis['change_impacts']
            high_impacts = [i for i in impacts if i.get('impact_level') == 'high']
            medium_impacts = [i for i in impacts if i.get('impact_level') == 'medium']
            summary_parts.append(f"高影响变更: {len(high_impacts)}个")
            summary_parts.append(f"中影响变更: {len(medium_impacts)}个")
        
        return '\n'.join(summary_parts)

    def _extract_system_context(self, system_context: Dict[str, Any]) -> str:
        """提取系统上下文"""
        context_parts = []
        
        if 'project_type' in system_context:
            context_parts.append(f"项目类型: {system_context['project_type']}")
        
        if 'tech_stack' in system_context:
            stack = system_context['tech_stack']
            context_parts.append(f"技术栈: {', '.join(stack) if isinstance(stack, list) else stack}")
        
        if 'user_roles' in system_context:
            roles = system_context['user_roles']
            context_parts.append(f"用户角色: {', '.join(roles) if isinstance(roles, list) else roles}")
        
        return '\n'.join(context_parts)

    def _format_changes_for_analysis(self, changes: List[Dict[str, Any]]) -> str:
        """格式化变更信息用于分析"""
        change_lines = []
        for i, change in enumerate(changes[:5]):  # 限制前5个变更
            file_path = change.get('file_path', 'unknown')
            lines_added = change.get('lines_added', 0)
            lines_removed = change.get('lines_removed', 0)
            change_lines.append(f"{i+1}. {file_path}: +{lines_added} -{lines_removed}")
        
        return '\n'.join(change_lines)

    def _format_architecture_info(self, arch_info: Dict[str, Any]) -> str:
        """格式化架构信息"""
        arch_lines = []
        
        if 'layers' in arch_info:
            arch_lines.append(f"架构层次: {', '.join(arch_info['layers'])}")
        
        if 'patterns' in arch_info:
            arch_lines.append(f"设计模式: {', '.join(arch_info['patterns'])}")
        
        if 'principles' in arch_info:
            arch_lines.append(f"架构原则: {', '.join(arch_info['principles'])}")
        
        return '\n'.join(arch_lines)

    async def _call_ai_model(self, prompt: str) -> Optional[Dict]:
        """调用AI模型"""
        try:
            self.logger.info("🤖 开始调用AI模型")
            self.logger.debug(f"🔍 使用模型: {self.model}")
            self.logger.debug(f"🔍 API端点: {self.base_url}/chat/completions")
            
            # 构建请求数据
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            self.logger.debug(f"📤 请求数据大小: {len(str(data))} 字符")
            
            async with aiohttp.ClientSession() as session:
                self.logger.info("🌐 发送HTTP请求到AI服务...")
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    self.logger.info(f"📥 收到HTTP响应，状态码: {response.status}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        self.logger.info("✅ AI API调用成功")
                        self.logger.debug(f"🔍 响应数据结构: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}")
                        
                        # 提取AI生成的内容
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            content = response_data['choices'][0]['message']['content']
                            self.logger.info(f"📝 AI生成内容长度: {len(content)} 字符")
                            self.logger.debug(f"🔍 AI生成内容预览: {content[:200]}...")
                            
                            # 尝试解析JSON
                            try:
                                # 清理markdown代码块
                                if '```json' in content:
                                    content = content.split('```json')[1].split('```')[0].strip()
                                elif '```' in content:
                                    content = content.split('```')[1].split('```')[0].strip()
                                
                                import json
                                parsed_content = json.loads(content)
                                self.logger.info("✅ JSON解析成功")
                                self.logger.debug(f"🔍 解析后数据结构: {list(parsed_content.keys()) if isinstance(parsed_content, dict) else type(parsed_content)}")
                                
                                return parsed_content
                            except json.JSONDecodeError as e:
                                self.logger.error(f"❌ JSON解析失败: {e}")
                                self.logger.debug(f"🔍 原始内容: {content}")
                                
                                # 尝试修复常见的JSON格式问题
                                try:
                                    # 移除可能的前后缀
                                    content = content.strip()
                                    if content.startswith('```'):
                                        content = content[3:]
                                    if content.endswith('```'):
                                        content = content[:-3]
                                    
                                    # 再次尝试解析
                                    fixed_content = json.loads(content)
                                    self.logger.info("✅ JSON修复解析成功")
                                    return fixed_content
                                except:
                                    self.logger.error("❌ JSON修复解析也失败，返回空结果")
                                    return None
                        else:
                            self.logger.error("❌ AI响应中未找到choices字段")
                            self.logger.debug(f"🔍 响应数据: {response_data}")
                            return None
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ AI API调用失败，状态码: {response.status}")
                        self.logger.error(f"❌ 错误信息: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            self.logger.error("❌ AI API调用超时")
            return None
        except Exception as e:
            self.logger.error(f"❌ AI API调用异常: {e}")
            import traceback
            self.logger.error(f"❌ 异常堆栈: {traceback.format_exc()}")
            return None

    async def _call_ai_api(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """调用AI API的通用方法"""
        try:
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.3,
                'extra_body': {"enable_thinking": False}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/chat/completions',
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {'raw_response': content}
                        
        except Exception as e:
            self.logger.error(f'AI API调用失败: {str(e)}')
            return None 