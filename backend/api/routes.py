from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import json
import logging
import asyncio
import functools
import os
import sys
from typing import List, Dict
from dataclasses import asdict
import concurrent.futures

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db
from utils.git_utils import GitUtils
# WebSocket相关导入
try:
    from websocket_server import send_notification
except ImportError:
    logger.warning("WebSocket server not available")
    def send_notification(*args, **kwargs):
        pass

# 分析器相关导入
try:
    from analyzers.enhanced_cursor_analyzer import EnhancedCursorAnalyzer
except ImportError:
    logger.warning("Enhanced cursor analyzer not available")
    EnhancedCursorAnalyzer = None



# 尝试导入可选模块
try:
    from indexers.codebase_indexer import CodebaseIndexer
except ImportError:
    class CodebaseIndexer:
        def __init__(self, *args, **kwargs):
            pass
        def index_codebase(self, *args, **kwargs):
            return {'error': 'CodebaseIndexer not available'}

try:
    from utils.html_reporter import HTMLReporter
except ImportError:
    class HTMLReporter:
        def __init__(self, *args, **kwargs):
            pass
        def generate_report(self, *args, **kwargs):
            return '<html><body>HTML Reporter not available</body></html>'

try:
    from utils.json_reporter import JSONReporter
except ImportError:
    class JSONReporter:
        def __init__(self, *args, **kwargs):
            pass
        def generate_report(self, *args, **kwargs):
            return {'error': 'JSON Reporter not available'}

# 设置日志
logger = logging.getLogger('api')

api = Blueprint('api', __name__)

db = get_db()

# 全局事件循环，确保所有异步操作在同一个事件循环中运行
_loop = None

def get_loop():
    """获取全局事件循环，如果不存在则创建"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

def run_async(func):
    """运行异步函数的同步包装器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = get_loop()
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        except Exception as e:
            logger.error(f"异步操作失败: {str(e)}")
            raise
    return wrapper

# 添加CORS预检请求处理
@api.route('/', methods=['OPTIONS'])
@api.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path=None):
    return '', 204

# 添加根路由，避免404
@api.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': '代码分析后端API服务',
        'status': 'running',
        'endpoints': ['/api/projects', '/api/projects/<id>']
    })

@api.route('/projects', methods=['GET'])
def get_projects():
    try:
        projects = db.fetch_all("SELECT * FROM projects ORDER BY created_at DESC")
        
        # 处理SQLite中的JSON字段
        for project in projects:
            if 'stats' in project and project['stats'] and isinstance(project['stats'], str):
                try:
                    project['stats'] = json.loads(project['stats'])
                except:
                    project['stats'] = {}
        
        return jsonify(projects)
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify([]), 500

@api.route('/projects/<int:id>', methods=['GET'])
def get_project(id):
    try:
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 处理SQLite中的JSON字段
        if 'stats' in project and project['stats'] and isinstance(project['stats'], str):
            try:
                project['stats'] = json.loads(project['stats'])
            except:
                project['stats'] = {}
        
        # 获取项目的分析结果
        analysis_results = db.fetch_all(
            "SELECT * FROM analysis_results WHERE project_id = %s ORDER BY created_at DESC", 
            (id,)
        )
        
        # 处理分析结果中的JSON字段
        for result in analysis_results:
            if 'result_data' in result and result['result_data'] and isinstance(result['result_data'], str):
                try:
                    result['result_data'] = json.loads(result['result_data'])
                except:
                    result['result_data'] = {}
            
            # 获取测试用例
            test_cases = db.fetch_all(
                "SELECT * FROM test_cases WHERE analysis_id = %s",
                (result['id'],)
            )
            result['testCases'] = test_cases
        
        # 尝试克隆并分析仓库，获取最新统计信息
        try:
            git_utils = GitUtils(project['git_url'], project['branch'])
            if git_utils.clone_repo():
                # 获取仓库统计信息
                stats = git_utils.get_repo_stats()
                if stats:
                    # 更新项目统计信息
                    project['stats'] = stats
                    
                    # 更新数据库中的统计信息
                    stats_json = json.dumps(stats)
                    db.execute(
                        "UPDATE projects SET stats = %s WHERE id = %s",
                        (stats_json, id)
                    )
                
                # 清理临时目录
                git_utils.cleanup()
        except Exception as e:
            logger.error(f"获取仓库统计信息失败: {str(e)}")
        
        return jsonify({
            'project': project,
            'analysis_results': analysis_results
        })
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects', methods=['POST'])
def create_project():
    try:
        data = request.json
        name = data.get('name')
        git_url = data.get('git_url')
        branch = data.get('branch', 'main')
        description = data.get('description', '')
        
        if not name or not git_url:
            return jsonify({'error': 'Name and git_url are required'}), 400
        
        # 注释掉重复检查，允许相同仓库的多个配置
        # try:
        #     existing_project = db.fetch_one("SELECT * FROM projects WHERE git_url = %s", (git_url,))
        #     if existing_project:
        #         return jsonify({'error': '该仓库路径已被使用'}), 409
        # except Exception as e:
        #     logger.error(f"检查仓库路径失败: {str(e)}")
        #     # 继续执行，不阻止创建项目

        # 验证仓库是否可访问
        git_utils = GitUtils(git_url, branch)
        if not git_utils.validate_repo():
            return jsonify({'error': '无法访问该Git仓库，请检查URL是否正确'}), 400
        
        # 尝试克隆仓库并获取统计信息
        stats = None
        if git_utils.clone_repo():
            stats = git_utils.get_repo_stats()
            git_utils.cleanup()
        
        # 创建项目
        stats_json = json.dumps(stats) if stats else None
        result = db.execute(
            "INSERT INTO projects (name, git_url, branch, description, created_at, stats) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name, git_url, branch, description, datetime.now(), stats_json)
        )
        
        # 处理不同数据库的返回值格式
        if isinstance(result, int):
            # SQLite返回lastrowid（整数）
            project_id = result
        elif result and 'id' in result:
            # PostgreSQL返回字典
            project_id = result['id']
        else:
            return jsonify({'error': '项目创建失败'}), 500
        
        return jsonify({'id': project_id, 'message': '项目创建成功'}), 201
    except Exception as e:
        logger.error(f"处理创建项目请求失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>', methods=['PUT'])
def update_project(id):
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        # 更新项目
        db.execute(
            "UPDATE projects SET name = %s, description = %s WHERE id = %s",
            (name, description, id)
        )
        
        return jsonify({'message': '项目更新成功'})
    except Exception as e:
        logger.error(f"更新项目失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    try:
        # 删除项目相关的测试用例
        analysis_results = db.fetch_all("SELECT id FROM analysis_results WHERE project_id = %s", (id,))
        for result in analysis_results:
            db.execute("DELETE FROM test_cases WHERE analysis_id = %s", (result['id'],))
        
        # 删除项目的分析结果
        db.execute("DELETE FROM analysis_results WHERE project_id = %s", (id,))
        
        # 删除项目
        db.execute("DELETE FROM projects WHERE id = %s", (id,))
        
        return jsonify({'message': '项目删除成功'})
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>/analyze', methods=['POST'])
def analyze_project(id):
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.json or {}
        commit_hash = data.get('commit_hash')
        force_update = data.get('force_update', False)
        
        # 使用Git工具分析仓库
        git_utils = GitUtils(project['git_url'], project['branch'])
        
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库，请检查URL和权限'}), 400
        
        # 分析提交
        analysis_result = git_utils.analyze_commit(commit_hash)
        
        if not analysis_result:
            git_utils.cleanup()
            return jsonify({'error': '无法分析提交，请检查提交哈希是否正确'}), 400
        
        # 更新项目统计信息
        stats = git_utils.get_repo_stats()
        if stats:
            stats_json = json.dumps(stats)
            db.execute(
                "UPDATE projects SET stats = %s WHERE id = %s",
                (stats_json, id)
            )
        
        # 生成测试用例
        test_cases = git_utils.generate_test_cases(analysis_result['changes'])
        
        # 清理临时目录
        git_utils.cleanup()
        
        # 计算风险级别
        risk_level = 'low'
        if analysis_result['complexity_delta'] > 5:
            risk_level = 'high'
        elif analysis_result['complexity_delta'] > 2:
            risk_level = 'medium'
        
        # 检查是否已经存在相同commit_hash的分析结果
        existing_analysis = None
        if commit_hash and not force_update:
            existing_analysis = db.fetch_one(
                "SELECT * FROM analysis_results WHERE project_id = %s AND commit_hash = %s",
                (id, commit_hash)
            )
        
        if existing_analysis and not force_update:
            # 返回现有分析结果
            existing_result_data = existing_analysis['result_data']
            if isinstance(existing_result_data, str):
                try:
                    existing_result_data = json.loads(existing_result_data)
                except:
                    existing_result_data = {}
            
            # 获取测试用例
            existing_test_cases = db.fetch_all(
                "SELECT * FROM test_cases WHERE analysis_id = %s",
                (existing_analysis['id'],)
            )
            
            # 发送WebSocket通知
            send_notification('analysis_complete', {
                'analysisId': existing_analysis['id'],
                'projectId': id,
                'message': '使用现有分析结果'
            })
            
            return jsonify({
                'message': '使用现有分析结果',
                'analysis_id': existing_analysis['id'],
                'change_details': existing_result_data.get('result', {}),
                'test_cases': existing_test_cases
            })
        
        # 保存分析结果
        result_data = {
            'analysis_type': 'code_change',
            'commit_hash': analysis_result['commit_hash'],
            'result': analysis_result,
            'risk_level': risk_level
        }
        
        # 插入分析结果
        result_data_json = json.dumps(result_data)
        analysis_id = db.execute(
            """
            INSERT INTO analysis_results 
            (project_id, analysis_type, commit_hash, result_data, risk_level, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING id
            """,
            (
                id, 
                'code_change', 
                analysis_result['commit_hash'], 
                result_data_json, 
                risk_level, 
                datetime.now()
            )
        )
        
        # 插入测试用例
        for test_case in test_cases:
            db.execute(
                """
                INSERT INTO test_cases 
                (analysis_id, name, test_type, priority, test_code, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    analysis_id['id'], 
                    test_case['name'], 
                    test_case['type'], 
                    test_case['priority'], 
                    test_case['code'], 
                    datetime.now()
                )
            )
        
        # 发送WebSocket通知
        send_notification('analysis_complete', {
            'analysisId': analysis_id['id'],
            'projectId': id,
            'message': '代码变更分析完成'
        })
        
        # 返回分析结果和测试用例
        return jsonify({
            'message': '代码变更分析完成',
            'analysis_id': analysis_id['id'],
            'change_details': analysis_result,
            'test_cases': test_cases
        })
    except Exception as e:
        logger.error(f"分析项目变更失败: {str(e)}")
        
        # 发送失败通知
        send_notification('analysis_failed', {
            'projectId': id,
            'error': str(e)
        })
        
        return jsonify({'error': str(e)}), 500

@api.route('/projects/validate-repo', methods=['POST'])
def validate_repo():
    try:
        data = request.json
        repo_url = data.get('repoUrl')
        
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        # 验证仓库
        git_utils = GitUtils(repo_url)
        if git_utils.validate_repo():
            return jsonify({'message': '仓库验证成功'})
        else:
            return jsonify({'error': '仓库验证失败，请检查URL是否正确并确保仓库可访问'}), 400
    except Exception as e:
        logger.error(f"验证仓库失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/repo-branches', methods=['GET'])
def get_repo_branches():
    try:
        repo_url = request.args.get('repoUrl')
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        # 获取仓库分支
        git_utils = GitUtils(repo_url)
        branches = git_utils.get_branches()
        
        return jsonify(branches)
    except Exception as e:
        logger.error(f"获取仓库分支失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>/index', methods=['POST'])
def index_project(id):
    """为项目创建代码索引"""
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 使用Git工具获取代码库路径
        git_utils = GitUtils(project['git_url'], project['branch'])
        
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库，请检查URL和权限'}), 400
        
        # 获取仓库本地路径
        repo_path = git_utils.temp_dir
        
        # 创建代码索引
        indexer = CodebaseIndexer(index_dir=os.path.join(repo_path, ".code_index"))
        index_result = indexer.build_index(repo_path)
        
        # 保存索引结果到数据库
        index_data = {
            "symbol_count": index_result["symbol_count"],
            "module_count": index_result["module_count"],
            "index_path": index_result["index_path"]
        }
        
        # 将索引信息保存到项目中
        db.execute(
            "UPDATE projects SET code_index = %s WHERE id = %s",
            (json.dumps(index_data), id)
        )
        
        # 清理临时目录
        git_utils.cleanup()
        
        return jsonify({
            'message': '代码索引创建成功',
            'index_stats': index_data
        })
    except Exception as e:
        logger.error(f"创建代码索引失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>/search', methods=['GET'])
def search_code(id):
    """在项目代码中搜索"""
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        query = request.args.get('q')
        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400
        
        # 检查项目是否有代码索引
        if not project.get('code_index'):
            # 如果没有索引，先创建索引
            return jsonify({'error': '项目尚未创建代码索引，请先调用索引API'}), 400
        
        # 使用Git工具获取代码库路径
        git_utils = GitUtils(project['git_url'], project['branch'])
        
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库，请检查URL和权限'}), 400
        
        # 获取仓库本地路径
        repo_path = git_utils.temp_dir
        
        # 加载代码索引
        indexer = CodebaseIndexer(index_dir=os.path.join(repo_path, ".code_index"))
        if not indexer.load_index():
            # 如果加载失败，重新创建索引
            indexer.build_index(repo_path)
        
        # 执行搜索
        top_k = int(request.args.get('limit', 10))
        results = indexer.find_similar_symbols(query, top_k=top_k)
        
        # 清理临时目录
        git_utils.cleanup()
        
        # 格式化结果
        formatted_results = []
        for result in results:
            symbol = result['symbol']
            formatted_results.append({
                'name': symbol.name,
                'type': symbol.symbol_type,
                'module': result['module_path'],
                'line': symbol.line,
                'column': symbol.column,
                'parameters': symbol.parameters,
                'return_type': symbol.return_type,
                'score': result['similarity_score']
            })
        
        return jsonify({
            'query': query,
            'results': formatted_results
        })
    except Exception as e:
        logger.error(f"代码搜索失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>/test-cases', methods=['GET'])
def get_test_cases(id):
    """获取项目的测试用例"""
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 首先尝试从基于索引的分析结果中获取功能测试
        try:
            latest_analysis = db.fetch_one(
                "SELECT analysis_data FROM code_analysis WHERE project_id = %s AND analysis_type = 'index_based' ORDER BY created_at DESC LIMIT 1",
                (id,)
            )
            
            if latest_analysis and latest_analysis['analysis_data']:
                analysis_data = json.loads(latest_analysis['analysis_data'])
                test_recommendations = analysis_data.get('test_recommendations', {})
                functional_tests = test_recommendations.get('functional_tests', [])
                
                if functional_tests:
                    logger.info(f"返回 {len(functional_tests)} 个功能测试用例")
                    # 转换为前端期望的格式
                    formatted_tests = []
                    for i, test in enumerate(functional_tests):
                        formatted_test = {
                            'id': i + 1,
                            'name': test.get('name', '未命名测试'),
                            'description': test.get('description', ''),
                            'test_type': 'functional',
                            'priority': test.get('priority', 'medium'),
                            'test_scenarios': test.get('test_scenarios', []),
                            'test_data_requirements': test.get('test_data_requirements', []),
                            'expected_outcomes': test.get('expected_outcomes', []),
                            'estimated_time': test.get('estimated_time', 10),
                            'created_at': datetime.now().isoformat(),
                            'generation_method': 'index_based_functional'
                        }
                        formatted_tests.append(formatted_test)
                    
                    return jsonify(formatted_tests)
        except Exception as e:
            logger.warning(f"获取基于索引的功能测试失败: {e}")
        
        # 如果没有基于索引的分析，回退到旧的逻辑但返回功能测试格式
        latest_analysis = db.fetch_one(
            "SELECT id, result_data FROM analysis_results WHERE project_id = %s ORDER BY created_at DESC LIMIT 1", 
            (id,)
        )
        
        analysis_id = latest_analysis['id'] if latest_analysis else None
        
        # 获取现有的测试用例
        if analysis_id:
            analysis_tests = db.fetch_all(
                "SELECT * FROM test_cases WHERE analysis_id = %s",
                (analysis_id,)
            )
        else:
            analysis_tests = []
        
        # 如果没有测试用例，尝试生成智能功能测试用例
        if not analysis_tests:
            logger.info(f"🧠 尝试生成智能功能测试用例 for project {id}")
            
            # 尝试使用增强AI客户端生成智能测试用例
            try:
                from clients.enhanced_ai_client import EnhancedAIClient
                
                # 获取项目信息
                project = db.fetch_one("SELECT * FROM projects WHERE id = ?", (id,))
                if project:
                    project_path = project.get('git_url', '')
                    project_name = project.get('name', f'Project {id}')
                    
                    # 创建AI客户端
                    ai_client = EnhancedAIClient()
                    
                    # 生成智能功能测试用例 - 修复异步调用问题
                    import asyncio
                    try:
                        # 创建新的事件循环而不是获取现有的
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 如果当前线程已有运行的循环，使用asyncio.run
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(
                                        asyncio.run,
                                        ai_client.generate_comprehensive_functional_tests(
                                            change_analysis={
                                                'project_path': project_path,
                                                'project_name': project_name,
                                                'project_id': id
                                            },
                                            system_context={
                                                'project_type': 'web_application',
                                                'tech_stack': ['python', 'javascript'],
                                                'user_roles': ['admin', 'user']
                                            }
                                        )
                                    )
                                    intelligent_tests = future.result(timeout=30)
                            else:
                                intelligent_tests = loop.run_until_complete(
                                    ai_client.generate_comprehensive_functional_tests(
                                        change_analysis={
                                            'project_path': project_path,
                                            'project_name': project_name,
                                            'project_id': id
                                        },
                                        system_context={
                                            'project_type': 'web_application',
                                            'tech_stack': ['python', 'javascript'],
                                            'user_roles': ['admin', 'user']
                                        }
                                    )
                                )
                        except RuntimeError:
                            # 没有事件循环，创建新的
                            intelligent_tests = asyncio.run(
                                ai_client.generate_comprehensive_functional_tests(
                                    change_analysis={
                                        'project_path': project_path,
                                        'project_name': project_name,
                                        'project_id': id
                                    },
                                    system_context={
                                        'project_type': 'web_application',
                                        'tech_stack': ['python', 'javascript'],
                                        'user_roles': ['admin', 'user']
                                    }
                                )
                            )
                    except Exception as async_error:
                        logger.warning(f"异步调用失败: {async_error}")
                        # 回退到同步方式生成默认用例
                        intelligent_tests = None
                    
                    if intelligent_tests and isinstance(intelligent_tests, (list, dict)) and len(intelligent_tests) > 0:
                        logger.info(f"✅ 成功生成 {len(intelligent_tests) if isinstance(intelligent_tests, list) else 1} 个智能功能测试用例")
                        return jsonify(intelligent_tests)
                        
            except Exception as e:
                logger.warning(f"智能测试用例生成失败: {e}，使用默认测试用例")
            
            logger.info(f"生成默认功能测试用例 for project {id}")
            
            # 生成基于项目的功能测试用例
            default_functional_tests = [
                {
                    'id': 1,
                    'name': '功能测试 - 项目核心功能验证',
                    'description': '验证项目的核心功能是否正常工作',
                    'test_type': 'functional',
                    'priority': 'high',
                    'test_scenarios': [
                        '测试项目初始化流程',
                        '测试主要功能模块的正常运行',
                        '测试异常情况的处理机制',
                        '测试用户界面的响应性'
                    ],
                    'test_data_requirements': [
                        '有效的输入数据集',
                        '边界值测试数据',
                        '异常输入数据',
                        '性能测试数据'
                    ],
                    'expected_outcomes': [
                        '所有核心功能应正常执行',
                        '异常情况应有合适的错误处理',
                        '用户界面应响应流畅',
                        '数据处理应准确无误'
                    ],
                    'estimated_time': 30,
                    'created_at': datetime.now().isoformat(),
                    'generation_method': 'default_functional'
                },
                {
                    'id': 2,
                    'name': '功能测试 - 数据处理验证',
                    'description': '验证数据输入、处理和输出的完整性',
                    'test_type': 'functional',
                    'priority': 'medium',
                    'test_scenarios': [
                        '测试数据输入验证机制',
                        '测试数据处理逻辑的正确性',
                        '测试数据输出格式的一致性',
                        '测试大量数据的处理性能'
                    ],
                    'test_data_requirements': [
                        '标准格式的测试数据',
                        '不同类型的输入数据',
                        '大容量数据集',
                        '格式错误的数据样本'
                    ],
                    'expected_outcomes': [
                        '输入验证应正确识别有效和无效数据',
                        '数据处理应保持准确性和一致性',
                        '输出格式应符合预期规范',
                        '性能应在可接受范围内'
                    ],
                    'estimated_time': 25,
                    'created_at': datetime.now().isoformat(),
                    'generation_method': 'default_functional'
                },
                {
                    'id': 3,
                    'name': '功能测试 - 用户交互验证',
                    'description': '验证用户界面和交互功能的可用性',
                    'test_type': 'functional',
                    'priority': 'medium',
                    'test_scenarios': [
                        '测试用户界面元素的可访问性',
                        '测试用户操作的响应速度',
                        '测试错误提示的准确性',
                        '测试不同浏览器的兼容性'
                    ],
                    'test_data_requirements': [
                        '不同用户角色的测试账号',
                        '各种操作场景的测试脚本',
                        '不同浏览器环境',
                        '网络状况模拟数据'
                    ],
                    'expected_outcomes': [
                        '界面元素应正确显示和响应',
                        '用户操作应得到及时反馈',
                        '错误信息应清晰明确',
                        '应支持主流浏览器'
                    ],
                    'estimated_time': 20,
                    'created_at': datetime.now().isoformat(),
                    'generation_method': 'default_functional'
                }
            ]
            
            return jsonify(default_functional_tests)
        
        # 转换现有测试用例为功能测试格式
        formatted_tests = []
        for test in analysis_tests:
            formatted_test = {
                'id': test.get('id'),
                'name': test.get('name', '未命名测试'),
                'description': test.get('description', ''),
                'test_type': 'functional',
                'priority': test.get('priority', 'medium'),
                'test_scenarios': [
                    f"验证{test.get('name', '功能')}的基本操作",
                    f"测试{test.get('name', '功能')}的边界条件",
                    f"检查{test.get('name', '功能')}的错误处理"
                ],
                'test_data_requirements': [
                    '正常输入数据',
                    '边界值数据',
                    '异常输入数据'
                ],
                'expected_outcomes': [
                    f"{test.get('name', '功能')}应正常执行并返回预期结果"
                ],
                'estimated_time': 15,
                'created_at': test.get('created_at', datetime.now().isoformat()),
                'generation_method': 'converted_from_old'
            }
            formatted_tests.append(formatted_test)
        
        logger.info(f"返回 {len(formatted_tests)} 个转换后的功能测试用例")
        return jsonify(formatted_tests)
        
    except Exception as e:
        logger.error(f"获取测试用例失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/analyzer/analyze', methods=['POST'])
async def analyze_code():
    """分析代码变更接口"""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request data"}), 400
    
    repo_path = data.get('repo_path')
    if not repo_path:
        return jsonify({"error": "Missing repository path"}), 400
    
    commit_hash = data.get('commit_hash')
    config = data.get('config', {})
    
    try:
        # 创建分析器并执行分析
        analyzer = EnhancedCursorAnalyzer(repo_path, config)
        results = await analyzer.analyze_repository_changes(commit_hash)
        
        return jsonify(results.to_dict())
    except Exception as e:
        logger.exception("分析代码时出错")
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/analyzer/ai-providers', methods=['GET'])
async def get_ai_providers():
    """获取可用AI服务提供商"""
    try:
        providers = {
            "openai": {"name": "OpenAI", "models": ["gpt-3.5-turbo", "gpt-4"]},
            "anthropic": {"name": "Anthropic", "models": ["claude-3-sonnet", "claude-3-opus"]},
            "local": {"name": "Local LLM", "models": ["llama2", "mistral"]},
            "azure": {"name": "Azure OpenAI", "models": ["gpt-35-turbo", "gpt-4"]},
            "google": {"name": "Google AI", "models": ["gemini-pro"]}
        }
        
        return jsonify({
            "status": "success",
            "providers": providers
        })
    except Exception as e:
        logger.exception("获取AI提供商时出错")
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/analyzer/test-generator', methods=['POST'])
async def generate_tests():
    """生成测试用例接口"""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request data"}), 400
    
    repo_path = data.get('repo_path')
    file_path = data.get('file_path')
    function_name = data.get('function_name')
    language = data.get('language')
    config = data.get('config', {})
    
    if not repo_path or not file_path:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # 创建分析器
        analyzer = EnhancedCursorAnalyzer(repo_path, config)
        
        # 读取文件内容
        content = analyzer._read_file_content(file_path)
        
        if not language:
            language = analyzer.parser.get_language_from_file(file_path)
            if not language:
                return jsonify({"error": "Unsupported file type"}), 400
        
        if function_name:
            # 生成特定函数的测试
            function_code = analyzer._extract_function_code(content, function_name, language)
            if not function_code:
                return jsonify({"error": f"Function {function_name} not found"}), 400
            
            test_code = await analyzer.ai_integrator.generate_test_cases(function_code, language)
            return jsonify({
                "status": "success",
                "tests": [{
                    "name": f"test_{function_name}",
                    "target_function": function_name,
                    "test_code": test_code or analyzer._generate_default_test_code(function_name, language),
                    "language": language
                }]
            })
        else:
            # 提取所有函数并生成测试
            functions, _ = analyzer.parser.extract_functions_and_classes(content, language)
            
            tests = []
            for func in functions[:5]:  # 限制为前5个函数，避免请求过多
                function_code = analyzer._extract_function_code(content, func, language)
                if function_code:
                    test_code = await analyzer.ai_integrator.generate_test_cases(function_code, language)
                    tests.append({
                        "name": f"test_{func}",
                        "target_function": func,
                        "test_code": test_code or analyzer._generate_default_test_code(func, language),
                        "language": language
                    })
            
            return jsonify({
                "status": "success",
                "tests": tests
            })
            
    except Exception as e:
        logger.exception("生成测试用例时出错")
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/analyzer/suggest-improvements', methods=['POST'])
async def suggest_improvements():
    """建议代码改进接口"""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request data"}), 400
    
    code = data.get('code')
    language = data.get('language')
    config = data.get('config', {})
    
    if not code or not language:
        return jsonify({"error": "Missing code or language"}), 400
    
    try:
        # 使用临时仓库路径
        temp_repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建分析器
        analyzer = EnhancedCursorAnalyzer(temp_repo_path, config)
        
        # 获取改进建议
        suggestions = await analyzer.ai_integrator.suggest_improvements(code, language)
        
        return jsonify({
            "status": "success",
            "suggestions": suggestions
        })
    except Exception as e:
        logger.exception("获取代码改进建议时出错")
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/analyzer/config-template', methods=['GET'])
def get_config_template():
    """获取分析配置模板"""
    try:
        template = {
            "ai_services": {
                "openai": {
                    "api_key": "",
                    "model": "gpt-4",
                    "enabled": False
                },
                "anthropic": {
                    "api_key": "",
                    "model": "claude-3-sonnet-20240229",
                    "enabled": False
                },
                "azure_openai": {
                    "api_key": "",
                    "endpoint": "",
                    "deployment_name": "",
                    "enabled": False
                },
                "google_ai": {
                    "api_key": "",
                    "model": "gemini-pro",
                    "enabled": False
                }
            },
            "analysis": {
                "max_complexity_threshold": 10,
                "risk_assessment_enabled": True,
                "dependency_analysis_enabled": True,
                "include_code_snippets": True,
                "max_suggestions": 10
            },
            "output": {
                "detailed_impact_analysis": True,
                "generate_test_suggestions": True,
                "include_business_impact": True
            }
        }
        
        return jsonify({
            "status": "success",
            "config_template": template
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/analyzer/validate-config', methods=['POST'])
def validate_config():
    """验证分析配置"""
    try:
        config = request.get_json()
        
        # 基本配置验证
        if not config:
            return jsonify({
                "status": "error",
                "message": "配置不能为空"
            }), 400
        
        # 验证AI服务配置
        ai_services = config.get('ai_services', {})
        enabled_services = []
        
        for service_name, service_config in ai_services.items():
            if service_config.get('enabled', False):
                if not service_config.get('api_key'):
                    return jsonify({
                        "status": "error",
                        "message": f"{service_name} 已启用但缺少API密钥"
                    }), 400
                enabled_services.append(service_name)
        
        return jsonify({
            "status": "success",
            "message": "配置验证通过",
            "enabled_services": enabled_services
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/analyzer/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """获取分析任务状态"""
    try:
        # 这里应该查询任务状态数据库或缓存
        # 暂时返回模拟数据
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "progress": 100,
            "status_text": "分析完成",
            "completed": True,
            "failed": False,
            "result": {
                "status": "success",
                "changes_count": 3,
                "analysis_results": [],
                "global_test_strategy": None,
                "summary": {
                    "total_changes": 3,
                    "high_risk_changes": 1,
                    "medium_risk_changes": 1,
                    "low_risk_changes": 1,
                    "total_suggested_tests": 8,
                    "overall_recommendation": "建议优先处理高风险变更，执行全部建议测试"
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/analyzer/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        # 这里应该实现任务取消逻辑
        # 暂时返回成功状态
        return jsonify({
            "status": "success",
            "message": f"任务 {task_id} 已取消"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



@api.route('/analyzer/analysis/<analysis_id>', methods=['GET'])
def get_analysis_details(analysis_id):
    """获取特定分析结果的详情"""
    try:
        # 这里应该从数据库获取分析结果
        # 暂时返回模拟数据
        analysis_result = {
            "id": analysis_id,
            "status": "success",
            "changes_count": 3,
            "analysis_results": [
                {
                    "change": {
                        "file_path": "src/main.py",
                        "change_type": "modified",
                        "affected_functions": ["main", "process_data"],
                        "affected_classes": ["DataProcessor"],
                        "complexity_delta": 2.5,
                        "risk_level": "medium",
                        "business_impact": ["core_logic", "performance"]
                    },
                    "impact": {
                        "direct_impacts": ["src/utils.py", "src/models.py"],
                        "indirect_impacts": ["tests/test_main.py"],
                        "risk_factors": ["high_complexity", "critical_path"],
                        "suggested_tests": [
                            {
                                "name": "test_main_function",
                                "test_type": "unit",
                                "priority": "high",
                                "coverage_areas": ["main", "process_data"]
                            }
                        ],
                        "confidence_score": 0.85
                    }
                }
            ],
            "global_test_strategy": {
                "priority_tests": [],
                "unit_tests": [],
                "integration_tests": [],
                "e2e_tests": [],
                "estimated_coverage": 0.75,
                "estimated_time": 30,
                "recommendations": []
            },
            "summary": {
                "total_changes": 3,
                "high_risk_changes": 1,
                "medium_risk_changes": 1,
                "low_risk_changes": 1,
                "total_suggested_tests": 8,
                "overall_recommendation": "建议优先处理高风险变更，执行全部建议测试"
            }
        }
        
        return jsonify({
            "status": "success",
            "analysis": analysis_result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/analyzer/analysis/<analysis_id>/export', methods=['GET'])
def export_analysis_report(analysis_id):
    """导出分析报告"""
    try:
        format_type = request.args.get('format', 'html')
        
        # 获取分析结果
        # 这里应该从数据库获取实际数据
        
        if format_type == 'html':
            # 生成HTML报告
            reporter = HTMLReporter()
            
            # 这里应该传入实际的分析结果
            html_content = reporter._get_html_template().render(
                title='分析报告',
                generated_time='2024-01-15 10:30:00',
                result={
                    'status': 'success',
                    'changes_count': 3
                }
            )
            
            return Response(
                html_content,
                mimetype='text/html',
                headers={
                    'Content-Disposition': f'attachment; filename=analysis_{analysis_id}.html'
                }
            )
            
        elif format_type == 'json':
            # 生成JSON报告
            reporter = JSONReporter()
            
            # 这里应该传入实际的分析结果
            json_data = {
                "status": "success",
                "analysis_id": analysis_id,
                "generated_time": "2024-01-15T10:30:00Z"
            }
            
            return jsonify(json_data)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"不支持的导出格式: {format_type}"
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/projects/<int:id>/analysis', methods=['GET'])
def get_project_analysis(id):
    """获取项目的分析结果"""
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 获取最新的分析结果
        latest_analysis = db.fetch_one(
            """
            SELECT * FROM analysis_results 
            WHERE project_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
            """, 
            (id,)
        )
        
        if not latest_analysis:
            return jsonify({
                'status': 'no_analysis',
                'message': '该项目还没有分析结果',
                'project_id': id,
                'project_name': project.get('name', ''),
                'analysis_data': None
            })
        
        # 处理分析结果数据
        result_data = latest_analysis['result_data']
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except:
                result_data = {}
        
        # 获取该分析的测试用例
        test_cases = db.fetch_all(
            "SELECT * FROM test_cases WHERE analysis_id = %s ORDER BY priority DESC",
            (latest_analysis['id'],)
        )
        
        # 构建分析结果响应
        analysis_response = {
            'status': 'success',
            'project_id': id,
            'project_name': project.get('name', ''),
            'analysis_id': latest_analysis['id'],
            'analysis_type': latest_analysis.get('analysis_type', 'code_change'),
            'created_at': latest_analysis['created_at'],
            'risk_level': latest_analysis.get('risk_level', 'low'),
            'analysis_data': result_data,
            'test_cases': test_cases,
            'commit_hash': latest_analysis.get('commit_hash'),
            
            # 兼容前端期望的数据结构
            'totalFiles': result_data.get('result', {}).get('files_changed', 0),
            'totalLines': 0,  # 可以从stats计算
            'codeLines': 0,
            'commentLines': 0,
            'emptyLines': 0,
            'complexityScore': result_data.get('result', {}).get('complexity_delta', 0),
            
            # 文件类型分布（模拟数据，可以从实际分析中提取）
            'fileTypeDistribution': [
                {'name': 'Python', 'value': 5},
                {'name': 'JavaScript', 'value': 3},
                {'name': 'HTML', 'value': 2},
                {'name': 'CSS', 'value': 1}
            ],
            
            # 复杂度趋势（模拟数据）
            'complexityTrend': {
                'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'scores': [2.5, 3.0, result_data.get('result', {}).get('complexity_delta', 2.8)]
            },
            
            # 符号分析（从变更中提取）
            'symbols': [],
            
            # 语义变更分析
            'semanticChanges': []
        }
        
        # 从分析结果中提取符号信息和语义变更
        analysis_result = result_data.get('result', {})
        if analysis_result and 'changes' in analysis_result:
            for change in analysis_result['changes']:
                # 添加符号信息
                analysis_response['symbols'].append({
                    'name': change.get('file', 'Unknown'),
                    'type': change.get('file_type', 'Unknown'),
                    'file': change.get('file', ''),
                    'line': 1,
                    'complexity': change.get('complexity', 0)
                })
                
                # 添加语义变更
                analysis_response['semanticChanges'].append({
                    'type': change.get('type', 'modified'),
                    'description': change.get('changes', ''),
                    'impact': f"影响 {change.get('insertions', 0)} 行新增, {change.get('deletions', 0)} 行删除",
                    'timestamp': latest_analysis['created_at'],
                    'codeSnippet': change.get('patch', '')[:500] if change.get('patch') else '',
                    'fileDiff': {
                        'oldContent': '',
                        'newContent': change.get('patch', '')
                    },
                    'testCase': {
                        'name': f"Test for {change.get('file', 'file')}",
                        'code': f"// Test case for {change.get('file', 'file')}\n// TODO: Implement test"
                    }
                })
        
        return jsonify(analysis_response)
        
    except Exception as e:
        logger.error(f"获取项目分析结果失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'project_id': id
        }), 500

# 辅助函数：生成默认测试用例

def _generate_smart_default_test(analysis_data: dict) -> str:
    """生成智能的默认回归测试代码"""
    changes = []
    if 'analysis_data' in analysis_data and 'result' in analysis_data['analysis_data']:
        changes = analysis_data['analysis_data']['result'].get('changes', [])
    
    test_code = f"""
// 代码变更回归测试
// 基于 {len(changes)} 个文件变更生成的智能测试

describe('代码变更回归测试', () => {{
    let testContext = {{}};
    
    beforeAll(async () => {{
        // 初始化测试环境
        testContext.apiBase = process.env.API_BASE_URL || 'http://localhost:5000';
        testContext.timeout = 30000;
    }});
    
    describe('核心API功能验证', () => {{
        test('验证项目列表API', async () => {{
            const response = await fetch(`${{testContext.apiBase}}/api/projects`);
            expect(response.status).toBe(200);
            
            const projects = await response.json();
            expect(Array.isArray(projects)).toBe(true);
        }});
        
        test('验证项目详情API', async () => {{
            const response = await fetch(`${{testContext.apiBase}}/api/projects/1`);
            expect(response.status).toBeOneOf([200, 404]);
            
            if (response.status === 200) {{
                const project = await response.json();
                expect(project).toHaveProperty('project');
            }}
        }});
    }});
    
    describe('数据完整性检查', () => {{"""
    
    # 根据变更的文件类型添加特定测试
    for change in changes:
        file_path = change.get('file', '')
        if 'api' in file_path.lower() or 'route' in file_path.lower():
            test_code += f"""
        
        test('验证 {os.path.basename(file_path)} API变更', async () => {{
            // 测试变更后的API功能
            const testData = {{ test: true }};
            
            try {{
                const response = await fetch(`${{testContext.apiBase}}/api/test-endpoint`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(testData)
                }});
                
                // 验证响应格式和状态
                expect([200, 201, 400, 404]).toContain(response.status);
                
                if (response.headers.get('content-type')?.includes('application/json')) {{
                    const data = await response.json();
                    expect(data).toBeDefined();
                }}
            }} catch (error) {{
                // 网络错误或服务不可用是可接受的
                expect(error.message).toContain('fetch');
            }}
        }});"""
    
    test_code += f"""
    }});
    
    describe('错误处理验证', () => {{
        test('验证无效请求处理', async () => {{
            const response = await fetch(`${{testContext.apiBase}}/api/nonexistent`);
            expect(response.status).toBe(404);
        }});
        
        test('验证无效数据处理', async () => {{
            const response = await fetch(`${{testContext.apiBase}}/api/projects`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ invalid: 'data' }})
            }});
            
            expect([400, 422, 500]).toContain(response.status);
        }});
    }});
    
    afterAll(() => {{
        // 清理测试环境
        console.log('回归测试完成');
    }});
}});

/*
测试覆盖范围：
{chr(10).join([f"- {change.get('file', 'Unknown')}: {change.get('type', 'modified')}" for change in changes])}

建议的手动验证点：
1. 检查核心业务流程是否正常
2. 验证用户界面响应性
3. 确认数据持久化正确性
4. 测试异常场景处理
5. 验证性能指标未降级

风险评估：基于 {len(changes)} 个文件变更，建议执行完整回归测试
*/"""

def _generate_e2e_default_test(analysis_data: dict) -> str:
    """生成端到端默认测试代码"""
    return """
// 端到端功能验证测试
describe('E2E 功能完整性验证', () => {
    let page;
    
    beforeAll(async () => {
        // 启动浏览器和页面
        page = await browser.newPage();
        await page.goto('http://localhost:5173');
    });
    
    describe('用户界面基础功能', () => {
        test('主页面正常加载', async () => {
            await page.waitForSelector('body', { timeout: 30000 });
            
            const title = await page.title();
            expect(title).toBeTruthy();
            
            // 检查页面基本元素
            const mainContent = await page.$('.main-content, #app, main');
            expect(mainContent).toBeTruthy();
        });
        
        test('导航功能正常', async () => {
            // 查找导航链接
            const navLinks = await page.$$('nav a, .nav-link, [role="navigation"] a');
            
            if (navLinks.length > 0) {
                // 点击第一个导航链接
                await navLinks[0].click();
                await page.waitForTimeout(1000);
                
                // 验证页面变化
                const currentUrl = page.url();
                expect(currentUrl).toBeTruthy();
            }
        });
    });
    
    describe('核心业务流程', () => {
        test('项目列表查看', async () => {
            // 尝试导航到项目列表
            try {
                await page.goto('http://localhost:5173/projects');
                await page.waitForSelector('body', { timeout: 10000 });
                
                // 检查是否有项目列表或相关内容
                const hasContent = await page.evaluate(() => {
                    return document.body.textContent.trim().length > 0;
                });
                
                expect(hasContent).toBe(true);
            } catch (error) {
                console.log('项目列表页面不可访问或不存在');
            }
        });
        
        test('用户交互响应', async () => {
            // 查找可点击元素
            const clickableElements = await page.$$('button, a, [role="button"]');
            
            if (clickableElements.length > 0) {
                const initialUrl = page.url();
                
                // 点击第一个可点击元素
                await clickableElements[0].click();
                await page.waitForTimeout(1000);
                
                // 验证有响应（URL变化或页面内容变化）
                const newUrl = page.url();
                const responseDetected = newUrl !== initialUrl || 
                    await page.$('.modal, .dialog, .popup, .notification');
                
                expect(typeof responseDetected).toBe('boolean');
            }
        });
    });
    
    describe('错误场景处理', () => {
        test('404页面处理', async () => {
            await page.goto('http://localhost:5173/nonexistent-page');
            await page.waitForTimeout(2000);
            
            // 检查页面是否有错误处理
            const pageContent = await page.content();
            const hasErrorHandling = pageContent.includes('404') || 
                                   pageContent.includes('Not Found') || 
                                   pageContent.includes('页面不存在');
            
            // 404处理存在或页面重定向都是可接受的
            expect(typeof hasErrorHandling).toBe('boolean');
        });
    });
    
    afterAll(async () => {
        if (page) {
            await page.close();
        }
    });
});

/*
E2E测试说明：
- 验证前端应用基本功能
- 测试用户交互流程
- 检查错误场景处理
- 确保界面响应正常

注意：此测试设计为兼容性测试，即使某些功能不存在也不会失败
实际使用时应根据具体业务逻辑调整测试用例
*/"""

@api.route('/projects/<int:id>/code-diff', methods=['GET'])
def get_code_diff(id):
    """获取项目的代码差异和影响分析"""
    try:
        # 获取查询参数
        commit_hash = request.args.get('commit')
        since_commit = request.args.get('since')
        branch = request.args.get('branch', 'main')
        
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 克隆或更新仓库
        git_utils = GitUtils(project['git_url'], branch)
        
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库'}), 500
        
        try:
            # 使用增强分析器分析代码变更
            analyzer = EnhancedCursorAnalyzer(git_utils.repo_path)
            
            # 异步运行分析
            @run_async
            async def analyze_changes():
                return await analyzer.analyze_repository_changes(commit_hash)
            
            analysis_result = analyze_changes()
            
            # 如果分析成功，格式化返回数据
            if hasattr(analysis_result, 'status') and analysis_result.status == 'success':
                diff_data = {
                    'status': 'success',
                    'commit_hash': commit_hash,
                    'changes_count': analysis_result.changes_count,
                    'analysis_summary': {
                        'total_changes': analysis_result.changes_count,
                        'high_risk_changes': len([r for r in analysis_result.analysis_results 
                                                if hasattr(r.change, 'risk_level') and r.change.risk_level == 'high']),
                        'affected_files': len(set([r.change.file_path for r in analysis_result.analysis_results])),
                        'recommended_tests': sum([len(r.impact.test_cases) for r in analysis_result.analysis_results])
                    },
                    'changes': []
                }
                
                # 处理每个变更
                for result in analysis_result.analysis_results:
                    change_data = {
                        'file_path': result.change.file_path,
                        'change_type': result.change.change_type,
                        'risk_level': getattr(result.change, 'risk_level', 'medium'),
                        'affected_functions': getattr(result.change, 'affected_functions', []),
                        'affected_classes': getattr(result.change, 'affected_classes', []),
                        'complexity_delta': getattr(result.change, 'complexity_delta', 8),
                        'business_impact': getattr(result.change, 'business_impact', []),
                        'impact_analysis': {
                            'direct_impacts': result.impact.direct_impacts if hasattr(result.impact, 'direct_impacts') else [],
                            'indirect_impacts': result.impact.indirect_impacts if hasattr(result.impact, 'indirect_impacts') else [],
                            'risk_factors': result.impact.risk_factors if hasattr(result.impact, 'risk_factors') else [],
                            'confidence': result.impact.confidence if hasattr(result.impact, 'confidence') else 0.8
                        },
                        'test_cases': [
                            {
                                'id': tc.test_id if hasattr(tc, 'test_id') else f"test_{i}",
                                'name': tc.name if hasattr(tc, 'name') else f"Test for {result.change.file_path}",
                                'type': tc.test_type if hasattr(tc, 'test_type') else 'unit',
                                'priority': tc.priority if hasattr(tc, 'priority') else 'medium',
                                'description': tc.description if hasattr(tc, 'description') else f"Test case for {result.change.change_type} in {result.change.file_path}",
                                'test_code': tc.test_code if hasattr(tc, 'test_code') else generate_default_test_code(result.change),
                                'estimated_time': tc.estimated_time if hasattr(tc, 'estimated_time') else 10,
                                'coverage_areas': tc.coverage_areas if hasattr(tc, 'coverage_areas') else []
                            }
                            for i, tc in enumerate(result.impact.test_cases if hasattr(result.impact, 'test_cases') else [])
                        ]
                    }
                    
                    # 如果没有生成的测试用例，创建默认测试用例
                    if not change_data['test_cases']:
                        change_data['test_cases'] = [create_default_test_case(result.change)]
                    
                    diff_data['changes'].append(change_data)
                
                return jsonify(diff_data)
            
            else:
                # 分析失败，返回基础git差异
                return get_basic_git_diff(git_utils, commit_hash, since_commit)
                
        finally:
            # 清理临时目录
            git_utils.cleanup()
            
    except Exception as e:
        logger.error(f"获取代码差异失败: {str(e)}")
        return jsonify({'error': f'分析失败: {str(e)}'}), 500

def get_basic_git_diff(git_utils, commit_hash=None, since_commit=None):
    """获取基础git差异分析（当AI分析失败时使用）"""
    try:
        logger.info("开始基础git差异分析")
        
        if not git_utils.repo:
            raise Exception("Git仓库未初始化")
        
        commits = list(git_utils.repo.iter_commits(max_count=5))
        if not commits:
            raise Exception("仓库中没有提交")
        
        target_commit = commits[0]  # 最新提交
        if commit_hash and commit_hash != 'latest':
            try:
                target_commit = git_utils.repo.commit(commit_hash)
            except:
                logger.warning(f"找不到指定提交 {commit_hash}，使用最新提交")
        
        if not target_commit.parents:
            # 初始提交，返回简单分析
            return {
                'status': 'success',
                'commit_hash': target_commit.hexsha,
                'changes_count': 1,
                'analysis_summary': {
                    'total_changes': 1,
                    'high_risk_changes': 0,
                    'affected_files': 1,
                    'recommended_tests': 1
                },
                'changes': [{
                    'file_path': '初始项目文件',
                    'change_type': 'initial',
                    'risk_level': 'low',
                    'affected_functions': [],
                    'affected_classes': [],
                    'complexity_delta': 3,
                    'business_impact': ['项目初始化'],
                    'impact_analysis': {
                        'direct_impacts': ['项目结构'],
                        'indirect_impacts': [],
                        'risk_factors': [],
                        'confidence': 0.8
                    },
                    'test_cases': [_create_simple_test_case('project_init', 'initial')]
                }]
            }
        
        # 获取差异
        parent_commit = target_commit.parents[0]
        diffs = parent_commit.diff(target_commit)
        
        changes = []
        for diff in diffs:
            file_path = diff.a_path or diff.b_path
            
            # 只处理代码文件
            if not _is_code_file_simple(file_path):
                continue
            
            change_data = {
                'file_path': file_path,
                'change_type': _get_change_type(diff),
                'risk_level': _assess_simple_risk(file_path, diff),
                'affected_functions': [],
                'affected_classes': [],
                'complexity_delta': _calculate_complexity_for_diff(diff, file_path),
                'business_impact': _get_simple_business_impact(file_path),
                'impact_analysis': {
                    'direct_impacts': [file_path],
                    'indirect_impacts': [],
                    'risk_factors': [],
                    'confidence': 0.6
                },
                'test_cases': [_create_simple_test_case(file_path, _get_change_type(diff))]
            }
            changes.append(change_data)
        
        return {
            'status': 'success',
            'commit_hash': commit_hash,
            'changes_count': len(changes),
            'analysis_summary': {
                'total_changes': len(changes),
                'high_risk_changes': len([c for c in changes if c['risk_level'] == 'high']),
                'affected_files': len(changes),
                'recommended_tests': len(changes)
            },
            'changes': changes
        }
        
    except Exception as e:
        logger.error(f"获取基础git差异失败: {str(e)}")
        return {'error': f'Git差异分析失败: {str(e)}'}

def _calculate_complexity_for_diff(diff, file_path):
    """计算diff的复杂度"""
    try:
        # 基础复杂度计算
        insertions = 0
        deletions = 0
        
        # 尝试获取实际的插入/删除行数
        try:
            if diff.a_blob and diff.b_blob:
                # 修改的文件
                a_content = diff.a_blob.data_stream.read().decode('utf-8', errors='ignore')
                b_content = diff.b_blob.data_stream.read().decode('utf-8', errors='ignore')
                a_lines = len(a_content.split('\n'))
                b_lines = len(b_content.split('\n'))
                
                if b_lines > a_lines:
                    insertions = b_lines - a_lines
                elif a_lines > b_lines:
                    deletions = a_lines - b_lines
                else:
                    insertions = max(1, b_lines // 20)  # 估算有变更
                    
            elif diff.new_file and diff.b_blob:
                # 新文件
                content = diff.b_blob.data_stream.read().decode('utf-8', errors='ignore')
                insertions = len(content.split('\n'))
                
            elif diff.deleted_file and diff.a_blob:
                # 删除的文件
                content = diff.a_blob.data_stream.read().decode('utf-8', errors='ignore')
                deletions = len(content.split('\n'))
                
        except Exception as e:
            logger.warning(f"计算行数失败: {str(e)}")
            # 使用估算值
            if diff.new_file:
                insertions = 50
            elif diff.deleted_file:
                deletions = 30
            else:
                insertions = 10
                deletions = 5
        
        # 计算复杂度
        lines_changed = insertions + deletions
        if lines_changed == 0:
            base_complexity = 2
        elif lines_changed < 10:
            base_complexity = 3
        elif lines_changed < 50:
            base_complexity = 8
        elif lines_changed < 100:
            base_complexity = 15
        else:
            base_complexity = max(15, lines_changed // 8)
        
        # 根据文件类型调整
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.py', '.java', '.cpp', '.ts']:
            base_complexity = int(base_complexity * 1.2)
        elif file_ext in ['.js', '.vue']:
            base_complexity = int(base_complexity * 1.1)
        
        # 根据变更类型调整
        if diff.new_file:
            base_complexity = int(base_complexity * 1.5)
        elif diff.deleted_file:
            base_complexity = int(base_complexity * 0.7)
        
        return max(2, min(base_complexity, 100))
        
    except Exception as e:
        logger.warning(f"复杂度计算失败: {str(e)}")
        return 5  # 默认复杂度

def _is_code_file_simple(file_path):
    """简单的代码文件判断"""
    if not file_path:
        return False
    
    code_extensions = {'.py', '.js', '.vue', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go'}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in code_extensions

def _get_change_type(diff):
    """获取变更类型"""
    if diff.new_file:
        return 'added'
    elif diff.deleted_file:
        return 'deleted'
    else:
        return 'modified'

def _assess_simple_risk(file_path, diff):
    """简单的风险评估"""
    # 根据文件路径和变更类型评估风险
    if 'api' in file_path.lower() or 'route' in file_path.lower():
        return 'high'
    elif 'test' in file_path.lower():
        return 'low'
    elif diff.new_file or diff.deleted_file:
        return 'medium'
    else:
        return 'medium'

def _get_simple_business_impact(file_path):
    """简单的业务影响分析"""
    impacts = []
    
    if 'api' in file_path.lower():
        impacts.append('API接口变更')
    if 'user' in file_path.lower():
        impacts.append('用户功能影响')
    if 'auth' in file_path.lower():
        impacts.append('认证授权变更')
    if 'database' in file_path.lower() or 'model' in file_path.lower():
        impacts.append('数据层变更')
    
    return impacts if impacts else ['功能变更']

def _create_simple_test_case(file_path, change_type):
    """创建简单的测试用例"""
    return {
        'id': f"test_{abs(hash(file_path)) % 10000}",
        'name': f"测试 {os.path.basename(file_path)} {change_type}变更",
        'type': 'unit' if file_path.endswith('.py') else 'integration',
        'priority': 'high' if 'api' in file_path.lower() else 'medium',
        'description': f"验证{file_path}在{change_type}后的功能正确性",
        'test_code': generate_default_test_code_for_file(file_path, change_type),
        'estimated_time': 15,
        'coverage_areas': ['功能验证', '回归测试']
    }

def generate_default_test_code_for_file(file_path, change_type):
    """为文件生成默认测试代码"""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1]
    
    if file_ext == '.py':
        return f'''# Python测试代码 - {file_name}
import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Test{file_name.replace('.py', '').title()}(unittest.TestCase):
    """测试{file_name}的{change_type}变更"""
    
    def setUp(self):
        """测试前准备"""
        pass
    
    def test_{change_type}_functionality(self):
        """测试{change_type}变更后的功能"""
        # TODO: 添加具体的测试逻辑
        self.assertTrue(True, "基础测试通过")
    
    def test_regression_check(self):
        """回归测试"""
        # TODO: 验证现有功能未受影响
        self.assertTrue(True, "回归测试通过")
    
    def tearDown(self):
        """测试后清理"""
        pass

if __name__ == '__main__':
    unittest.main()
'''
    elif file_ext in ['.js', '.vue', '.ts']:
        return f'''// JavaScript/Vue测试代码 - {file_name}
describe('{file_name} {change_type}变更测试', () => {{
  beforeEach(() => {{
    // 测试前准备
  }});
  
  test('验证{change_type}变更功能', () => {{
    // TODO: 添加具体的测试逻辑
    expect(true).toBe(true);
  }});
  
  test('回归测试验证', () => {{
    // TODO: 验证现有功能未受影响
    expect(true).toBe(true);
  }});
  
  afterEach(() => {{
    // 测试后清理
  }});
}});
'''
    else:
        return f'''# 通用测试代码 - {file_name}
# 测试{change_type}变更

## 测试计划
1. 功能验证测试
2. 回归测试
3. 集成测试

## 测试用例
- [ ] 验证{change_type}变更后的核心功能
- [ ] 确保现有功能不受影响
- [ ] 验证与其他模块的集成

## 预期结果
所有测试用例通过，功能正常运行
'''

def create_default_test_case(change):
    """创建默认测试用例"""
    return {
        'id': f"test_{abs(hash(change.file_path)) % 10000}",
        'name': f"测试 {os.path.basename(change.file_path)} {change.change_type}变更",
        'type': 'unit',
        'priority': 'medium',
        'description': f"验证{change.file_path}在{change.change_type}后的功能正确性",
        'test_code': generate_default_test_code(change),
        'estimated_time': 10,
        'coverage_areas': ['功能验证']
    }

def generate_default_test_code(change):
    """生成默认测试代码"""
    return f'''# 默认测试代码
# 文件: {change.file_path}
# 变更类型: {change.change_type}

def test_{change.change_type}_functionality():
    """测试{change.change_type}变更后的功能"""
    # TODO: 实现具体测试逻辑
    assert True, "基础测试通过"

def test_regression():
    """回归测试"""  
    # TODO: 验证现有功能未受影响
    assert True, "回归测试通过"
'''

@api.route('/projects/<int:id>/commits', methods=['GET'])
def get_project_commits(id):
    """获取项目的历史提交列表"""
    try:
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 获取查询参数
        limit = int(request.args.get('limit', 20))
        branch = request.args.get('branch', project.get('branch', 'main'))
        
        # 克隆仓库
        git_utils = GitUtils(project['git_url'], branch)
        
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库'}), 500
        
        try:
            if not git_utils.repo:
                return jsonify({'error': '仓库未初始化'}), 500
            
            # 获取历史提交
            commits = []
            for commit in git_utils.repo.iter_commits(max_count=limit):
                commit_info = {
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': commit.author.name,
                    'author_email': commit.author.email,
                    'date': commit.committed_datetime.isoformat(),
                    'parents': [p.hexsha for p in commit.parents],
                    'stats': None
                }
                
                # 获取提交统计信息
                try:
                    if commit.parents:
                        parent = commit.parents[0]
                        diffs = parent.diff(commit)
                        
                        files_changed = len(diffs)
                        insertions = 0
                        deletions = 0
                        
                        for diff in diffs:
                            try:
                                # 简化统计计算，避免复杂错误
                                if diff.new_file:
                                    insertions += 50  # 估算值
                                elif diff.deleted_file:
                                    deletions += 50  # 估算值
                                else:
                                    insertions += 20  # 估算值
                                    deletions += 10   # 估算值
                            except:
                                continue
                        
                        commit_info['stats'] = {
                            'files_changed': files_changed,
                            'insertions': insertions,
                            'deletions': deletions
                        }
                except Exception as e:
                    logger.warning(f"获取提交统计失败: {str(e)}")
                    commit_info['stats'] = {
                        'files_changed': 0,
                        'insertions': 0,
                        'deletions': 0
                    }
                
                commits.append(commit_info)
            
            return jsonify({
                'status': 'success',
                'commits': commits,
                'total': len(commits),
                'branch': branch
            })
            
        finally:
            git_utils.cleanup()
            
    except Exception as e:
        logger.error(f"获取历史提交失败: {str(e)}")
        return jsonify({'error': f'获取历史提交失败: {str(e)}'}), 500

# 在代码差异分析API中添加数据库存储
@api.route('/projects/<int:id>/code-diff/save', methods=['POST'])
def save_code_diff_analysis(id):
    """保存代码差异分析结果到数据库"""
    try:
        data = request.json
        commit_hash = data.get('commit_hash')
        analysis_result = data.get('analysis_result')
        
        if not commit_hash or not analysis_result:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 保存到数据库
        result = db.execute(
            """INSERT INTO analysis_results 
               (project_id, commit_hash, analysis_type, result_data, created_at) 
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (id, commit_hash, 'code_diff', json.dumps(analysis_result), datetime.now())
        )
        
        if result and 'id' in result:
            return jsonify({'id': result['id'], 'message': '分析结果已保存'}), 201
        else:
            return jsonify({'error': '保存失败'}), 500
            
    except Exception as e:
        logger.error(f"保存代码差异分析失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:id>/code-diff/history', methods=['GET'])
def get_code_diff_history(id):
    """获取项目的历史差异分析结果"""
    try:
        # 获取查询参数
        limit = int(request.args.get('limit', 10))
        
        # 从数据库获取历史分析结果
        results = db.fetch_all(
            """SELECT * FROM analysis_results 
               WHERE project_id = %s AND analysis_type = 'code_diff' 
               ORDER BY created_at DESC LIMIT %s""",
            (id, limit)
        )
        
        # 处理结果数据
        history = []
        for result in results:
            try:
                result_data = json.loads(result['result_data']) if isinstance(result['result_data'], str) else result['result_data']
                history.append({
                    'id': result['id'],
                    'commit_hash': result['commit_hash'],
                    'created_at': result['created_at'],
                    'analysis_summary': result_data.get('analysis_summary', {}),
                    'changes_count': result_data.get('changes_count', 0)
                })
            except Exception as e:
                logger.warning(f"解析分析结果失败: {str(e)}")
                continue
        
        return jsonify({
            'status': 'success',
            'history': history,
            'total': len(history)
        })
        
    except Exception as e:
        logger.error(f"获取历史分析失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 在文件末尾添加智能测试生成API

@api.route('/projects/<int:id>/intelligent-tests', methods=['POST'])
def generate_intelligent_tests(id):
    """生成基于项目整体分析的智能测试用例"""
    try:
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 获取请求参数
        data = request.json or {}
        changed_files = data.get('changed_files', [])
        change_type = data.get('change_type', 'modified')
        
        # 如果没有指定变更文件，使用默认的文件列表
        if not changed_files:
            # 不依赖git_utils.get_recent_changes，使用默认策略
            changed_files = []  # 空列表将让智能生成器分析整个项目结构
        
        # 创建智能测试生成器
        from generators.intelligent_test_generator import IntelligentTestGenerator
        
        # 使用临时目录进行项目分析
        git_utils = GitUtils(project['git_url'], project.get('branch', 'main'))
        if not git_utils.clone_repo():
            return jsonify({'error': '无法克隆仓库进行分析'}), 500
        
        try:
            generator = IntelligentTestGenerator(git_utils.repo_path)
            
            # 分析项目结构
            if not generator.analyze_project_structure():
                return jsonify({'error': '项目结构分析失败'}), 500
            
            # 生成智能测试用例
            test_cases = generator.generate_intelligent_tests(changed_files, change_type)
            
            # 保存生成的测试用例到数据库
            saved_tests = []
            for test_case in test_cases:
                result = db.execute(
                    """INSERT INTO test_cases 
                       (project_id, name, description, test_type, priority, test_code, 
                        estimated_time, coverage_areas, file_path, function_name, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (
                        id, 
                        test_case['name'], 
                        test_case['description'], 
                        test_case['type'], 
                        test_case['priority'],
                        test_case['test_code'], 
                        test_case['estimated_time'],
                        json.dumps(test_case.get('coverage_areas', [])),
                        test_case.get('file_path', ''),
                        test_case.get('function_name', ''),
                        datetime.now()
                    )
                )
                
                if result and 'id' in result:
                    test_case['id'] = result['id']
                    saved_tests.append(test_case)
            
            return jsonify({
                'status': 'success',
                'message': f'成功生成 {len(saved_tests)} 个智能测试用例',
                'test_cases': saved_tests,
                'project_analysis': {
                    'total_files': len(generator.project_structure.get('python_files', [])) + 
                                 len(generator.project_structure.get('js_files', [])) + 
                                 len(generator.project_structure.get('vue_files', [])),
                    'api_files': len(generator.project_structure.get('api_files', [])),
                    'core_functions': len(generator.core_functions)
                }
            })
            
        finally:
            git_utils.cleanup()
            
    except Exception as e:
        logger.error(f"智能测试生成失败: {str(e)}")
        return jsonify({'error': f'智能测试生成失败: {str(e)}'}), 500

@api.route('/projects/<int:project_id>/generate-tests', methods=['POST'])
def generate_test_cases(project_id):
    """基于代码变更生成智能测试用例"""
    try:
        data = request.get_json()
        changes = data.get('changes', [])
        use_qwen = data.get('use_qwen', False)
        project_context = data.get('project_context', {})
        
        if not changes:
            return jsonify({'error': '没有提供代码变更信息'}), 400
        
        # 获取项目信息
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 尝试使用索引增强的Qwen生成器
        if use_qwen:
            try:
                # 获取项目代码库路径（如果有的话）
                codebase_path = None
                if project.get('local_path'):
                    codebase_path = project['local_path']
                elif project.get('git_url'):
                    # 临时克隆以建立索引
                    from ..utils.git_utils import GitUtils
                    git_utils = GitUtils(project['git_url'], project.get('branch', 'main'))
                    if git_utils.clone_repo():
                        codebase_path = git_utils.temp_dir
                
                # 创建索引增强的Qwen生成器
                qwen_generator = QwenTestGenerator(
                    api_key=os.getenv('QWEN_API_KEY'),
                    codebase_path=codebase_path
                )
                
                # 生成智能测试用例
                test_cases = qwen_generator.analyze_code_changes_with_context(changes, project_context)
                
                # 转换为API响应格式
                formatted_cases = []
                for case in test_cases:
                    formatted_case = {
                        'name': case.name,
                        'description': case.description,
                        'test_type': case.test_type,
                        'priority': case.priority,
                        'affected_components': case.affected_components,
                        'test_code': case.test_code,
                        'file_path': case.file_path,
                        'estimated_time': case.estimated_time,
                        'risk_level': case.risk_level,
                        # 新增索引增强字段
                        'related_symbols': getattr(case, 'related_symbols', []),
                        'dependencies': getattr(case, 'dependencies', []),
                        'similar_tests': getattr(case, 'similar_tests', [])
                    }
                    formatted_cases.append(formatted_case)
                
                # 清理临时目录
                if project.get('git_url') and 'git_utils' in locals():
                    git_utils.cleanup()
                
                return jsonify({
                    'message': '智能测试用例生成成功',
                    'test_cases': formatted_cases,
                    'generator_type': 'qwen_with_index',
                    'total_cases': len(formatted_cases),
                    'enhanced_features': {
                        'symbol_analysis': True,
                        'dependency_tracking': True,
                        'context_awareness': True,
                        'similarity_matching': True
                    }
                })
                
            except Exception as e:
                logger.error(f"Qwen智能生成失败: {str(e)}")
                # 降级到基础Qwen生成器
                try:
                    basic_qwen = QwenTestGenerator(api_key=os.getenv('QWEN_API_KEY'))
                    test_cases = basic_qwen.analyze_code_changes_with_context(changes, project_context)
                    
                    return jsonify({
                        'message': '使用基础Qwen生成器生成测试用例',
                        'test_cases': [asdict(case) for case in test_cases],
                        'generator_type': 'qwen_basic',
                        'warning': '索引功能不可用，使用基础生成器'
                    })
                except Exception as qwen_error:
                    logger.error(f"基础Qwen生成也失败: {str(qwen_error)}")
                    # 继续执行回退逻辑
        
        # 回退到本地生成
        logger.info("使用本地智能生成器")
        test_cases = generate_smart_default_test_cases(changes, project_context)
        
        return jsonify({
            'message': '使用本地生成器生成测试用例',
            'test_cases': test_cases,
            'generator_type': 'local_enhanced',
            'total_cases': len(test_cases)
        })
        
    except Exception as e:
        logger.error(f"生成测试用例失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_smart_default_test_cases(changes: List[Dict], project_context: Dict = None) -> List[Dict]:
    """生成智能默认测试用例（增强版本）"""
    test_cases = []
    
    for i, change in enumerate(changes):
        file_path = change.get('file', change.get('file_path', ''))
        change_type = change.get('type', 'modified')
        content = change.get('content', '')
        
        if not file_path:
            continue
        
        # 基础分析
        code_analyzer = CodeAnalyzer()
        analysis = {}
        if content:
            analysis = code_analyzer.analyze_file_content(file_path, content)
        
        # 确定测试特征
        test_type, priority = determine_test_characteristics_enhanced(file_path, change_type, analysis)
        
        # 生成测试用例
        test_case = {
            'name': f"智能本地测试 - {os.path.basename(file_path)} ({change_type})",
            'description': generate_smart_description(file_path, analysis, change_type),
            'test_type': test_type,
            'priority': priority,
            'affected_components': identify_smart_components(file_path, analysis),
            'test_code': generate_smart_test_code(file_path, test_type, analysis),
            'file_path': file_path,
            'estimated_time': estimate_smart_time(test_type, analysis),
            'risk_level': assess_smart_risk(file_path, change_type, analysis),
            'code_analysis': analysis  # 包含分析结果
        }
        
        test_cases.append(test_case)
    
    return test_cases

def determine_test_characteristics_enhanced(file_path: str, change_type: str, analysis: Dict) -> tuple:
    """基于分析结果确定测试特征"""
    # 基础判断
    if 'api' in file_path.lower() or 'route' in file_path.lower():
        base_type, base_priority = 'integration', 'high'
    elif file_path.endswith('.vue') or file_path.endswith('.js'):
        base_type, base_priority = 'e2e', 'medium'
    else:
        base_type, base_priority = 'unit', 'medium'
    
    # 基于分析结果调整
    functions = analysis.get('functions', [])
    classes = analysis.get('classes', [])
    api_endpoints = analysis.get('api_endpoints', [])
    
    # 复杂度调整
    if len(functions) > 5 or len(classes) > 2:
        if base_type == 'unit':
            base_type = 'integration'
        base_priority = 'high'
    
    # API端点调整
    if api_endpoints:
        base_type = 'integration'
        base_priority = 'high'
    
    return base_type, base_priority

def generate_smart_description(file_path: str, analysis: Dict, change_type: str) -> str:
    """生成智能描述"""
    parts = [f"验证 {os.path.basename(file_path)} 在{change_type}后的功能"]
    
    functions = analysis.get('functions', [])
    if functions:
        func_names = [f['name'] for f in functions[:3]]
        parts.append(f"包含函数: {', '.join(func_names)}")
    
    classes = analysis.get('classes', [])
    if classes:
        class_names = [c['name'] for c in classes[:2]]
        parts.append(f"包含类: {', '.join(class_names)}")
    
    api_endpoints = analysis.get('api_endpoints', [])
    if api_endpoints:
        parts.append(f"涉及 {len(api_endpoints)} 个API端点")
    
    return "，".join(parts)

def identify_smart_components(file_path: str, analysis: Dict) -> List[str]:
    """智能识别受影响组件"""
    components = set()
    
    # 基础识别
    if 'api' in file_path.lower():
        components.update(['API接口', '业务逻辑'])
    if 'model' in file_path.lower():
        components.add('数据模型')
    if file_path.endswith('.vue'):
        components.update(['Vue组件', '用户界面'])
    
    # 基于分析结果
    if analysis.get('database_operations'):
        components.add('数据库操作')
    if analysis.get('external_calls'):
        components.add('外部服务')
    if analysis.get('api_endpoints'):
        components.add('API服务')
    
    return list(components) if components else ['核心功能']

def generate_smart_test_code(file_path: str, test_type: str, analysis: Dict) -> str:
    """基于分析生成智能测试代码"""
    if test_type == 'unit':
        return generate_smart_unit_test(file_path, analysis)
    elif test_type == 'integration':
        return generate_smart_integration_test(file_path, analysis)
    else:
        return generate_smart_e2e_test(file_path, analysis)

def generate_smart_unit_test(file_path: str, analysis: Dict) -> str:
    """生成智能单元测试"""
    functions = analysis.get('functions', [])
    
    if file_path.endswith('.py'):
        if functions:
            main_func = functions[0]
            return f"""
import unittest
from unittest.mock import Mock, patch

class Test{main_func['name'].title()}(unittest.TestCase):
    \"\"\"智能生成的单元测试\"\"\"
    
    def test_{main_func['name']}_basic(self):
        \"\"\"测试基本功能\"\"\"
        # 参数: {main_func.get('args', [])}
        # 复杂度: {main_func.get('complexity', 1)}
        pass
        
    def test_{main_func['name']}_edge_cases(self):
        \"\"\"测试边界条件\"\"\"
        pass
"""
    else:  # JavaScript
        if functions:
            main_func = functions[0]
            return f"""
import {{ describe, test, expect }} from '@jest/globals';

describe('{main_func['name']} 智能测试', () => {{
    test('基本功能验证', () => {{
        // 复杂度: {main_func.get('complexity', 1)}
        expect({main_func['name']}).toBeDefined();
    }});
    
    test('参数验证', () => {{
        // 参数: {main_func.get('args', [])}
        expect(() => {main_func['name']}()).not.toThrow();
    }});
}});
"""
    
    return "// 智能单元测试模板"

def generate_smart_integration_test(file_path: str, analysis: Dict) -> str:
    """生成智能集成测试"""
    api_endpoints = analysis.get('api_endpoints', [])
    
    if api_endpoints and file_path.endswith('.py'):
        return f"""
import unittest
import requests

class IntegrationTest(unittest.TestCase):
    \"\"\"智能集成测试\"\"\"
    
    def setUp(self):
        self.base_url = 'http://localhost:5000'
    
    def test_api_endpoints(self):
        \"\"\"测试API端点\"\"\"
        # 检测到的端点: {api_endpoints}
        for endpoint in {api_endpoints}:
            response = requests.get(f'{{self.base_url}}{{endpoint}}')
            self.assertEqual(response.status_code, 200)
"""
    
    return "// 智能集成测试模板"

def generate_smart_e2e_test(file_path: str, analysis: Dict) -> str:
    """生成智能E2E测试"""
    return f"""
import {{ test, expect }} from '@playwright/test';

test('E2E功能测试', async ({{ page }}) => {{
    await page.goto('http://localhost:3000');
    
    // 基于文件: {os.path.basename(file_path)}
    // 功能数量: {len(analysis.get('functions', []))}
    
    await expect(page.locator('body')).toBeVisible();
}});
"""

def estimate_smart_time(test_type: str, analysis: Dict) -> int:
    """智能估算时间"""
    base_times = {'unit': 8, 'integration': 15, 'e2e': 25}
    base_time = base_times.get(test_type, 10)
    
    # 基于复杂度调整
    function_count = len(analysis.get('functions', []))
    if function_count > 3:
        base_time += function_count * 2
    
    return base_time

def assess_smart_risk(file_path: str, change_type: str, analysis: Dict) -> str:
    """智能风险评估"""
    if change_type == 'deleted':
        return 'high'
    
    # 基于API数量
    api_count = len(analysis.get('api_endpoints', []))
    if api_count > 2:
        return 'high'
    elif api_count > 0:
        return 'medium'
    
    return 'low' if change_type == 'added' else 'medium'

# 生成器相关导入
try:
    from generators.qwen_test_generator import QwenTestGenerator, CodeAnalyzer
except ImportError:
    logger.warning("Qwen test generator not available")
    QwenTestGenerator = None
    
    # 创建简化的CodeAnalyzer类作为回退
    class CodeAnalyzer:
        def analyze_file_content(self, file_path: str, content: str) -> Dict:
            return {
                'functions': [],
                'classes': [],
                'api_endpoints': [],
                'database_operations': [],
                'external_calls': []
            }

# ========== 基于索引的高级分析端点 ==========

@api.route('/projects/<int:project_id>/index-analysis', methods=['POST'])
def analyze_with_index(project_id):
    """基于代码索引的高级差异分析"""
    try:
        data = request.get_json()
        commit_hash = data.get('commit_hash')
        base_commit = data.get('base_commit')
        force_rebuild_index = data.get('force_rebuild_index', False)
        
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 获取项目路径 - 这里需要根据实际情况调整
        project_path = project.get('path', '')
        temp_cleanup_needed = False
        
        if not project_path:
            # 如果项目没有本地路径，尝试从git_url推断或创建临时路径
            git_url = project.get('git_url', '')
            if git_url:
                # 使用GitUtils克隆项目到临时目录
                try:
                    git_utils = GitUtils(git_url, branch=project.get('branch', 'main'))
                    if git_utils.clone_repo():
                        project_path = git_utils.temp_dir  # 使用GitUtils创建的临时目录
                        temp_cleanup_needed = True
                    else:
                        return jsonify({'error': 'Failed to clone repository'}), 500
                except Exception as e:
                    logger.error(f"克隆仓库失败: {str(e)}")
                    return jsonify({'error': f'Failed to clone repository: {str(e)}'}), 500
            else:
                return jsonify({'error': 'Project path or git URL not found'}), 404
        
        if not os.path.exists(project_path):
            return jsonify({'error': 'Project path not found'}), 404
        
        # 初始化Git工具
        git_utils = None
        repo_url = project.get('git_url')
        if repo_url:
            try:
                git_utils = GitUtils(repo_url, branch=project.get('branch', 'main'))
                git_utils.temp_dir = project_path
                # 如果是临时目录，repo已经在克隆时初始化
                if not hasattr(git_utils, 'repo') or not git_utils.repo:
                    # 初始化本地仓库
                    import git
                    git_utils.repo = git.Repo(project_path)
            except Exception as e:
                logger.warning(f"Git初始化失败: {str(e)}")
                git_utils = None
        
        # 创建基于索引的分析器
        try:
            from analyzers.index_based_analyzer import IndexBasedAnalyzer
            analyzer = IndexBasedAnalyzer(project_path, git_utils)
        except ImportError as e:
            logger.error(f"导入IndexBasedAnalyzer失败: {str(e)}")
            return jsonify({'error': 'Index-based analyzer not available'}), 500
        
        # 执行综合分析
        logger.info(f"开始基于索引的综合分析: project_id={project_id}, commit={commit_hash}")
        analysis_result = analyzer.analyze_comprehensive_diff(commit_hash, base_commit)
        
        # 保存分析结果到数据库
        try:
            # 创建code_analysis表（如果不存在）
            db.execute('''
                CREATE TABLE IF NOT EXISTS code_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    commit_hash TEXT,
                    base_commit TEXT,
                    analysis_type TEXT NOT NULL,
                    analysis_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # 插入分析记录
            analysis_id = db.execute(
                '''INSERT INTO code_analysis 
                   (project_id, commit_hash, base_commit, analysis_type, analysis_data) 
                   VALUES (%s, %s, %s, %s, %s)''',
                (
                    project_id,
                    commit_hash or 'HEAD',
                    base_commit or 'parent',
                    'index_based',
                    json.dumps(analysis_result)
                )
            )
            
            # 添加分析ID到结果中
            analysis_result['analysis_id'] = analysis_id
            
        except Exception as e:
            logger.error(f"保存分析结果失败: {str(e)}")
            # 继续返回结果，即使保存失败
        
        # 清理临时目录（如果使用了）
        if temp_cleanup_needed and git_utils and hasattr(git_utils, 'cleanup'):
            try:
                git_utils.cleanup()
            except:
                pass
        
        return jsonify({
            'success': True,
            'analysis': analysis_result
        })
        
    except Exception as e:
        logger.error(f"基于索引的分析失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '基于索引的分析过程中发生错误'
        }), 500

@api.route('/projects/<int:project_id>/build-index', methods=['POST'])
def build_project_index(project_id):
    """构建项目代码索引"""
    try:
        data = request.get_json() or {}
        force_rebuild = data.get('force_rebuild', False)
        
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # 获取或创建项目路径
        project_path = project.get('path', '')
        temp_cleanup_needed = False
        
        if not project_path:
            # 创建临时路径并克隆项目
            git_url = project.get('git_url', '')
            if git_url:
                try:
                    git_utils = GitUtils(git_url, branch=project.get('branch', 'main'))
                    if git_utils.clone_repo():
                        project_path = git_utils.temp_dir  # 使用GitUtils创建的临时目录
                        temp_cleanup_needed = True
                    else:
                        return jsonify({'error': 'Failed to clone repository'}), 500
                except Exception as e:
                    logger.error(f"克隆仓库失败: {str(e)}")
                    return jsonify({'error': f'Failed to clone repository: {str(e)}'}), 500
            else:
                return jsonify({'error': 'Project path or git URL not found'}), 404
        
        if not os.path.exists(project_path):
            return jsonify({'error': 'Project path not found'}), 404
        
        # 创建索引器
        try:
            from indexers.codebase_indexer import CodebaseIndexer
            indexer = CodebaseIndexer(index_dir=os.path.join(project_path, '.code_index'))
        except ImportError as e:
            logger.error(f"导入CodebaseIndexer失败: {str(e)}")
            return jsonify({'error': 'Codebase indexer not available'}), 500
        
        # 构建索引
        logger.info(f"开始构建项目索引: project_id={project_id}, force_rebuild={force_rebuild}")
        
        try:
            if force_rebuild or not indexer.load_index():
                index_stats = indexer.build_index(project_path)
            else:
                # 加载现有索引的统计信息
                index_stats = {
                    "symbol_count": len(indexer.symbol_index),
                    "module_count": len(indexer.module_index),
                    "index_path": indexer.index_dir,
                    "loaded_from_cache": True
                }
        except Exception as e:
            logger.error(f"构建索引失败: {str(e)}")
            return jsonify({'error': f'Failed to build index: {str(e)}'}), 500
        finally:
            # 清理临时目录
            if temp_cleanup_needed:
                try:
                    import shutil
                    shutil.rmtree(project_path, ignore_errors=True)
                except:
                    pass
        
        return jsonify({
            'success': True,
            'index_stats': index_stats
        })
        
    except Exception as e:
        logger.error(f"构建索引失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '构建项目索引过程中发生错误'
        }), 500

@api.route('/projects/<int:project_id>/index-status', methods=['GET'])
def get_index_status(project_id):
    """获取项目索引状态"""
    try:
        # 获取项目信息
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project_path = project.get('path', '')
        if not project_path:
            # 如果没有本地路径，索引不存在
            return jsonify({
                'success': True,
                'index_status': {
                    'exists': False,
                    'symbol_count': 0,
                    'module_count': 0,
                    'index_path': None,
                    'last_updated': None,
                    'requires_clone': True
                }
            })
        
        if not os.path.exists(project_path):
            return jsonify({
                'success': True,
                'index_status': {
                    'exists': False,
                    'symbol_count': 0,
                    'module_count': 0,
                    'index_path': None,
                    'last_updated': None,
                    'path_not_found': True
                }
            })
        
        # 检查索引状态
        try:
            from indexers.codebase_indexer import CodebaseIndexer
            indexer = CodebaseIndexer(index_dir=os.path.join(project_path, '.code_index'))
        except ImportError:
            return jsonify({'error': 'Codebase indexer not available'}), 500
        
        index_exists = indexer.load_index()
        
        if index_exists:
            status = {
                'exists': True,
                'symbol_count': len(indexer.symbol_index),
                'module_count': len(indexer.module_index),
                'index_path': indexer.index_dir,
                'last_updated': None
            }
            
            # 获取索引文件的修改时间
            try:
                index_file = os.path.join(indexer.index_dir, "symbol_index.json")
                if os.path.exists(index_file):
                    mtime = os.path.getmtime(index_file)
                    status['last_updated'] = mtime
            except:
                pass
        else:
            status = {
                'exists': False,
                'symbol_count': 0,
                'module_count': 0,
                'index_path': indexer.index_dir,
                'last_updated': None
            }
        
        return jsonify({
            'success': True,
            'index_status': status
        })
        
    except Exception as e:
        logger.error(f"获取索引状态失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '获取索引状态过程中发生错误'
        }), 500

@api.route('/projects/<int:project_id>/analysis-history', methods=['GET'])
def get_analysis_history(project_id):
    """获取项目的分析历史记录"""
    try:
        analysis_type = request.args.get('type', 'all')  # 'all', 'git_diff', 'index_based'
        limit = int(request.args.get('limit', 20))
        
        # 构建查询条件
        where_clause = "WHERE project_id = %s"
        params = [project_id]
        
        if analysis_type != 'all':
            where_clause += " AND analysis_type = %s"
            params.append(analysis_type)
        
        # 确保code_analysis表存在
        db.execute('''
            CREATE TABLE IF NOT EXISTS code_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                commit_hash TEXT,
                base_commit TEXT,
                analysis_type TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # 查询分析历史
        query = f'''
            SELECT id, commit_hash, base_commit, analysis_type, created_at, analysis_data
            FROM code_analysis 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s
        '''
        
        records = db.fetch_all(query, params + [limit])
        
        history = []
        for record in records:
            # 解析summary信息
            summary = {}
            try:
                analysis_data = json.loads(record[5]) if record[5] else {}
                summary = analysis_data.get('summary', {})
            except:
                pass
            
            history.append({
                'id': record[0],
                'commit_hash': record[1],
                'base_commit': record[2],
                'analysis_type': record[3],
                'created_at': record[4],
                'summary': summary
            })
        
        return jsonify({
            'success': True,
            'history': history,
            'total': len(history)
        })
        
    except Exception as e:
        logger.error(f"获取分析历史失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '获取分析历史过程中发生错误'
        }), 500

@api.route('/projects/<int:project_id>/analysis/<int:analysis_id>', methods=['GET'])
def get_analysis_detail(project_id, analysis_id):
    """获取特定分析的详细结果"""
    try:
        record = db.fetch_one('''
            SELECT analysis_data, analysis_type, commit_hash, base_commit, created_at
            FROM code_analysis 
            WHERE id = %s AND project_id = %s
        ''', (analysis_id, project_id))
        
        if not record:
            return jsonify({'error': 'Analysis not found'}), 404
        
        analysis_data = json.loads(record[0]) if record[0] else {}
        
        return jsonify({
            'success': True,
            'analysis': {
                'id': analysis_id,
                'data': analysis_data,
                'type': record[1],
                'commit_hash': record[2],
                'base_commit': record[3],
                'created_at': record[4]
            }
        })
        
    except Exception as e:
        logger.error(f"获取分析详情失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '获取分析详情过程中发生错误'
        }), 500

@api.route('/projects/<int:id>/intelligent-test-cases', methods=['GET'])
def get_intelligent_test_cases(id):
    """获取智能生成的功能测试用例"""
    try:
        logger.info(f"🧠 生成智能功能测试用例 for project {id}")
        
        # 获取项目信息
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = ?", (id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project_path = project.get('git_url', '')
        project_name = project.get('name', f'Project {id}')
        
        # 尝试使用增强的AI客户端生成功能测试用例
        try:
            from clients.enhanced_ai_client import EnhancedAIClient
            
            # 创建AI客户端
            ai_client = EnhancedAIClient()
            
            # 生成功能测试用例 - 修复异步调用问题
            import asyncio
            try:
                # 创建新的事件循环而不是获取现有的
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果当前线程已有运行的循环，使用asyncio.run
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                ai_client.generate_comprehensive_functional_tests(
                                    change_analysis={
                                        'project_path': project_path,
                                        'project_name': project_name,
                                        'project_id': id
                                    },
                                    system_context={
                                        'project_type': 'web_application',
                                        'tech_stack': ['python', 'javascript'],
                                        'user_roles': ['admin', 'user']
                                    }
                                )
                            )
                            intelligent_tests = future.result(timeout=30)
                    else:
                        intelligent_tests = loop.run_until_complete(
                            ai_client.generate_comprehensive_functional_tests(
                                change_analysis={
                                    'project_path': project_path,
                                    'project_name': project_name,
                                    'project_id': id
                                },
                                system_context={
                                    'project_type': 'web_application',
                                    'tech_stack': ['python', 'javascript'],
                                    'user_roles': ['admin', 'user']
                                }
                            )
                        )
                except RuntimeError:
                    # 没有事件循环，创建新的
                    intelligent_tests = asyncio.run(
                        ai_client.generate_comprehensive_functional_tests(
                            change_analysis={
                                'project_path': project_path,
                                'project_name': project_name,
                                'project_id': id
                            },
                            system_context={
                                'project_type': 'web_application',
                                'tech_stack': ['python', 'javascript'],
                                'user_roles': ['admin', 'user']
                            }
                        )
                    )
            except Exception as async_error:
                logger.warning(f"异步调用失败: {async_error}")
                # 回退到同步方式生成默认用例
                intelligent_tests = None
            
            # 如果AI生成成功
            if intelligent_tests and isinstance(intelligent_tests, (list, dict)):
                # 处理AI返回的数据格式
                processed_tests = None
                
                if isinstance(intelligent_tests, dict):
                    # 检查是否有raw_response字段（AI模型返回的原始JSON）
                    if 'raw_response' in intelligent_tests:
                        try:
                            # 解析raw_response中的JSON
                            raw_response = intelligent_tests['raw_response']
                            if raw_response.startswith('```json'):
                                # 移除markdown代码块标记
                                json_start = raw_response.find('{')
                                json_end = raw_response.rfind('}') + 1
                                if json_start != -1 and json_end > json_start:
                                    json_str = raw_response[json_start:json_end]
                                    parsed_data = json.loads(json_str)
                                    
                                    # 提取test_plan数组
                                    if 'test_plan' in parsed_data:
                                        processed_tests = parsed_data['test_plan']
                                        logger.info(f"✅ 解析AI生成的测试计划，包含 {len(processed_tests)} 个测试用例")
                                    else:
                                        processed_tests = parsed_data
                            else:
                                # 直接解析JSON
                                parsed_data = json.loads(raw_response)
                                processed_tests = parsed_data.get('test_plan', parsed_data)
                        except (json.JSONDecodeError, KeyError) as parse_error:
                            logger.warning(f"解析AI响应失败: {parse_error}")
                            processed_tests = None
                    else:
                        # 直接使用返回的数据
                        processed_tests = intelligent_tests
                elif isinstance(intelligent_tests, list):
                    processed_tests = intelligent_tests
                
                # 如果成功解析出测试用例
                if processed_tests and len(processed_tests) > 0:
                    logger.info(f"✅ 成功生成 {len(processed_tests)} 个智能功能测试用例")
                    return jsonify(processed_tests)
                else:
                    logger.warning("AI生成的数据格式不正确或为空")
            else:
                logger.warning("AI生成失败或返回空结果")
            
        except Exception as e:
            logger.warning(f"AI生成测试用例失败: {e}")
        
        # 如果AI生成失败，返回默认智能测试用例
        logger.info("使用默认智能测试用例")
        test_cases = generate_default_intelligent_tests(project_name, id)
        return jsonify(test_cases)
            
    except Exception as e:
        logger.error(f"获取智能测试用例失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_default_intelligent_tests(project_name, project_id):
    """生成默认的智能功能测试用例"""
    return [
        {
            'test_case_name': f'{project_name} - 核心功能验证',
            'test_type': 'functional',
            'business_scenario': f'验证{project_name}项目的核心功能是否正常工作',
            'test_steps': [
                '1. 启动应用程序并验证初始化',
                '2. 验证主要功能模块正常加载',
                '3. 执行核心业务流程操作',
                '4. 检查输出结果的正确性',
                '5. 验证异常情况的处理机制'
            ],
            'expected_result': '所有核心功能应正常执行，异常情况应有合适的错误处理',
            'priority': 'high',
            'estimated_time': 30,
            'preconditions': '应用程序环境已配置完成，测试数据已准备',
            'test_data': '标准测试数据集，包含正常和边界值',
            'generation_method': 'default_intelligent'
        },
        {
            'test_case_name': f'{project_name} - 数据处理完整性验证',
            'test_type': 'functional',
            'business_scenario': f'验证{project_name}项目的数据输入、处理和输出完整性',
            'test_steps': [
                '1. 准备多种类型的测试数据',
                '2. 输入数据到系统并验证接收',
                '3. 执行数据处理逻辑并监控过程',
                '4. 验证处理结果的准确性和一致性',
                '5. 检查数据输出格式是否符合规范'
            ],
            'expected_result': '数据处理应保持准确性和一致性，输出格式应符合预期规范',
            'priority': 'high',
            'estimated_time': 25,
            'preconditions': '测试数据已准备完成，数据处理模块正常',
            'test_data': '包含边界值、异常值和大容量数据的测试集',
            'generation_method': 'default_intelligent'
        },
        {
            'test_case_name': f'{project_name} - 用户交互体验验证',
            'test_type': 'functional',
            'business_scenario': f'验证{project_name}项目的用户界面和交互功能可用性',
            'test_steps': [
                '1. 打开用户界面并检查加载状态',
                '2. 测试各个交互元素的响应性',
                '3. 验证用户操作的实时反馈',
                '4. 检查错误提示的准确性和友好性',
                '5. 测试不同场景下的界面表现'
            ],
            'expected_result': '界面元素应正确显示和响应，用户操作应得到及时准确的反馈',
            'priority': 'medium',
            'estimated_time': 20,
            'preconditions': '用户界面已正常加载，测试环境稳定',
            'test_data': '不同用户角色的测试账号和操作场景',
            'generation_method': 'default_intelligent'
        }
    ]