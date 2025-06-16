import asyncio
import json
import os
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import asyncpg

# PostgreSQL连接URL - 请根据实际环境修改
CONNECTION_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/code_analyzer')

@dataclass
class Project:
    id: int
    name: str
    repo_path: str
    config: Dict[str, Any]
    created_at: datetime

@dataclass
class CodeSymbol:
    id: int
    file_id: int
    name: str
    symbol_type: str
    signature: Optional[str]
    docstring: Optional[str]
    start_line: int
    end_line: int
    complexity_score: int
    parent_id: Optional[int]
    embedding: Optional[np.ndarray]
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class TestCase:
    id: int
    analysis_result_id: int
    symbol_id: int
    name: str
    description: Optional[str]
    test_type: str
    priority: str
    test_code: str
    metadata: Dict[str, Any]
    created_at: datetime

class Database:
    def __init__(self):
        self.connection_url = CONNECTION_URL
        self.pool = None

    async def initialize(self):
        """初始化数据库连接池和表结构"""
        try:
            self.pool = await asyncpg.create_pool(self.connection_url)
            await self._setup_extensions()
            await self._create_all_tables()
            print("✅ PostgreSQL数据库初始化成功")
            return True
        except Exception as e:
            print(f"❌ PostgreSQL初始化失败: {e}")
            return False

    async def _setup_extensions(self):
        """设置PostgreSQL扩展"""
        async with self.pool.acquire() as conn:
            # 启用必要扩展
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")  # pgvector用于向量存储
                print("✅ pgvector扩展已启用")
            except Exception as e:
                print(f"⚠️ pgvector扩展不可用: {e}，将使用JSONB存储向量")

            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS ltree")  # ltree用于层次数据
                print("✅ ltree扩展已启用")
            except Exception as e:
                print(f"⚠️ ltree扩展不可用: {e}")

    async def _create_all_tables(self):
        """创建所有数据表"""
        async with self.pool.acquire() as conn:
            # 创建项目表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    repo_path TEXT NOT NULL,
                    config JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建文件表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER REFERENCES projects(id),
                    file_path TEXT NOT NULL,
                    language VARCHAR(50),
                    content_hash VARCHAR(64),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, file_path)
                )
            ''')

            # 创建代码符号表 (支持向量存储)
            try:
                # 尝试使用pgvector
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS code_symbols (
                        id SERIAL PRIMARY KEY,
                        file_id INTEGER REFERENCES files(id),
                        name VARCHAR(255) NOT NULL,
                        symbol_type VARCHAR(50),
                        signature TEXT,
                        docstring TEXT,
                        start_line INTEGER,
                        end_line INTEGER,
                        complexity_score INTEGER DEFAULT 0,
                        parent_id INTEGER REFERENCES code_symbols(id),
                        embedding vector(384), -- pgvector字段
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("✅ 使用pgvector存储嵌入向量")
            except:
                # 降级到JSONB存储
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS code_symbols (
                        id SERIAL PRIMARY KEY,
                        file_id INTEGER REFERENCES files(id),
                        name VARCHAR(255) NOT NULL,
                        symbol_type VARCHAR(50),
                        signature TEXT,
                        docstring TEXT,
                        start_line INTEGER,
                        end_line INTEGER,
                        complexity_score INTEGER DEFAULT 0,
                        parent_id INTEGER REFERENCES code_symbols(id),
                        embedding_json JSONB, -- 降级方案
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("⚠️ 使用JSONB存储嵌入向量")

            # 创建测试用例表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS test_cases (
                    id SERIAL PRIMARY KEY,
                    analysis_result_id INTEGER,
                    symbol_id INTEGER REFERENCES code_symbols(id),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    test_type VARCHAR(50),
                    priority VARCHAR(20),
                    test_code TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建索引
            await self._create_indexes(conn)

    async def _create_indexes(self, conn):
        # 创建项目表索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_repo_path ON projects(repo_path)')
        
        # 创建代码符号表索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_code_symbols_file_id ON code_symbols(file_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(name)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_code_symbols_symbol_type ON code_symbols(symbol_type)')
        
        # 创建测试用例表索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_test_cases_analysis_result_id ON test_cases(analysis_result_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_test_cases_symbol_id ON test_cases(symbol_id)')

    def _create_tables(self):
        # 创建项目表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            git_url TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 创建代码变更表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS code_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            commit_hash TEXT NOT NULL,
            change_details TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
        ''')

        # 创建测试用例表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            code_change_id INTEGER NOT NULL,
            test_code TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (code_change_id) REFERENCES code_changes (id) ON DELETE CASCADE
        )
        ''')

        self.conn.commit()

    # 项目相关操作
    def create_project(self, name, git_url):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO projects (name, git_url, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
            (name, git_url)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_projects(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY created_at DESC')
        rows = cursor.fetchall()
        return [Project(
            id=row['id'],
            name=row['name'],
            git_url=row['git_url'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        ) for row in rows]

    def get_project(self, project_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        if row:
            return Project(
                id=row['id'],
                name=row['name'],
                git_url=row['git_url'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        return None

    # 代码变更相关操作
    def create_code_change(self, project_id, commit_hash, change_details):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO code_changes (project_id, commit_hash, change_details) VALUES (?, ?, ?)',
            (project_id, commit_hash, change_details)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_code_changes_by_project(self, project_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM code_changes WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
        rows = cursor.fetchall()
        return [CodeChange(
            id=row['id'],
            project_id=row['project_id'],
            commit_hash=row['commit_hash'],
            change_details=row['change_details'],
            created_at=datetime.fromisoformat(row['created_at'])
        ) for row in rows]

    # 测试用例相关操作
    def create_test_case(self, project_id, code_change_id, test_code):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO test_cases (project_id, code_change_id, test_code) VALUES (?, ?, ?)',
            (project_id, code_change_id, test_code)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_test_cases_by_code_change(self, code_change_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM test_cases WHERE code_change_id = ?', (code_change_id,))
        rows = cursor.fetchall()
        return [TestCase(
            id=row['id'],
            project_id=row['project_id'],
            code_change_id=row['code_change_id'],
            test_code=row['test_code'],
            created_at=datetime.fromisoformat(row['created_at'])
        ) for row in rows]

    def close(self):
        self.conn.close()

    async def cache_get(self, key: str) -> Optional[Dict]:
        """获取缓存"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT cache_value FROM cache_entries 
                WHERE cache_key = $1 
                AND (expires_at IS NULL OR expires_at > NOW())
            ''', key)
            
            if row:
                return json.loads(row['cache_value'])
            return None

    # 项目相关操作
    async def create_project(self, name: str, repo_path: str, config: Dict = None) -> int:
        """创建新项目"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO projects (name, repo_path, config)
                VALUES ($1, $2, $3)
                RETURNING id
            ''', name, repo_path, json.dumps(config or {}))

    async def get_projects(self) -> List[Project]:
        """获取所有项目"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM projects ORDER BY created_at DESC')
            return [Project(
                id=row['id'],
                name=row['name'],
                repo_path=row['repo_path'],
                config=json.loads(row['config']),
                created_at=row['created_at']
            ) for row in rows]

    async def get_project(self, project_id: int) -> Optional[Project]:
        """获取单个项目"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM projects WHERE id = $1', project_id)
            if row:
                return Project(
                    id=row['id'],
                    name=row['name'],
                    repo_path=row['repo_path'],
                    config=json.loads(row['config']),
                    created_at=row['created_at']
                )
            return None

    async def save_analysis_result(self, project_id: int, analysis_data: Dict) -> int:
        """保存分析结果"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO analysis_results 
                (project_id, commit_hash, branch_name, analysis_type, result_data, 
                 risk_level, confidence_score, analysis_duration_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            ''', project_id, analysis_data.get('commit_hash'), 
                analysis_data.get('branch_name'), analysis_data.get('analysis_type'),
                json.dumps(analysis_data), analysis_data.get('risk_level'),
                analysis_data.get('confidence_score'), 
                analysis_data.get('analysis_duration_ms', 0))

    async def create_test_case(self, analysis_result_id: int, symbol_id: Optional[int], 
                              name: str, test_code: str, test_type: str, 
                              priority: str, description: Optional[str] = None, 
                              metadata: Dict = None) -> int:
        """创建测试用例"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO test_cases 
                (analysis_result_id, symbol_id, name, description, test_type, 
                 priority, test_code, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            ''', analysis_result_id, symbol_id, name, description, test_type, 
                priority, test_code, json.dumps(metadata or {}))

    async def get_analysis_results_by_project(self, project_id: int) -> List[Dict]:
        """获取项目的所有分析结果"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM analysis_results 
                WHERE project_id = $1 
                ORDER BY created_at DESC
            ''', project_id)
            return [{
                'id': row['id'],
                'project_id': row['project_id'],
                'commit_hash': row['commit_hash'],
                'branch_name': row['branch_name'],
                'analysis_type': row['analysis_type'],
                'result_data': row['result_data'],
                'risk_level': row['risk_level'],
                'confidence_score': row['confidence_score'],
                'analysis_duration_ms': row['analysis_duration_ms'],
                'created_at': row['created_at']
            } for row in rows]

    async def get_test_cases_by_analysis(self, analysis_result_id: int) -> List[Dict]:
        """获取分析结果的所有测试用例"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM test_cases 
                WHERE analysis_result_id = $1
                ORDER BY created_at DESC
            ''', analysis_result_id)
            return [{
                'id': row['id'],
                'analysis_result_id': row['analysis_result_id'],
                'symbol_id': row['symbol_id'],
                'name': row['name'],
                'description': row['description'],
                'test_type': row['test_type'],
                'priority': row['priority'],
                'test_code': row['test_code'],
                'metadata': json.loads(row['metadata']),
                'created_at': row['created_at']
            } for row in rows]

# 创建全局数据库实例
db = Database()

def get_db():
    """获取数据库实例"""
    return db