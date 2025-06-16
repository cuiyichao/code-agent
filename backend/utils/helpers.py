import json
import logging
from typing import Dict, Any, Optional
from backend.models.semantic_change import SemanticChange

logger = logging.getLogger(__name__)

def _extract_json(response_text: str) -> Optional[Dict[str, Any]]:
    """从AI响应文本中提取JSON内容

    Args:
        response_text: AI返回的文本响应

    Returns:
        解析后的JSON字典，如果提取失败则返回None
    """
    if not response_text:
        return None

    # 尝试提取JSON对象（处理可能的代码块格式）
    start_marker = '{'
    end_marker = '}'
    start_idx = response_text.find(start_marker)
    end_idx = response_text.rfind(end_marker)

    if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
        logger.warning('无法从AI响应中提取JSON内容')
        return None

    json_str = response_text[start_idx:end_idx+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f'解析JSON失败: {str(e)}')
        logger.debug(f'待解析的JSON字符串: {json_str}')
        return None

def _semantic_change_to_dict(change: SemanticChange) -> Dict[str, Any]:
    """将SemanticChange对象转换为字典表示

    Args:
        change: SemanticChange对象

    Returns:
        包含变更信息的字典
    """
    return {
        'file_path': change.file_path,
        'change_type': change.change_type,
        'old_code': change.old_code,
        'new_code': change.new_code,
        'semantic_similarity': change.semantic_similarity,
        'affected_symbols': [
            {
                'name': symbol.name,
                'symbol_type': symbol.symbol_type,
                'start_line': symbol.start_line,
                'end_line': symbol.end_line
            } for symbol in change.affected_symbols
        ],
        'business_impact': change.business_impact,
        'risk_factors': change.risk_factors,
        'suggested_tests': change.suggested_tests,
        'confidence_score': change.confidence_score
    }