"""
=============================================================
蓝图自动化 第2课：蓝图的创建、编译与父类管理
=============================================================

学习目标：
  - 用 Python 创建蓝图资产并指定父类
  - 编译蓝图、查询蓝图的父类
  - 修改（重设）蓝图父类
  - 理解 UE Python 目前无法直接操作蓝图组件树 (SCS)

核心类：
  - unreal.BlueprintFactory - 蓝图工厂（用 parent_class 指定父类）
  - unreal.BlueprintEditorLibrary - 蓝图编辑器工具（编译、查询父类、重新指定父类）
  - unreal.Blueprint - 蓝图资产

⚠️ 关于蓝图组件（重要）：
  UE Python 并没有暴露 SimpleConstructionScript / SCS_Node 相关接口
  （在 Intermediate/PythonStub/unreal.py 中搜索 SimpleConstructionScript 无结果），
  因此"往蓝图中添加组件"无法用纯 Python 完成，需要在蓝图编辑器里手动添加组件，
  或者通过 C++ 编辑器扩展实现。本课改为演示 Python 确实能完成的部分：
  创建蓝图、指定/修改父类、编译、查询信息。

本课可能用到的 API：
  unreal.EditorAssetLibrary.load_asset(asset_path) -> Object  —— 加载蓝图资产到内存
  unreal.EditorAssetLibrary.save_asset(asset_to_save, only_if_is_dirty=True) -> bool  —— 保存修改后的蓝图
  unreal.EditorAssetLibrary.make_directory(directory_path) -> bool  —— 创建资产目录
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具单例
  unreal.BlueprintFactory()  —— 蓝图工厂，配合 set_editor_property("parent_class", ...) 设置父类
  asset_tools.create_asset(asset_name, package_path, asset_class, factory, calling_context="None", overwrite_existing=False) -> Object  —— 用工厂创建新蓝图资产
  unreal.BlueprintEditorLibrary.compile_blueprint(blueprint: Blueprint) -> bool  —— 编译蓝图
  unreal.BlueprintEditorLibrary.get_blueprint_parent_class(blueprint: Blueprint) -> Class  —— 读取蓝图父类
  unreal.BlueprintEditorLibrary.reparent_blueprint(blueprint: Blueprint, new_parent_class: Class) -> None  —— 重新指定蓝图父类
  obj.get_name() -> str  —— 获取对象名称
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 创建蓝图并指定父类
# ─────────────────────────────────────────────────────────

def create_blueprint(name, parent_class, destination="/Game/Blueprints"):
    """
    创建蓝图资产

    参数:
        name: 蓝图名称 (如 "BP_MyActor")
        parent_class: 父类 (如 unreal.Actor、unreal.Pawn)
        destination: 保存路径
    """
    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BlueprintFactory()
    # 蓝图工厂通过 parent_class 属性指定新蓝图的父类
    factory.set_editor_property("parent_class", parent_class)

    new_bp = asset_tools.create_asset(
        name,
        destination,
        unreal.Blueprint,
        factory
    )

    if not new_bp:
        unreal.log_error(f"创建蓝图失败: {name}")
        return None

    # 创建后编译一次，保证 GeneratedClass 可用
    unreal.BlueprintEditorLibrary.compile_blueprint(new_bp)
    full_path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(full_path)
    unreal.log(f"已创建蓝图: {full_path} 父类={parent_class.get_name()}")
    return new_bp

# ─────────────────────────────────────────────────────────
# 2. 查询蓝图信息
# ─────────────────────────────────────────────────────────

def inspect_blueprint(blueprint_path):
    """读取蓝图的名称、类型和父类"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp or not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    unreal.log(f"\n蓝图: {bp.get_name()}")
    unreal.log(f"  类: {bp.get_class().get_name()}")

    parent = unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)
    if parent:
        unreal.log(f"  父类: {parent.get_name()}")

    return bp

# ─────────────────────────────────────────────────────────
# 3. 修改蓝图父类
# ─────────────────────────────────────────────────────────

def reparent_blueprint(blueprint_path, new_parent_class):
    """把蓝图重新挂到一个新的父类下"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp or not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return False

    old_parent = unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)
    old_name = old_parent.get_name() if old_parent else "None"

    # reparent_blueprint 会重建蓝图的父类继承关系
    unreal.BlueprintEditorLibrary.reparent_blueprint(bp, new_parent_class)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(blueprint_path)

    unreal.log(
        f"已修改父类: {bp.get_name()}  {old_name} → {new_parent_class.get_name()}"
    )
    return True

# ─────────────────────────────────────────────────────────
# 4. 批量创建不同父类的蓝图
# ─────────────────────────────────────────────────────────

def create_blueprint_set(blueprint_defs, destination="/Game/Blueprints"):
    """
    批量创建一组蓝图

    参数:
        blueprint_defs: list of (名称, 父类) 元组

    示例:
        create_blueprint_set([
            ("BP_EnemyBase", unreal.Character),
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
# 5. 编译蓝图
# ─────────────────────────────────────────────────────────

def compile_blueprint(blueprint_path):
    """编译单个蓝图"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp or not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return False

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.log(f"已编译蓝图: {blueprint_path}")
    return True

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 示例1: 创建一个 Actor 蓝图
# create_blueprint("BP_TestActor", unreal.Actor)

# 示例2: 创建一组不同父类的蓝图
# create_blueprint_set([
#     ("BP_EnemyBase", unreal.Character),
#     ("BP_PickupItem", unreal.Actor),
# ])

# 示例3: 查询蓝图父类
# inspect_blueprint("/Game/Blueprints/BP_EnemyBase")

# 示例4: 修改父类（把 Actor 蓝图改成 Pawn）
# reparent_blueprint("/Game/Blueprints/BP_PickupItem", unreal.Pawn)

unreal.log("蓝图自动化第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 批量创建 10 个 Actor 蓝图，并统计它们的父类
# 2. 编写工具：列出项目中每个蓝图的父类关系
# 3. 编写脚本，把一批蓝图的父类统一改成 Character
# 4. 研究：如何在 Python 中通过编辑器工具调用蓝图组件的增删
#    （提示：UE Python 无 SCS 接口，需要 C++ 编辑器扩展）
