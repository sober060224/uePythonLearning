"""
=============================================================
第1课：Hello Unreal - 你的第一个 UE Python 脚本
=============================================================

学习目标：
  - 了解 unreal 模块的基本结构
  - 学会获取引擎和编辑器信息
  - 理解 UE Python 的基本工作方式

前置要求：
  - 已启用 Python Editor Script Plugin
  - 已启用 Editor Scripting Utilities

运行方式：
  - 在 UE Python Console 中逐段执行
  - 或执行: exec(open("path/to/01_hello_unreal.py").read())
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 确认 unreal 模块可用
# ─────────────────────────────────────────────────────────
# unreal 模块是 UE 提供的核心 Python 接口
# 只有在 UE 编辑器内部才能 import 成功
print("=" * 50)
print("Hello, Unreal Engine!")
print("=" * 50)

# ─────────────────────────────────────────────────────────
# 2. 获取引擎版本信息
# ─────────────────────────────────────────────────────────
# unreal.SystemLibrary 提供了大量系统级工具函数
engine_version = unreal.SystemLibrary.get_engine_version()
unreal.log(f"引擎版本: {engine_version}")

# ─────────────────────────────────────────────────────────
# 3. 获取项目信息
# ─────────────────────────────────────────────────────────
# EditorAssetLibrary 是资产管理的核心工具类
# 它可以在不加载资产的情况下查询和操作资产
project_dir = unreal.Paths.project_dir()
unreal.log(f"项目目录: {project_dir}")

content_dir = unreal.Paths.project_content_dir()
unreal.log(f"Content 目录: {content_dir}")  

# ─────────────────────────────────────────────────────────
# 4. 了解 unreal 模块的结构
# ─────────────────────────────────────────────────────────
# unreal 模块包含数百个类，按功能分组：
#
# 核心系统类:
#   unreal.SystemLibrary       - 系统级工具函数
#   unreal.Paths               - 路径处理工具
#   unreal.EditorAssetLibrary  - 资产管理（不加载资产）
#   unreal.AssetTools          - 资产创建、导入、导出
#
# 编辑器类:
#   unreal.EditorLevelLibrary  - 关卡编辑操作
#   unreal.LevelEditor         - 编辑器窗口管理
#   unreal.Subsystem           - 编辑器子系统
#
# 游戏类:
#   unreal.Actor               - Actor 基类
#   unreal.Blueprint           - 蓝图相关
#   unreal.Material            - 材质相关
#
# 让我们看看有多少可用的类：
all_classes = [name for name in dir(unreal) if not name.startswith('_')]
unreal.log(f"unreal 模块包含 {len(all_classes)} 个类/函数")

# ─────────────────────────────────────────────────────────
# 5. 使用 EditorAssetLibrary 查看项目资产概况
# ─────────────────────────────────────────────────────────
# list_assets 返回指定路径下所有资产的列表
# 这是最常用的函数之一！
all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)
unreal.log(f"项目中共有 {len(all_assets)} 个资产")

# 列出前10个资产看看
for asset_path in all_assets[:10]:
    unreal.log(f"  资产: {asset_path}")

# ─────────────────────────────────────────────────────────
# 6. 了解类型系统
# ─────────────────────────────────────────────────────────
# UE Python 使用强类型，每个资产都有明确的类型
# 可以用 load_asset 加载资产并检查其类型
if all_assets:
    # 尝试加载第一个资产
    first_asset = unreal.EditorAssetLibrary.load_asset(all_assets[0])
    if first_asset:
        unreal.log(f"\n第一个资产详情:")
        unreal.log(f"  路径: {all_assets[0]}")
        unreal.log(f"  类型: {type(first_asset).__name__}")
        unreal.log(f"  类: {first_asset.get_class().get_name()}")

# ─────────────────────────────────────────────────────────
# 7. 常用工具函数一览
# ─────────────────────────────────────────────────────────
# 这里列出一些你会频繁使用的函数：
#
# unreal.EditorAssetLibrary.list_assets(path)     - 列出资产
# unreal.EditorAssetLibrary.load_asset(path)       - 加载资产
# unreal.EditorAssetLibrary.does_asset_exist(path) - 检查资产是否存在
# unreal.EditorAssetLibrary.find_asset_data(path)  - 获取资产元数据
# unreal.Paths.project_dir()                       - 获取项目目录
# unreal.Paths.combine([path1, path2])             - 拼接路径
# unreal.SystemLibrary.get_engine_version()        - 获取引擎版本

unreal.log("\n" + "=" * 50)
unreal.log("第1课完成！你已经成功运行了第一个 UE Python 脚本")
unreal.log("=" * 50)

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 修改代码，只列出 /Game/Characters 路径下的资产
# 2. 统计项目中每种类型的资产各有多少个
# 3. 找到项目中最近创建的5个资产（提示：查看 find_asset_data 的返回值）
#
# 提示：可以用 unreal.log 输出到 UE 的输出日志窗口查看结果
