"""
=============================================================
蓝图自动化 第1课：蓝图基础 - 创建和修改蓝图
=============================================================

学习目标：
  - 使用 Python 创建蓝图类
  - 了解蓝图的内部结构
  - 通过脚本修改蓝图属性

核心概念：
  - Blueprint = 蓝图资产（类定义）
  - BlueprintGeneratedClass = 蓝图编译后的类
  - SimpleConstructionScript = 组件树结构
  - 蓝图本质上是一个 "可视化 C++ 类"

前置要求：
  - 启用 Editor Scripting Utilities 插件

本课可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path, recursive=True, include_folder=False) -> Array[str]  —— 递归列出路径下全部资产
  unreal.EditorAssetLibrary.find_asset_data(asset_path) -> AssetData  —— 按路径查资产数据，不加载资产
  unreal.EditorAssetLibrary.load_asset(asset_path) -> Object  —— 把资产加载进内存
  unreal.EditorAssetLibrary.make_directory(directory_path) -> bool  —— 创建资产目录
  unreal.EditorAssetLibrary.save_asset(asset_to_save, only_if_is_dirty=True) -> bool  —— 保存指定资产
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具单例
  unreal.BlueprintFactory()  —— 蓝图工厂，配合 set_editor_property 设置父类
  obj.set_editor_property(name, value)  —— 设置 UObject 的编辑器属性
  asset_tools.create_asset(asset_name, package_path, asset_class, factory, calling_context="None", overwrite_existing=False) -> Object  —— 用工厂创建新资产
  unreal.BlueprintEditorLibrary.compile_blueprint(blueprint) -> bool  —— 重新编译蓝图
  unreal.ScopedSlowTask(work, desc="", enabled=True)  —— 创建带进度的慢任务对象
  task.make_dialog(can_cancel=False, allow_in_pie=False) -> None  —— 弹出进度对话框
  task.enter_progress_frame(work=1.0, desc="") -> None  —— 推进一帧进度
  task.should_cancel() -> bool  —— 用户是否请求取消
  obj.get_class() -> Class  —— 取对象的 Unreal 类
  obj.get_name() -> str  —— 取对象名称
  unreal.log() / unreal.log_warning() / unreal.log_error()  —— 输出日志/警告/错误
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 查找和加载现有蓝图
# ─────────────────────────────────────────────────────────

def find_all_blueprints(search_path="/Game"):
    """查找项目中所有蓝图"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    blueprints = []

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        class_str = str(asset_data.asset_class_path)
        if "Blueprint" in class_str:
            blueprints.append(asset_data)

    return blueprints

# 查找所有蓝图
bps = find_all_blueprints()
unreal.log(f"项目中共有 {len(bps)} 个蓝图:")
for bp in bps[:20]:
    unreal.log(f"  {bp.package_name} - {bp.asset_name}")

# ─────────────────────────────────────────────────────────
# 2. 加载和检查蓝图
# ─────────────────────────────────────────────────────────

def inspect_blueprint(blueprint_path):
    """详细检查一个蓝图的信息"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)

    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"蓝图: {bp.get_name()}")
    unreal.log(f"路径: {blueprint_path}")
    unreal.log(f"类型: {type(bp).__name__}")

    # 检查是否是 Blueprint 类型
    if hasattr(bp, 'get_class'):
        unreal.log(f"类名: {bp.get_class().get_name()}")

    # 获取父类信息
    if hasattr(bp, 'parent_class'):
        parent = bp.parent_class
        if parent:
            unreal.log(f"父类: {parent.get_name()}")

    return bp

# 加载第一个蓝图进行检查（替换为你项目中的蓝图路径）
if bps:
    inspect_blueprint(bps[0].package_name)

# ─────────────────────────────────────────────────────────
# 3. 创建新蓝图
# ─────────────────────────────────────────────────────────

def create_blueprint(name, parent_class, destination_path="/Game/Blueprints"):
    """
    创建一个新的蓝图资产

    参数:
        name: 蓝图名称 (如 "BP_MyActor")
        parent_class: 父类 (如 unreal.Actor, unreal.Pawn 等)
        destination_path: 保存路径
    """
    # 确保目录存在
    unreal.EditorAssetLibrary.make_directory(destination_path)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # 使用 BlueprintFactory 创建蓝图
    factory = unreal.BlueprintFactory()
    # 【修改前】factory.set_editor_property("ParentClass", parent_class)
    # 【问题分析】蓝图工厂的编辑器属性名是 parent_class（小写），
    #   见 stub 中 class BlueprintFactory 的属性列表。
    factory.set_editor_property("parent_class", parent_class)

    # 创建资产
    new_bp = asset_tools.create_asset(
        name,
        destination_path,
        unreal.Blueprint,
        factory
    )

    if new_bp:
        full_path = f"{destination_path}/{name}"
        unreal.log(f"成功创建蓝图: {full_path}")

        # 自动保存
        unreal.EditorAssetLibrary.save_asset(full_path)
        return new_bp
    else:
        unreal.log_error(f"创建蓝图失败: {name}")
        return None

# ─────────────────────────────────────────────────────────
# 4. 创建 Actor 蓝图的实用封装
# ─────────────────────────────────────────────────────────

def create_actor_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 Actor 的蓝图"""
    return create_blueprint(name, unreal.Actor, destination)

def create_pawn_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 Pawn 的蓝图"""
    return create_blueprint(name, unreal.Pawn, destination)

def create_player_controller_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 PlayerController 的蓝图"""
    return create_blueprint(name, unreal.PlayerController, destination)

def create_game_mode_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 GameMode 的蓝图"""
    return create_blueprint(name, unreal.GameModeBase, destination)

def create_actor_component_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 ActorComponent 的蓝图"""
    return create_blueprint(name, unreal.ActorComponent, destination)

# ─────────────────────────────────────────────────────────
# 5. 批量创建蓝图模板
# ─────────────────────────────────────────────────────────

def create_blueprint_set(blueprint_defs, destination="/Game/Blueprints"):
    """
    批量创建一组蓝图

    参数:
        blueprint_defs: list of (name, parent_class) 元组
        destination: 目标路径

    示例:
        create_blueprint_set([
            ("BP_EnemyBase", unreal.Character),
            ("BP_EnemyFlyer", unreal.Character),
            ("BP_PickupItem", unreal.Actor),
        ])
    """
    created = []

    task = unreal.ScopedSlowTask(len(blueprint_defs), "批量创建蓝图...")
    task.make_dialog(True)

    for name, parent_class in blueprint_defs:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, f"创建: {name}")
        bp = create_blueprint(name, parent_class, destination)
        if bp:
            created.append(bp)

    unreal.log(f"成功创建 {len(created)}/{len(blueprint_defs)} 个蓝图")
    return created

# ─────────────────────────────────────────────────────────
# 6. 蓝图的编译
# ─────────────────────────────────────────────────────────

def compile_blueprint(blueprint_path):
    """编译蓝图"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return False

    # 使用 BlueprintsLibrary 编译
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.log(f"已编译蓝图: {blueprint_path}")
    return True

def compile_all_blueprints(search_path="/Game"):
    """编译指定路径下的所有蓝图"""
    bps = find_all_blueprints(search_path)

    task = unreal.ScopedSlowTask(len(bps), "编译蓝图...")
    task.make_dialog(True)

    compiled = 0
    for bp_data in bps:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, bp_data.asset_name)
        if compile_blueprint(bp_data.package_name):
            compiled += 1

    unreal.log(f"已编译 {compiled}/{len(bps)} 个蓝图")

# ─────────────────────────────────────────────────────────
# 7. 实用示例：创建游戏框架蓝图集
# ─────────────────────────────────────────────────────────

def create_game_framework():
    """创建一套基本的游戏框架蓝图"""
    definitions = [
        ("BP_GameMode", unreal.GameModeBase),
        ("BP_GameState", unreal.GameStateBase),
        ("BP_PlayerController", unreal.PlayerController),
        ("BP_PlayerState", unreal.PlayerState),
        ("BP_Pawn", unreal.Pawn),
        ("BP_HUD", unreal.HUD),
    ]

    return create_blueprint_set(definitions, "/Game/Framework")

# ─────────────────────────────────────────────────────────
# 使用示例（取消注释来运行）
# ─────────────────────────────────────────────────────────

# 示例1: 创建一个简单的 Actor 蓝图
# create_actor_blueprint("BP_TestActor")

# 示例2: 创建游戏框架
# create_game_framework()

# 示例3: 编译所有蓝图
# compile_all_blueprints("/Game/Blueprints")

unreal.log("蓝图自动化第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个蓝图，它继承自 Character，并包含一个
#    StaticMeshComponent 作为视觉表示
# 2. 批量创建 10 个不同的 Actor 蓝图，每个都有独特名称
# 3. 编写一个工具，列出项目中所有蓝图的父类关系图
# 4. 查找所有编译有错误的蓝图（提示：检查编译状态）
