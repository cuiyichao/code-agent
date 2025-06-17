"""
API路由清理指南
==============

本文档说明了新旧API路由的映射关系，用于清理重复的实现。

## 路由映射关系

### 原有路由 (routes.py) -> 新路由 (advanced_routes.py)

1. 分析相关：
   - `/api/analyzer/analyze` -> `/api/advanced/analyze/changes`
   - `/api/analyzer/ai-providers` -> 保留在 routes.py (通用功能)
   - `/api/analyzer/test-generator` -> 保留在 routes.py (专门的测试生成)

2. 新增的高级功能：
   - `/api/advanced/index/build` (新功能)
   - `/api/advanced/search/semantic` (新功能)
   - `/api/advanced/github/pr/<id>/analyze` (新功能)
   - `/api/advanced/symbols/find` (新功能)
   - `/api/advanced/repository/info` (新功能)

## 建议的清理步骤

### 第一阶段：共存
- 保持两套API同时存在
- 前端逐步迁移到新API
- 添加废弃警告

### 第二阶段：迁移
- 更新前端组件使用新API
- 在旧API中添加重定向或代理

### 第三阶段：清理
- 移除重复的API实现
- 保留必要的通用功能

## 功能职责划分

### routes.py (通用API)
- 项目管理
- 基础分析配置
- AI服务提供商
- 任务状态管理
- 分析历史

### advanced_routes.py (高级分析API)
- 符号索引管理
- 语义搜索
- 深度变更分析
- GitHub集成
- 符号查找

## 数据库统一

使用 `database_migration.py` 统一管理：
- 所有表结构定义
- 索引创建
- 迁移脚本

## 前端组件映射

### 原有组件
- `EnhancedAnalyzer.vue` -> 基础分析功能

### 新组件
- `AdvancedAnalyzer.vue` -> 高级分析功能

## 注意事项

1. **API版本管理**：
   - 考虑添加版本号 (v1, v2)
   - 保持向后兼容

2. **错误处理**：
   - 统一错误响应格式
   - 使用 response_utils.py

3. **认证授权**：
   - 复用 auth_utils.py
   - 保持一致的认证策略

4. **日志记录**：
   - 统一日志格式
   - 区分不同模块的日志

## 清理检查清单

- [ ] 确认新API功能完整性
- [ ] 前端组件迁移完成
- [ ] 数据库结构统一
- [ ] 移除重复的分析器类
- [ ] 更新文档和测试
- [ ] 性能测试和验证
"""

# 实用工具函数

def check_duplicate_routes():
    """检查重复的路由定义"""
    import os
    import re
    from pathlib import Path
    
    routes_file = Path(__file__).parent / 'routes.py'
    advanced_file = Path(__file__).parent / 'advanced_routes.py'
    
    if not routes_file.exists() or not advanced_file.exists():
        print("API文件不存在")
        return
    
    # 提取路由定义
    route_pattern = r"@\w+\.route\(['\"](.*?)['\"]"
    
    routes_endpoints = []
    advanced_endpoints = []
    
    # 读取routes.py
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
        routes_endpoints = re.findall(route_pattern, content)
    
    # 读取advanced_routes.py
    with open(advanced_file, 'r', encoding='utf-8') as f:
        content = f.read()
        advanced_endpoints = re.findall(route_pattern, content)
    
    # 查找重复
    duplicates = set(routes_endpoints) & set(advanced_endpoints)
    
    print("=== API路由重复检查 ===")
    print(f"routes.py 端点数量: {len(routes_endpoints)}")
    print(f"advanced_routes.py 端点数量: {len(advanced_endpoints)}")
    print(f"重复端点数量: {len(duplicates)}")
    
    if duplicates:
        print("\n重复的端点:")
        for endpoint in duplicates:
            print(f"  - {endpoint}")
    else:
        print("\n✅ 没有发现重复的端点")
    
    return duplicates

if __name__ == "__main__":
    check_duplicate_routes() 