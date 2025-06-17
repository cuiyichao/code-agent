from flask import Blueprint, request, jsonify
import asyncio
import logging
from typing import Dict, Any, Optional

from ..analyzers.integrated_analyzer import IntegratedCursorAnalyzer
from ..utils.auth_utils import require_auth
from ..utils.response_utils import success_response, error_response

# 创建高级分析蓝图
advanced_bp = Blueprint('advanced', __name__, url_prefix='/api/advanced')
logger = logging.getLogger(__name__)

# 全局分析器实例缓存
analyzer_cache: Dict[str, IntegratedCursorAnalyzer] = {}

def get_analyzer(config: Dict[str, Any]) -> IntegratedCursorAnalyzer:
    """获取或创建分析器实例"""
    cache_key = f"{config.get('source_type', 'local')}_{config.get('repo_path', '')}_{config.get('github_repo', '')}"
    
    if cache_key not in analyzer_cache:
        analyzer = IntegratedCursorAnalyzer(config)
        
        if config.get('source_type') == 'github':
            analyzer.initialize_for_github(
                config['github_owner'], 
                config['github_repo']
            )
        else:
            analyzer.initialize_for_path(config['repo_path'])
        
        analyzer_cache[cache_key] = analyzer
    
    return analyzer_cache[cache_key]

@advanced_bp.route('/index/build', methods=['POST'])
def build_index():
    """构建项目索引"""
    try:
        data = request.get_json()
        
        # 验证输入
        if not data:
            return error_response("请求数据不能为空")
        
        config = {
            'source_type': data.get('source_type', 'local'),
            'repo_path': data.get('repo_path'),
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token'),
            'force_rebuild': data.get('force_rebuild', False)
        }
        
        # 验证必要参数
        if config['source_type'] == 'github':
            if not config['github_owner'] or not config['github_repo']:
                return error_response("GitHub分析需要提供owner和repo参数")
        else:
            if not config['repo_path']:
                return error_response("本地分析需要提供repo_path参数")
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 异步构建索引
        async def build_async():
            return await analyzer.build_full_index(config['force_rebuild'])
        
        # 运行异步任务
        stats = asyncio.run(build_async())
        
        return success_response({
            'message': '索引构建完成',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"构建索引失败: {str(e)}")
        return error_response(f"构建索引失败: {str(e)}")

@advanced_bp.route('/analyze/changes', methods=['POST'])
def analyze_changes():
    """分析代码变更"""
    try:
        data = request.get_json()
        
        config = {
            'source_type': data.get('source_type', 'local'),
            'repo_path': data.get('repo_path'),
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token')
        }
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 异步分析变更
        async def analyze_async():
            return await analyzer.analyze_changes(
                commit_hash=data.get('commit_hash'),
                pr_number=data.get('pr_number')
            )
        
        # 运行异步任务
        result = asyncio.run(analyze_async())
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"分析变更失败: {str(e)}")
        return error_response(f"分析变更失败: {str(e)}")

@advanced_bp.route('/search/semantic', methods=['POST'])
def semantic_search():
    """语义搜索代码"""
    try:
        data = request.get_json()
        
        query = data.get('query', '').strip()
        if not query:
            return error_response("搜索查询不能为空")
        
        config = {
            'source_type': data.get('source_type', 'local'),
            'repo_path': data.get('repo_path'),
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token')
        }
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 异步搜索
        async def search_async():
            return await analyzer.semantic_search(
                query=query,
                limit=data.get('limit', 10),
                file_filter=data.get('file_filter')
            )
        
        # 运行异步任务
        results = asyncio.run(search_async())
        
        return success_response({
            'query': query,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        logger.error(f"语义搜索失败: {str(e)}")
        return error_response(f"语义搜索失败: {str(e)}")

@advanced_bp.route('/github/pr/<int:pr_number>/analyze', methods=['POST'])
def analyze_github_pr(pr_number):
    """分析GitHub PR"""
    try:
        data = request.get_json() or {}
        
        config = {
            'source_type': 'github',
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token')
        }
        
        if not config['github_owner'] or not config['github_repo']:
            return error_response("需要提供GitHub owner和repo参数")
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 异步分析PR
        async def analyze_pr_async():
            return await analyzer.analyze_github_pr(pr_number)
        
        # 运行异步任务
        result = asyncio.run(analyze_pr_async())
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"分析GitHub PR失败: {str(e)}")
        return error_response(f"分析GitHub PR失败: {str(e)}")

@advanced_bp.route('/repository/info', methods=['POST'])
def get_repository_info():
    """获取仓库信息"""
    try:
        data = request.get_json()
        
        if data.get('source_type') == 'github':
            from ..clients.github_client import GitHubClient
            
            github_client = GitHubClient(data.get('github_token'))
            
            async def get_info_async():
                return await github_client.get_repository_info(
                    data['github_owner'], 
                    data['github_repo']
                )
            
            repo_info = asyncio.run(get_info_async())
            
            if repo_info:
                return success_response(repo_info)
            else:
                return error_response("无法获取仓库信息")
        else:
            # 本地仓库信息
            repo_path = data.get('repo_path')
            if not repo_path:
                return error_response("请提供仓库路径")
            
            import os
            from pathlib import Path
            
            repo_path = Path(repo_path)
            if not repo_path.exists():
                return error_response("仓库路径不存在")
            
            # 获取基本信息
            try:
                from git import Repo
                repo = Repo(repo_path)
                
                info = {
                    'name': repo_path.name,
                    'path': str(repo_path),
                    'default_branch': repo.active_branch.name,
                    'is_dirty': repo.is_dirty(),
                    'commit_count': len(list(repo.iter_commits())),
                    'remotes': [str(remote) for remote in repo.remotes]
                }
                
                return success_response(info)
                
            except Exception as e:
                return error_response(f"无法读取Git仓库信息: {str(e)}")
        
    except Exception as e:
        logger.error(f"获取仓库信息失败: {str(e)}")
        return error_response(f"获取仓库信息失败: {str(e)}")

@advanced_bp.route('/index/status', methods=['POST'])
def get_index_status():
    """获取索引状态"""
    try:
        data = request.get_json()
        
        config = {
            'source_type': data.get('source_type', 'local'),
            'repo_path': data.get('repo_path'),
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token')
        }
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 检查索引状态
        has_index = analyzer.load_index()
        
        status = {
            'has_index': has_index,
            'symbols_count': len(analyzer.symbols) if has_index else 0,
            'references_count': len(analyzer.references) if has_index else 0,
            'database_path': str(analyzer.db_path) if analyzer.db_path else None
        }
        
        return success_response(status)
        
    except Exception as e:
        logger.error(f"获取索引状态失败: {str(e)}")
        return error_response(f"获取索引状态失败: {str(e)}")

@advanced_bp.route('/symbols/find', methods=['POST'])
def find_symbols():
    """查找符号"""
    try:
        data = request.get_json()
        
        symbol_name = data.get('symbol_name', '').strip()
        if not symbol_name:
            return error_response("符号名称不能为空")
        
        config = {
            'source_type': data.get('source_type', 'local'),
            'repo_path': data.get('repo_path'),
            'github_owner': data.get('github_owner'),
            'github_repo': data.get('github_repo'),
            'github_token': data.get('github_token')
        }
        
        # 获取分析器
        analyzer = get_analyzer(config)
        
        # 确保索引已加载
        if not analyzer.symbols:
            analyzer.load_index()
        
        # 查找匹配的符号
        matching_symbols = []
        for symbol in analyzer.symbols.values():
            if symbol_name.lower() in symbol.name.lower():
                matching_symbols.append(symbol.to_dict())
        
        return success_response({
            'query': symbol_name,
            'symbols': matching_symbols,
            'total': len(matching_symbols)
        })
        
    except Exception as e:
        logger.error(f"查找符号失败: {str(e)}")
        return error_response(f"查找符号失败: {str(e)}")

@advanced_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return success_response({
        'status': 'healthy',
        'active_analyzers': len(analyzer_cache),
        'version': '1.0.0'
    })

# 错误处理
@advanced_bp.errorhandler(404)
def not_found_error(error):
    return error_response("API端点不存在", 404)

@advanced_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"内部服务器错误: {str(error)}")
    return error_response("内部服务器错误", 500) 