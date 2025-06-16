import argparse
import json
import os
import asyncio
from typing import Optional
from backend.analyzers.cursor_level_analyzer import CursorLevelAnalyzer
from backend.utils.logging import setup_logging, get_logger

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Cursor Level Code Analyzer - 智能代码变更分析系统')
    parser.add_argument('--codebase', type=str, default='.', help='代码库路径')
    parser.add_argument('--index-dir', type=str, default='.code_index', help='索引目录路径')
    parser.add_argument('--commit', type=str, help='要分析的提交哈希')
    parser.add_argument('--rebuild-index', action='store_true', help='重建代码库索引')
    parser.add_argument('--output', type=str, help='分析结果输出文件路径')
    parser.add_argument('--log-dir', type=str, default='.logs', help='日志目录路径')
    parser.add_argument('--log-level', type=str, default='INFO', help='日志级别 (DEBUG, INFO, WARNING, ERROR)')
    args = parser.parse_args()

    # 配置日志
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(args.log_dir, log_level)
    logger = get_logger(__name__)
    logger.info("Starting Cursor Level Code Analyzer")

    try:
        # 初始化分析器
        analyzer = CursorLevelAnalyzer(
            codebase_path=os.path.abspath(args.codebase),
            index_dir=args.index_dir
        )

        # 重建索引（如果需要）
        if args.rebuild_index:
            logger.info("Rebuilding codebase index...")
            index_result = analyzer.rebuild_index()
            logger.info(f"Index rebuilt successfully: {index_result}")
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(index_result, f, indent=2)
            return

        # 分析代码变更
        logger.info(f"Analyzing code changes for commit: {args.commit or 'working directory'}")
        changes = await analyzer.analyze_code_changes(args.commit)

        # 准备输出结果
        output = {
            "commit_hash": args.commit,
            "file_changes_count": len(changes),
            "changes": [{
                "file_path": c.file_path,
                "change_type": c.change_type,
                "affected_symbols_count": len(c.affected_symbols),
                "semantic_similarity": c.semantic_similarity,
                "business_impact": c.business_impact,
                "risk_factors": c.risk_factors,
                "suggested_tests": c.suggested_tests
            } for c in changes]
        }

        # 输出结果
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            logger.info(f"Analysis results saved to {args.output}")
        else:
            logger.info("Analysis results:")
            print(json.dumps(output, indent=2))

    except Exception as e:
        logger.error(f"An error occurred during analysis: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())