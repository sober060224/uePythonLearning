"""
=============================================================
关卡与Actor 第1课：在关卡中生成 Actor
=============================================================

学习目标：
  - 使用 Python 在关卡中生成 Actor
  - 设置 Actor 的位置、旋转和缩放
  - 使用不同的生成模式（单个、批量、模式化）

核心类：
  - unreal.EditorLevelLibrary - 关卡编辑操作
  - unreal.Actor - Actor 基类

习题可能用到的 API：
  ── unreal ──
    unreal.EditorLevelLibrary.spawn_actor_from_class(cls, actor_class, location, rotation, transient) -> Actor
        —— 在关卡中生成 Actor
    unreal.EditorAssetLibrary.load_blueprint_class(cls, asset_path) -> Class
        —— 加载蓝图类（练习3棋盘格需要交替两种网格体）
        实测：资产叫 BP_Cannon 时拿到的类名是 "BP_Cannon_C"（带 _C 后缀），
        spawn_actor_from_class 之后 actor.get_class().get_name() 也是 BP_Cannon_C
    unreal.EditorAssetLibrary.load_asset(cls, asset_path: str) -> Object
        —— 加载资产（练习2 地形装饰器加载岩石/树木、练习3 棋盘格加载两种网格体）
        实测：路径不存在时**返回 None**（传 /Game/Nope_Xyz → None），
           练习3「加载失败就整体放弃」靠这个判断，不用 try/except
    unreal.Vector.length(self) -> float
        —— 向量长度（练习4泊松圆盘采样需要计算点间距离）
    unreal.Vector.__sub__(self, other) -> Vector
        —— 向量相减（练习4泊松圆盘采样需要计算两点间距）
    unreal.EditorLevelLibrary.get_all_level_actors(cls) -> Array[Actor]
        —— 获取所有 Actor（练习2、4需要检查已放置的 Actor）
  ── Python 标准库 ──
    math.radians / math.cos / math.sin / math.sqrt / math.pi
        —— 练习1 螺旋路径的半径与角度计算、练习4 泊松采样的最小间距
    random.uniform
        —— 练习2 地形装饰器的随机摆放、练习4 随机撒点
=============================================================
"""

import contextlib

import unreal


# ─────────────────────────────────────────────────────────
# 工具：编辑器事务上下文
# ─────────────────────────────────────────────────────────
@contextlib.contextmanager
def editor_transaction(description, context):
    """
    在编辑器事务里执行一段操作：

      - 正常结束    -> 提交事务（用户可以 Ctrl+Z 一次性撤销整段操作）
      - 抛异常      -> cancel_transaction 回滚，撤销栈不会留在"半开"状态
      - 中途 return -> __exit__ 照样执行，收尾不会漏
    """
    token = unreal.SystemLibrary.begin_transaction("Python脚本", description, context)
    try:
        yield token
    except BaseException:
        unreal.SystemLibrary.cancel_transaction(token)
        raise
    else:
        unreal.SystemLibrary.end_transaction()


def editor_world():
    """取当前编辑会话所在的 World；不在编辑器环境（或 World 未就绪）时返回 None。

    【为什么不能一行写完】get_editor_subsystem 的返回类型是 Optional —— 它可能返回
    None。直接写 unreal.get_editor_subsystem(...).get_editor_world() 会在 None 上
    取属性，类型检查器判为错误，运行时会抛 AttributeError。
    """
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return subsystem.get_editor_world() if subsystem else None


import math
import random

# ─────────────────────────────────────────────────────────
# 1. 基础 Actor 生成
# ─────────────────────────────────────────────────────────


def spawn_basic_actor(actor_class, location, rotation=None, label=None):
    """
    在关卡中生成一个 Actor

    参数:
        actor_class: Actor 类 (如 unreal.StaticMeshActor)
        location: 位置 Vector
        rotation: 旋转 Rotator (可选)
        label: Actor 标签 (可选)
    """
    # Rotator 是 UE 中表示旋转的结构体，Python 构造函数参数顺序是 (Roll, Pitch, Yaw)
    # —— 实测确认：Rotator(10,0,0) 得到 roll=10；Rotator(0,10,0) 得到 pitch=10；
    #    Rotator(0,0,10) 得到 yaw=10。所以千万别按 (Pitch, Yaw, Roll) 写，会全错位。
    # 三个轴的含义：Pitch 绕 Y 轴（抬头低头）、Yaw 绕 Z 轴（左右转）、Roll 绕 X 轴（翻滚）
    # 建议全部用关键字参数：unreal.Rotator(roll=0, pitch=0, yaw=90)
    # 如果不传 rotation，默认生成一个无旋转的 Actor
    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    # spawn_actor_from_class 是编辑器专用的生成方法
    # 它会在当前编辑器关卡中创建一个新 Actor 实例
    # 注意：这只是编辑器操作，不是运行时的 SpawnActor
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class, location, rotation
    )

    # 生成后要检查 actor 是否成功创建（如果参数错误可能返回 None）
    # set_actor_label 设置的名称只影响编辑器里的显示名，不影响 C++ 类名
    if actor and label:
        actor.set_actor_label(label)
        unreal.log(f"已生成: {label} 在 {location}")
    elif actor:
        unreal.log(f"已生成 Actor 在 {location}")

    return actor


# ─────────────────────────────────────────────────────────
# 2. 从蓝图生成 Actor
# ─────────────────────────────────────────────────────────


def spawn_blueprint_actor(blueprint_path, location, rotation=None, label=None):
    """
    从蓝图类生成 Actor

    参数:
        blueprint_path: 蓝图路径 (如 "/Game/Blueprints/BP_Enemy")
        location: 位置
        rotation: 旋转
        label: 标签
    """
    # 蓝图在 UE 中本质上也是一种资产（Asset），需要用 load_blueprint_class 加载
    # load_asset 只能加载"数据资产"，蓝图类必须用专用方法
    # 加载后得到的是一个 Class（类），不是实例——你拿到的是"图纸"，不是"成品"
    bp_class = unreal.EditorAssetLibrary.load_blueprint_class(blueprint_path)
    if not bp_class:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    # 拿到蓝图类后，用 spawn_actor_from_class 生成，和普通类一样
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        bp_class, location, rotation
    )

    if actor and label:
        actor.set_actor_label(label)

    return actor


# ─────────────────────────────────────────────────────────
# 3. 批量生成 - 网格排列
# ─────────────────────────────────────────────────────────


def spawn_grid(actor_class, rows, cols, spacing, start_location=None, mesh_path=None):
    """
    在网格中批量生成 Actor

    参数:
        actor_class: Actor 类
        rows: 行数
        cols: 列数
        spacing: 间距
        start_location: 起始位置
        mesh_path: 可选的网格体路径
    """
    # 如果没指定起始位置，就从世界原点 (0,0,0) 开始
    if start_location is None:
        start_location = unreal.Vector(0, 0, 0)

    total = rows * cols
    spawned = []

    # ScopedSlowTask 是编辑器专用的"进度条"工具
    # 当你做耗时操作时（比如批量生成几百个 Actor），应该给用户显示进度
    # 参数1: 总工作量（用于计算百分比），参数2: 显示的文字
    task = unreal.ScopedSlowTask(total, "生成网格 Actor...")
    # make_dialog(True) 打开一个带"取消"按钮的进度对话框
    # 如果用户点了取消，should_cancel() 会返回 True
    task.make_dialog(True)

    # 事务（Transaction）是 UE 的"撤销/重做"机制
    # 你在编辑器里按 Ctrl+Z 能撤销操作，就是因为有事务系统
    # begin_transaction 开启一个事务，所有操作会在 end_transaction 时作为一个整体
    # 参数说明：
    #   - "Python脚本" 是上下文名称（显示在撤销历史里）
    #   - "生成网格" 是操作描述
    #   - world 是被修改的主对象（生成操作中 Actor 还不存在，用 World 代替）
    # 【性能】mesh_path 在每次迭代里都是同一个资产，加载一次就够了。
    #   原来把它写在双重循环里，rows*cols 次调用 load_asset 纯属浪费。
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path) if mesh_path else None
    if mesh_path and not mesh:
        unreal.log_warning(f"网格体加载失败，将只生成空 Actor: {mesh_path}")

    world = editor_world()
    if world is None:
        unreal.log_error("取不到编辑器 World，网格生成未执行")
        return []

    with editor_transaction("生成网格", world):
        for row in range(rows):
            for col in range(cols):
                # 检查用户是否点了取消按钮
                if task.should_cancel():
                    break

                # 每生成一个 Actor，进度条就前进一格
                task.enter_progress_frame(1.0)

                # 计算网格位置：
                # x 轴方向由 col 控制（左右移动），y 轴方向由 row 控制（前后移动）
                # spacing 是相邻 Actor 之间的距离（单位：厘米）
                location = unreal.Vector(
                    start_location.x + col * spacing,
                    start_location.y + row * spacing,
                    start_location.z,
                )

                actor = spawn_basic_actor(
                    actor_class, location, label=f"Grid_R{row}_C{col}"
                )

                # 如果指定了网格体路径，就给生成的 Actor 设置网格体
                # Actor 本身只是一个"容器"，真正显示 3D 模型的是它的 StaticMeshComponent
                if actor and mesh:
                    # get_component_by_class 获取 Actor 上指定类型的组件
                    # StaticMeshComponent 是负责渲染静态网格体的组件
                    # 参数写成 .static_class()：它要的是「类对象」而不是 Python 类
                    mesh_comp = actor.get_component_by_class(
                        unreal.StaticMeshComponent.static_class()
                    )
                    # get_component_by_class 在桩里声明返回基类 ActorComponent，
                    # 所以要用 isinstance 收窄成具体子类，才能调子类自己的方法
                    # set_static_mesh 要求 StaticMesh，而 load_asset 返回的是 Object，
                    # 所以还要把网格体本身也收窄一层
                    if isinstance(mesh_comp, unreal.StaticMeshComponent) and isinstance(
                        mesh, unreal.StaticMesh
                    ):
                        # set_static_mesh 把加载的网格体资产赋给组件
                        # 这就像给 Actor "穿上"一个 3D 模型
                        mesh_comp.set_static_mesh(mesh)

                spawned.append(actor)

    # with 块结束时事务提交：整批生成操作在撤销历史里是一个整体
    unreal.log(f"已生成 {len(spawned)} 个 Actor ({rows}x{cols} 网格)")
    return spawned


# ─────────────────────────────────────────────────────────
# 4. 沿路径生成 Actor
# ─────────────────────────────────────────────────────────


def spawn_along_path(actor_class, points, count, randomize_rotation=False):
    """
    沿路径点生成 Actor

    参数:
        actor_class: Actor 类
        points: 路径点列表 [Vector, ...]
        count: 生成数量
        randomize_rotation: 是否随机旋转
    """
    # 至少需要 2 个点才能定义一条路径
    if len(points) < 2:
        unreal.log_error("至少需要 2 个路径点")
        return []

    spawned = []
    world = editor_world()
    if world is None:
        unreal.log_error("取不到编辑器 World，沿路径生成未执行")
        return []

    with editor_transaction("沿路径生成", world):
        for i in range(count):
            # t 是 0~1 之间的归一化参数，表示在整条路径上的百分比位置
            # 比如 count=10 时，i=0 得 t=0（起点），i=9 得 t=1（终点）
            t = i / max(count - 1, 1)
            total_length = 0

            # 先计算每段路径的长度，累加得到总长度
            # Vector 相减可以得到两点间的向量，.length() 得到向量长度
            segments = []
            for j in range(len(points) - 1):
                seg_len = (points[j + 1] - points[j]).length()
                segments.append(seg_len)
                total_length += seg_len

            # 找到 t 对应的实际距离位置
            target_dist = t * total_length
            current_dist = 0

            for j, seg_len in enumerate(segments):
                if current_dist + seg_len >= target_dist:
                    # local_t 是在当前线段上的局部比例（0~1）
                    # 用线性插值计算最终位置：A*(1-t) + B*t
                    # 这是最基本的向量插值（Lerp）公式
                    local_t = (target_dist - current_dist) / seg_len
                    location = points[j] * (1 - local_t) + points[j + 1] * local_t

                    # 计算朝向：用 atan2 算出方向向量的角度
                    # atan2 返回弧度，用 math.degrees 转换为角度
                    # 这样 Actor 会面朝路径的前进方向
                    direction = points[j + 1] - points[j]
                    yaw = math.degrees(math.atan2(direction.y, direction.x))
                    # 【易错点】Rotator 位置参数顺序是 (roll, pitch, yaw)，用关键字参数避免串位。
                    rotation = unreal.Rotator(
                        pitch=0,
                        yaw=yaw + (random.uniform(0, 360) if randomize_rotation else 0),
                        roll=0,
                    )

                    actor = spawn_basic_actor(
                        actor_class, location, rotation, label=f"Path_{i}"
                    )
                    spawned.append(actor)
                    break

                current_dist += seg_len
    unreal.log(f"沿路径生成了 {len(spawned)} 个 Actor")
    return spawned


# ─────────────────────────────────────────────────────────
# 5. 在区域中随机散布
# ─────────────────────────────────────────────────────────


def spawn_in_area(
    actor_class, center, radius, count, min_distance=0, height_range=(0, 0)
):
    """
    在圆形区域中随机散布 Actor

    参数:
        actor_class: Actor 类
        center: 圆心位置
        radius: 半径
        count: 数量
        min_distance: 最小间距（0 = 不检查）
        height_range: (最低高度, 最高高度)
    """
    spawned_locations = []
    spawned_actors = []
    max_attempts = count * 10

    world = editor_world()
    if world is None:
        unreal.log_error("取不到编辑器 World，随机散布未执行")
        return []

    with editor_transaction("随机散布", world):
        attempts = 0
        while len(spawned_actors) < count and attempts < max_attempts:
            attempts += 1

            # 在圆内均匀随机采样的经典算法：
            # 1. angle 在 0~2π 之间随机（决定方向）
            # 2. dist = radius * sqrt(random) 而不是 radius * random
            #    为什么用 sqrt？因为圆的面积和半径平方成正比
            #    如果直接用 random，点会聚集在圆心附近
            #    用 sqrt 可以让点在整个圆内均匀分布
            angle = random.uniform(0, 2 * math.pi)
            dist = radius * math.sqrt(random.uniform(0, 1))

            x = center.x + dist * math.cos(angle)
            y = center.y + dist * math.sin(angle)
            z = random.uniform(height_range[0], height_range[1])

            location = unreal.Vector(x, y, z)

            # min_distance 可以防止点之间太近（比如避免岩石重叠）
            # 这是一个简单的"排斥"机制，但不是泊松圆盘采样
            if min_distance > 0:
                too_close = False
                for existing in spawned_locations:
                    if (location - existing).length() < min_distance:
                        too_close = True
                        break
                if too_close:
                    continue

            rotation = unreal.Rotator(pitch=0, yaw=random.uniform(0, 360), roll=0)
            actor = spawn_basic_actor(
                actor_class, location, rotation, label=f"Scatter_{len(spawned_actors)}"
            )

            if actor:
                spawned_actors.append(actor)
                spawned_locations.append(location)
    unreal.log(f"在半径 {radius} 区域内散布了 {len(spawned_actors)} 个 Actor")
    return spawned_actors


# ─────────────────────────────────────────────────────────
# 6. 生成带碰撞的触发器
# ─────────────────────────────────────────────────────────


def spawn_trigger_volume(location, extent, label="TriggerVolume"):
    """生成一个触发器体积"""
    # TriggerBox 是 UE 内置的触发器 Actor
    # 它自带一个 BoxComponent 用于碰撞检测
    actor = spawn_basic_actor(unreal.TriggerBox, location, label=label)

    if actor:
        # BoxComponent 是 TriggerBox 的碰撞组件
        # set_box_extent 设置碰撞盒的半尺寸（从中心到边缘的距离）
        # 比如 extent=100 表示碰撞盒总大小是 200x200x200
        box_comp = actor.get_component_by_class(unreal.BoxComponent.static_class())
        # 同样要收窄类型：桩里返回的是基类 ActorComponent
        if isinstance(box_comp, unreal.BoxComponent):
            box_comp.set_box_extent(unreal.Vector(extent, extent, extent))

    return actor


# ─────────────────────────────────────────────────────────
# 7. 实用：生成灯光阵列
# ─────────────────────────────────────────────────────────


def spawn_light_array(center, radius, count, height=300.0, intensity=5000.0):
    """在圆形区域生成灯光阵列"""
    spawned = []
    # 【易错点】count 为 0 时 360.0 / count 会抛 ZeroDivisionError，
    #   先挡掉非法输入，返回空列表并说明原因。
    if count <= 0:
        unreal.log_error(f"灯光数量必须大于 0（收到 count={count}）")
        return []

    # 360度除以灯光数量，得到每个灯光之间的角度间隔
    angle_step = 360.0 / count

    world = editor_world()
    if world is None:
        unreal.log_error("取不到编辑器 World，灯光阵列未执行")
        return []

    with editor_transaction("生成灯光阵列", world):
        for i in range(count):
            # math.radians 将角度转为弧度（UE的三角函数用弧度制）
            angle = math.radians(i * angle_step)
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = center.z + height

            # PointLight 是点光源 Actor，会向四周均匀发光
            # spawn_actor_from_class 的 actor_class 参数要「类对象」，故用 .static_class()
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight.static_class(),
                unreal.Vector(x, y, z),
            )

            if actor:
                actor.set_actor_label(f"Light_{i}")
                # PointLightComponent 是点光源的核心组件
                # set_intensity 设置光照强度（单位：流明）
                # 数值越大越亮，典型室内灯 500-2000，阳光 10000+
                light_comp = actor.get_component_by_class(
                    unreal.PointLightComponent.static_class()
                )
                # 同样要收窄类型：桩里返回的是基类 ActorComponent
                if isinstance(light_comp, unreal.PointLightComponent):
                    light_comp.set_intensity(intensity)
                spawned.append(actor)
    unreal.log(f"已生成 {len(spawned)} 个点光源")
    return spawned


# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 示例1: 生成单个 Actor
# spawn_basic_actor(
#     unreal.StaticMeshActor,
#     unreal.Vector(0, 0, 100),
#     label="MyFirstActor"
# )

# 示例2: 生成 5x5 网格
# spawn_grid(unreal.StaticMeshActor, 5, 5, 200.0)

# 示例3: 随机散布
# spawn_in_area(
#     unreal.StaticMeshActor,
#     unreal.Vector(0, 0, 0),
#     1000.0, 20,
#     min_distance=100.0
# )

# 示例4: 灯光阵列
# spawn_light_array(unreal.Vector(0, 0, 0), 500.0, 8)

unreal.log("关卡与Actor第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 【练习 1】沿螺旋线生成 Actor
#   输入： 起点 Vector(0,0,0)、圈数 turns=3、每圈半径增量 radius_step=200.0、
#          总数 count=60
#   任务： 第 i 个点：角度 = i * (turns*360/count) 度，
#          半径 = i * (turns*radius_step/count)，
#          x = 半径*cos(角度)、y = 半径*sin(角度)、z 恒为起点 Z
#          （i 从 0 数到 count-1，所以首点落在圆心、末点半径 = turns*radius_step - 一档）
#   输出： 视口里一条由 count 个 Actor 组成的螺旋线
#   验收： count=60、turns=3、radius_step=200 → 相邻两点半径差恰好 10.0；
#          末点（i=59）的水平半径 = 59*10 = 590.0（用 Vector.length2d() 验证）；
#          相邻两点到圆心的半径差恒定 ⇒ 是等距螺旋，不是越绕越松

# 【练习 2】山坡上的地形装饰器
#   输入： 要用的岩石/树木资产路径、撒点中心 center、半径 radius、
#          总数 count、最小间距 min_distance=200.0
#   任务： 用 spawn_in_area 的思路在圆内随机撒点，但每生成一个点都要和
#          已生成的点比距离（Vector 相减后取 length），小于 min_distance 就重抽，
#          单个点最多重抽 30 次，超了就放弃这个点并计数
#   输出： 圆内 rocks 和 trees 交替分布，任意两棵树的间距 >= 200
#   验收： count=50、radius=500、min_distance=200 → 实际生成数明显小于 50
#          （面积放不下），函数要如实返回「请求 50，实际 16，放弃 34」
#          （UE 5.8 实测 20 个随机种子：放置数 14~18、中位数 16；
#            几何上限 ≈ π·500² / (√3/2·200²) ≈ 22.7，所以 16 已接近饱和）

# 【练习 3】棋盘格（两种网格体交替）
#   输入： rows=8、cols=8、spacing=200.0、两个网格体资产路径 A 和 B
#   任务： 第 (row, col) 个格子，(row+col) 为偶数放 A、奇数放 B；
#          位置 = (col*spacing, row*spacing, 0)；用 load_asset 加载两个网格体，
#          加载失败就整体放弃并报错（不要只放一半）
#   输出： 8x8 黑白相间的棋盘
#   验收： 数一下**主对角线**（row==col）的格子 → 全是同一种网格体
#          （实测 8x8 时 row+col 恒为偶数 → 8 格全 A）；
#          副对角线（row+col==7）也全是同一种，但恒为奇数 → 8 格全 B。
#          所以题目说"对角线同一种"只对**奇数尺寸**的棋盘成立两条对角线同色；
#          8x8 这种偶数尺寸两条对角线颜色相反，别当成 bug 去改代码；
#          把 B 的路径改成不存在的 → 函数一开始就报错，视口里一个都没生成
#          （实测 load_asset 对不存在的路径返回 None，用它判断即可）

# 【练习 4】泊松圆盘采样，让随机分布更自然
#   输入： 半径 radius=1000.0、最小间距 r=200.0
#   任务： 实现 Bridson 算法：随机取一个种子点放进「活跃列表」，
#          每轮从活跃列表随机取一个点，在它周围 [r, 2r] 的环带里抽 30 个候选点，
#          候选点若离所有已有点都 >= r 且落在圆内，就接受并加入活跃列表；
#          30 次都失败就把这个点从活跃列表移除
#   输出： 一大堆点，任意两点间距 >= r，且分布比纯随机均匀得多
#   验收： radius=1000、r=200 → 点数落在 35~65 之间（Bridson 实测中位数约 54，
#          圆面积/12√3·r² ≈ 75 只是渐近上界，达不到），且任意两点间距 >= 200
