import unreal


def UnrealLog(text):
    unreal.log("*" * 50)
    unreal.log(f"{text}")
    unreal.log("*" * 50)


unreal.log_warning("警告信息")
unreal.log_error("错误信息")

UnrealLog(unreal.Paths.get_base_filename(unreal.Paths.get_project_file_path()))

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个函数，用不同颜色在屏幕上显示当前关卡名称
# 2. 编写一个 inspect_all_assets() 函数，列出指定目录
#    下所有资产的类型和名称
# 3. 创建一个日志系统，同时输出到屏幕和日志文件
# ─────────────────────────────────────────────────────────


def get_editor_world():
    """小工具：拿到"编辑器当前打开的那个世界"。

    深入浅出：
    - UE 里几乎所有和场景有关的操作都需要一个 World（世界）作为上下文，
      引擎要知道"你在哪个世界里干活"。
    - 在编辑器脚本里，这个世界就是 get_editor_world()。
    - 子系统必须用 get_editor_subsystem() 获取单例，
      直接 unreal.UnrealEditorSubsystem() 构造是 UE5.2 起废弃的写法。
    """
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


# ═════════════════════════════════════════════════════════
# 修改 1：log_level —— 核心 bug：颜色参数收了却没用
# ═════════════════════════════════════════════════════════
# 【修改前】
# def log_level(color):
#     editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
#     world = editor_subsystem.get_editor_world()
#     print(world.get_name())
#
# 【问题分析】
# 1. 参数 color 从头到尾没有被使用 → 练习题要求的"不同颜色显示"根本没实现，
#    调三次 log_level 传三种颜色，输出却一模一样。
# 2. print() 是 Python 自己的输出，只会出现在 Output Log 的 Python 命令行里，
#    不会显示在视口（屏幕）上。想在屏幕上显示文字，要用
#    unreal.SystemLibrary.print_string —— 它就是蓝图 Print String 节点的 Python 版。
# 3. print_string 的第一个参数是 world context（世界上下文），
#    引擎靠它决定把字画到哪个世界的屏幕上。
# 4. 颜色在 UE 里是 LinearColor 结构体（r/g/b/a 各 0~1 的浮点数），
#    Python 的列表 [1, 1, 1, 1] 需要转换一下，显式构造最稳妥。
def log_level(color):
    world = get_editor_world()
    level_name = world.get_name()

    # 把 [r, g, b, a] 列表解包成 LinearColor(r=..., g=..., b=..., a=...)
    text_color = unreal.LinearColor(*color)

    # 完整签名：print_string(world_context_object, in_string,
    #                        print_to_screen, print_to_log, text_color, duration)
    unreal.SystemLibrary.print_string(
        world,  # 画到编辑器世界的屏幕上
        level_name,  # 要显示的文字：当前关卡名
        print_to_screen=True,  # 显示在视口左上角
        print_to_log=True,  # 同时写进 Output Log（日志系统雏形）
        text_color=text_color,  # 这次颜色真的被用上了
        duration=10.0,  # 停留秒数
    )


# ═════════════════════════════════════════════════════════
# 修改 2：inspect_all_assets —— 原代码基本正确，补两处健壮性
# ═════════════════════════════════════════════════════════
# 【修改前】
# def inspect_all_assets(path):
#     assets = unreal.EditorAssetLibrary.list_assets(path, False)
#
#     for asset_path in assets:
#         unreal.log(f"asset_path:{asset_path}")
#         asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
#         unreal.log(f"资产类型：{asset_data.asset_class_path.asset_name}")
#         unreal.log(f"名称：{asset_data.asset_name}")
#
# 【问题分析】
# 1. list_assets(path, False) 的第二个参数是 recursive（是否递归子目录），
#    位置传参能跑，但写成关键字 recursive=False 可读性更好。
# 2. find_asset_data 找不到时会返回一个"无效"的 AssetData，
#    直接访问它的字段不报错但全是空值，容易输出垃圾数据 —— 先 is_valid() 检查一下。
# 3. 顺手把三个字段合成一行输出，日志更清爽（可选项，不算 bug）。
def inspect_all_assets(path):
    # recursive=True 表示连子目录一起扫描，按需改
    assets = unreal.EditorAssetLibrary.list_assets(path, recursive=True)
    unreal.log(f"目录 {path} 下共找到 {len(assets)} 个资产")

    for asset_path in assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if not asset_data.is_valid():
            unreal.log_warning(f"跳过无效资产：{asset_path}")
            continue

        # asset_class_path.asset_name 就是资产类型，如 "LevelSequence"、"Blueprint"
        unreal.log(
            f"[{asset_data.asset_class_path.asset_name}] "
            f"{asset_data.asset_name}  ({asset_path})"
        )


# ═════════════════════════════════════════════════════════
# 修改 3：log_screen —— world context 传了 None
# ═════════════════════════════════════════════════════════
# 【修改前】
# def log_screen(text):
#     unreal.SystemLibrary.print_string(None, text)
#
# 【问题分析】
# 第一个参数 world_context_object 传 None 时，引擎找不到该往哪个世界的屏幕上画，
# 在编辑器里运行很可能什么都不显示（不报错，静默失败，最难查的那种）。
# 传编辑器的 world 即可 —— 正好复用上面的 get_editor_world()。
def log_screen(text):
    unreal.SystemLibrary.print_string(get_editor_world(), text)


# ─────────────────────────────────────────────────────────
# 测试调用（未改动）
# 三种颜色：白、青、淡蓝 —— 现在屏幕上真的能看到三种颜色了
# ─────────────────────────────────────────────────────────
log_level([1, 1, 1, 1])
log_level([0.5, 1, 1, 1])
log_level([0.5, 0.5, 1, 1])

inspect_all_assets("/Game/EditorWidgetUtilities")
log_screen("abcdomg")
