"""
=============================================================
关卡与Actor 第3课：关卡管理
=============================================================

学习目标：
  - 加载、保存和管理关卡
  - 子关卡操作
  - 关卡属性配置

核心 API：
  - unreal.EditorLevelLibrary - 关卡操作
  - unreal.LevelSequence - 序列相关

本课可能用到的 API：
  unreal.EditorLevelLibrary.get_editor_world() -> World  —— 获取编辑器世界
  unreal.EditorLevelLibrary.get_all_level_actors() -> Array[Actor]  —— 获取当前关卡全部 Actor
  unreal.EditorLevelLibrary.save_current_level() -> None  —— 保存当前关卡
  unreal.EditorLevelLibrary.save_all_dirty_levels() -> None  —— 保存所有被修改过的关卡
  unreal.EditorLevelLibrary.load_level(level_path: str) -> None  —— 加载指定关卡
  unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool  —— 检查资产是否存在
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建目录
  unreal.EditorLevelUtils.add_level_to_world(world: World, level_package_name: str, level_streaming_class: Class) -> LevelStreaming  —— 将子关卡添加到世界
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例
  unreal.WorldFactory() -> WorldFactory  —— 世界工厂（用于创建关卡资产）
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 关卡基本信息
# ─────────────────────────────────────────────────────────

def get_current_level_info():
    """获取当前关卡的信息"""
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world:
        unreal.log_error("无法获取编辑器世界")
        return

    level_name = world.get_name()
    level_path = world.get_path_name()

    unreal.log(f"\n当前关卡信息:")
    unreal.log(f"  名称: {level_name}")
    unreal.log(f"  路径: {level_path}")

    # Actor 数量
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    unreal.log(f"  Actor 数量: {len(actors)}")

    return {
        "name": level_name,
        "path": level_path,
        "actor_count": len(actors)
    }

# ─────────────────────────────────────────────────────────
# 2. 保存关卡
# ─────────────────────────────────────────────────────────

def save_current_level():
    """保存当前关卡"""
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log("当前关卡已保存")

def save_all_levels():
    """保存所有已加载的关卡"""
    unreal.EditorLevelLibrary.save_all_dirty_levels()
    unreal.log("所有脏关卡已保存")

# ─────────────────────────────────────────────────────────
# 3. 加载关卡
# ─────────────────────────────────────────────────────────

def load_level(level_path):
    """
    加载指定的关卡

    参数:
        level_path: 关卡路径 (如 "/Game/Maps/MyLevel")
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.log_error(f"关卡不存在: {level_path}")
        return False

    unreal.EditorLevelLibrary.load_level(level_path)
    unreal.log(f"已加载关卡: {level_path}")
    return True

# ─────────────────────────────────────────────────────────
# 4. 创建新关卡
# ─────────────────────────────────────────────────────────

def create_new_level(name, destination="/Game/Maps",
                      template="Basic"):
    """
    创建新关卡

    参数:
        name: 关卡名称
        destination: 保存路径
        template: 模板 ("Basic", "Empty" 等)
    """
    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.WorldFactory()

    # 设置模板
    if template == "Basic":
        # 使用基本模板
        pass
    elif template == "Empty":
        factory.set_editor_property("create_new", True)

    new_world = asset_tools.create_asset(
        name,
        destination,
        unreal.World,
        factory
    )

    if new_world:
        path = f"{destination}/{name}"
        unreal.log(f"已创建关卡: {path}")
        return new_world

    return None

# ─────────────────────────────────────────────────────────
# 5. 列出项目中的所有关卡
# ─────────────────────────────────────────────────────────

def list_all_levels(search_path="/Game"):
    """查找项目中的所有关卡"""
    all_assets = unreal.EditorAssetLibrary.list_assets(
        search_path, recursive=True
    )

    levels = []
    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        class_str = str(asset_data.asset_class_path)
        if "World" in class_str:
            levels.append({
                "path": asset_path,
                "name": asset_data.asset_name,
            })

    unreal.log(f"\n项目中共有 {len(levels)} 个关卡:")
    for level in levels:
        unreal.log(f"  {level['path']}")

    return levels

# ─────────────────────────────────────────────────────────
# 6. 关卡中的 Actor 统计
# ─────────────────────────────────────────────────────────

def analyze_level_actors():
    """分析当前关卡中 Actor 的组成"""
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    stats = {}
    for actor in actors:
        type_name = type(actor).__name__
        if type_name not in stats:
            stats[type_name] = {
                "count": 0,
                "labels": []
            }
        stats[type_name]["count"] += 1
        stats[type_name]["labels"].append(actor.get_actor_label())

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"  关卡 Actor 分析")
    unreal.log(f"{'=' * 50}")
    unreal.log(f"  总 Actor 数: {len(actors)}")

    for type_name, info in sorted(stats.items(), key=lambda x: -x[1]["count"]):
        unreal.log(f"\n  [{type_name}] x{info['count']}")
        for label in info["labels"][:5]:
            unreal.log(f"    - {label}")
        if len(info["labels"]) > 5:
            unreal.log(f"    ... 还有 {len(info['labels']) - 5} 个")

    return stats

# ─────────────────────────────────────────────────────────
# 7. 子关卡管理 (Sub-Levels)
# ─────────────────────────────────────────────────────────

def list_sublevels():
    """列出当前关卡的所有子关卡"""
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world:
        return []

    # 获取关卡流数据
    # 注意：具体 API 取决于引擎版本
    unreal.log("\n子关卡列表:")
    unreal.log("  （子关卡需要通过 World Composition 或 Level Streaming 管理）")

def add_sublevel(level_path):
    """添加子关卡到当前关卡"""
    # 检查关卡是否存在
    if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.log_error(f"关卡不存在: {level_path}")
        return False

    # 添加为流关卡
    # 【修改前】
    # unreal.EditorLevelLibrary.add_level_to_world(
    #     unreal.EditorLevelLibrary.get_editor_world(),
    #     level_path
    # )
    #
    # 【问题分析】
    # 1. add_level_to_world 不在 EditorLevelLibrary 上 —— stub 里它的真身在
    #    EditorLevelUtils（又一个功能被拆走的老 Editor Scripting Utilities 成员）。
    # 2. 就算类名对了，原代码还少传一个参数。真实签名：
    #    EditorLevelUtils.add_level_to_world(world, level_package_name, level_streaming_class)
    #    第三个参数是"用哪种流送方式加载这个子关卡"：
    #      LevelStreamingAlwaysLoaded —— 进游戏就常驻（编辑器里加子关卡的默认值）
    #      LevelStreamingKismet     —— 由蓝图/代码控制加载
    unreal.EditorLevelUtils.add_level_to_world(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
        level_path,
        unreal.LevelStreamingAlwaysLoaded,
    )
    unreal.log(f"已添加子关卡: {level_path}")
    return True

# ─────────────────────────────────────────────────────────
# 8. 关卡设置
# ─────────────────────────────────────────────────────────

def set_world_settings(game_mode_class=None):
    """
    设置世界设置

    参数:
        game_mode_class: 默认 GameMode 类
    """
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world:
        return

    # 【修改前】unreal.get_engine_subsystem(unreal.LevelEditorSubsystem)
    # 【问题分析】LevelEditorSubsystem 是编辑器子系统（EditorSubsystem），
    #   必须用 get_editor_subsystem 获取，get_engine_subsystem 只用于引擎子系统。
    world_settings = unreal.get_editor_subsystem(
        unreal.LevelEditorSubsystem
    )

    if game_mode_class:
        unreal.log(f"设置 GameMode: {game_mode_class}")

    unreal.log("世界设置已更新")

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 获取当前关卡信息
get_current_level_info()

# 分析 Actor
# analyze_level_actors()

# 列出所有关卡
# list_all_levels("/Game")

# 保存关卡
# save_current_level()

unreal.log("关卡与Actor第3课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个工具，自动备份当前关卡（复制一份并加时间戳）
# 2. 创建一个关卡模板系统：保存/加载预设的 Actor 布局
# 3. 编写关卡迁移工具：将一个关卡中的 Actor 复制到另一个关卡
# 4. 实现关卡差异对比：比较两个关卡中 Actor 的不同
