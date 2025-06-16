from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models.database import get_db
from ..analyzers.cursor_level_analyzer import CursorLevelAnalyzer
import json

api = Blueprint('api', __name__)

db = get_db()

@api.route('/projects', methods=['GET'])
async def get_projects():
    try:
        projects = await db.get_projects()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'repo_path': p.repo_path,
            'config': p.config,
            'created_at': p.created_at.isoformat()
        } for p in projects]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/projects', methods=['POST'])
async def create_project():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'repo_path' not in data:
            return jsonify({'error': '项目名称和仓库路径为必填项'}), 400

        # 检查仓库路径是否已存在
        existing_projects = await db.get_projects()
        for project in existing_projects:
            if project.repo_path == data['repo_path']:
                return jsonify({'error': '该仓库路径已被使用'}), 409

        project_id = await db.create_project(
            name=data['name'],
            repo_path=data['repo_path'],
            config=data.get('config', {})
        )
        return jsonify({'id': project_id, 'message': '项目创建成功'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:project_id>', methods=['GET'])
async def get_project_details(project_id):
    try:
        project = await db.get_project(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        # 获取分析结果
        analysis_results = await db.get_analysis_results_by_project(project_id)
        results_with_tests = []
        for result in analysis_results:
            test_cases = await db.get_test_cases_by_analysis(result.id)
            results_with_tests.append({
                'id': result.id,
                'commit_hash': result.commit_hash,
                'analysis_type': result.analysis_type,
                'result_data': json.loads(result.result_data),
                'risk_level': result.risk_level,
                'created_at': result.created_at.isoformat(),
                'testCases': [{
                    'id': tc.id,
                    'name': tc.name,
                    'test_code': tc.test_code,
                    'test_type': tc.test_type,
                    'priority': tc.priority,
                    'created_at': tc.created_at.isoformat()
                } for tc in test_cases]
            })

        return jsonify({
            'project': {
                'id': project.id,
                'name': project.name,
                'git_url': project.git_url,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat()
            },
            'code_changes': changes_with_tests
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/projects/<int:project_id>/analyze', methods=['POST'])
async def analyze_project_changes(project_id):
    try:
        data = request.get_json()
        commit_hash = data.get('commit_hash', '')

        project = db.get_project(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        # 执行代码变更分析
        analyzer = CursorLevelAnalyzer(project.git_url)
        change_details = analyzer.analyze_code_changes(commit_hash)
        test_cases = analyzer.generate_test_cases()

        # 保存分析结果到数据库
        analysis_result_id = await db.save_analysis_result(
            project_id=project_id,
            analysis_data={
                'commit_hash': commit_hash,
                'analysis_type': 'code_change',
                'result_data': change_details,
                'test_cases': test_cases
            }
        )

        # 保存测试用例
        for test_case in test_cases:
            await db.create_test_case(
                analysis_result_id=analysis_result_id,
                symbol_id=None,  # 需要根据实际分析结果获取symbol_id
                name=f"Test for {commit_hash[:8]}",
                test_code=test_case,
                test_type="unit",
                priority="medium"
            )

        return jsonify({
            'message': '代码变更分析完成',
            'change_id': change_id,
            'change_details': change_details,
            'test_cases': test_cases
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500