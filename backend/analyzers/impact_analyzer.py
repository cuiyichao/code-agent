import logging
import networkx as nx
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, deque

from ..models.code_symbol import CodeSymbol, CodeReference, ChangeAnalysis

class ImpactAnalyzer:
    """影响分析器 - 负责深度影响分析"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 依赖图
        self.dependency_graph = nx.DiGraph()
        self.call_graph = nx.DiGraph()
        self.inheritance_graph = nx.DiGraph()
        
        # 分析配置
        self.max_depth = 5  # 影响分析最大深度
        self.risk_thresholds = {
            'low': 5,
            'medium': 15,
            'high': 30,
            'critical': 50
        }
    
    def build_dependency_graphs(self, symbols: Dict[str, CodeSymbol], 
                              references: List[CodeReference]):
        """构建依赖图"""
        self.logger.info("构建依赖图...")
        
        # 清空现有图
        self.dependency_graph.clear()
        self.call_graph.clear()
        self.inheritance_graph.clear()
        
        # 添加符号节点
        for symbol_id, symbol in symbols.items():
            self.dependency_graph.add_node(symbol_id, symbol=symbol)
            self.call_graph.add_node(symbol_id, symbol=symbol)
            self.inheritance_graph.add_node(symbol_id, symbol=symbol)
        
        # 构建引用关系
        for ref in references:
            if ref.source_symbol_id in symbols and ref.target_symbol_id in symbols:
                # 通用依赖图
                self.dependency_graph.add_edge(ref.source_symbol_id, ref.target_symbol_id, 
                                             reference=ref)
                
                # 特定类型的图
                if ref.reference_type == "call":
                    self.call_graph.add_edge(ref.source_symbol_id, ref.target_symbol_id, 
                                           reference=ref)
                elif ref.reference_type == "inherit":
                    self.inheritance_graph.add_edge(ref.source_symbol_id, ref.target_symbol_id, 
                                                   reference=ref)
        
        self.logger.info(f"依赖图构建完成: {len(self.dependency_graph.nodes)} 节点, "
                        f"{len(self.dependency_graph.edges)} 边")
    
    def analyze_symbol_impact(self, changed_symbols: List[CodeSymbol]) -> ChangeAnalysis:
        """分析符号变更的影响"""
        self.logger.info(f"分析 {len(changed_symbols)} 个符号的影响...")
        
        direct_impacts = []
        indirect_impacts = []
        affected_files = set()
        business_impact = []
        
        # 分析每个变更符号
        for symbol in changed_symbols:
            affected_files.add(symbol.file_path)
            
            # 分析直接影响
            direct_deps = self._get_direct_dependents(symbol.id)
            direct_impacts.extend(direct_deps)
            
            # 分析间接影响
            indirect_deps = self._get_indirect_dependents(symbol.id, max_depth=self.max_depth)
            indirect_impacts.extend(indirect_deps)
            
            # 收集受影响的文件
            for dep_id in direct_deps + indirect_deps:
                if dep_id in self.dependency_graph.nodes:
                    dep_symbol = self.dependency_graph.nodes[dep_id].get('symbol')
                    if dep_symbol:
                        affected_files.add(dep_symbol.file_path)
            
            # 业务影响评估
            business_impact.extend(self._assess_business_impact(symbol))
        
        # 去重
        direct_impacts = list(set(direct_impacts))
        indirect_impacts = list(set(indirect_impacts))
        
        # 计算风险等级
        risk_level = self._calculate_risk_level(
            len(direct_impacts), 
            len(indirect_impacts), 
            len(affected_files)
        )
        
        # 计算置信度
        confidence_score = self._calculate_confidence_score(
            changed_symbols, direct_impacts, indirect_impacts
        )
        
        return ChangeAnalysis(
            changed_symbols=changed_symbols,
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            affected_files=list(affected_files),
            risk_level=risk_level,
            confidence_score=confidence_score,
            business_impact=list(set(business_impact)),
            suggested_tests=[]  # 由测试生成器填充
        )
    
    def analyze_breaking_changes(self, old_symbols: Dict[str, CodeSymbol], 
                               new_symbols: Dict[str, CodeSymbol]) -> List[Dict[str, Any]]:
        """分析破坏性变更"""
        breaking_changes = []
        
        for symbol_id in old_symbols:
            if symbol_id in new_symbols:
                old_symbol = old_symbols[symbol_id]
                new_symbol = new_symbols[symbol_id]
                
                # 检查签名变更
                if old_symbol.signature != new_symbol.signature:
                    breaking_changes.append({
                        'type': 'signature_change',
                        'symbol_id': symbol_id,
                        'symbol_name': old_symbol.name,
                        'old_signature': old_symbol.signature,
                        'new_signature': new_symbol.signature,
                        'risk_level': self._assess_signature_change_risk(old_symbol, new_symbol),
                        'affected_dependents': self._get_direct_dependents(symbol_id)
                    })
                
                # 检查参数变更
                old_params = set(old_symbol.parameters)
                new_params = set(new_symbol.parameters)
                
                if old_params != new_params:
                    breaking_changes.append({
                        'type': 'parameter_change',
                        'symbol_id': symbol_id,
                        'symbol_name': old_symbol.name,
                        'removed_params': list(old_params - new_params),
                        'added_params': list(new_params - old_params),
                        'risk_level': 'high' if old_params - new_params else 'medium',
                        'affected_dependents': self._get_direct_dependents(symbol_id)
                    })
            else:
                # 符号被删除
                old_symbol = old_symbols[symbol_id]
                breaking_changes.append({
                    'type': 'symbol_removed',
                    'symbol_id': symbol_id,
                    'symbol_name': old_symbol.name,
                    'symbol_type': old_symbol.symbol_type,
                    'risk_level': 'critical',
                    'affected_dependents': self._get_direct_dependents(symbol_id)
                })
        
        return breaking_changes
    
    def get_critical_path(self, start_symbol_id: str, end_symbol_id: str) -> Optional[List[str]]:
        """获取符号间的关键路径"""
        try:
            if start_symbol_id in self.dependency_graph and end_symbol_id in self.dependency_graph:
                return nx.shortest_path(self.dependency_graph, start_symbol_id, end_symbol_id)
        except nx.NetworkXNoPath:
            pass
        return None
    
    def get_symbol_centrality(self, symbols: Dict[str, CodeSymbol]) -> Dict[str, float]:
        """计算符号的中心性（重要性）"""
        if not self.dependency_graph.nodes:
            return {}
        
        try:
            # 计算PageRank中心性
            centrality = nx.pagerank(self.dependency_graph, weight='weight')
            return centrality
        except Exception as e:
            self.logger.error(f"计算中心性失败: {e}")
            return {}
    
    def cluster_by_dependency(self, min_cluster_size: int = 3) -> Dict[str, List[str]]:
        """基于依赖关系的符号聚类"""
        if not self.dependency_graph.nodes:
            return {}
        
        try:
            # 使用强连通分量进行聚类
            components = list(nx.strongly_connected_components(self.dependency_graph))
            
            clusters = {}
            for i, component in enumerate(components):
                if len(component) >= min_cluster_size:
                    clusters[f"cluster_{i}"] = list(component)
            
            return clusters
        except Exception as e:
            self.logger.error(f"依赖聚类失败: {e}")
            return {}
    
    def _get_direct_dependents(self, symbol_id: str) -> List[str]:
        """获取直接依赖者"""
        if symbol_id not in self.dependency_graph:
            return []
        
        return list(self.dependency_graph.predecessors(symbol_id))
    
    def _get_indirect_dependents(self, symbol_id: str, max_depth: int = 3) -> List[str]:
        """获取间接依赖者（多层传播）"""
        if symbol_id not in self.dependency_graph:
            return []
        
        visited = set()
        queue = deque([(symbol_id, 0)])
        indirect_deps = []
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # 获取直接依赖者
            for dependent in self.dependency_graph.predecessors(current_id):
                if dependent not in visited:
                    if depth > 0:  # 排除直接依赖，只包含间接依赖
                        indirect_deps.append(dependent)
                    queue.append((dependent, depth + 1))
        
        return list(set(indirect_deps))
    
    def _assess_business_impact(self, symbol: CodeSymbol) -> List[str]:
        """评估业务影响"""
        business_impacts = []
        
        # 基于符号名称判断业务重要性
        critical_keywords = {
            'auth': '认证相关',
            'login': '登录功能',
            'payment': '支付功能',
            'order': '订单处理',
            'user': '用户管理',
            'admin': '管理功能',
            'security': '安全功能',
            'validate': '验证逻辑',
            'process': '核心处理',
            'create': '创建功能',
            'delete': '删除功能',
            'update': '更新功能'
        }
        
        symbol_name_lower = symbol.name.lower()
        for keyword, impact in critical_keywords.items():
            if keyword in symbol_name_lower:
                business_impacts.append(impact)
        
        # 基于文件路径判断模块重要性
        file_path_lower = symbol.file_path.lower()
        if 'api' in file_path_lower or 'service' in file_path_lower:
            business_impacts.append("核心API服务")
        elif 'model' in file_path_lower or 'entity' in file_path_lower:
            business_impacts.append("数据模型层")
        elif 'controller' in file_path_lower:
            business_impacts.append("控制器层")
        elif 'util' in file_path_lower or 'helper' in file_path_lower:
            business_impacts.append("工具函数层")
        
        # 基于复杂度判断
        if symbol.complexity > 10:
            business_impacts.append("高复杂度函数")
        
        return business_impacts
    
    def _calculate_risk_level(self, direct_count: int, indirect_count: int, 
                            file_count: int) -> str:
        """计算风险等级"""
        # 计算总影响分数
        impact_score = direct_count + (indirect_count * 0.3) + (file_count * 0.5)
        
        if impact_score >= self.risk_thresholds['critical']:
            return "critical"
        elif impact_score >= self.risk_thresholds['high']:
            return "high"
        elif impact_score >= self.risk_thresholds['medium']:
            return "medium"
        else:
            return "low"
    
    def _calculate_confidence_score(self, changed_symbols: List[CodeSymbol], 
                                  direct_impacts: List[str], 
                                  indirect_impacts: List[str]) -> float:
        """计算分析置信度"""
        confidence = 0.5  # 基础置信度
        
        # 基于图的完整性
        if len(self.dependency_graph.nodes) > 100:
            confidence += 0.2
        
        if len(self.dependency_graph.edges) > 200:
            confidence += 0.1
        
        # 基于分析覆盖度
        if direct_impacts:
            confidence += 0.1
        
        if indirect_impacts:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _assess_signature_change_risk(self, old_symbol: CodeSymbol, 
                                    new_symbol: CodeSymbol) -> str:
        """评估签名变更风险"""
        old_params = set(old_symbol.parameters)
        new_params = set(new_symbol.parameters)
        
        # 参数减少 = 高风险
        if old_params - new_params:
            return "high"
        
        # 参数增加但有默认值 = 中风险
        if new_params - old_params:
            return "medium"
        
        # 返回类型变更
        if old_symbol.return_type != new_symbol.return_type:
            return "medium"
        
        return "low" 