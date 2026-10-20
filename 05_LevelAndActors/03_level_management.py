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
  ── unreal ──
    unreal.EditorLevelLibrary.get_editor_world() -> World
        —— 获取编辑器世界（练习1备份关卡需要引用当前世界）
    unreal.EditorLevelLibrary.save_current_level() -> bool
        —— 保存当前关卡（练习1备份前需确保关卡已保存）
    unreal.LevelEditorSubsystem.load_level(level_path: str) -> bool
        —— 加载指定关卡（练习3迁移工具需切换关卡）
        ⚠️ 实测：**路径不存在也返回 True**（把 /Game/Maps/Nope_Xyz 传进去照样 True），
          所以必须先 does_asset_exist 判一遍再调，否则你以为切过去了其实没切
    unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool
        —— 检查资产是否存在（练习1备份前需验证路径）
    unreal.EditorAssetLibrary.list_assets(search_path, recursive) -> Array[str]
        —— 列出资产（练习4差异对比需遍历关卡资产）
    unreal.EditorLevelLibrary.get_all_level_actors() -> Array[Actor]
        —— 获取所有 Actor（练习2、3、4都需要操作 Actor 列表）
    unreal.EditorActorSubsystem.spawn_actor_from_class(actor_class: Class, location: Vector,
                                                       rotation: Rotator = [0,0,0]) -> Actor
        —— 练习2/3/4 还原 Actor 时用它生成；实测位置精度不损（写入 12.3456789
           读回还是 12.3456789），但 Rotator 是 float，读回有小数尾差
    unreal.load_class(outer: Object, name: str) -> Optional[Class]
        —— 练习2/3 按 class_name 还原类。⚠️ 实测只认**完整路径名**：
           load_class(None, "/Script/Engine.DirectionalLight") 拿到类；
           load_class(None, "DirectionalLight") 返回 None。
           所以模板里存 cls.get_path_name()，别只存 cls.get_name()
    actor.get_class() -> Class
        —— 取 Actor 的类；再 get_path_name() 才是能喂给 load_class 的字符串
    unreal.EditorActorSubsystem.duplicate_actors(self, actors_to_duplicate, to_world, offset) -> Array[Actor]
        —— 复制 Actor（练习3迁移工具需要复制 Actor）
    unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools
        —— 获取资产工具（练习1创建备份需要生成新资产）
    unreal.AssetTools.duplicate_asset(asset_name: str, package_path: str, original_object: Object) -> Object
        —— 复制资产（练习1 备份关卡就是复制一份 .umap；桩 330396）
  ── Python 标准库 ──
    time.strftime / os.path
        —— 练习1 备份关卡时给副本加时间戳命名
    json.dump / json.load
        —— 练习2 关卡模板存读（本课的 write_json/read_json 就是它们的包装）
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 工具：编辑器子系统取用
# ─────────────────────────────────────────────────────────
#
# 【为什么要有这两个 helper】get_editor_subsystem 的返回类型是 Optional —— 它可能
# 返回 None。直接写 unreal.get_editor_subsystem(X).method() 会在 None 上取属性，
# 类型检查器判为错误，运行时会抛 AttributeError。


def editor_world():
    """取当前编辑会话所在的 World；不在编辑器环境（或 World 未就绪）时返回 None。"""
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return subsystem.get_editor_world() if subsystem else None


def level_editor():
    """取 LevelEditorSubsystem（关卡保存/加载）；不在编辑器环境时返回 None。"""
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


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

    unreal.log("\n当前关卡信息:")
    unreal.log(f"  名称: {level_name}")
    unreal.log(f"  路径: {level_path}")

    # get_all_level_actors 只返回当前关卡的 Actor
    # 如果使用了子关卡（Sub-Level），子关卡的 Actor 不会在这里出现
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    unreal.log(f"  Actor 数量: {len(actors)}")

    return {"name": level_name, "path": level_path, "actor_count": len(actors)}


# ─────────────────────────────────────────────────────────
# 2. 保存关卡
# ─────────────────────────────────────────────────────────


def save_current_level():
    """保存当前关卡"""
    # save_current_level 会把当前关卡的修改写入磁盘
    # 等同于编辑器里按 Ctrl+S
    # 注意：这只保存当前关卡，其他已加载的"脏"关卡不受影响
    # 【UE5】关卡保存/加载都在 LevelEditorSubsystem 上
    #   （EditorLevelLibrary 属于已废弃的 Editor Scripting Utilities 插件）
    subsystem = level_editor()
    if subsystem is None:
        unreal.log_error("取不到 LevelEditorSubsystem，关卡未保存")
        return False
    # save_current_level 返回 bool，用它判断是否真的写盘成功
    saved = subsystem.save_current_level()
    unreal.log("当前关卡已保存" if saved else "保存失败（save_current_level 返回 False）")
    return saved


def save_all_levels():
    """保存所有已加载的关卡"""
    # save_all_dirty_levels 保存所有被修改过但还没保存的关卡
    # "dirty" 在编程术语里表示"有未保存的修改"
    # 这在批量操作后很有用，确保所有修改都被持久化
    subsystem = level_editor()
    if subsystem is None:
        unreal.log_error("取不到 LevelEditorSubsystem，脏关卡未保存")
        return False
    saved = subsystem.save_all_dirty_levels()
    unreal.log("所有脏关卡已保存" if saved else "没有脏关卡需要保存，或保存失败")
    return saved


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
    subsystem = level_editor()
    if subsystem is None:
        unreal.log_error("取不到 LevelEditorSubsystem，关卡未加载")
        return False
    # load_level 返回 bool（桩里签名 load_level(asset_path: str) -> bool）
    loaded = subsystem.load_level(level_path)
    if loaded:
        unreal.log(f"已加载关卡: {level_path}")
    else:
        unreal.log_error(f"加载失败: {level_path}")
    return loaded


# ─────────────────────────────────────────────────────────
# 4. 创建新关卡
# ─────────────────────────────────────────────────────────


def create_new_level(name, destination="/Game/Maps", template="Basic"):
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
    # 【易错点】"Basic"（自带地板和天空球）只是编辑器"新建关卡"对话框里的选项，
    #   Python 的 WorldFactory 没有对应开关 —— 原来那个 pass 分支什么也没做，
    #   却让人以为已经应用了模板。这里把行为写清楚。
    if template == "Empty":
        # 空关卡：create_new=True 表示不复制任何已有世界
        factory.set_editor_property("create_new", True)
    elif template != "Basic":
        unreal.log_warning(f"未知模板 {template!r}，按 Basic（默认世界）处理")

    # create_asset 参数：资产名、路径、资产类型、工厂
    # 资产类型要写成 .static_class()：Class 参数要的是「类对象」
    # 创建后会自动保存到内容浏览器指定路径
    new_world = asset_tools.create_asset(
        name, destination, unreal.World.static_class(), factory
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
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    levels = []
    for asset_path in all_assets:
        # find_asset_data 获取资产的元数据（不加载资产本身）
        # 这比 load_asset 快得多——加载资产需要把整个资产读入内存
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # UE5 中 asset_class_path 是一个 PathName 对象，转为字符串后检查
        # 如果包含 "World" 就说明这是一个关卡资产
        class_str = str(asset_data.asset_class_path)
        if "World" in class_str:
            levels.append(
                {
                    "path": asset_path,
                    "name": asset_data.asset_name,
                }
            )

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
            stats[type_name] = {"count": 0, "labels": []}
        stats[type_name]["count"] += 1
        stats[type_name]["labels"].append(actor.get_actor_label())

    unreal.log(f"\n{'=' * 50}")
    unreal.log("  关卡 Actor 分析")
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
    world = editor_world()
    if not world:
        return []

    # 子关卡（Sub-Level）是嵌套在主关卡中的其他关卡
    # 常见用途：把大型地图拆分成多个小区域，按需加载
    # 【UE5】EditorLevelUtils.get_levels(world) 直接列出世界里的所有关卡对象。
    #   注意：UWorld 本身也是 ULevel 的子类，所以列表里第一个就是持久化关卡，
    #   要减掉它才是真正的"子关卡"。
    levels = unreal.EditorLevelUtils.get_levels(world)
    sublevels = [level for level in levels if level != world]

    unreal.log("\n子关卡列表:")
    if not sublevels:
        unreal.log("  （当前世界没有子关卡）")
    for level in sublevels:
        unreal.log(f"  - {level.get_name()}")

    # 【重要】函数必须有返回值：原来这里没有 return，调用方拿到的是 None，
    #   一旦有人写 for lv in list_sublevels() 就会 TypeError。
    return sublevels


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
    world = editor_world()
    if world is None:
        unreal.log_error("取不到编辑器 World，子关卡未添加")
        return False
    unreal.EditorLevelUtils.add_level_to_world(
        world,
        level_path,
        # level_streaming_class 参数要「类对象」，所以用 .static_class()
        unreal.LevelStreamingAlwaysLoaded.static_class(),
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
    world = editor_world()
    if not world:
        return

    # 【UE5】WorldSettings 通过 World.get_world_settings() 获取（UWorld 上的方法）。
    # 【修改前】这里用 get_engine_subsystem 拿 LevelEditorSubsystem 就完事了 ——
    #   既没有真正读到 WorldSettings，world_settings 变量也从未被使用。
    world_settings = world.get_world_settings()
    if not world_settings:
        unreal.log_error("无法获取 WorldSettings")
        return

    current_mode = world_settings.get_editor_property("default_game_mode")
    unreal.log(
        f"当前默认 GameMode: {current_mode if current_mode else '（未设置，用项目默认）'}"
    )

    if game_mode_class:
        world_settings.set_editor_property("default_game_mode", game_mode_class)
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
# 【练习 1】备份当前关卡，文件名带时间戳
#   输入： 当前打开关卡的名字（用 get_current_level_info() 取）
#   任务： 目标路径 = "/Game/Maps/_Backup/{关卡名}_{时间戳}"，
#          时间戳用 time.strftime("%Y%m%d_%H%M%S")；
#          用 asset_tools.duplicate_asset(新名, 目标目录, 关卡资产对象) 复制，
#          复制成功后打印完整路径
#   输出： /Game/Maps/_Backup/ 下多出一个带时间戳的关卡资产
#   验收： 连跑两次（间隔 1 秒以上）→ 出现两个不同时间戳的文件，原始关卡没被改动；
#          把时间戳固定成同一个字符串再跑 → duplicate_asset 返回 None，
#          函数要打警告说明「目标已存在」而不是崩。
#          编辑器实测：duplicate_asset 返回的是 World 对象、类型正确，
#          同名第二次确实返回 None；时间戳精度到秒即可区分，两次间隔 1.1 秒
#          能拿到两个不同名字。做完记得 delete_asset 删掉测试备份，
#          并 delete_directory("/Game/Maps/_Backup") 清掉空目录

# 【练习 2】关卡模板系统：把当前 Actor 布局存成 JSON，再还原
#   输入： 模板名 name；当前关卡里所有非编辑器-only 的 Actor
#   任务： 保存时对每个 Actor 记录 {class_name, label, location, rotation, scale}，
#          class_name 存 actor.get_class().get_path_name()（如
#          "/Script/Engine.DirectionalLight"）而不是 get_name()；
#          用 write_json 写到 Saved/Templates/{name}.json；
#          加载时用 unreal.load_class(None, class_name) 找类
#          （实测只认完整路径名，短名返回 None），找不到就跳过并计数，
#          生成后把变换设回去，整个加载过程包在一个事务里
#   输出： 一个 JSON 模板文件 + 一键还原出同样布局的关卡
#   验收： 存一个模板 → 删掉 3 个 Actor → 加载模板 → 3 个 Actor 回来了，
#          位置精确到小数点后至少 1 位（实测位置是 double，12.3456789 能原样读回；
#          旋转是 float，写入 33.333333 读回 33.333332，比精度时容差留到 1e-4）；
#          Ctrl+Z 一次全部撤销。
#          实测本关卡全部 Actor 的 is_editor_only_actor **都是 False**，
#          Actor 对象上也没有 is_editor_only() 方法（那是 ActorComponent 的）；
#          所以过滤要写 get_editor_property("is_editor_only_actor") 再判值，
#          别按类名猜、也别调 actor.is_editor_only()（会 AttributeError）

# 【练习 3】把一个关卡里的 Actor 搬到另一个关卡
#   输入： 源关卡路径、目标关卡路径
#   任务： load_level(源) 后遍历 Actor 收集数据（同练习 2 的记录格式），
#          再 load_level(目标) 逐一生成并还原变换；
#          切换关卡前提示「原关卡未保存的改动会丢失」并询问是否继续
#          （实测 LevelEditorSubsystem 只有 save_all_dirty_levels，
#            **没有任何"查询关卡脏不脏"的接口**，Package 上也没有 is_dirty，
#            所以只能：要么每次都问用户，要么无条件先调 save_all_dirty_levels）
#   输出： 目标关卡里出现源关卡的全部 Actor
#   验收： 源关卡放 4 个 Actor → 迁移后目标关卡里多出 4 个，变换一致；
#          目标关卡里已有同名 Actor → 不能因为重名就抛异常。
#          实测**标签允许重复**：两个 Actor 都叫 LVLTEST_SAME 可以同时存在、
#          都能被取到（2 个），所以按标签匹配时要处理一对多

# 【练习 4】对比两个关卡的 Actor 差异
#   输入： 两个关卡路径
#   任务： 分别加载并收集 Actor 快照（class_name + label 作为键），
#          用集合差算出「只在 A」「只在 B」，用集合交算出「两边都有」；
#          对「两边都有」的再比 location（差值 > 0.01 才算变了）；
#          对比期间不要保存任何关卡（避免污染数据）
#   输出： 「只在 A: 3 个 / 只在 B: 5 个 / 位置变了: 2 个」并列出具体标签
#   验收： 把同一个关卡当两边传进去 → 三项全是 0；
#          在 B 里挪动一个 Actor 1 cm → 「位置变了」报出 1 个，且标签正确。
#          ⚠️ 因为「标签可重复」（练习3 实测），键要用 get_name()
#          （同一关卡内 Actor 名唯一，实测两个同名标签的 Actor 的 get_name() 不同）
#          或 (label, class_name, 序号)，只用 label 当键会把重名的合并掉
