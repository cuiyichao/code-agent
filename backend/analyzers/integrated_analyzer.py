import os
import sqlite3
import pickle
import logging
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from ..models.code_symbol import CodeSymbol, CodeReference, ChangeAnalysis
from ..indexers.symbol_indexer import SymbolIndexer
from .semantic_analyzer import SemanticAnalyzer
from .impact_analyzer import ImpactAnalyzer
from ..clients.github_client import GitHubClient
from ..generators.test_code_generator import TestCodeGenerator

class IntegratedCursorAnalyzer:
    """集成的Cursor风格代码分析器 - 主要控制器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.symbol_indexer = SymbolIndexer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.impact_analyzer = ImpactAnalyzer()
        self.github_client = GitHubClient(self.config.get('github_token'))
        self.test_generator = TestCodeGenerator()
        
        # 数据存储
        self.symbols: Dict[str, CodeSymbol] = {}
        self.references: List[CodeReference] = []
        
        # 数据库路径
        self.db_path = None
        self.conn = None
    
    def initialize_for_path(self, path: str):
        """为指定路径初始化分析器"""
        self.repo_path = Path(path)
        
        # 设置数据库路径
        index_dir = self.repo_path / ".cursor_index"
        index_dir.mkdir(exist_ok=True)
        self.db_path = index_dir / "codebase.db"
        
        # 初始化数据库
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_database()
    
    def initialize_for_github(self, owner: str, repo: str):
        """为GitHub仓库初始化分析器"""
        self.github_owner = owner
        self.github_repo = repo
        
        # 设置数据库路径
        cache_dir = Path.home() / ".cursor_analyzer_cache" / f"{owner}_{repo}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "codebase.db"
        
        # 初始化数据库
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_database()
    
    async def build_full_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """构建完整项目索引"""
        start_time = time.time()
        stats = {
            'total_files': 0,
            'processed_files': 0,
            'total_symbols': 0,
            'index_time': 0,
            'source': 'local' if hasattr(self, 'repo_path') else 'github'
        }
        
        try:
            if hasattr(self, 'repo_path'):
                # 本地仓库分析
                await self._build_local_index(stats, force_rebuild)
            else:
                # GitHub仓库分析
                await self._build_github_index(stats, force_rebuild)
            
            # 构建依赖图
            self.impact_analyzer.build_dependency_graphs(self.symbols, self.references)
            
            # 生成语义嵌入
            self.symbols = self.semantic_analyzer.generate_embeddings(self.symbols)
            
            # 保存到数据库
            self._save_index_to_database()
            
            stats['index_time'] = time.time() - start_time
            self.logger.info(f"索引构建完成: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"构建索引失败: {str(e)}")
            raise
    
    async def _build_local_index(self, stats: Dict[str, Any], force_rebuild: bool):
        """构建本地仓库索引"""
        # 发现代码文件
        code_files = self.symbol_indexer.discover_code_files(str(self.repo_path))
        stats['total_files'] = len(code_files)
        
        # 增量更新检查
        if not force_rebuild:
            code_files = self._filter_changed_files(code_files)
        else:
            self._clear_index()
        
        # 批量处理文件
        result = self.symbol_indexer.process_files_batch(code_files)
        self.symbols.update(result['symbols'])
        self.references.extend(result['references'])
        
        stats['processed_files'] = len(code_files)
        stats['total_symbols'] = len(self.symbols)
    
    async def _build_github_index(self, stats: Dict[str, Any], force_rebuild: bool):
        """构建GitHub仓库索引"""
        # 获取仓库信息
        repo_info = await self.github_client.get_repository_info(
            self.github_owner, self.github_repo
        )
        if not repo_info:
            raise Exception("无法获取GitHub仓库信息")
        
        # 获取文件树
        tree_items = await self.github_client.get_repository_tree(
            self.github_owner, self.github_repo
        )
        
        # 过滤代码文件
        code_files = await self.github_client.filter_code_files(tree_items)
        stats['total_files'] = len(code_files)
        
        # 批量获取文件内容
        file_paths = [item['path'] for item in code_files]
        file_contents = await self.github_client.batch_get_files(
            self.github_owner, self.github_repo, file_paths[:100]  # 限制数量避免API限制
        )
        
        # 处理文件内容
        for file_path, content in file_contents.items():
            if content:
                # 检测语言
                language = self.symbol_indexer._detect_language(Path(file_path))
                if language:
                    # 提取符号
                    symbols = self.symbol_indexer._extract_symbols(
                        Path(file_path), content, language
                    )
                    references = self.symbol_indexer._extract_references(
                        Path(file_path), content, language
                    )
                    
                    # 更新索引
                    for symbol in symbols:
                        self.symbols[symbol.id] = symbol
                    self.references.extend(references)
        
        stats['processed_files'] = len(file_contents)
        stats['total_symbols'] = len(self.symbols)
    
    async def analyze_changes(self, commit_hash: Optional[str] = None, 
                            pr_number: Optional[int] = None) -> Dict[str, Any]:
        """分析代码变更"""
        try:
            # 确保索引已加载
            if not self.symbols:
                if not self.load_index():
                    self.logger.info("索引不存在，构建新索引...")
                    await self.build_full_index()
            
            # 获取变更
            if hasattr(self, 'github_owner') and pr_number:
                # GitHub PR分析
                changes = await self._analyze_github_pr(pr_number)
            elif hasattr(self, 'repo_path'):
                # 本地Git变更分析
                changes = await self._analyze_local_changes(commit_hash)
            else:
                return {"status": "error", "message": "未指定变更来源"}
            
            if not changes:
                return {"status": "no_changes", "message": "未检测到代码变更"}
            
            # 执行影响分析
            impact_analysis = self.impact_analyzer.analyze_symbol_impact(changes)
            
            # 生成测试建议
            test_suggestions = await self.test_generator.generate_test_suggestions(
                impact_analysis.changed_symbols, impact_analysis
            )
            impact_analysis.suggested_tests = test_suggestions
            
            return {
                "status": "success",
                "analysis": impact_analysis.to_dict(),
                "summary": self._generate_analysis_summary(impact_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"分析失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def semantic_search(self, query: str, limit: int = 10, 
                            file_filter: Optional[List[str]] = None) -> List[Dict]:
        """语义搜索代码"""
        if not self.symbols:
            self.load_index()
        
        return self.semantic_analyzer.semantic_search(
            query, self.symbols, limit, file_filter
        )
    
    async def analyze_github_pr(self, pr_number: int) -> Dict[str, Any]:
        """分析GitHub PR"""
        if not hasattr(self, 'github_owner'):
            return {"status": "error", "message": "未配置GitHub仓库"}
        
        return await self.analyze_changes(pr_number=pr_number)
    
    def load_index(self) -> bool:
        """从数据库加载索引"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 加载符号
            cursor.execute('SELECT * FROM symbols')
            for row in cursor.fetchall():
                symbol = self._row_to_symbol(row)
                self.symbols[symbol.id] = symbol
            
            # 加载引用关系
            cursor.execute('SELECT * FROM references')
            for row in cursor.fetchall():
                ref = self._row_to_reference(row)
                self.references.append(ref)
            
            # 重建依赖图
            self.impact_analyzer.build_dependency_graphs(self.symbols, self.references)
            
            self.logger.info(f"索引加载完成: {len(self.symbols)} 个符号, {len(self.references)} 个引用")
            return True
            
        except Exception as e:
            self.logger.error(f"加载索引失败: {e}")
            return False
    
    def _init_database(self):
        """初始化数据库表 - 使用统一的迁移工具"""
        from ..utils.database_migration import DatabaseMigration
        
        # 使用迁移工具创建表
        migration = DatabaseMigration(self.db_path)
        migration.conn = self.conn  # 复用现有连接
        migration.create_all_tables()
    
    def _save_index_to_database(self):
        """保存索引到数据库"""
        cursor = self.conn.cursor()
        
        # 保存符号
        for symbol in self.symbols.values():
            cursor.execute('''
            INSERT OR REPLACE INTO symbols 
            (id, name, symbol_type, file_path, start_line, end_line, signature, 
             docstring, parameters, return_type, decorators, parent_class, 
             language, complexity, content_hash, embedding) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol.id, symbol.name, symbol.symbol_type, symbol.file_path,
                symbol.start_line, symbol.end_line, symbol.signature,
                symbol.docstring, pickle.dumps(symbol.parameters), symbol.return_type,
                pickle.dumps(symbol.decorators), symbol.parent_class,
                symbol.language, symbol.complexity, symbol.content_hash,
                pickle.dumps(symbol.embedding) if symbol.embedding is not None else None
            ))
        
        # 保存引用关系
        cursor.execute('DELETE FROM references')  # 清空旧引用
        for ref in self.references:
            cursor.execute('''
            INSERT INTO references 
            (source_symbol_id, target_symbol_id, reference_type, file_path, line_number, context)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ref.source_symbol_id, ref.target_symbol_id, ref.reference_type,
                ref.file_path, ref.line_number, ref.context
            ))
        
        self.conn.commit()
    
    def _filter_changed_files(self, files: List[Path]) -> List[Path]:
        """过滤出有变更的文件（简化实现）"""
        # 这里可以实现基于文件修改时间或Git状态的过滤
        return files
    
    def _clear_index(self):
        """清空索引"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM symbols')
        cursor.execute('DELETE FROM references')
        self.conn.commit()
        
        self.symbols.clear()
        self.references.clear()
    
    async def _analyze_github_pr(self, pr_number: int) -> List[CodeSymbol]:
        """分析GitHub PR变更"""
        # 获取PR文件变更
        pr_files = await self.github_client.get_pull_request_files(
            self.github_owner, self.github_repo, pr_number
        )
        
        changed_symbols = []
        for file_change in pr_files:
            file_path = file_change.get('filename', '')
            if file_change.get('status') in ['modified', 'added']:
                # 获取新版本文件内容
                content = await self.github_client.get_file_content(
                    self.github_owner, self.github_repo, file_path
                )
                
                if content:
                    language = self.symbol_indexer._detect_language(Path(file_path))
                    if language:
                        symbols = self.symbol_indexer._extract_symbols(
                            Path(file_path), content, language
                        )
                        
                        # 识别变更的符号
                        for symbol in symbols:
                            if symbol.id in self.symbols:
                                old_symbol = self.symbols[symbol.id]
                                if old_symbol.content_hash != symbol.content_hash:
                                    changed_symbols.append(symbol)
                            else:
                                # 新符号
                                changed_symbols.append(symbol)
        
        return changed_symbols
    
    async def _analyze_local_changes(self, commit_hash: Optional[str]) -> List[CodeSymbol]:
        """分析本地Git变更（简化实现）"""
        # 这里可以实现基于Git diff的变更检测
        return []
    
    def _row_to_symbol(self, row) -> CodeSymbol:
        """将数据库行转换为CodeSymbol"""
        return CodeSymbol(
            id=row[0],
            name=row[1],
            symbol_type=row[2],
            file_path=row[3],
            start_line=row[4],
            end_line=row[5],
            signature=row[6],
            docstring=row[7],
            parameters=pickle.loads(row[8]) if row[8] else [],
            return_type=row[9],
            decorators=pickle.loads(row[10]) if row[10] else [],
            parent_class=row[11],
            language=row[12],
            complexity=row[13],
            content_hash=row[14],
            embedding=pickle.loads(row[15]) if row[15] else None
        )
    
    def _row_to_reference(self, row) -> CodeReference:
        """将数据库行转换为CodeReference"""
        return CodeReference(
            source_symbol_id=row[1],
            target_symbol_id=row[2],
            reference_type=row[3],
            file_path=row[4],
            line_number=row[5],
            context=row[6]
        )
    
    def _generate_analysis_summary(self, analysis: ChangeAnalysis) -> str:
        """生成分析总结"""
        summary_parts = []
        
        summary_parts.append(f"检测到 {len(analysis.changed_symbols)} 个符号发生变更")
        
        if analysis.direct_impacts:
            summary_parts.append(f"直接影响 {len(analysis.direct_impacts)} 个符号")
        
        if analysis.indirect_impacts:
            summary_parts.append(f"间接影响 {len(analysis.indirect_impacts)} 个符号")
        
        summary_parts.append(f"风险等级: {analysis.risk_level}")
        
        if analysis.suggested_tests:
            high_priority_tests = len([t for t in analysis.suggested_tests if t.get('priority') == 'high'])
            summary_parts.append(f"建议执行 {len(analysis.suggested_tests)} 个测试，其中 {high_priority_tests} 个高优先级")
        
        return "。".join(summary_parts) + "。" 