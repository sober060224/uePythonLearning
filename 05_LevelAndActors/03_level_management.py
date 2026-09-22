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

习题可能用到的 API：
  - unreal.EditorLevelLibrary.get_editor_world() -> World —— 获取编辑器世界（练习1备份关卡需要引用当前世界）
  - unreal.EditorLevelLibrary.save_current_level() -> None —— 保存当前关卡（练习1备份前需确保关卡已保存）
  - unreal.EditorLevelLibrary.load_level(level_path: str) -> None —— 加载指定关卡（练习3迁移工具需切换关卡）
  - unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool —— 检查资产是否存在（练习1备份前需验证路径）
  - unreal.EditorAssetLibrary.list_assets(search_path, recursive) -> Array[str] —— 列出资产（练习4差异对比需遍历关卡资产）
  - unreal.EditorLevelLibrary.get_all_level_actors() -> Array[Actor] —— 获取所有 Actor（练习2、3、4都需要操作 Actor 列表）
  - unreal.EditorActorSubsystem.duplicate_actors(self, actors_to_duplicate, to_world, offset) -> Array[Actor] —— 复制 Actor（练习3迁移工具需要复制 Actor）
  - unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools —— 获取资产工具（练习1创建备份需要生成新资产）
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 关卡基本信息
# ─────────────────────────────────────────────────────────

def get_current_level_info():
    """获取当前关卡的信息"""
    # get_editor_world 获取当前编辑器正在编辑的世界（关卡）
    # 在编辑器中同时可以打开多个关卡（通过 World Outliner 切换）
    # 这个方法拿到的是当前被激活的那个
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world:
        unreal.log_error("无法获取编辑器世界")
        return

    # get_name 返回资产名（不含路径），get_path_name 返回完整路径
    # 比如 get_name() -> "MainMap"，get_path_name() -> "/Game/Maps/MainMap.MainMap"
    level_name = world.get_name()
    level_path = world.get_path_name()

    unreal.log(f"\n当前关卡信息:")
    unreal.log(f"  名称: {level_name}")
    unreal.log(f"  路径: {level_path}")

    # get_all_level_actors 只返回当前关卡的 Actor
    # 如果使用了子关卡（Sub-Level），子关卡的 Actor 不会在这里出现
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
    # save_current_level 会把当前关卡的修改写入磁盘
    # 等同于编辑器里按 Ctrl+S
    # 注意：这只保存当前关卡，其他已加载的"脏"关卡不受影响
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log("当前关卡已保存")

def save_all_levels():
    """保存所有已加载的关卡"""
    # save_all_dirty_levels 保存所有被修改过但还没保存的关卡
    # "dirty" 在编程术语里表示"有未保存的修改"
    # 这在批量操作后很有用，确保所有修改都被持久化
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
    # 先检查资产是否存在，避免加载不存在的关卡导致错误
    if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.log_error(f"关卡不存在: {level_path}")
        return False

    # load_level 会关闭当前关卡并加载目标关卡
    # 注意：当前关卡未保存的修改会丢失！
    # 所以在调用之前应该先调用 save_current_level
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
    # 先确保目标目录存在，如果不存在就创建
    unreal.EditorAssetLibrary.make_directory(destination)

    # AssetTools 是 UE 的资产工厂，负责创建各种类型的资产
    # WorldFactory 是专门用来创建关卡资产的工厂
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.WorldFactory()

    # 设置模板
    if template == "Basic":
        # 使用基本模板（自带地板和天空球）
        pass
    elif template == "Empty":
        # 空关卡（什么都没有，纯黑）
        factory.set_editor_property("create_new", True)

    # create_asset 参数：资产名、路径、资产类型、工厂
    # 创建后会自动保存到内容浏览器指定路径
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
    # list_assets 返回指定路径下的所有资产路径
    # recursive=True 会递归搜索子文件夹
    # 注意：这个操作可能很慢（大项目有成千上万个资产）
    all_assets = unreal.EditorAssetLibrary.list_assets(
        search_path, recursive=True
    )

    levels = []
    for asset_path in all_assets:
        # find_asset_data 获取资产的元数据（不加载资产本身）
        # 这比 load_asset 快得多——加载资产需要把整个资产读入内存
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # UE5 中 asset_class_path 是一个 PathName 对象，转为字符串后检查
        # 如果包含 "World" 就说明这是一个关卡资产
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

    # 按类型统计
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

    # 按数量从多到少排序输出
    # key=lambda x: -x[1]["count"] 用负数实现降序排列
    for type_name, info in sorted(stats.items(), key=lambda x: -x[1]["count"]):
        unreal.log(f"\n  [{type_name}] x{info['count']}")
        # 每种类型最多显示 5 个 Actor 名，超过的用省略号
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

    # 子关卡（Sub-Level）是嵌套在主关卡中的其他关卡
    # 常见用途：把大型地图拆分成多个小区域，按需加载
    # UE5 中子关卡管理可以通过 Level Streaming 实现
    unreal.log("\n子关卡列表:")
    unreal.log("  （子关卡需要通过 World Composition 或 Level Streaming 管理）")

def add_sublevel(level_path):
    """添加子关卡到当前关卡"""
    if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.log_error(f"关卡不存在: {level_path}")
        return False

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
    #   两者获取的子系统类型不同，用错方法会返回 None 或报错
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
