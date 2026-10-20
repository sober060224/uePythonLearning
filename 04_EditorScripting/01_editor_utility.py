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

习题可能用到的 API：
  ── unreal ──
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem) -> EditorActorSubsystem
        —— 取 Actor 子系统，练习1/2/3 的入口（返回 Optional，必须先判空）
    subsystem.get_selected_level_actors() -> Array[Actor]
        —— 取当前选中的 Actor，练习1 要 ≥3 个、练习3 只要前两个
    actor.get_actor_location() -> Vector
        —— 读世界坐标，练习1/2/3 都要
    actor.set_actor_location(new_location: Vector, sweep: bool, teleport: bool) -> Optional[HitResult]
        —— 写世界坐标，练习1/2 移动 Actor
    actor.set_actor_rotation(new_rotation: Rotator, teleport_physics: bool) -> bool
        —— 改朝向，练习1 让每个 Actor 面朝圆心
    unreal.Vector(x: float, y: float, z: float) -> Vector
        —— 构造目标位置，练习1/2
    unreal.Rotator(roll: float, pitch: float, yaw: float) -> Rotator
        —— 构造朝向，练习1（注意参数顺序是 roll, pitch, yaw，不是 x, y, z）
    vector.length() -> float
        —— 向量长度，练习3 用它算两点距离（先相减再 length）
    subsystem.duplicate_actor(actor_to_duplicate: Actor, to_world: World = None, offset: Vector = [0,0,0]) -> Actor
        —— 复制 Actor，练习2（这是子系统的方法，不是 Actor 的方法）
    unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int
    unreal.SystemLibrary.end_transaction() -> int
    unreal.SystemLibrary.cancel_transaction(index: int) -> None
        —— 练习1/2 想支持 Ctrl+Z 就必须包事务；本文件已有 editor_transaction 直接用
  ── Python 标准库 ──
    math.radians / math.cos / math.sin
        —— 练习1 把角度换成圆周上的 X/Y 坐标
    sys.path.append(...) / importlib.reload(...)
        —— 练习4 把工具组织成模块后导入并热重载
=============================================================
"""

import contextlib
import math

import unreal


# ─────────────────────────────────────────────────────────
# 工具：编辑器事务上下文
# ─────────────────────────────────────────────────────────
@contextlib.contextmanager
def editor_transaction(description, primary_object):
    """
    在编辑器事务里执行一段操作：

      - 正常结束    -> 提交事务（用户可以 Ctrl+Z 一次性撤销整段操作）
      - 抛异常      -> cancel_transaction 回滚，撤销栈不会留在"半开"状态
      - 中途 return -> __exit__ 照样执行，收尾不会漏

    【参数命名注意】begin_transaction 的三个参数是
      (context, description, primary_object)
    其中 context 是"脚本名"（撤销历史里显示是谁干的），不是被修改对象。
    被修改的主对象是第 3 个参数，所以这里形参叫 primary_object，别叫 context。
    """
    token = unreal.SystemLibrary.begin_transaction(
        "Python脚本", unreal.Text(description), primary_object
    )
    try:
        yield token
    except BaseException:
        unreal.SystemLibrary.cancel_transaction(token)
        raise
    else:
        unreal.SystemLibrary.end_transaction()


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
#
# 【为什么需要事务？】
# 编辑器里修改了 Actor 位置后，用户按 Ctrl+Z 期望能撤销。
# 如果不包在事务里，撤销不会生效——这是新手最常踩的坑。
#
# 【事务的工作原理】
# begin_transaction() 就像"拍照"，把当前状态记录下来。
# end_transaction() 就像"确认保存"，这个操作进入撤销历史栈。
# cancel_transaction() 就像"回滚到快照"，所有改动被还原。
#
# 【begin_transaction 的参数含义】
# - context: 脚本名称（出现在撤销历史里，方便用户识别是谁改的）
# - description: 操作描述（如"对齐到网格"，显示在 Edit → Undo 菜单里）
# - primary_object: 被修改的主要对象（拿不到具体对象就传编辑器 World）
# - 返回值: 事务索引（token），cancel_transaction 时必须传回去
#
# 【常见错误】
# 1. 不传 primary_object 或传 None → 编辑器会崩溃或静默失败
# 2. 忘记 end_transaction → 事务永远处于"进行中"状态，后续操作全部被阻止
# 3. begin 和 end 不配对 → 编辑器状态异常


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
    # 获取编辑器世界作为 primary_object（因为操作可能涉及多个 Actor，没有单一的"主对象"）
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem is None:
        # 拿不到子系统说明不在编辑器环境；必须显式报错，否则调用方以为操作已执行
        unreal.log_error(f"事务未执行（不在编辑器环境）: {operation_name}")
        return None

    world = subsystem.get_editor_world()
    # 【修改后】手写的 try/except + begin/end/cancel 统一交给 editor_transaction：
    #   正常结束自动提交；抛异常自动 cancel 回滚，不会把编辑器留在"事务进行中"。
    with editor_transaction(operation_name, world):
        result = func(*args, **kwargs)

    unreal.log(f"事务完成: {operation_name}")
    return result


# ─────────────────────────────────────────────────────────
# 3. 编辑器通知系统
# ─────────────────────────────────────────────────────────
#
# 【print_string 的 world_context_object 参数】
# 这是 UE4/5 最容易踩坑的地方之一：
# - 传 None → 在编辑器里静默失败，消息不显示
# - 传错误的对象类型 → 编辑器崩溃
# - 正确做法：用 UnrealEditorSubsystem 获取编辑器世界，然后传进去
#
# 【为什么需要 world_context_object？】
# UE 的很多静态函数设计为"在某个对象的上下文中执行"，
# print_string 需要知道"在哪个世界里显示屏幕消息"。
# 编辑器里没有 Game World，所以要用"编辑器 World"。


def notify_user(message, notification_type="info", duration=5.0):
    """
    向用户显示通知

    参数:
        message: 通知内容
        notification_type: "info", "success", "warning", "error"
        duration: 显示持续时间
    """
    # 颜色映射：RGBA 四通道，每个值 0.0-1.0
    color_map = {
        "info": [0.5, 0.8, 1.0, 1.0],  # 浅蓝色
        "success": [0.0, 1.0, 0.3, 1.0],  # 绿色
        "warning": [1.0, 0.8, 0.0, 1.0],  # 橙黄色
        "error": [1.0, 0.2, 0.2, 1.0],  # 红色
    }

    color = color_map.get(notification_type, [1.0, 1.0, 1.0, 1.0])

    # 【关键】必须先获取编辑器世界，再传给 print_string
    # get_editor_subsystem 的参数是"子系统类型"，返回该类型的实例
    # UnrealEditorSubsystem 提供编辑器级别的全局操作（获取世界、关卡等）
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem is None:
        return

    world = subsystem.get_editor_world()
    unreal.SystemLibrary.print_string(
        world,
        message,
        True,
        True,
        unreal.LinearColor(color[0], color[1], color[2], color[3]),
        duration,
    )

    # 同时输出到日志（Output Log 窗口，可搜索、可保存）
    # log / log_warning / log_error 三种级别，对应不同图标颜色
    log_funcs = {
        "info": unreal.log,
        "success": unreal.log,
        "warning": unreal.log_warning,
        "error": unreal.log_error,
    }
    log_funcs.get(notification_type, unreal.log)(
        f"[{notification_type.upper()}] {message}"
    )


# ─────────────────────────────────────────────────────────
# 4. 获取编辑器选区
# ─────────────────────────────────────────────────────────
#
# 【EditorLevelLibrary vs EditorActorSubsystem】
# UE5 中，选 Actor 的操作从 EditorLevelLibrary 搬到了 EditorActorSubsystem。
# 老代码用 get_selected_level_actors() 还能跑，但会有 DeprecationWarning。
# 新代码应该用：
#   actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
#
# 【选区是"快照"还是"引用"？】
# 返回的是 Actor 对象的引用（不是副本），修改位置会直接影响场景中的 Actor。
# 如果选区变了，之前获取的列表不会自动更新。


def get_selected_actors():
    """获取关卡中选中的 Actor 列表（返回普通 list，切片才不会被类型检查器误解）"""
    # 【旧写法对照】unreal.EditorLevelLibrary.get_selected_level_actors()
    # 桩里已标 deprecated: The Editor Scripting Utilities Plugin is deprecated。
    # 迁移不是机械改名：EditorLevelLibrary 那份是 classmethod，子系统那份是实例方法。
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if subsystem is None:
        return []
    # list() 是必需的：桩里 Array 只声明了 __getitem__(index: int)，没有 slice 重载，
    # 所以 Array[1:] 会被类型检查器当成「取元素」而不是「取子列表」。
    return list(subsystem.get_selected_level_actors())


def get_selected_assets():
    """获取 Content Browser 中选中的资产路径列表"""
    # get_selected_asset_data() 返回 AssetData 对象数组
    # AssetData 包含：package_name（完整路径如 /Game/MyFolder/MyAsset）
    #                 asset_name（仅名称）
    #                 asset_class_path（资产类型路径）
    # 这里只取 package_name 转为字符串
    selected = unreal.EditorUtilityLibrary.get_selected_asset_data()
    return [str(d.package_name) for d in selected]


def require_actors(min_count=1):
    """
    检查是否选中了足够多的 Actor，不足则提示并返回空列表。

    用法:
        actors = require_actors(2)
        if not actors:
            return  # 已显示警告

    【为什么按类型拆成两个函数】一个函数不可能同时返回 list[Actor] 和 list[str]。
    旧的 require_selection 用 selection_type 分支返回两种元素类型，类型检查器只能
    取并集（Array[Actor] | list[str] | None），于是 Actor 那半边被推成 str，
    后续每个 get_actor_location() 都报「属性未知」。
    这里返回空列表而不是 None：空列表本身是假值，调用点的 `if not actors` 不用改。
    """
    actors = get_selected_actors()
    # 这是"防御性编程"的典型模式：先检查前提条件
    if len(actors) < min_count:
        notify_user(f"请至少选中 {min_count} 个 Actor！", "warning")
        return []

    return actors


# ─────────────────────────────────────────────────────────
# 5. 实用编辑器工具函数集
# ─────────────────────────────────────────────────────────
#
# 以下是几个实用的编辑器工具函数，展示了常见的 UE Python 操作模式。

# 字母 → 坐标索引的映射（x=0, y=1, z=2）
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def resolve_axis(axis):
    """把轴名转成坐标索引；无法识别返回 None，由调用方提示用户。"""
    return AXIS_INDEX.get(axis.lower()) if isinstance(axis, str) else None


def actor_xyz(actor):
    """取 Actor 世界坐标的 [x, y, z] 普通列表。

    【为什么拆成列表】unreal.Vector 的 x/y/z 是可写的（桩里标 [Read-Write]，
    也生成了 setter），但 Vector 不支持按下标赋值 —— 而下面的工具需要
    loc[axis_index] = ...，所以先拆成普通 list 改完再装回 Vector。
    """
    loc = actor.get_actor_location()
    return [loc.x, loc.y, loc.z]


def snap_selected_to_grid(grid_size=100.0):
    """
    将选中的 Actor 对齐到最近的网格点

    【对齐原理】
    把坐标除以格长、四舍五入、再乘回来。grid_size=100 时：
      x=150 → x=200（1.5 → 2）
      x=120 → x=100（1.2 → 1）
      x=250 → x=300（2.5 → 3）
    Z 轴保持不变（通常不需要把物体对齐到高度网格）。

    【为什么不用 round()】Python 的 round() 是"银行家舍入"（half-to-even），
    round(2.5) == 2 而不是 3，所以 x=250 会被对齐到 200。这里用 floor(v + 0.5)
    拿到真正的四舍五入。
    """
    if grid_size <= 0:
        notify_user(f"网格大小必须大于 0（当前: {grid_size}）", "error")
        return

    actors = require_actors(1)
    if not actors:
        return

    def do_snap():
        for actor in actors:
            location = actor.get_actor_location()
            # 登记进当前事务，否则 Ctrl+Z 撤销不到这个 Actor 的位移
            unreal.SystemLibrary.transact_object(actor)
            snapped = unreal.Vector(
                math.floor(location.x / grid_size + 0.5) * grid_size,
                math.floor(location.y / grid_size + 0.5) * grid_size,
                location.z,  # Z 轴保持原值
            )
            # sweep=False: 不做碰撞检测直接移动
            # teleport=False: 更新物理模拟状态
            actor.set_actor_location(snapped, False, False)

        notify_user(
            f"已将 {len(actors)} 个 Actor 对齐到网格 (大小: {grid_size})", "success"
        )

    # 包装在事务里，用户可以 Ctrl+Z 撤销
    transactional_operation("对齐到网格", do_snap)


def align_selected_to_first(axis="z"):
    """
    将选中的 Actor 对齐到第一个选中 Actor 的指定轴

    【使用场景】
    比如选了 5 个 Actor，想让它们都和第 1 个在同一高度（Z 轴），
    或者在同一水平位置（X 或 Y 轴）。
    """
    # 至少需要选中 2 个 Actor（第 1 个做参考，其他对齐到它）
    actors = require_actors(2)
    if not actors:
        return

    axis_index = resolve_axis(axis)
    if axis_index is None:
        notify_user(f"无法识别的坐标轴: {axis}（只支持 x / y / z）", "error")
        return

    # 第一个 Actor 作为参考点
    ref_location = actor_xyz(actors[0])

    def do_align():
        for actor in actors[1:]:  # 跳过第一个（参考 Actor 不动）
            loc = actor_xyz(actor)
            # 只修改目标轴的值，其他轴保持不变
            loc[axis_index] = ref_location[axis_index]
            # 登记进事务后才能撤销
            unreal.SystemLibrary.transact_object(actor)
            actor.set_actor_location(
                unreal.Vector(loc[0], loc[1], loc[2]), False, False
            )

        notify_user(
            f"已将 {len(actors) - 1} 个 Actor 对齐到 {axis.upper()} 轴", "success"
        )

    transactional_operation(f"对齐到{axis.upper()}轴", do_align)


def distribute_actors_evenly(axis="x", spacing=200.0):
    """
    将选中的 Actor 均匀分布

    【算法思路】
    1. 按目标轴的坐标排序
    2. 以第一个 Actor 的位置为起点
    3. 每个后续 Actor 的间距为 spacing
    """
    actors = require_actors(2)
    if not actors:
        return

    idx = resolve_axis(axis)
    if idx is None:
        notify_user(f"无法识别的坐标轴: {axis}（只支持 x / y / z）", "error")
        return

    def do_distribute():
        # 按指定轴排序（sorted 返回新列表，不修改原列表）
        sorted_actors = sorted(actors, key=lambda a: actor_xyz(a)[idx])

        # 计算起始位置（排序后第一个 Actor 的目标轴坐标）
        start_val = actor_xyz(sorted_actors[0])[idx]

        for i, actor in enumerate(sorted_actors):
            loc = actor_xyz(actor)
            # 等间距排列：第 i 个 Actor 的位置 = 起始 + i × 间距
            loc[idx] = start_val + i * spacing
            unreal.SystemLibrary.transact_object(actor)
            actor.set_actor_location(
                unreal.Vector(loc[0], loc[1], loc[2]), False, False
            )

        notify_user(f"已均匀分布 {len(actors)} 个 Actor (间距: {spacing})", "success")

    transactional_operation("均匀分布", do_distribute)


def randomize_rotation(
    selected_actors=None, max_yaw=360.0, max_pitch=0.0, max_roll=0.0
):
    """
    随机化 Actor 的旋转

    【Rotator 的三个轴】
    - Pitch: 俯仰角（抬头/低头），绕 Y 轴旋转
    - Yaw: 偏航角（左转/右转），绕 Z 轴旋转
    - Roll: 翻滚角（侧翻），绕 X 轴旋转
    注意：UE 的旋转顺序是 Yaw → Pitch → Roll

    【为什么默认只随机 Yaw？】
    大多数游戏物体只需要水平旋转（比如树木、石头、建筑）。
    Pitch 和 Roll 随机化会导致物体"歪倒"，通常只用于特殊效果。
    """
    import random

    # 必须用 is None 判断：写成 `selected_actors or require_actors(1)` 时，
    # 调用方显式传空列表会被当成"没传"，从而悄悄去操作当前选区。
    actors = require_actors(1) if selected_actors is None else list(selected_actors)
    if not actors:
        return

    def do_randomize():
        for actor in actors:
            # random.uniform(a, b) 返回 [a, b] 之间的随机浮点数
            # 【易错点】Rotator 的位置参数顺序是 (roll, pitch, yaw)，不是 (pitch, yaw, roll)。
            #   按旧顺序传会让三个角度整体串位，这里一律用关键字参数。
            rot = unreal.Rotator(
                pitch=random.uniform(-max_pitch, max_pitch),
                yaw=random.uniform(-max_yaw, max_yaw),
                roll=random.uniform(-max_roll, max_roll),
            )
            # set_actor_rotation 的第二个参数 teleport_physics=False
            # 表示不强制传送物理体（如果是物理模拟的 Actor，会更平滑）
            unreal.SystemLibrary.transact_object(actor)
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
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected = list(subsystem.get_selected_level_actors()) if subsystem else []
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
# 【练习 1】把选中的 Actor 均匀摆在一个圆上
#   输入： 视口中选中 ≥3 个 Actor；不足 3 个就提示后退出，一个都不许动
#   任务： 圆心 = 这些 Actor 当前位置的平均值（X/Y/Z 各取均值，即质心）；
#          半径 = 300.0（写成函数参数 radius=300.0）；
#          从 +X 方向起算，第 i 个 Actor 的角度 = i * 360°/N；
#          每个 Actor 的 Yaw 设成该角度（= 指向圆心外侧），Roll/Pitch 归零
#          （UE 里 Yaw=0 指向 +X、Yaw=90 指向 +Y，所以圆周上 θ 角处的外法线就是 Yaw=θ；
#           写 θ+90 会变成沿切线方向，是常见错法）
#   输出： 圆周上出现 N 个等距 Actor；日志打印「已排列 N 个 Actor，半径 R」
#   验收： 选中 5 个跑一次 → 5 个点应构成正五边形（相邻点夹角 72°）；
#          再按 Ctrl+Z 一次 → 全部回到原位（说明事务包对了）

# 【练习 2】把选中的 Actor 复制成 cols × rows 的网格
#   输入： 选中 1 个或多个 Actor；一个都没选就提示后退出
#   任务： 每个选中的 Actor 各复制出 cols*rows 份（cols 默认 3、rows 默认 2），
#          复制体按行列偏移：第 (row, col) 个的偏移 = (col*spacing, row*spacing, 0)，
#          spacing 默认 200.0，行列都从原 Actor 的 +X / +Y 方向增长；
#          偏移量相对原 Actor 的原始位置，不要累加
#   输出： 视口里出现整齐的网格阵列；日志打印「复制了 N 个 Actor」
#   验收： 选中 1 个跑 cols=3 rows=2 → 场景多出 6 个（连原件共 7 个），
#          相邻间距严格是 200；Ctrl+Z 一次全部消失

# 【练习 3】测量两个选中 Actor 之间的距离
#   输入： 选中恰好 2 个 Actor；少于或多于 2 个都提示后退出（不要偷偷取前两个）
#   任务： 算三维直线距离（X/Y/Z 三个轴都算），同时打印 XY 平面距离；
#          不做任何修改，所以不需要事务
#   输出： 日志「A → B 直线距离 123.4 cm（平面距离 100.0 cm）」
#   验收： 把两个 Actor 摆在同 X/Y、Z 差 100 → 应打印「100.0 cm（平面距离 0.0 cm）」

# 【练习 4】把上面三个工具收拾成一个可导入的模块
#   输入： 本文件里已经写好的工具函数
#   任务： 新建 04_EditorScripting/editor_tools.py，只暴露 3 个公有函数
#          （下划线开头的内部函数不导出），并在文件末尾提供
#          TOOLS = {"命令名": 函数} 字典，供 Editor Utility Widget 做下拉选择
#   输出： 新文件 editor_tools.py 可被其他脚本导入
#   验收： 另写 3 行脚本 `import editor_tools` + `editor_tools.place_in_circle()`
#          能跑通；改完 editor_tools.py 后不重启编辑器，用 importlib.reload 生效
