import os
import logging
import json
import aiohttp
from typing import Optional, Dict, Any
from backend.utils.logging import get_logger

class AIClient:
    """AI API客户端，用于调用外部AI服务进行代码分析"""
    def __init__(self):
        self.logger = get_logger(__name__)
        self.api_key = os.environ.get('AI_API_KEY')
        self.base_url = os.environ.get('AI_API_BASE_URL', 'https://api.openai.com/v1')
        self.headers = {
            'Content-Type': 'application/json'
        }

        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        else:
            self.logger.warning('AI_API_KEY environment variable not set')

    async def analyze_code_change(self, old_code: str, new_code: str) -> Optional[Dict[str, Any]]:
        """分析代码变更并返回AI评估结果

        Args:
            old_code: 旧代码
            new_code: 新代码

        Returns:
            AI评估结果字典，包含变更类型、风险评估等
        """
        if not self.api_key:
            self.logger.error('API key not available, cannot call AI API')
            return None

        prompt = f"""Analyze the following code change and provide:
1. A classification of the change type (bug fix, feature addition, refactoring, etc.)
2. Potential risks introduced by this change
3. Suggested test cases to verify the change
4. A confidence score (0-100) for your analysis

Old code:
{old_code}

New code:
{new_code}

Provide your response as a JSON object with keys: change_type, risks, suggested_tests, confidence_score"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/chat/completions',
                    headers=self.headers,
                    json={
                        'model': 'gpt-3.5-turbo',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3
                    }
                ):
                    response.raise_for_status()
                    result = await response.json()
                    content = result['choices'][0]['message']['content']

            # 解析JSON响应
            return json.loads(content)

        except requests.exceptions.RequestException as e:
            self.logger.error(f'Error calling AI API: {str(e)}')
        except json.JSONDecodeError as e:
            self.logger.error(f'Error parsing AI response: {str(e)}')
            self.logger.debug(f'AI response content: {content}')
        except Exception as e:
            self.logger.error(f'Unexpected error in AI client: {str(e)}')

        return None

    async def generate_test_case(self, function_code: str) -> Optional[str]:
        """为给定函数生成测试用例

        Args:
            function_code: 函数代码

        Returns:
            生成的测试用例代码
        """
        if not self.api_key:
            self.logger.error('API key not available, cannot call AI API')
            return None

        prompt = f"""Generate a unit test case for the following function. Use pytest style.
Return only the test code without explanations or markdown formatting.

Function code:
{function_code}

Test case:"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/chat/completions',
                    headers=self.headers,
                    json={
                        'model': 'gpt-3.5-turbo',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.5
                    }
                ):
                    response.raise_for_status()
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f'Error calling AI API: {str(e)}')
        except Exception as e:
            self.logger.error(f'Unexpected error in AI client: {str(e)}')

        return None