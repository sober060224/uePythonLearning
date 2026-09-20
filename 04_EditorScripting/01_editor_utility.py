"""
=============================================================
编辑器脚本 第1课：编辑器工具基础
=============================================================

学习目标：
  - 创建 Editor Utility Widget（编辑器工具窗口）
  - 了解编辑器脚本的执行模式
  - 构建实用的编辑器工具函数库

关键概念：
  - Editor Utility Blueprint / Widget: UE 提供的编辑器扩展方式
  - Python 脚本可以作为这些工具的逻辑后端
  - 所有编辑器操作都应该是"事务性"的（可撤销）

本课可能用到的 API：
  unreal.get_editor_subsystem(subsystem: Class) -> EditorSubsystem  —— 获取指定类型的编辑器子系统实例
  unreal.UnrealEditorSubsystem.get_editor_world() -> World  —— 获取当前编辑会话所在的 World
  unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int  —— 开启一个可撤销事务并返回其索引
  unreal.SystemLibrary.end_transaction() -> int  —— 结束并提交当前事务
  unreal.SystemLibrary.cancel_transaction(index: int) -> None  —— 取消指定索引的事务并回滚
  unreal.SystemLibrary.print_string(world_context_object: Object, string: str = "Hello", print_to_screen: bool = True, print_to_log: bool = True, text_color: LinearColor, duration: float = 2.0, key: Name = "None") -> None  —— 向屏幕和日志输出字符串
  unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor]  —— 获取当前关卡选中的 Actor 列表
  unreal.EditorUtilityLibrary.get_selected_asset_data() -> Array[AssetData]  —— 获取内容浏览器中选中的资产数据
  actor.get_actor_location() -> Vector  —— 获取 Actor 的世界坐标位置
  actor.set_actor_location(new_location: Vector, sweep: bool, teleport: bool) -> Optional[HitResult]  —— 设置 Actor 的世界坐标位置
  actor.set_actor_rotation(new_rotation: Rotator, teleport_physics: bool) -> bool  —— 设置 Actor 的旋转角度
  unreal.log(arg: Any) -> None  —— 输出一般消息到日志
  unreal.log_warning(arg: Any) -> None  —— 输出警告到日志
  unreal.log_error(arg: Any) -> None  —— 输出错误到日志
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 编辑器工具的基本模式
# ─────────────────────────────────────────────────────────
# UE Python 脚本在编辑器中有三种执行方式：
#
# 1. Python Console: 交互式执行（调试用）
# 2. 命令行参数: -ExecutePythonScript="path"（批处理用）
# 3. Editor Utility Blueprint: 从编辑器 UI 触发（用户友好）
#
# 本课重点：编写可以被 Editor Utility 调用的工具函数

# ─────────────────────────────────────────────────────────
# 2. 事务系统（可撤销操作）
# ─────────────────────────────────────────────────────────
# UE 的事务系统让操作可以被撤销（Ctrl+Z）

def transactional_operation(operation_name, func, *args, **kwargs):
    """
    将操作包装为事务（可撤销）

    用法:
        def my_operation():
            # 做一些修改...
            pass

        transactional_operation("我的操作", my_operation)
    """
    # 【修改前】
    # unreal.Transactions.begin_transaction(operation_name)   # Transactions 类不存在
    # unreal.Transactions.end_transaction()
    # unreal.Transactions.cancel_transaction()
    #
    # 【问题分析】
    # 1. unreal.Transactions 这个类在 stub 里查无此类 —— 事务方法其实在 SystemLibrary 上。
    # 2. 签名也完全不同：
    #    begin_transaction(context, description, primary_object) -> int
    #      - 3 个参数：context 写脚本名，description 写操作名，
    #        primary_object 是被修改的主对象（没有具体对象就传编辑器 world）
    #      - 返回"事务索引"，cancel 时必须传回去
    #    cancel_transaction(index)  —— 必须带索引，不是零参数
    # 开始事务
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", operation_name, world)

    try:
        result = func(*args, **kwargs)
        unreal.SystemLibrary.end_transaction()
        unreal.log(f"事务完成: {operation_name}")
        return result
    except Exception as e:
        unreal.SystemLibrary.cancel_transaction(token)
        unreal.log_error(f"事务失败，已回滚: {e}")
        raise

# ─────────────────────────────────────────────────────────
# 3. 编辑器通知系统
# ─────────────────────────────────────────────────────────

def notify_user(message, notification_type="info", duration=5.0):
    """
    向用户显示通知

    参数:
        message: 通知内容
        notification_type: "info", "success", "warning", "error"
        duration: 显示持续时间
    """
    color_map = {
        "info":    [0.5, 0.8, 1.0, 1.0],
        "success": [0.0, 1.0, 0.3, 1.0],
        "warning": [1.0, 0.8, 0.0, 1.0],
        "error":   [1.0, 0.2, 0.2, 1.0],
    }

    color = color_map.get(notification_type, [1.0, 1.0, 1.0, 1.0])

    # 屏幕消息
    # 【修改前】print_string(None, ...) —— world_context_object 传 None 在编辑器里静默失败，
    # 必须传有效的 World（这里用 UnrealEditorSubsystem 取编辑器世界）
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    unreal.SystemLibrary.print_string(
        world, message, True, True,
        unreal.LinearColor(color[0], color[1], color[2], color[3]),
        duration
    )

    # 同时输出到日志
    log_funcs = {
        "info": unreal.log,
        "success": unreal.log,
        "warning": unreal.log_warning,
        "error": unreal.log_error,
    }
    log_funcs.get(notification_type, unreal.log)(f"[{notification_type.upper()}] {message}")

# ─────────────────────────────────────────────────────────
# 4. 获取编辑器选区
# ─────────────────────────────────────────────────────────

def get_selected_actors():
    """获取关卡中选中的 Actor 列表"""
    return unreal.EditorLevelLibrary.get_selected_level_actors()

def get_selected_assets():
    """获取 Content Browser 中选中的资产路径列表"""
    selected = unreal.EditorUtilityLibrary.get_selected_asset_data()
    return [str(d.package_name) for d in selected]

def require_selection(min_count=1, selection_type="actor"):
    """
    检查是否有足够的选中项，否则提示用户

    用法:
        actors = require_selection(1, "actor")
        if not actors:
            return  # 已显示错误消息
    """
    if selection_type == "actor":
        selected = get_selected_actors()
        label = "Actor"
    else:
        selected = get_selected_assets()
        label = "资产"

    if len(selected) < min_count:
        notify_user(
            f"请至少选中 {min_count} 个 {label}！",
            "warning"
        )
        return None

    return selected

# ─────────────────────────────────────────────────────────
# 5. 实用编辑器工具函数集
# ─────────────────────────────────────────────────────────

def snap_selected_to_grid(grid_size=100.0):
    """将选中的 Actor 对齐到网格"""
    actors = require_selection(1, "actor")
    if not actors:
        return

    def do_snap():
        for actor in actors:
            location = actor.get_actor_location()
            snapped = unreal.Vector(
                round(location.x / grid_size) * grid_size,
                round(location.y / grid_size) * grid_size,
                location.z
            )
            actor.set_actor_location(snapped, False, False)

        notify_user(f"已将 {len(actors)} 个 Actor 对齐到网格 (大小: {grid_size})", "success")

    transactional_operation("对齐到网格", do_snap)

def align_selected_to_first(axis="z"):
    """将选中的 Actor 对齐到第一个选中 Actor 的指定轴"""
    actors = require_selection(2, "actor")
    if not actors:
        return

    reference = actors[0]
    ref_location = reference.get_actor_location()

    axis_map = {"x": 0, "y": 1, "z": 2}
    axis_index = axis_map.get(axis.lower(), 2)

    def do_align():
        for actor in actors[1:]:
            loc = list([actor.get_actor_location().x,
                        actor.get_actor_location().y,
                        actor.get_actor_location().z])
            ref_vals = [ref_location.x, ref_location.y, ref_location.z]
            loc[axis_index] = ref_vals[axis_index]
            actor.set_actor_location(unreal.Vector(loc[0], loc[1], loc[2]), False, False)

        notify_user(f"已将 {len(actors)-1} 个 Actor 对齐到 {axis.upper()} 轴", "success")

    transactional_operation(f"对齐到{axis.upper()}轴", do_align)

def distribute_actors_evenly(axis="x", spacing=200.0):
    """将选中的 Actor 均匀分布"""
    actors = require_selection(2, "actor")
    if not actors:
        return

    axis_map = {"x": 0, "y": 1, "z": 2}
    idx = axis_map.get(axis.lower(), 0)

    def do_distribute():
        # 按指定轴排序
        sorted_actors = sorted(actors, key=lambda a: [
            a.get_actor_location().x,
            a.get_actor_location().y,
            a.get_actor_location().z
        ][idx])

        # 计算起始位置
        start_val = [
            sorted_actors[0].get_actor_location().x,
            sorted_actors[0].get_actor_location().y,
            sorted_actors[0].get_actor_location().z
        ][idx]

        for i, actor in enumerate(sorted_actors):
            loc = [actor.get_actor_location().x,
                   actor.get_actor_location().y,
                   actor.get_actor_location().z]
            loc[idx] = start_val + i * spacing
            actor.set_actor_location(unreal.Vector(loc[0], loc[1], loc[2]), False, False)

        notify_user(
            f"已均匀分布 {len(actors)} 个 Actor (间距: {spacing})",
            "success"
        )

    transactional_operation("均匀分布", do_distribute)

def randomize_rotation(selected_actors=None, max_yaw=360.0,
                        max_pitch=0.0, max_roll=0.0):
    """随机化 Actor 的旋转"""
    import random

    actors = selected_actors or require_selection(1, "actor")
    if not actors:
        return

    def do_randomize():
        for actor in actors:
            rot = unreal.Rotator(
                random.uniform(-max_pitch, max_pitch),
                random.uniform(-max_yaw, max_yaw),
                random.uniform(-max_roll, max_roll)
            )
            actor.set_actor_rotation(rot, False)

        notify_user(f"已随机旋转 {len(actors)} 个 Actor", "success")

    transactional_operation("随机旋转", do_randomize)

# ─────────────────────────────────────────────────────────
# 6. 创建 Editor Utility Blueprint
# ─────────────────────────────────────────────────────────
# 注意：创建 Editor Utility Widget 通常需要在编辑器中手动操作
# 但可以创建调用的 Python 脚本

EDITOR_TOOL_SCRIPT_TEMPLATE = '''
"""
自动生成的编辑器工具脚本
使用方法：在 Editor Utility Widget 中调用此脚本
"""
import unreal

def run():
    """工具主入口"""
    # 在这里编写工具逻辑
    selected = unreal.EditorLevelLibrary.get_selected_level_actors()
    if not selected:
        unreal.log_warning("请先选中 Actor")
        return

    for actor in selected:
        # 你的逻辑...
        pass

    unreal.log(f"处理了 {len(selected)} 个 Actor")

run()
'''

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 取消注释以下代码来测试（需要先选中 Actor）
# snap_selected_to_grid(100.0)
# align_selected_to_first("z")
# distribute_actors_evenly("x", 200.0)
# randomize_rotation(max_yaw=180.0)

unreal.log("编辑器脚本第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个工具：将选中的 Actor 排列成圆形
# 2. 创建一个工具：复制选中 Actor 并按网格粘贴
# 3. 创建一个工具：测量两个选中 Actor 之间的距离
# 4. 将上面的工具函数组织成一个可导入的模块
