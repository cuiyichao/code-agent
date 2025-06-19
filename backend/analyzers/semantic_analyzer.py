import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from sentence_transformers import SentenceTransformer
import pickle
import asyncio

from ..models.code_symbol import CodeSymbol, CodeReference

class SemanticAnalyzer:
    """语义分析器 - 负责代码的语义理解和搜索"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        
        # 初始化语义模型
        try:
            self.embedding_model = SentenceTransformer(model_name)
            self.logger.info(f"语义模型加载成功: {model_name}")
        except Exception as e:
            self.logger.error(f"语义模型加载失败: {e}")
            self.embedding_model = None
    
    def generate_embeddings(self, symbols: Dict[str, CodeSymbol]) -> Dict[str, CodeSymbol]:
        """为符号生成语义嵌入"""
        if not self.embedding_model:
            self.logger.warning("语义模型未加载，跳过嵌入生成")
            return symbols
        
        self.logger.info(f"开始为 {len(symbols)} 个符号生成语义嵌入")
        
        # 构建描述文本
        texts = []
        symbol_ids = []
        
        for symbol_id, symbol in symbols.items():
            text = self._build_symbol_text(symbol)
            texts.append(text)
            symbol_ids.append(symbol_id)
        
        # 批量生成嵌入
        if texts:
            try:
                embeddings = self.embedding_model.encode(texts, batch_size=32, show_progress_bar=True)
                
                # 更新符号的嵌入
                for i, symbol_id in enumerate(symbol_ids):
                    symbols[symbol_id].embedding = embeddings[i]
                
                self.logger.info("语义嵌入生成完成")
            except Exception as e:
                self.logger.error(f"生成语义嵌入失败: {e}")
        
        return symbols
    
    def semantic_search(self, query: str, symbols: Dict[str, CodeSymbol], 
                       limit: int = 10, file_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """语义搜索代码符号"""
        if not self.embedding_model or not query.strip():
            return []
        
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode([query])[0]
            
            # 计算相似度
            similarities = []
            for symbol_id, symbol in symbols.items():
                # 文件过滤
                if file_filter and symbol.file_path not in file_filter:
                    continue
                
                if symbol.embedding is not None:
                    similarity = self._calculate_cosine_similarity(query_embedding, symbol.embedding)
                    
                    similarities.append({
                        'symbol': symbol.to_dict(),
                        'similarity': float(similarity),
                        'context': self._build_symbol_context(symbol),
                        'usage_hint': self._generate_usage_hint(symbol)
                    })
            
            # 排序并返回
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            self.logger.error(f"语义搜索失败: {e}")
            return []
    
    def find_similar_symbols(self, target_symbol: CodeSymbol, symbols: Dict[str, CodeSymbol], 
                           limit: int = 5) -> List[Dict[str, Any]]:
        """查找相似的符号"""
        if not target_symbol.embedding:
            return []
        
        similarities = []
        for symbol_id, symbol in symbols.items():
            if symbol.id == target_symbol.id or not symbol.embedding:
                continue
            
            similarity = self._calculate_cosine_similarity(target_symbol.embedding, symbol.embedding)
            
            similarities.append({
                'symbol': symbol.to_dict(),
                'similarity': float(similarity),
                'reason': self._analyze_similarity_reason(target_symbol, symbol)
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:limit]
    
    def cluster_symbols(self, symbols: Dict[str, CodeSymbol], n_clusters: int = 10) -> Dict[str, List[str]]:
        """符号聚类分析"""
        try:
            from sklearn.cluster import KMeans
            
            # 提取有嵌入的符号
            embeddings = []
            symbol_ids = []
            
            for symbol_id, symbol in symbols.items():
                if symbol.embedding is not None:
                    embeddings.append(symbol.embedding)
                    symbol_ids.append(symbol_id)
            
            if len(embeddings) < n_clusters:
                return {}
            
            # 执行K-means聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(embeddings)
            
            # 组织聚类结果
            clusters = {}
            for i, label in enumerate(cluster_labels):
                cluster_key = f"cluster_{label}"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(symbol_ids[i])
            
            return clusters
            
        except ImportError:
            self.logger.warning("sklearn未安装，跳过聚类分析")
            return {}
        except Exception as e:
            self.logger.error(f"符号聚类失败: {e}")
            return {}
    
    def analyze_semantic_drift(self, old_symbols: Dict[str, CodeSymbol], 
                             new_symbols: Dict[str, CodeSymbol]) -> List[Dict[str, Any]]:
        """分析语义漂移"""
        drift_analysis = []
        
        for symbol_id in old_symbols:
            if symbol_id in new_symbols:
                old_symbol = old_symbols[symbol_id]
                new_symbol = new_symbols[symbol_id]
                
                if old_symbol.embedding is not None and new_symbol.embedding is not None:
                    similarity = self._calculate_cosine_similarity(old_symbol.embedding, new_symbol.embedding)
                    
                    # 语义变化阈值
                    if similarity < 0.8:
                        drift_analysis.append({
                            'symbol_id': symbol_id,
                            'symbol_name': old_symbol.name,
                            'semantic_change': 1.0 - similarity,
                            'old_signature': old_symbol.signature,
                            'new_signature': new_symbol.signature,
                            'risk_level': self._assess_drift_risk(similarity),
                            'analysis': self._analyze_change_details(old_symbol, new_symbol)
                        })
        
        return drift_analysis
    
    def _build_symbol_text(self, symbol: CodeSymbol) -> str:
        """构建符号的描述文本"""
        text_parts = [symbol.name]
        
        # 添加符号类型信息
        text_parts.append(f"({symbol.symbol_type})")
        
        # 添加签名
        if symbol.signature:
            text_parts.append(symbol.signature)
        
        # 添加文档字符串
        if symbol.docstring:
            # 限制文档字符串长度
            doc_text = symbol.docstring[:200] + "..." if len(symbol.docstring) > 200 else symbol.docstring
            text_parts.append(doc_text)
        
        # 添加参数信息
        if symbol.parameters:
            text_parts.append(f"参数: {', '.join(symbol.parameters)}")
        
        # 添加装饰器信息
        if symbol.decorators:
            text_parts.append(f"装饰器: {', '.join(symbol.decorators)}")
        
        # 添加文件路径信息（用于上下文）
        file_name = symbol.file_path.split('/')[-1] if '/' in symbol.file_path else symbol.file_path
        text_parts.append(f"位置: {file_name}")
        
        return " ".join(text_parts)
    
    def _build_symbol_context(self, symbol: CodeSymbol) -> str:
        """构建符号上下文信息"""
        context_parts = []
        
        if symbol.parent_class:
            context_parts.append(f"类 {symbol.parent_class} 的成员")
        
        if symbol.decorators:
            context_parts.append(f"装饰器: {', '.join(symbol.decorators)}")
        
        if symbol.complexity > 5:
            context_parts.append(f"复杂度: {symbol.complexity}")
        
        context_parts.append(f"语言: {symbol.language}")
        
        return "，".join(context_parts) if context_parts else "无额外上下文"
    
    def _generate_usage_hint(self, symbol: CodeSymbol) -> str:
        """生成使用提示"""
        if symbol.symbol_type == 'function':
            if symbol.parameters:
                return f"函数调用: {symbol.name}({', '.join(symbol.parameters)})"
            else:
                return f"函数调用: {symbol.name}()"
        elif symbol.symbol_type == 'class':
            return f"类实例化: {symbol.name}()"
        elif symbol.symbol_type == 'variable':
            return f"变量访问: {symbol.name}"
        else:
            return f"符号引用: {symbol.name}"
    
    def _calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def _analyze_similarity_reason(self, symbol1: CodeSymbol, symbol2: CodeSymbol) -> str:
        """分析相似性原因"""
        reasons = []
        
        if symbol1.symbol_type == symbol2.symbol_type:
            reasons.append(f"相同类型({symbol1.symbol_type})")
        
        if symbol1.language == symbol2.language:
            reasons.append(f"相同语言({symbol1.language})")
        
        # 检查名称相似性
        if symbol1.name.lower() in symbol2.name.lower() or symbol2.name.lower() in symbol1.name.lower():
            reasons.append("名称相似")
        
        # 检查参数相似性
        common_params = set(symbol1.parameters) & set(symbol2.parameters)
        if common_params:
            reasons.append(f"共同参数({len(common_params)}个)")
        
        return "，".join(reasons) if reasons else "语义相似"
    
    def _assess_drift_risk(self, similarity: float) -> str:
        """评估语义漂移风险"""
        if similarity < 0.5:
            return "高风险"
        elif similarity < 0.7:
            return "中等风险"
        else:
            return "低风险"
    
    def _analyze_change_details(self, old_symbol: CodeSymbol, new_symbol: CodeSymbol) -> str:
        """分析变更详情"""
        changes = []
        
        if old_symbol.signature != new_symbol.signature:
            changes.append("签名变更")
        
        if set(old_symbol.parameters) != set(new_symbol.parameters):
            changes.append("参数变更")
        
        if old_symbol.return_type != new_symbol.return_type:
            changes.append("返回类型变更")
        
        if set(old_symbol.decorators) != set(new_symbol.decorators):
            changes.append("装饰器变更")
        
        if old_symbol.complexity != new_symbol.complexity:
            changes.append(f"复杂度变更({old_symbol.complexity} -> {new_symbol.complexity})")
        
        return "，".join(changes) if changes else "内容变更" 