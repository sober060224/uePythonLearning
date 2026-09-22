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

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path, recursive=True, include_folder=False) -> Array[str]
      —— 递归列出路径下全部资产，练习1/2/4都需要用它遍历蓝图
  unreal.EditorAssetLibrary.find_asset_data(asset_path) -> AssetData
      —— 按路径查资产元数据，不加载资产，练习4检查编译状态时需要
  unreal.EditorAssetLibrary.load_asset(asset_path) -> Object
      —— 加载蓝图到内存以便读取父类信息，练习3需要
  unreal.BlueprintEditorLibrary.compile_blueprint(blueprint) -> bool
      —— 编译蓝图，练习4检查编译错误后可尝试重新编译
  unreal.BlueprintEditorLibrary.get_blueprint_parent_class(blueprint) -> Class
      —— 读取蓝图父类，练习1创建蓝图后验证父类、练习3绘制关系图都需要
  asset_tools.create_asset(asset_name, package_path, asset_class, factory, ...) -> Object
      —— 用工厂创建新蓝图资产，练习1/2的核心操作
  unreal.BlueprintFactory() 配合 set_editor_property("parent_class", cls)
      —— 蓝图工厂，指定新蓝图的父类，练习1/2创建蓝图时必须
  unreal.ScopedSlowTask(work, desc="", enabled=True)
      —— 批量操作时显示进度条并允许用户取消，练习2/4需要
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 查找和加载现有蓝图
# ─────────────────────────────────────────────────────────

def find_all_blueprints(search_path="/Game"):
    """查找项目中所有蓝图"""
    # list_assets 会递归遍历 search_path 下的所有资产，
    # 返回的是字符串路径列表（如 ["/Game/Blueprints/BP_Player", ...]），
    # 而不是对象列表 —— 这是初学者常犯的错误，以为返回的是对象。
    # include_folder=False 表示只返回资产，不包含文件夹。
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    blueprints = []

    for asset_path in all_assets:
        # find_asset_data 不会真正加载资产到内存，只是查询元数据（类名、大小等）。
        # 如果用 load_asset 加载全部资产会非常慢，而且可能导致内存溢出。
        # 这里用 find_asset_data 做轻量级筛选，是 UE Python 的最佳实践。
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # asset_class_path 是 UE5 新增的属性（UE4 的 asset_class 已弃用），
        # 它是一个 TopLevelAssetPath 对象，转成字符串后包含类名。
        class_str = str(asset_data.asset_class_path)
        if "Blueprint" in class_str:
            blueprints.append(asset_data)

    return blueprints

# 查找所有蓝图
# 注意：这会在 /Game 下递归搜索，项目大时可能需要较长时间
bps = find_all_blueprints()
unreal.log(f"项目中共有 {len(bps)} 个蓝图:")
for bp in bps[:20]:
    # package_name 是完整路径，asset_name 是纯文件名
    unreal.log(f"  {bp.package_name} - {bp.asset_name}")

# ─────────────────────────────────────────────────────────
# 2. 加载和检查蓝图
# ─────────────────────────────────────────────────────────

def inspect_blueprint(blueprint_path):
    """详细检查一个蓝图的信息"""
    # load_asset 会把资产真正加载到内存，返回的是一个 UObject 对象。
    # 如果路径不存在或资产损坏，返回 None —— 所以一定要做空值检查！
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)

    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    unreal.log(f"\n{'=' * 50}")
    # get_name() 返回对象名称（不含路径），是 UObject 基类提供的方法
    unreal.log(f"蓝图: {bp.get_name()}")
    unreal.log(f"路径: {blueprint_path}")
    # type().__name__ 是 Python 内置写法，获取类名字符串
    unreal.log(f"类型: {type(bp).__name__}")

    # 检查是否是 Blueprint 类型
    # hasattr 是 Python 内置函数，检查对象是否有某属性
    # 在 UE Python 中，不同类型的对象有不同的属性集，用 hasattr 做安全检查
    if hasattr(bp, 'get_class'):
        # get_class() 返回对象的 Unreal 类（UClass），不是 Python 类
        # UClass 是 UE 反射系统的核心，描述一个类的元信息
        unreal.log(f"类名: {bp.get_class().get_name()}")

    # 获取父类信息
    # parent_class 是蓝图资产对象的属性，表示该蓝图继承自哪个 C++ 类
    # 例如一个继承自 Actor 的蓝图，parent_class 就是 unreal.Actor
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
    # 先确保目标目录存在，否则创建资产时会失败
    # make_directory 类似 mkdir -p，会递归创建所有层级目录
    unreal.EditorAssetLibrary.make_directory(destination_path)

    # AssetTools 是 UE 编辑器提供的资产操作工具单例，
    # 通过 get_asset_tools() 获取，它封装了创建、重命名、删除等资产操作
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # BlueprintFactory 是蓝图的工厂类，
    # UE 中创建资产通常需要通过"工厂模式"——先创建工厂，配置参数，再调用 create_asset
    factory = unreal.BlueprintFactory()
    # 【修改前】factory.set_editor_property("ParentClass", parent_class)
    # 【问题分析】蓝图工厂的编辑器属性名是 parent_class（小写），
    #   见 stub 中 class BlueprintFactory 的属性列表。
    # set_editor_property 是 UObject 的通用方法，用于设置编辑器可编辑的属性
    # 属性名必须与 UE 反射系统中注册的名称完全一致（大小写敏感！）
    factory.set_editor_property("parent_class", parent_class)

    # create_asset 参数说明：
    #   asset_name: 资产文件名（不含扩展名，蓝图会自动加 .uasset）
    #   package_path: 保存目录路径
    #   asset_class: 资产类（unreal.Blueprint 是蓝图资产的类）
    #   factory: 工厂对象，负责创建资产的具体逻辑
    new_bp = asset_tools.create_asset(
        name,
        destination_path,
        unreal.Blueprint,
        factory
    )

    if new_bp:
        full_path = f"{destination_path}/{name}"
        unreal.log(f"成功创建蓝图: {full_path}")

        # 创建后必须保存，否则资产只存在于内存中，关闭编辑器后会丢失
        # save_asset 会把资产写入磁盘（.uasset 文件）
        unreal.EditorAssetLibrary.save_asset(full_path)
        return new_bp
    else:
        unreal.log_error(f"创建蓝图失败: {name}")
        return None

# ─────────────────────────────────────────────────────────
# 4. 创建 Actor 蓝图的实用封装
# ─────────────────────────────────────────────────────────

# 以下是常用的蓝图创建快捷函数，封装了常见的父类选择。
# 父类决定了蓝图"是什么"——Actor 是可放置的基础物体，
# Character 自带移动组件，Pawn 可被控制器 Possess，
# PlayerController 处理玩家输入，GameModeBase 定义游戏规则。

def create_actor_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 Actor 的蓝图 —— Actor 是最基本的可放置对象"""
    return create_blueprint(name, unreal.Actor, destination)

def create_pawn_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 Pawn 的蓝图 —— Pawn 可以被 Controller Possess（控制）"""
    return create_blueprint(name, unreal.Pawn, destination)

def create_player_controller_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 PlayerController 的蓝图 —— 处理玩家输入和相机"""
    return create_blueprint(name, unreal.PlayerController, destination)

def create_game_mode_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 GameMode 的蓝图 —— 定义游戏规则、玩家生成等"""
    return create_blueprint(name, unreal.GameModeBase, destination)

def create_actor_component_blueprint(name, destination="/Game/Blueprints"):
    """创建基于 ActorComponent 的蓝图 —— 可复用的组件逻辑"""
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

    # ScopedSlowTask 是 UE 提供的进度条工具，
    # 当操作可能耗时较长时（如批量创建），给用户显示进度并允许取消。
    # 参数是总工作量（帧数）和描述文字
    task = unreal.ScopedSlowTask(len(blueprint_defs), "批量创建蓝图...")
    # make_dialog(True) 弹出一个进度对话框
    # 如果不调用 make_dialog，进度条不会显示，但代码逻辑仍然有效
    task.make_dialog(True)

    for name, parent_class in blueprint_defs:
        # should_cancel() 检查用户是否点击了"取消"按钮
        # 这是良好的 UX 实践——长时间操作应该允许用户中断
        if task.should_cancel():
            break

        # enter_progress_frame 推进一帧进度，第二个参数是当前步骤的描述
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

    # 编译蓝图会将其可视化节点转换为可执行的字节码，
    # 并生成 BlueprintGeneratedClass（蓝图编译后的类）。
    # 没有编译的蓝图就像没有编译的 C++ 代码——不能运行。
    # compile_blueprint 返回 True 表示编译成功，False 表示有错误
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
    # 这些是 UE 游戏框架的核心类，每个游戏都需要它们：
    # GameModeBase - 定义游戏规则（谁能重生、用什么 Pawn 等）
    # GameStateBase - 存储游戏状态（分数、时间等所有玩家共享的数据）
    # PlayerController - 处理玩家输入，连接 Player 和 Pawn
    # PlayerState - 存储玩家个人数据（名字、分数等）
    # Pawn - 玩家在世界中的物理化身
    # HUD - 负责在屏幕上绘制 UI 元素
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
