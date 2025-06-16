import os
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from backend.utils.logging import get_logger

logger = get_logger(__name__)

def get_file_hash(file_path: str) -> Optional[str]:
    """计算文件的MD5哈希值

    Args:
        file_path: 文件路径

    Returns:
        文件的MD5哈希值，或None（如果文件不存在或无法读取）
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None

    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # 分块读取大文件
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {str(e)}")
        return None

def read_file_content(file_path: str) -> Optional[str]:
    """读取文件内容

    Args:
        file_path: 文件路径

    Returns:
        文件内容字符串，或None（如果文件不存在或无法读取）
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"Cannot decode file as UTF-8: {file_path}")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return None

def write_file_content(file_path: str, content: str) -> bool:
    """写入内容到文件

    Args:
        file_path: 文件路径
        content: 要写入的内容

    Returns:
        是否写入成功
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {str(e)}")
        return False

def json_dump_pretty(data: Any, file_path: str) -> bool:
    """将数据以格式化的JSON写入文件

    Args:
        data: 要序列化的数据
        file_path: 文件路径

    Returns:
        是否写入成功
    """
    try:
        content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        return write_file_content(file_path, content)
    except Exception as e:
        logger.error(f"Error serializing data to JSON: {str(e)}")
        return False

def json_load(file_path: str) -> Optional[Any]:
    """从JSON文件加载数据

    Args:
        file_path: 文件路径

    Returns:
        加载的数据，或None（如果文件不存在或无法解析）
    """
    content = read_file_content(file_path)
    if not content:
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from {file_path}: {str(e)}")
        return None

def get_relative_path(base_path: str, target_path: str) -> str:
    """获取目标路径相对于基准路径的相对路径

    Args:
        base_path: 基准路径
        target_path: 目标路径

    Returns:
        相对路径字符串
    """
    return os.path.relpath(target_path, base_path)

def split_full_symbol(symbol_id: str) -> Tuple[str, str, str]:
    """拆分完整符号ID为模块路径、符号名称和类型

    Args:
        symbol_id: 完整符号ID，格式为"module_path::symbol_name::symbol_type"

    Returns:
        模块路径、符号名称和类型的元组
    """
    parts = symbol_id.split('::')
    if len(parts) != 3:
        logger.warning(f"Invalid symbol ID format: {symbol_id}")
        return ('', '', '')
    return (parts[0], parts[1], parts[2])

def merge_dicts(*dicts: Dict) -> Dict:
    """合并多个字典，后面的字典会覆盖前面的字典中的相同键

    Args:
        *dicts: 要合并的字典

    Returns:
        合并后的字典
    """
    merged = {}
    for d in dicts:
        if isinstance(d, dict):
            merged.update(d)
    return merged

def flatten_list(nested_list: List[Any]) -> List[Any]:
    """展平嵌套列表

    Args:
        nested_list: 可能包含嵌套列表的列表

    Returns:
        展平后的列表
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result

def get_file_extension(file_path: str) -> str:
    """获取文件扩展名（不带点）

    Args:
        file_path: 文件路径

    Returns:
        小写的文件扩展名
    """
    return os.path.splitext(file_path)[1].lower().lstrip('.')

def is_binary_file(file_path: str) -> bool:
    """判断文件是否为二进制文件

    Args:
        file_path: 文件路径

    Returns:
        是否为二进制文件
    """
    try:
        with open(file_path, 'rb') as f:
            # 读取前1024字节判断是否为二进制文件
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception as e:
        logger.error(f"Error checking if file is binary: {str(e)}")
        return False