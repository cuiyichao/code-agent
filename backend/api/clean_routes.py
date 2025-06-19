#!/usr/bin/env python3
"""
清理后的API路由文件，移除重复路由
"""

from flask import Blueprint, request, jsonify, Response
from models.database import get_db
import json
import logging
import os
import tempfile
import shutil
from datetime import datetime
import time
from analyzers.intelligent_impact_analyzer import IntelligentImpactAnalyzer

# 创建蓝图
clean_api = Blueprint('clean_api', __name__)
logger = logging.getLogger(__name__)

# 基础路由
@clean_api.route('/', methods=['GET'])
def index():
    """API根路径"""
    return jsonify({
        'message': '代码分析后端API服务',
        'status': 'running',
        'version': '1.0.0'
    })

@clean_api.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok'})

# 项目管理路由
@clean_api.route('/projects', methods=['GET'])
def get_projects():
    """获取所有项目"""
    try:
        db = get_db()
        projects = db.fetch_all("SELECT * FROM projects ORDER BY created_at DESC")
        return jsonify(projects)
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@clean_api.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取单个项目"""
    try:
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify(project)
    except Exception as e:
        logger.error(f"获取项目失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@clean_api.route('/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.get_json()
        if not data or not data.get('name') or not data.get('git_url'):
            return jsonify({'error': 'Missing required fields: name, git_url'}), 400
        
        db = get_db()
        result = db.execute(
            """INSERT INTO projects (name, description, git_url, branch, created_at) 
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (
                data['name'],
                data.get('description', ''),
                data['git_url'],
                data.get('branch', 'main')
            )
        )
        
        # 获取插入的ID
        if isinstance(result, dict) and 'id' in result:
            project_id = result['id']
        else:
            # 如果没有返回ID，查询最后插入的记录
            project = db.fetch_one("SELECT id FROM projects WHERE git_url = ? ORDER BY id DESC LIMIT 1", (data['git_url'],))
            project_id = project['id'] if project else None
        
        return jsonify({
            'id': project_id,
            'message': 'Project created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@clean_api.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目及其相关数据"""
    try:
        logger.info(f"🗑️ 开始删除项目 - 项目ID: {project_id}")
        
        db = get_db()
        
        # 检查项目是否存在
        project = db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        
        # 1. 删除项目相关的测试用例
        logger.info("📋 删除相关测试用例...")
        analysis_results = db.fetch_all("SELECT id FROM analysis_results WHERE project_id = ?", (project_id,))
        for result in analysis_results:
            db.execute("DELETE FROM test_cases WHERE analysis_id = ?", (result['id'],))
        
        # 2. 删除项目的分析结果
        logger.info("📊 删除分析结果...")
        db.execute("DELETE FROM analysis_results WHERE project_id = ?", (project_id,))
        
        # 3. 删除项目相关的符号索引（如果存在）
        logger.info("🔍 删除符号索引...")
        try:
            db.execute("DELETE FROM symbols WHERE file_path LIKE ?", (f"%project_{project_id}%",))
            db.execute("DELETE FROM symbol_references WHERE source_symbol_id LIKE ?", (f"%project_{project_id}%",))
            db.execute("DELETE FROM file_index WHERE file_path LIKE ?", (f"%project_{project_id}%",))
        except Exception as e:
            logger.warning(f"⚠️ 删除符号索引时出错: {e}")
        
        # 4. 删除项目本身
        logger.info("🗂️ 删除项目记录...")
        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        
        logger.info(f"✅ 项目删除成功 - 项目ID: {project_id}")
        return jsonify({
            'success': True,
            'message': '项目删除成功'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ 删除项目失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 索引分析路由
@clean_api.route('/projects/<int:project_id>/index-analysis', methods=['POST'])
def analyze_project_index(project_id):
    """基于代码索引的智能分析"""
    try:
        logger.info(f"🔍 开始项目索引分析 - 项目ID: {project_id}")
        
        # 获取项目信息
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not project:
            return jsonify({"error": "项目不存在"}), 404
        
        # 修复：使用字典方式访问，而不是索引
        project_path = project.get('git_url', '')  # 项目路径是git_url字段
        logger.info(f"📂 项目路径: {project_path}")
        
        # 获取请求参数
        data = request.get_json() or {}
        commit_hash = data.get('commit_hash')
        base_commit = data.get('base_commit')
        
        # 日志记录分析参数
        logger.info(f"📋 分析参数 - commit_hash: {commit_hash}, base_commit: {base_commit}")
        if commit_hash is None and base_commit is None:
            logger.info("🔄 使用默认模式：分析最新提交与其父提交的对比")
        elif commit_hash is not None and base_commit is None:
            logger.info(f"🔍 分析指定提交与其父提交的对比：{commit_hash}")
        elif commit_hash is not None and base_commit is not None:
            logger.info(f"🔀 分析两个指定提交的对比：{base_commit} -> {commit_hash}")
        
        # 创建智能影响分析器（传递project_id）
        analyzer = IntelligentImpactAnalyzer(project_path, project_id=project_id)
        
        # 执行分析
        result = analyzer.analyze_impact(commit_hash, base_commit)
        
        # 保存分析结果到数据库
        if result.get('status') == 'success':
            analysis_id = db.execute("""
                INSERT INTO analysis_results 
                (project_id, analysis_type, commit_hash, base_commit, result_data, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                project_id,
                'intelligent_impact',
                result.get('code_changes', {}).get('commit_info', {}).get('latest_commit'),
                result.get('code_changes', {}).get('commit_info', {}).get('base_commit'),
                json.dumps(result, ensure_ascii=False)
            ))
            
            result['analysis_id'] = analysis_id
            logger.info(f"✅ 分析结果已保存 - 分析ID: {analysis_id}")
        
        # 确保返回数据格式符合前端期望
        return jsonify({
            "status": "success",
            "success": True,
            "analysis_result": result,
            "analysis": result,  # 兼容字段
            "message": "索引分析完成"
        })
        
    except Exception as e:
        logger.error(f"❌ 项目索引分析失败: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@clean_api.route('/projects/<int:project_id>/build-index', methods=['POST'])
def build_project_index(project_id):
    """构建项目代码索引"""
    try:
        from indexers.codebase_indexer import CodebaseIndexer
        
        # 获取项目信息
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project_path = project.get('path', '')
        if not project_path or not os.path.exists(project_path):
            return jsonify({'error': 'Project path not found'}), 400
        
        # 创建索引器
        indexer = CodebaseIndexer(index_dir=os.path.join(project_path, '.code_index'))
        
        # 构建索引
        logger.info(f"开始构建项目索引: project_id={project_id}, path={project_path}")
        index_stats = indexer.build_index(project_path)
        
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

@clean_api.route('/projects/<int:project_id>/index-status', methods=['GET'])
def get_index_status(project_id):
    """获取项目索引状态"""
    try:
        # 获取项目信息
        db = get_db()
        project = db.fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project_path = project.get('path', '')
        if not project_path:
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

@clean_api.route('/projects/<int:project_id>/analysis-history', methods=['GET'])
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
        db = get_db()
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

@clean_api.route('/projects/<int:project_id>/analysis/<int:analysis_id>', methods=['GET'])
def get_analysis_detail(project_id, analysis_id):
    """获取特定分析的详细结果"""
    try:
        db = get_db()
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

@clean_api.route('/projects/<int:project_id>/index-history', methods=['GET'])
def get_index_history(project_id):
    """获取项目的索引历史记录"""
    try:
        limit = int(request.args.get('limit', 10))
        
        db = get_db()
        
        # 获取索引历史
        indexes = db.fetch_all(
            '''SELECT id, commit_hash, symbol_count, module_count, created_at 
               FROM code_indexes 
               WHERE project_id = %s 
               ORDER BY created_at DESC 
               LIMIT %s''',
            (project_id, limit)
        )
        
        return jsonify({
            'success': True,
            'indexes': [
                {
                    'id': idx['id'],
                    'commit_hash': idx['commit_hash'],
                    'symbol_count': idx['symbol_count'],
                    'module_count': idx['module_count'],
                    'created_at': idx['created_at']
                }
                for idx in indexes
            ]
        })
        
    except Exception as e:
        logger.error(f"获取索引历史失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '获取索引历史过程中发生错误'
        }), 500

@clean_api.route('/projects/<int:project_id>/index/<int:index_id>', methods=['GET'])
def get_index_detail(project_id, index_id):
    """获取特定索引的详细信息"""
    try:
        db = get_db()
        
        # 获取索引详情
        index = db.fetch_one(
            '''SELECT * FROM code_indexes 
               WHERE project_id = %s AND id = %s''',
            (project_id, index_id)
        )
        
        if not index:
            return jsonify({'error': 'Index not found'}), 404
        
        # 解析索引数据
        index_data = json.loads(index['index_data'])
        
        return jsonify({
            'success': True,
            'index': {
                'id': index['id'],
                'commit_hash': index['commit_hash'],
                'symbol_count': index['symbol_count'],
                'module_count': index['module_count'],
                'created_at': index['created_at'],
                'symbol_index': index_data.get('symbol_index', {}),
                'index_stats': index_data.get('index_stats', {})
            }
        })
        
    except Exception as e:
        logger.error(f"获取索引详情失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': '获取索引详情过程中发生错误'
        }), 500 