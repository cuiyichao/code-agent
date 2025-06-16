import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from backend.utils.logging import get_logger

@dataclass
class AppConfig:
    """应用程序配置"""
    # 代码库路径
    codebase_path: str = "."
    # 索引目录
    index_dir: str = ".code_index"
    # 日志目录
    log_dir: str = ".logs"
    # 日志级别
    log_level: str = "INFO"
    # AI API基础URL
    ai_api_base_url: str = "https://api.openai.com/v1"
    # 默认嵌入模型
    embedding_model: str = "all-MiniLM-L6-v2"
    # 分析结果缓存目录
    cache_dir: str = ".cache"
    # 支持的编程语言
    supported_languages: Dict[str, str] = None

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = {
                'py': 'python',
                'js': 'javascript',
                'java': 'java',
                'cpp': 'cpp',
                'hpp': 'cpp',
                'c': 'cpp',
                'h': 'cpp',
                'go': 'go'
            }

class ConfigManager:
    """配置管理器，用于加载和管理应用程序配置"""
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = AppConfig()
        self.config_paths = [
            os.path.expanduser("~/.code_analyzer/config.json"),
            "./code_analyzer_config.json",
            os.environ.get("CODE_ANALYZER_CONFIG")
        ]

    def load_config(self, config_file: Optional[str] = None) -> AppConfig:
        """加载配置

        Args:
            config_file: 自定义配置文件路径

        Returns:
            加载后的配置对象
        """
        # 从文件加载配置
        if config_file:
            self._load_from_file(config_file)
        else:
            # 尝试从默认路径加载
            for path in self.config_paths:
                if path and os.path.exists(path):
                    self._load_from_file(path)
                    break

        # 从环境变量加载配置（覆盖文件配置）
        self._load_from_env()

        # 确保目录存在
        self._ensure_directories()

        self.logger.info("Configuration loaded successfully")
        return self.config

    def _load_from_file(self, file_path: str) -> None:
        """从配置文件加载配置"""
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)

            # 更新配置
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.logger.warning(f"Unknown configuration key: {key}")

            self.logger.info(f"Loaded configuration from {file_path}")

        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {file_path}")
        except Exception as e:
            self.logger.error(f"Error loading config file {file_path}: {str(e)}")

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        env_mappings = {
            'CODEBASE_PATH': 'codebase_path',
            'INDEX_DIR': 'index_dir',
            'LOG_DIR': 'log_dir',
            'LOG_LEVEL': 'log_level',
            'AI_API_BASE_URL': 'ai_api_base_url',
            'EMBEDDING_MODEL': 'embedding_model',
            'CACHE_DIR': 'cache_dir'
        }

        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                setattr(self.config, config_key, value)
                self.logger.debug(f"Set {config_key} from environment variable: {value}")

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        directories = [
            self.config.index_dir,
            self.config.log_dir,
            self.config.cache_dir
        ]

        for dir_path in directories:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                self.logger.info(f"Created directory: {dir_path}")

    def save_config(self, file_path: str) -> bool:
        """保存配置到文件

        Args:
            file_path: 保存路径

        Returns:
            是否保存成功
        """
        try:
            # 获取配置字典
            config_dict = {
                key: value for key, value in self.config.__dict__.items()
                if not key.startswith('_')
            }

            # 确保目录存在
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # 保存到文件
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)

            self.logger.info(f"Configuration saved to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config file {file_path}: {str(e)}")
            return False

# 创建全局配置管理器实例
config_manager = ConfigManager()
# 加载配置
config = config_manager.load_config()