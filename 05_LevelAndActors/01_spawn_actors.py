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

本课可能用到的 API：
  - unreal.EditorLevelLibrary.get_editor_world(cls) -> World —— 获取编辑器世界
  - unreal.EditorLevelLibrary.spawn_actor_from_class(cls, actor_class: Class, location: Vector, rotation: Rotator = [0.000000, 0.000000, 0.000000], transient: bool = False) -> Actor —— 生成 Actor
  - unreal.EditorAssetLibrary.load_asset(cls, asset_path: str) -> Object —— 加载资产
  - unreal.EditorAssetLibrary.load_blueprint_class(cls, asset_path: str) -> Class —— 加载蓝图类
  - unreal.ScopedSlowTask(work: float, desc: Union[Text, str] = "", enabled: bool = True) —— 创建慢速任务
  - task.make_dialog(can_cancel: bool = False, allow_in_pie: bool = False) -> None —— 显示进度对话框
  - task.enter_progress_frame(work: float = 1.0, desc: Union[Text, str] = "") -> None —— 推进进度
  - task.should_cancel() -> bool —— 是否请求取消
  - unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int —— 开启事务
  - unreal.SystemLibrary.end_transaction() -> int —— 结束事务
  - actor.set_actor_label(new_actor_label: str, mark_dirty: bool = True) -> None —— 设置 Actor 名称
  - mesh_comp.set_static_mesh(new_mesh: StaticMesh) -> bool —— 设置网格体
  - box_comp.set_box_extent(box_extent: Vector, update_overlaps: bool = True) -> None —— 设置碰撞盒范围
  - light_comp.set_intensity(new_intensity: float) -> None —— 设置灯光强度
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
    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class,
        location,
        rotation
    )

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
    bp_class = unreal.EditorAssetLibrary.load_blueprint_class(blueprint_path)
    if not bp_class:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

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
    if start_location is None:
        start_location = unreal.Vector(0, 0, 0)

    total = rows * cols
    spawned = []

    task = unreal.ScopedSlowTask(total, "生成网格 Actor...")
    task.make_dialog(True)

    # 【修改前】unreal.Transactions.begin_transaction("生成网格")
    #
    # 【问题分析】
    # unreal.Transactions 这个类在 stub 里不存在 —— 事务方法其实在 SystemLibrary 上，
    # 而且签名不同：begin_transaction(context, description, primary_object) -> int
    #   - context：一般写脚本/工具名
    #   - description：操作描述，会出现在编辑器撤销历史里
    #   - primary_object：被修改的主对象。生成类操作开始时 Actor 还不存在，
    #     拿编辑器 world 顶上即可（World 也是 UObject）
    # 本文件 4 个生成函数原来全是这种错误写法，下面不再重复解释。
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "生成网格", world)

    for row in range(rows):
        for col in range(cols):
            if task.should_cancel():
                break

            task.enter_progress_frame(1.0)

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

            # 设置网格体
            if actor and mesh_path:
                mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
                if mesh:
                    mesh_comp = actor.get_component_by_class(
                        unreal.StaticMeshComponent
                    )
                    if mesh_comp:
                        mesh_comp.set_static_mesh(mesh)

            spawned.append(actor)

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
    if len(points) < 2:
        unreal.log_error("至少需要 2 个路径点")
        return []

    spawned = []
    # 【修改前】unreal.Transactions.begin_transaction("沿路径生成")
    # （Transactions 类不存在，正确用法见上面"生成网格"处的注释）
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "沿路径生成", world)

    for i in range(count):
        # 计算路径上的位置（均匀分布）
        t = i / max(count - 1, 1)
        total_length = 0

        # 计算总路径长度
        segments = []
        for j in range(len(points) - 1):
            seg_len = (points[j+1] - points[j]).length()
            segments.append(seg_len)
            total_length += seg_len

        # 找到对应的位置
        target_dist = t * total_length
        current_dist = 0

        for j, seg_len in enumerate(segments):
            if current_dist + seg_len >= target_dist:
                local_t = (target_dist - current_dist) / seg_len
                location = (
                    points[j] * (1 - local_t) +
                    points[j+1] * local_t
                )

                # 计算朝向
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

    # 【修改前】unreal.Transactions.begin_transaction("随机散布")
    # （Transactions 类不存在，正确用法见上面"生成网格"处的注释）
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "随机散布", world)

    attempts = 0
    while len(spawned_actors) < count and attempts < max_attempts:
        attempts += 1

        # 随机位置（在圆内）
        angle = random.uniform(0, 2 * math.pi)
        dist = radius * math.sqrt(random.uniform(0, 1))

        x = center.x + dist * math.cos(angle)
        y = center.y + dist * math.sin(angle)
        z = random.uniform(height_range[0], height_range[1])

        location = unreal.Vector(x, y, z)

        # 检查最小距离
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
    actor = spawn_basic_actor(
        unreal.TriggerBox,
        location,
        label=label
    )

    if actor:
        # 设置碰撞范围
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
    angle_step = 360.0 / count

    # 【修改前】unreal.Transactions.begin_transaction("生成灯光阵列")
    # （Transactions 类不存在，正确用法见上面"生成网格"处的注释）
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    token = unreal.SystemLibrary.begin_transaction("Python脚本", "生成灯光阵列", world)

    for i in range(count):
        angle = math.radians(i * angle_step)
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        z = center.z + height

        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PointLight,
            unreal.Vector(x, y, z)
        )

        if actor:
            actor.set_actor_label(f"Light_{i}")
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
