import logging
import re
import json
from typing import Dict, Optional


class AIServiceIntegrator:
    """AI服务集成器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化AI服务提供商"""
        ai_config = self.config.get('ai_integration', {})
        
        if ai_config.get('enabled', False):
            provider = ai_config.get('provider', 'openai')
            
            if provider == 'openai':
                self.providers['openai'] = self._setup_openai(ai_config)
            elif provider == 'anthropic':
                self.providers['anthropic'] = self._setup_anthropic(ai_config)
            elif provider == 'local':
                self.providers['local'] = self._setup_local_ai(ai_config)
            elif provider == 'azure':
                self.providers['azure'] = self._setup_azure_openai(ai_config)
            elif provider == 'google':
                self.providers['google'] = self._setup_google_ai(ai_config)
    
    def _setup_openai(self, config: Dict) -> Optional[Dict]:
        """设置OpenAI服务"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=config.get('api_key'),
                base_url=config.get('base_url', 'https://api.openai.com/v1')
            )
            
            return {
                'client': client,
                'model': config.get('model', 'gpt-3.5-turbo'),
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
        except ImportError:
            logging.warning("OpenAI库未安装，请运行：pip install openai")
            return None
    
    def _setup_anthropic(self, config: Dict) -> Optional[Dict]:
        """设置Anthropic Claude服务"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(
                api_key=config.get('api_key')
            )
            
            return {
                'client': client,
                'model': config.get('model', 'claude-3-sonnet-20240229'),
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
        except ImportError:
            logging.warning("Anthropic库未安装，请运行：pip install anthropic")
            return None
    
    def _setup_azure_openai(self, config: Dict) -> Optional[Dict]:
        """设置Azure OpenAI服务"""
        try:
            import openai
            
            client = openai.AzureOpenAI(
                api_key=config.get('api_key'),
                azure_endpoint=config.get('azure_endpoint'),
                api_version=config.get('api_version', '2024-02-01')
            )
            
            return {
                'client': client,
                'model': config.get('deployment_name', 'gpt-35-turbo'),
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
        except ImportError:
            logging.warning("OpenAI库未安装，请运行：pip install openai")
            return None
    
    def _setup_google_ai(self, config: Dict) -> Optional[Dict]:
        """设置Google AI服务"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=config.get('api_key'))
            model = genai.GenerativeModel(config.get('model', 'gemini-pro'))
            
            return {
                'client': model,
                'model': config.get('model', 'gemini-pro'),
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
        except ImportError:
            logging.warning("Google AI库未安装，请运行：pip install google-generativeai")
            return None
    
    def _setup_local_ai(self, config: Dict) -> Optional[Dict]:
        """设置本地AI服务"""
        try:
            import requests
            
            return {
                'base_url': config.get('base_url', 'http://localhost:11434'),
                'model': config.get('model', 'llama2'),
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
        except ImportError:
            logging.warning("requests库未安装")
            return None
    
    async def analyze_code_change(self, old_code: str, new_code: str, language: str = 'python') -> Optional[Dict]:
        """使用AI分析代码变更"""
        if not self.providers:
            return None
        
        provider_name = list(self.providers.keys())[0]
        provider = self.providers[provider_name]
        
        if not provider:
            return None
        
        prompt = self._create_analysis_prompt(old_code, new_code, language)
        
        try:
            if provider_name == 'openai':
                return await self._analyze_with_openai(provider, prompt)
            elif provider_name == 'anthropic':
                return await self._analyze_with_anthropic(provider, prompt)
            elif provider_name == 'azure':
                return await self._analyze_with_azure(provider, prompt)
            elif provider_name == 'google':
                return await self._analyze_with_google(provider, prompt)
            elif provider_name == 'local':
                return await self._analyze_with_local(provider, prompt)
        except Exception as e:
            logging.error(f"AI分析失败: {str(e)}")
            return None
    
    def _create_analysis_prompt(self, old_code: str, new_code: str, language: str) -> str:
        """创建分析提示词"""
        return f"""
请分析以下{language}代码变更，并以JSON格式返回分析结果：

旧代码：
```{language}
{old_code}
```

新代码：
```{language}
{new_code}
```

请提供以下分析：
1. change_type: 变更类型（new_feature, bug_fix, refactoring, optimization, breaking_change）
2. complexity_change: 复杂度变化（increased, decreased, unchanged）
3. risks: 潜在风险列表
4. business_impact: 业务影响描述
5. test_suggestions: 测试建议列表
6. review_points: 代码审查要点
7. performance_impact: 性能影响评估
8. security_considerations: 安全考虑

请只返回JSON格式的结果，不要包含其他文本。
"""
    
    async def _analyze_with_openai(self, provider: Dict, prompt: str) -> Dict:
        """使用OpenAI进行分析"""
        response = await provider['client'].chat.completions.acreate(
            model=provider['model'],
            messages=[
                {"role": "system", "content": "你是一个专业的代码分析专家，擅长分析代码变更的影响和风险。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=provider['max_tokens'],
            temperature=provider['temperature']
        )
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return None
    
    async def _analyze_with_anthropic(self, provider: Dict, prompt: str) -> Dict:
        """使用Anthropic Claude进行分析"""
        response = await provider['client'].messages.acreate(
            model=provider['model'],
            max_tokens=provider['max_tokens'],
            temperature=provider['temperature'],
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return None
    
    async def _analyze_with_local(self, provider: Dict, prompt: str) -> Dict:
        """使用本地AI服务进行分析"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{provider['base_url']}/api/generate",
                json={
                    "model": provider['model'],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": provider['temperature'],
                        "num_predict": provider['max_tokens']
                    }
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get('response', '')
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group(1))
                        return None
                return None
    
    async def generate_test_cases(self, function_code: str, language: str) -> Optional[str]:
        """使用AI生成测试用例"""
        if not self.providers:
            return None
        
        provider_name = list(self.providers.keys())[0]
        provider = self.providers[provider_name]
        
        if not provider:
            return None
        
        prompt = f"""
请为以下{language}函数生成完整的测试用例：

```{language}
{function_code}
```

要求：
1. 生成完整可运行的测试代码
2. 包含正常情况、边界条件、异常情况的测试
3. 使用合适的测试框架（Python用pytest，JavaScript用Jest等）
4. 添加必要的mock和断言
5. 包含测试数据准备和清理

请直接返回测试代码，不要包含解释文本。
"""
        
        try:
            if provider_name == 'openai':
                response = await provider['client'].chat.completions.acreate(
                    model=provider['model'],
                    messages=[
                        {"role": "system", "content": "你是一个专业的测试工程师，擅长编写高质量的自动化测试代码。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=provider['max_tokens'],
                    temperature=provider['temperature']
                )
                return response.choices[0].message.content
            
            elif provider_name == 'anthropic':
                response = await provider['client'].messages.acreate(
                    model=provider['model'],
                    max_tokens=provider['max_tokens'],
                    temperature=provider['temperature'],
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
        except Exception as e:
            logging.error(f"AI测试生成失败: {str(e)}")
            return None
    
    async def suggest_improvements(self, code: str, language: str) -> Optional[str]:
        """使用AI建议代码改进"""
        if not self.providers:
            return None
        
        provider_name = list(self.providers.keys())[0]
        provider = self.providers[provider_name]
        
        if not provider:
            return None
        
        prompt = f"""
请分析以下{language}代码并提供改进建议：

```{language}
{code}
```

请提供以下方面的建议：
1. 代码质量改进
2. 性能优化建议
3. 安全漏洞识别
4. 最佳实践建议
5. 可维护性改进
6. 错误处理改进

请以结构化的方式返回建议，包含具体的代码示例。
"""
        
        try:
            if provider_name == 'openai':
                response = await provider['client'].chat.completions.acreate(
                    model=provider['model'],
                    messages=[
                        {"role": "system", "content": "你是一个资深的代码架构师，擅长代码质量分析和改进建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=provider['max_tokens'],
                    temperature=provider['temperature']
                )
                return response.choices[0].message.content
            
            elif provider_name == 'anthropic':
                response = await provider['client'].messages.acreate(
                    model=provider['model'],
                    max_tokens=provider['max_tokens'],
                    temperature=provider['temperature'],
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
        except Exception as e:
            logging.error(f"AI改进建议失败: {str(e)}")
            return None 