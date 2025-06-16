from setuptools import setup
import subprocess
import os

# 编译Tree-sitter语言定义
def build_tree_sitter_languages():
    # 创建build目录
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    os.makedirs(build_dir, exist_ok=True)
    output_path = os.path.join(build_dir, 'my-languages.so')

    # 检查是否已存在编译好的文件
    if os.path.exists(output_path):
        return

    # 定义要编译的语言和对应的仓库URL
    languages = {
        'python': 'https://github.com/tree-sitter/tree-sitter-python.git',
        'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript.git',
        'java': 'https://github.com/tree-sitter/tree-sitter-java.git',
        'cpp': 'https://github.com/tree-sitter/tree-sitter-cpp.git',
        'go': 'https://github.com/tree-sitter/tree-sitter-go.git'
    }

    # 克隆语言仓库
    for lang, repo in languages.items():
        lang_dir = os.path.join(build_dir, lang)
        if not os.path.exists(lang_dir):
            subprocess.run([
                'git', 'clone', '--depth', '1', repo, lang_dir
            ], check=True)

    # 编译语言定义
    subprocess.run([
        'tree-sitter', 'build-wasm', '--output', output_path
    ] + list(languages.keys()), check=True)

# 在安装前编译Tree-sitter语言
build_tree_sitter_languages()

setup(
    name='cursor-level-analyzer',
    version='0.1',
    packages=['backend'],
    install_requires=[
        'tree-sitter>=0.20.0',
        'requests>=2.26.0',
        'sentence-transformers>=2.2.2',
        'python-dotenv>=0.19.0',
        'pytest>=7.0.1'
    ],
    entry_points={
        'console_scripts': [
            'cursor-analyzer=backend.main:main'
        ]
    }
)