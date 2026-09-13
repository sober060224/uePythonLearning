"""
=============================================================
第2课：日志系统 - 掌握 UE Python 的调试技巧
=============================================================

学习目标：
  - 掌握 unreal 的日志输出方法
  - 了解不同日志级别的使用
  - 学会使用屏幕消息进行调试

运行方式：
  - 在 UE Python Console 中逐段执行
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 基本日志输出
# ─────────────────────────────────────────────────────────
# unreal.log() 输出到 UE 的 Output Log 窗口
# 这是最常用的调试方式
unreal.log("这是一条普通日志消息")

# ─────────────────────────────────────────────────────────
# 2. 不同级别的日志
# ─────────────────────────────────────────────────────────
# UE 提供了不同级别的日志函数

# 警告级别 - 黄色显示，表示需要注意但不影响运行
unreal.log_warning("这是一条警告消息 - 用于提醒潜在问题")

# 错误级别 - 红色显示，表示出现了问题
unreal.log_error("这是一条错误消息 - 用于报告错误")

# ─────────────────────────────────────────────────────────
# 3. 屏幕消息（Screen Message）
# ─────────────────────────────────────────────────────────
# 屏幕消息直接显示在编辑器视口上，非常适合调试
# 参数: 消息文本, 是否显示, 持续时间(秒), 颜色

# 显示一条白色消息，持续3秒
unreal.SystemLibrary.print_string(
    world=None,                          # 世界上下文（None 表示编辑器）
    string="Hello from Python!",         # 消息内容
    print_to_screen=True,                # 是否显示在屏幕上
    print_to_log=True,                   # 是否同时输出到日志
    text_color=[1.0, 1.0, 1.0, 1.0],    # RGBA 颜色 (白色)
    duration=3.0                         # 持续时间
)

# 不同颜色的屏幕消息
unreal.SystemLibrary.print_string(
    None, "红色警告消息", True, True,
    [1.0, 0.0, 0.0, 1.0], 5.0   # 红色
)

unreal.SystemLibrary.print_string(
    None, "绿色成功消息", True, True,
    [0.0, 1.0, 0.0, 1.0], 5.0   # 绿色
)

unreal.SystemLibrary.print_string(
    None, "蓝色信息消息", True, True,
    [0.0, 0.5, 1.0, 1.0], 5.0   # 蓝色
)

# ─────────────────────────────────────────────────────────
# 4. 格式化输出
# ─────────────────────────────────────────────────────────
# 使用 Python 的 f-string 进行格式化输出
project_name = unreal.Paths.get_base_filename(
    unreal.Paths.get_project_file_path()
)
asset_count = len(unreal.EditorAssetLibrary.list_assets("/Game"))

unreal.log(f"项目: {project_name}")
unreal.log(f"资产总数: {asset_count}")
unreal.log(f"引擎: {unreal.SystemLibrary.get_engine_version()}")

# 使用分隔线美化输出
separator = "=" * 40
unreal.log(f"\n{separator}")
unreal.log(f"  项目信息报告")
unreal.log(f"{separator}")
unreal.log(f"  项目名称: {project_name}")
unreal.log(f"  资产数量: {asset_count}")
unreal.log(f"  项目目录: {unreal.Paths.project_dir()}")
unreal.log(f"{separator}\n")

# ─────────────────────────────────────────────────────────
# 5. 实用的调试辅助函数
# ─────────────────────────────────────────────────────────
# 定义一些可复用的调试函数

def log_section(title):
    """输出一个带标题的分隔区域"""
    line = "=" * 50
    unreal.log(f"\n{line}")
    unreal.log(f"  {title}")
    unreal.log(f"{line}")

def log_info(message):
    """输出信息级别的日志"""
    unreal.log(f"[INFO] {message}")

def log_warn(message):
    """输出警告级别的日志"""
    unreal.log_warning(f"[WARN] {message}")

def log_err(message):
    """输出错误级别的日志"""
    unreal.log_error(f"[ERROR] {message}")

def show_screen(message, color=None, duration=3.0):
    """在屏幕上显示调试消息"""
    if color is None:
        color = [1.0, 1.0, 1.0, 1.0]  # 默认白色
    unreal.SystemLibrary.print_string(
        None, message, True, True, color, duration
    )

# 使用自定义函数
log_section("调试工具演示")
log_info("这是信息消息")
log_warn("这是警告消息")
log_err("这是错误消息")
show_screen("屏幕消息测试!", [0.0, 1.0, 1.0, 1.0], 5.0)

# ─────────────────────────────────────────────────────────
# 6. 对象信息调试
# ─────────────────────────────────────────────────────────
# 学会检查 UE 对象的属性和方法

def inspect_object(obj, max_attrs=20):
    """检查一个 UE 对象的属性和方法"""
    log_section(f"检查对象: {type(obj).__name__}")

    # 获取所有属性和方法
    attrs = [a for a in dir(obj) if not a.startswith('_')]

    # 分类
    methods = [a for a in attrs if callable(getattr(obj, a, None))]
    properties = [a for a in attrs if not callable(getattr(obj, a, None))]

    log_info(f"属性数量: {len(properties)}")
    for prop in properties[:max_attrs]:
        try:
            value = getattr(obj, prop)
            log_info(f"  .{prop} = {value}")
        except:
            log_info(f"  .{prop} = <无法读取>")

    log_info(f"\n方法数量: {len(methods)}")
    for method in methods[:max_attrs]:
        log_info(f"  .{method}()")

# 创建一个示例对象并检查
# 这里用 Vector 作为简单的示例
sample_vector = unreal.Vector(1.0, 2.0, 3.0)
inspect_object(sample_vector)

# ─────────────────────────────────────────────────────────
# 7. 异常处理与日志
# ─────────────────────────────────────────────────────────
# 良好的错误处理习惯

def safe_load_asset(asset_path):
    """安全地加载资产，带错误处理"""
    try:
        if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            log_warn(f"资产不存在: {asset_path}")
            return None

        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            log_err(f"加载资产失败: {asset_path}")
            return None

        log_info(f"成功加载资产: {asset_path} (类型: {type(asset).__name__})")
        return asset

    except Exception as e:
        log_err(f"加载资产时发生异常: {e}")
        return None

# 测试
safe_load_asset("/Game/SomeAssetThatDoesNotExist")
safe_load_asset("/Game/Characters/Player")  # 替换为你项目中实际存在的资产

unreal.log("\n第2课完成！你已经掌握了 UE Python 的日志和调试技巧")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个函数，用不同颜色在屏幕上显示当前关卡名称
# 2. 编写一个 inspect_all_assets() 函数，列出指定目录
#    下所有资产的类型和名称
# 3. 创建一个日志系统，同时输出到屏幕和日志文件
