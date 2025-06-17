from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models.database import get_db
import json
import logging
import asyncio
import functools
from ..utils.git_utils import GitUtils
from ..websocket_server import send_notification
import os
from ..analyzers.enhanced_cursor_analyzer import EnhancedCursorAnalyzer

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
        
        # 检查仓库路径是否已存在
        try:
            existing_project = db.fetch_one("SELECT * FROM projects WHERE git_url = %s", (git_url,))
            if existing_project:
                return jsonify({'error': '该仓库路径已被使用'}), 409
        except Exception as e:
            logger.error(f"检查仓库路径失败: {str(e)}")
            # 继续执行，不阻止创建项目

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
        
        if result and 'id' in result:
            return jsonify({'id': result['id'], 'message': '项目创建成功'}), 201
        else:
            return jsonify({'error': '项目创建失败'}), 500
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
        from ..indexers.codebase_indexer import CodebaseIndexer
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
        from ..indexers.codebase_indexer import CodebaseIndexer
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
        
        # 获取最新的分析结果
        latest_analysis = db.fetch_one(
            "SELECT id FROM analysis_results WHERE project_id = %s ORDER BY created_at DESC LIMIT 1", 
            (id,)
        )
        
        if not latest_analysis:
            return jsonify([])
        
        # 获取测试用例
        test_cases = db.fetch_all(
            "SELECT * FROM test_cases WHERE analysis_id = %s",
            (latest_analysis['id'],)
        )
        
        return jsonify(test_cases)
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
    """取消分析任务"""
    try:
        # 这里应该取消正在运行的任务
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

@api.route('/analyzer/history', methods=['GET'])
def get_analysis_history():
    """获取分析历史记录"""
    try:
        # 获取查询参数
        repo_path = request.args.get('repo_path')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 10))
        
        # 这里应该查询数据库
        # 暂时返回模拟数据
        history = [
            {
                "id": "analysis_1",
                "repo_path": "/path/to/repo",
                "created_at": "2024-01-15T10:30:00Z",
                "changes_count": 5,
                "high_risk_changes": 2,
                "status": "completed"
            },
            {
                "id": "analysis_2",
                "repo_path": "/path/to/another/repo",
                "created_at": "2024-01-14T15:45:00Z",
                "changes_count": 3,
                "high_risk_changes": 1,
                "status": "completed"
            }
        ]
        
        return jsonify({
            "status": "success",
            "history": history
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
            from ..utils.html_reporter import HTMLReporter
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
            from ..utils.json_reporter import JSONReporter
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