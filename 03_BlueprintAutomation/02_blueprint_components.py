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

习题可能用到的 API：
  unreal.BlueprintEditorLibrary.reparent_blueprint(blueprint, new_parent_class) -> None
      —— 重新指定蓝图父类，练习3批量改父类的核心 API
  unreal.BlueprintEditorLibrary.get_blueprint_parent_class(blueprint) -> Class
      —— 读取蓝图父类，练习1统计父类、练习2列出父类关系都需要
  unreal.EditorAssetLibrary.list_assets(directory_path, recursive=True, include_folder=False) -> Array[str]
      —— 递归列出资产，练习1/2遍历蓝图的入口
  unreal.EditorAssetLibrary.find_asset_data(asset_path) -> AssetData
      —— 查询资产元数据，快速判断是否为蓝图
  unreal.BlueprintEditorLibrary.compile_blueprint(blueprint) -> bool
      —— 编译蓝图，修改父类后必须重新编译，练习3需要
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools
      —— 获取资产工具单例，创建蓝图时使用
  unreal.BlueprintFactory() 配合 set_editor_property("parent_class", cls)
      —— 蓝图工厂，练习1批量创建蓝图时使用
  unreal.ScopedSlowTask(work, desc="", enabled=True)
      —— 进度条工具，批量操作时给用户显示进度
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
    # make_directory 类似 mkdir -p，会自动创建不存在的目录层级
    # 如果目录已存在则什么也不做，不会报错
    unreal.EditorAssetLibrary.make_directory(destination)

    # 获取资产工具单例，UE 编辑器通过它来执行所有资产操作
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # BlueprintFactory 是蓝图专用的工厂类，
    # 工厂模式是 UE 创建资产的标准流程：创建工厂 -> 配置参数 -> create_asset
    factory = unreal.BlueprintFactory()
    # 蓝图工厂通过 parent_class 属性指定新蓝图的父类
    # 属性名必须与 UE 反射系统注册的名称完全一致（大小写敏感）
    factory.set_editor_property("parent_class", parent_class)

    # create_asset 创建新蓝图，返回蓝图 UObject 或 None（失败时）
    new_bp = asset_tools.create_asset(
        name,
        destination,
        unreal.Blueprint,
        factory
    )

    if not new_bp:
        unreal.log_error(f"创建蓝图失败: {name}")
        return None

    # 创建后编译一次，保证 GeneratedClass（蓝图编译后生成的类）可用
    # 未编译的蓝图就像未编译的 C++ 源码——不能运行
    unreal.BlueprintEditorLibrary.compile_blueprint(new_bp)

    # 保存到磁盘（.uasset 文件），否则只存在于内存中
    full_path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(full_path)
    unreal.log(f"已创建蓝图: {full_path} 父类={parent_class.get_name()}")
    return new_bp

# ─────────────────────────────────────────────────────────
# 2. 查询蓝图信息
# ─────────────────────────────────────────────────────────

def inspect_blueprint(blueprint_path):
    """读取蓝图的名称、类型和父类"""
    # load_asset 加载蓝图到内存，返回 Blueprint UObject
    # 注意：load_asset 可能返回 None（路径错误、资产损坏等），必须检查
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    # isinstance 检查确保加载的确实是蓝图，而不是其他类型的资产
    if not bp or not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    unreal.log(f"\n蓝图: {bp.get_name()}")
    # get_class() 返回 UClass（UE 反射系统的类元信息），不是 Python 的 type()
    unreal.log(f"  类: {bp.get_class().get_name()}")

    # get_blueprint_parent_class 是 BlueprintEditorLibrary 提供的方法，
    # 专门用于查询蓝图继承的父类（如 Actor、Pawn、Character 等）
    # 注意：它返回的是 UClass 对象，不是蓝图资产
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

    # 先记录旧父类，方便打印日志
    old_parent = unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)
    old_name = old_parent.get_name() if old_parent else "None"

    # reparent_blueprint 会重建蓝图的父类继承关系：
    # 1. 移除旧父类的默认组件和函数
    # 2. 继承新父类的组件和函数
    # 3. 蓝图中与新父类不兼容的节点可能产生编译错误
    unreal.BlueprintEditorLibrary.reparent_blueprint(bp, new_parent_class)
    # 修改父类后必须重新编译，否则蓝图处于不一致状态
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    # 保存到磁盘，确保修改持久化
    unreal.EditorAssetLibrary.save_asset(blueprint_path)

    unreal.log(
        f"已修改父类: {bp.get_name()}  {old_name} -> {new_parent_class.get_name()}"
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

    # ScopedSlowTask 创建进度条对话框
    # 参数1: 总工作量（每步占1帧），参数2: 标题文字
    task = unreal.ScopedSlowTask(len(blueprint_defs), "批量创建蓝图...")
    task.make_dialog(True)  # 弹出进度对话框

    for name, parent_class in blueprint_defs:
        # should_cancel() 检查用户是否点了"取消"，长时间操作必须支持取消
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

    # 编译将蓝图的可视化脚本转换为可执行字节码
    # 编译成功返回 True，有错误返回 False
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
