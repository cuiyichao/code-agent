import os
import base64
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile
import shutil
import asyncio
import aiohttp
import json
from dataclasses import asdict

class GitHubClient:
    """GitHub API客户端 - 实现远程仓库分析"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        
        # API限制管理
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
        
        # 缓存管理
        self.cache_dir = Path.home() / ".cursor_analyzer_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        if not self.github_token:
            self.logger.warning("GitHub token未设置，API调用可能受限")
    
    def get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Cursor-Analyzer/1.0'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        return headers
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取仓库信息"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'name': data['name'],
                        'full_name': data['full_name'],
                        'description': data.get('description', ''),
                        'language': data.get('language'),
                        'languages_url': data['languages_url'],
                        'default_branch': data['default_branch'],
                        'size': data['size'],
                        'stargazers_count': data['stargazers_count'],
                        'forks_count': data['forks_count'],
                        'updated_at': data['updated_at']
                    }
                else:
                    self.logger.error(f"获取仓库信息失败: {response.status}")
                    return {}
    
    async def get_repository_tree(self, owner: str, repo: str, 
                                sha: str = 'HEAD', recursive: bool = True) -> List[Dict[str, Any]]:
        """获取仓库文件树"""
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{sha}"
        params = {'recursive': '1'} if recursive else {}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers(), params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('tree', [])
                else:
                    self.logger.error(f"获取文件树失败: {response.status}")
                    return []
    
    async def get_file_content(self, owner: str, repo: str, path: str, 
                             ref: str = 'HEAD') -> Optional[str]:
        """获取文件内容"""
        # 检查缓存
        cache_key = f"{owner}_{repo}_{path}_{ref}"
        cached_content = self._get_cached_content(cache_key)
        if cached_content:
            return cached_content
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {'ref': ref}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers(), params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('type') == 'file':
                        # 解码base64内容
                        content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                        
                        # 缓存内容
                        self._cache_content(cache_key, content)
                        
                        return content
                else:
                    self.logger.error(f"获取文件内容失败 {path}: {response.status}")
                    return None
    
    async def get_pull_request_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """获取PR变更的文件"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"获取PR文件失败: {response.status}")
                    return []
    
    async def get_commit_changes(self, owner: str, repo: str, sha: str) -> List[Dict[str, Any]]:
        """获取提交变更"""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('files', [])
                else:
                    self.logger.error(f"获取提交变更失败: {response.status}")
                    return []
    
    async def create_pr_comment(self, owner: str, repo: str, pr_number: int, 
                              body: str, commit_sha: Optional[str] = None) -> bool:
        """创建PR评论"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        
        data = {'body': body}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.get_headers(), json=data) as response:
                if response.status == 201:
                    self.logger.info(f"PR评论创建成功: {pr_number}")
                    return True
                else:
                    self.logger.error(f"创建PR评论失败: {response.status}")
                    return False
    
    async def get_repository_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """获取仓库语言统计"""
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
    
    async def filter_code_files(self, tree_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤代码文件"""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', 
            '.rs', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.vue'
        }
        
        ignore_patterns = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'env', 'dist', 'build', 'target', '.idea', '.vscode', 'coverage'
        }
        
        code_files = []
        for item in tree_items:
            if item.get('type') == 'blob':  # 文件类型
                path = item.get('path', '')
                
                # 检查扩展名
                if any(path.endswith(ext) for ext in code_extensions):
                    # 检查是否在忽略路径中
                    if not any(ignore in path for ignore in ignore_patterns):
                        code_files.append(item)
        
        return code_files
    
    async def batch_get_files(self, owner: str, repo: str, 
                            file_paths: List[str], max_concurrent: int = 10) -> Dict[str, str]:
        """批量获取文件内容"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_file_with_semaphore(path: str) -> Tuple[str, Optional[str]]:
            async with semaphore:
                content = await self.get_file_content(owner, repo, path)
                await asyncio.sleep(0.1)  # 避免触发速率限制
                return path, content
        
        # 创建任务
        tasks = [get_file_with_semaphore(path) for path in file_paths]
        
        # 执行任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        file_contents = {}
        for result in results:
            if isinstance(result, tuple):
                path, content = result
                if content is not None:
                    file_contents[path] = content
            else:
                self.logger.error(f"批量获取文件失败: {result}")
        
        return file_contents
    
    async def clone_lightweight(self, owner: str, repo: str, branch: str = None) -> Optional[str]:
        """轻量级克隆（仅元数据）"""
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"cursor_repo_{owner}_{repo}_")
            
            # 构建Git命令
            repo_url = f"https://github.com/{owner}/{repo}.git"
            if self.github_token:
                repo_url = f"https://{self.github_token}@github.com/{owner}/{repo}.git"
            
            # 执行轻量级克隆
            import subprocess
            
            cmd = [
                'git', 'clone',
                '--filter=blob:none',  # 不下载blob对象
                '--no-checkout',       # 不检出工作树
                '--depth=1'            # 仅最新提交
            ]
            
            if branch:
                cmd.extend(['--branch', branch])
            
            cmd.extend([repo_url, temp_dir])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"轻量级克隆成功: {temp_dir}")
                return temp_dir
            else:
                self.logger.error(f"克隆失败: {stderr.decode()}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None
                
        except Exception as e:
            self.logger.error(f"轻量级克隆失败: {e}")
            return None
    
    def _get_cached_content(self, cache_key: str) -> Optional[str]:
        """获取缓存的文件内容"""
        cache_file = self.cache_dir / f"{hashlib.md5(cache_key.encode()).hexdigest()}.txt"
        
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            self.logger.debug(f"读取缓存失败: {e}")
        
        return None
    
    def _cache_content(self, cache_key: str, content: str):
        """缓存文件内容"""
        cache_file = self.cache_dir / f"{hashlib.md5(cache_key.encode()).hexdigest()}.txt"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            self.logger.debug(f"写入缓存失败: {e}")
    
    def clear_cache(self):
        """清空缓存"""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            self.logger.info("缓存清空成功")
        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """检查API速率限制"""
        url = f"{self.base_url}/rate_limit"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    self.rate_limit_remaining = data['rate']['remaining']
                    self.rate_limit_reset = data['rate']['reset']
                    return data
                else:
                    return {}
    
    def parse_github_url(self, url: str) -> Optional[Tuple[str, str]]:
        """解析GitHub URL"""
        import re
        
        patterns = [
            r'github\.com[:/]([^/]+)/([^/.]+)',
            r'github\.com/([^/]+)/([^/]+)/?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        
        return None 