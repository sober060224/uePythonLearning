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
  - unreal.EditorLevelLibrary.spawn_actor_from_class(cls, actor_class, location, rotation, transient) -> Actor —— 在关卡中生成 Actor
  - unreal.EditorAssetLibrary.load_blueprint_class(cls, asset_path) -> Class —— 加载蓝图类（练习3棋盘格需要交替两种网格体）
  - unreal.EditorAssetLibrary.load_asset(cls, asset_path) -> Object —— 加载资产（练习2地形装饰器需要加载岩石/树木资产）
  - unreal.Vector.length(self) -> float —— 向量长度（练习4泊松圆盘采样需要计算点间距离）
  - unreal.Vector.__sub__(self, other) -> Vector —— 向量相减（练习4泊松圆盘采样需要计算两点间距）
  - unreal.EditorLevelLibrary.get_all_level_actors(cls) -> Array[Actor] —— 获取所有 Actor（练习2、4需要检查已放置的 Actor）
  - math.radians(x) -> float / math.cos(x) -> float / math.sin(x) -> float —— 三角函数（练习1螺旋路径需要数学计算）
=============================================================
"""

import unreal
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
    # Rotator 是 UE 中表示旋转的结构体，参数为 (Pitch, Yaw, Roll)
    # Pitch = 绕X轴旋转（俯仰），Yaw = 绕Z轴旋转（偏航），Roll = 绕Y轴旋转（翻滚）
    # 如果不传 rotation，默认生成一个无旋转的 Actor
    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    # spawn_actor_from_class 是编辑器专用的生成方法
    # 它会在当前编辑器关卡中创建一个新 Actor 实例
    # 注意：这只是编辑器操作，不是运行时的 SpawnActor
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class,
        location,
        rotation
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

def spawn_blueprint_actor(blueprint_path, location,
                           rotation=None, label=None):
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
        bp_class,
        location,
        rotation
    )

    if actor and label:
        actor.set_actor_label(label)

    return actor

# ─────────────────────────────────────────────────────────
# 3. 批量生成 - 网格排列
# ─────────────────────────────────────────────────────────

def spawn_grid(actor_class, rows, cols, spacing,
               start_location=None, mesh_path=None):
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
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "生成网格", world)

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
                start_location.z
            )

            actor = spawn_basic_actor(
                actor_class,
                location,
                label=f"Grid_R{row}_C{col}"
            )

            # 如果指定了网格体路径，就给生成的 Actor 设置网格体
            # Actor 本身只是一个"容器"，真正显示 3D 模型的是它的 StaticMeshComponent
            if actor and mesh_path:
                mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
                if mesh:
                    # get_component_by_class 获取 Actor 上指定类型的组件
                    # StaticMeshComponent 是负责渲染静态网格体的组件
                    mesh_comp = actor.get_component_by_class(
                        unreal.StaticMeshComponent
                    )
                    if mesh_comp:
                        # set_static_mesh 把加载的网格体资产赋给组件
                        # 这就像给 Actor "穿上"一个 3D 模型
                        mesh_comp.set_static_mesh(mesh)

            spawned.append(actor)

    # 结束事务——到这里为止的所有操作会被打包成一个"可撤销"的整体
    unreal.SystemLibrary.end_transaction()
    unreal.log(f"已生成 {len(spawned)} 个 Actor ({rows}x{cols} 网格)")
    return spawned

# ─────────────────────────────────────────────────────────
# 4. 沿路径生成 Actor
# ─────────────────────────────────────────────────────────

def spawn_along_path(actor_class, points, count,
                      randomize_rotation=False):
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
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "沿路径生成", world)

    for i in range(count):
        # t 是 0~1 之间的归一化参数，表示在整条路径上的百分比位置
        # 比如 count=10 时，i=0 得 t=0（起点），i=9 得 t=1（终点）
        t = i / max(count - 1, 1)
        total_length = 0

        # 先计算每段路径的长度，累加得到总长度
        # Vector 相减可以得到两点间的向量，.length() 得到向量长度
        segments = []
        for j in range(len(points) - 1):
            seg_len = (points[j+1] - points[j]).length()
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
                location = (
                    points[j] * (1 - local_t) +
                    points[j+1] * local_t
                )

                # 计算朝向：用 atan2 算出方向向量的角度
                # atan2 返回弧度，用 math.degrees 转换为角度
                # 这样 Actor 会面朝路径的前进方向
                direction = points[j+1] - points[j]
                yaw = math.degrees(math.atan2(direction.y, direction.x))
                rotation = unreal.Rotator(
                    0,
                    yaw + (random.uniform(0, 360) if randomize_rotation else 0),
                    0
                )

                actor = spawn_basic_actor(
                    actor_class, location, rotation,
                    label=f"Path_{i}"
                )
                spawned.append(actor)
                break

            current_dist += seg_len

    unreal.SystemLibrary.end_transaction()
    unreal.log(f"沿路径生成了 {len(spawned)} 个 Actor")
    return spawned

# ─────────────────────────────────────────────────────────
# 5. 在区域中随机散布
# ─────────────────────────────────────────────────────────

def spawn_in_area(actor_class, center, radius, count,
                   min_distance=0, height_range=(0, 0)):
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

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "随机散布", world)

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

        rotation = unreal.Rotator(0, random.uniform(0, 360), 0)
        actor = spawn_basic_actor(
            actor_class, location, rotation,
            label=f"Scatter_{len(spawned_actors)}"
        )

        if actor:
            spawned_actors.append(actor)
            spawned_locations.append(location)

    unreal.SystemLibrary.end_transaction()
    unreal.log(
        f"在半径 {radius} 区域内散布了 {len(spawned_actors)} 个 Actor"
    )
    return spawned_actors

# ─────────────────────────────────────────────────────────
# 6. 生成带碰撞的触发器
# ─────────────────────────────────────────────────────────

def spawn_trigger_volume(location, extent, label="TriggerVolume"):
    """生成一个触发器体积"""
    # TriggerBox 是 UE 内置的触发器 Actor
    # 它自带一个 BoxComponent 用于碰撞检测
    actor = spawn_basic_actor(
        unreal.TriggerBox,
        location,
        label=label
    )

    if actor:
        # BoxComponent 是 TriggerBox 的碰撞组件
        # set_box_extent 设置碰撞盒的半尺寸（从中心到边缘的距离）
        # 比如 extent=100 表示碰撞盒总大小是 200x200x200
        box_comp = actor.get_component_by_class(
            unreal.BoxComponent
        )
        if box_comp:
            box_comp.set_box_extent(unreal.Vector(extent, extent, extent))

    return actor

# ─────────────────────────────────────────────────────────
# 7. 实用：生成灯光阵列
# ─────────────────────────────────────────────────────────

def spawn_light_array(center, radius, count, height=300.0,
                       intensity=5000.0):
    """在圆形区域生成灯光阵列"""
    spawned = []
    # 360度除以灯光数量，得到每个灯光之间的角度间隔
    angle_step = 360.0 / count

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "生成灯光阵列", world)

    for i in range(count):
        # math.radians 将角度转为弧度（UE的三角函数用弧度制）
        angle = math.radians(i * angle_step)
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        z = center.z + height

        # PointLight 是点光源 Actor，会向四周均匀发光
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PointLight,
            unreal.Vector(x, y, z)
        )

        if actor:
            actor.set_actor_label(f"Light_{i}")
            # PointLightComponent 是点光源的核心组件
            # set_intensity 设置光照强度（单位：流明）
            # 数值越大越亮，典型室内灯 500-2000，阳光 10000+
            light_comp = actor.get_component_by_class(
                unreal.PointLightComponent
            )
            if light_comp:
                light_comp.set_intensity(intensity)
            spawned.append(actor)

    unreal.SystemLibrary.end_transaction()
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
# 1. 沿螺旋路径生成 Actor
# 2. 创建一个 "地形装饰器"：在山坡上随机放置岩石和树木
# 3. 生成一个棋盘格图案（交替使用两种网格体）
# 4. 实现泊松圆盘采样算法来获得更自然的随机分布
