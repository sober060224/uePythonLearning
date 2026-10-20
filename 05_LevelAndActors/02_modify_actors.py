"""
=============================================================
关卡与Actor 第2课：修改 Actor 属性和变换
=============================================================

学习目标：
  - 获取和修改 Actor 的变换（位置、旋转、缩放）
  - 操作 Actor 的组件
  - 查找和修改关卡中的现有 Actor

核心 API：
  - actor.get_actor_location() / set_actor_location()
  - actor.get_actor_rotation() / set_actor_rotation()
  - actor.get_actor_scale3d() / set_actor_scale3d()
  - actor.get_component_by_class()
  - actor.set_editor_property()

习题可能用到的 API：
  ── unreal ──
    unreal.EditorLevelLibrary.get_all_level_actors(cls) -> Array[Actor]
        —— 获取所有 Actor（练习1、2、4都需要遍历 Actor）
    actor.get_actor_location() -> Vector / actor.set_actor_location(new_location, sweep, teleport) -> Optional[HitResult]
        —— 位置操作（练习2移动到指定高度）
    actor.get_actor_rotation() -> Rotator / actor.set_actor_rotation(new_rotation, teleport_physics) -> bool
        —— 旋转操作（练习1计算方向需要朝向）
    unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool
        —— 检查资产是否存在（练习4替换蓝图前需验证）
    unreal.EditorActorSubsystem.duplicate_actors(self, actors_to_duplicate, to_world, offset) -> Array[Actor]
        —— 复制 Actor（练习4替换工具需要先复制再删除）
    unreal.EditorLevelLibrary.destroy_actor(cls, actor_to_destroy) -> bool
        —— 销毁 Actor（练习4替换工具需要删除旧 Actor）
    unreal.Vector.__sub__(self, other) -> Vector / unreal.Vector.length(self) -> float
        —— 向量运算（练习1测量距离和方向）
    actor.get_actor_label(create_if_none=True) -> str
        —— 获取 Actor 名称（练习4匹配蓝图名称）
    unreal.MathLibrary.find_look_at_rotation(cls, start: Vector, target: Vector) -> Rotator
        —— 求从 start 看向 target 的朝向（练习1 打方向、练习3 让相机看向目标；桩 377312）
    unreal.EditorLevelLibrary.spawn_actor_from_class(cls, actor_class, location, rotation, transient) -> Actor
        —— 在关卡中生成 Actor（练习3 造相机、练习4 用蓝图 B 的类生成新实例）
    unreal.EditorAssetLibrary.load_blueprint_class(cls, asset_path: str) -> Class
        —— 加载蓝图编译后的类（练习4 先拿到 B 的类才能生成实例）
    actor.get_class() -> Class
        —— 取 Actor 的运行时类（练习4 靠类名判定谁该被替换；记得是 BP_X_C 不是 BP_X）
  ── Python 标准库 ──
    contextlib.contextmanager
        —— 练习4 把整批替换包进一个可撤销事务，异常时自动回滚
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

# ─────────────────────────────────────────────────────────
# 1. 获取关卡中的所有 Actor
# ─────────────────────────────────────────────────────────


def get_all_actors():
    """获取关卡中的所有 Actor"""
    # get_all_level_actors 返回当前关卡中所有 Actor 的列表
    # 这个列表包含所有类型：StaticMeshActor、PointLight、Camera 等
    return unreal.EditorLevelLibrary.get_all_level_actors()


def get_actors_by_class(actor_class):
    """获取指定类型的所有 Actor"""
    all_actors = get_all_actors()
    # isinstance 检查是否是该类或其子类的实例
    # 比如传入 unreal.Actor 会匹配所有 Actor
    # 传入 unreal.StaticMeshActor 只匹配静态网格体 Actor
    return [a for a in all_actors if isinstance(a, actor_class)]


def get_actors_by_label(label_contains):
    """按标签名称搜索 Actor"""
    all_actors = get_all_actors()
    # .lower() 转小写实现不区分大小写的搜索
    # 比如搜 "light" 能匹配 "PointLight_01" 和 "SpotLight_A"
    return [
        a for a in all_actors if label_contains.lower() in a.get_actor_label().lower()
    ]


def find_actor_by_label(label):
    """通过精确标签查找 Actor"""
    all_actors = get_all_actors()
    for actor in all_actors:
        if actor.get_actor_label() == label:
            return actor
    return None


# ─────────────────────────────────────────────────────────
# 2. 变换操作（Transform）
# ─────────────────────────────────────────────────────────


def move_actor(actor, new_location):
    """移动 Actor 到新位置"""
    old_location = actor.get_actor_location()
    # set_actor_location 的参数：
    #   - new_location: 目标位置（世界坐标）
    #   - False (sweep): 是否做扫掠检测（如果 True，碰到东西会停在碰撞点）
    #   - False (teleport): 是否传送（影响物理模拟，设 True 会重置物理速度）
    # 日常编辑器脚本里一般两个都传 False
    actor.set_actor_location(new_location, False, False)
    unreal.log(
        f"移动 {actor.get_actor_label()}: "
        f"({old_location.x:.0f}, {old_location.y:.0f}, {old_location.z:.0f}) "
        f"-> ({new_location.x:.0f}, {new_location.y:.0f}, {new_location.z:.0f})"
    )


def move_actor_relative(actor, offset):
    """相对移动 Actor"""
    # get_actor_location 返回的是世界坐标（不是局部坐标）
    # 所以直接加上偏移量就是在世界空间里移动
    current = actor.get_actor_location()
    new_loc = current + offset
    actor.set_actor_location(new_loc, False, False)


def rotate_actor(actor, new_rotation):
    """设置 Actor 旋转"""
    # set_actor_rotation 的第二个参数 teleport_physics 同样控制物理行为
    actor.set_actor_rotation(new_rotation, False)


def rotate_actor_relative(actor, delta_rotation):
    """相对旋转 Actor"""
    # Rotator 不能直接用 + 号相加（不像 Vector 那样重载了运算符）
    # 所以需要手动把三个分量分别相加
    current = actor.get_actor_rotation()
    # 【易错点】Rotator 位置参数顺序是 (roll, pitch, yaw)，用关键字参数避免串位。
    new_rot = unreal.Rotator(
        pitch=current.pitch + delta_rotation.pitch,
        yaw=current.yaw + delta_rotation.yaw,
        roll=current.roll + delta_rotation.roll,
    )
    actor.set_actor_rotation(new_rot, False)


def scale_actor(actor, new_scale):
    """设置 Actor 缩放"""
    # 支持传入单个数字（等比缩放）或 Vector（非等比缩放）
    # 比如 scale_actor(actor, 2.0) 让 Actor 各方向放大 2 倍
    # scale_actor(actor, Vector(1,1,2)) 只在 Z 轴拉伸
    if isinstance(new_scale, (int, float)):
        new_scale = unreal.Vector(new_scale, new_scale, new_scale)
    actor.set_actor_scale3d(new_scale)


def print_actor_transform(actor):
    """打印 Actor 的变换信息"""
    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()

    label = actor.get_actor_label()
    # f-string 里的 :.1f 表示保留一位小数
    # :.0f 是整数，:.2f 是两位小数
    unreal.log(f"\nActor: {label}")
    unreal.log(f"  位置: ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f})")
    unreal.log(f"  旋转: P={rot.pitch:.1f} Y={rot.yaw:.1f} R={rot.roll:.1f}")
    unreal.log(f"  缩放: ({scale.x:.2f}, {scale.y:.2f}, {scale.z:.2f})")


# ─────────────────────────────────────────────────────────
# 3. 组件操作
# ─────────────────────────────────────────────────────────


def list_actor_components(actor):
    """列出 Actor 的所有组件"""
    # 传入基类 unreal.ActorComponent 会返回所有类型的组件
    # 包括 SceneComponent、StaticMeshComponent、LightComponent 等
    components = actor.get_components_by_class(unreal.ActorComponent)
    label = actor.get_actor_label()

    unreal.log(f"\n{label} 的组件:")
    for comp in components:
        # type(comp).__name__ 获取类名（如 "StaticMeshComponent"）
        # get_name() 获取组件在编辑器里的名字（如 "StaticMeshComponent0"）
        comp_type = type(comp).__name__
        comp_name = comp.get_name()
        unreal.log(f"  [{comp_type}] {comp_name}")

    return components


def set_mesh_on_actor(actor, mesh_path):
    """设置 Actor 的 StaticMeshComponent 的网格体"""
    # EditorAssetLibrary.load_asset 加载内容浏览器中的资产
    # 路径格式："/Game/文件夹/资产名"（不带扩展名）
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not mesh:
        unreal.log_error(f"无法加载网格体: {mesh_path}")
        return False

    # get_component_by_class 只返回第一个匹配的组件
    # 如果 Actor 有多个 StaticMeshComponent，只会拿到第一个
    # 需要多个组件时用 get_components_by_class（注意是复数）
    mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if mesh_comp:
        mesh_comp.set_static_mesh(mesh)
        unreal.log(f"已设置网格体: {mesh_path}")
        return True
    else:
        unreal.log_warning("Actor 没有 StaticMeshComponent")
        return False


def set_material_on_actor(actor, material_path, element_index=0):
    """设置 Actor 网格体上的材质"""
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material:
        unreal.log_error(f"无法加载材质: {material_path}")
        return False

    mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if mesh_comp:
        # element_index 对应网格体的材质槽位（Material Slot）
        # 大多数简单网格体只有 1 个槽位（index=0）
        # 复杂模型可能有多个槽位，可以给不同部位贴不同材质
        mesh_comp.set_material(element_index, material)
        unreal.log(f"已设置材质 (元素 {element_index}): {material_path}")
        return True
    return False


# ─────────────────────────────────────────────────────────
# 4. 批量修改工具
# ─────────────────────────────────────────────────────────


def batch_move_actors(actors, offset):
    """批量移动一组 Actor"""
    # 【修改前】unreal.Transactions.begin_transaction("批量移动")
    #           unreal.Transactions.end_transaction()
    #
    # 【问题分析】
    # unreal.Transactions 类在 stub 里不存在 —— 事务方法在 SystemLibrary 上，
    # 且签名不同：begin_transaction(context, description, primary_object) -> int
    #   primary_object 是"被修改的主对象"（撤销历史里的锚点），传第一个 Actor；
    #   列表为空时没有 Actor 可传，就拿编辑器 world 顶上（World 也是 UObject）。
    if actors:
        primary = actors[0]
    else:
        primary = editor_world()
        if primary is None:
            unreal.log_error("没有 Actor 可传，也取不到编辑器 World，批量移动未执行")
            return
    with editor_transaction("批量移动", primary):
        for actor in actors:
            move_actor_relative(actor, offset)
    unreal.log(f"已移动 {len(actors)} 个 Actor")


def batch_scale_actors(actors, scale_factor):
    """批量缩放一组 Actor"""
    # 【修改前】unreal.Transactions.begin_transaction("批量缩放")
    # （Transactions 类不存在，正确用法见上面 batch_move_actors 的注释）
    if actors:
        primary = actors[0]
    else:
        primary = editor_world()
        if primary is None:
            unreal.log_error("没有 Actor 可传，也取不到编辑器 World，批量缩放未执行")
            return
    with editor_transaction("批量缩放", primary):
        for actor in actors:
            current_scale = actor.get_actor_scale3d()
            new_scale = unreal.Vector(
                current_scale.x * scale_factor,
                current_scale.y * scale_factor,
                current_scale.z * scale_factor,
            )
            actor.set_actor_scale3d(new_scale)
    unreal.log(f"已缩放 {len(actors)} 个 Actor (倍率: {scale_factor})")


def batch_set_material(actors, material_path):
    """批量设置材质"""
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material:
        unreal.log_error(f"无法加载材质: {material_path}")
        return

    count = 0
    for actor in actors:
        mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp:
            # 材质只需加载一次（在循环外），然后批量赋给所有 Actor
            # 如果放在循环里每次都 load_asset 会非常慢
            mesh_comp.set_material(0, material)
            count += 1

    unreal.log(f"已为 {count} 个 Actor 设置材质")


# ─────────────────────────────────────────────────────────
# 5. Actor 分组和标签
# ─────────────────────────────────────────────────────────


def set_actor_folder(actor, folder_path):
    """设置 Actor 的文件夹路径（Outliner 中的分组）"""
    # set_folder_path 控制的是在编辑器 Outliner 面板里的分组
    # 这不是文件系统路径，只是编辑器里的组织方式
    # 比如 "/Game/Props" 会让 Actor 出现在 Outliner 的 Props 文件夹下
    actor.set_folder_path(folder_path)
    unreal.log(f"已设置文件夹: {actor.get_actor_label()} -> {folder_path}")


def organize_actors_into_folders():
    """按类型将关卡中的 Actor 组织到文件夹"""
    all_actors = get_all_actors()

    # 先按类名分组
    type_groups = {}
    for actor in all_actors:
        type_name = type(actor).__name__
        if type_name not in type_groups:
            type_groups[type_name] = []
        type_groups[type_name].append(actor)

    # 然后按类型设置文件夹路径
    for type_name, actors in type_groups.items():
        folder = f"/Game/{type_name}"
        for actor in actors:
            actor.set_folder_path(folder)

        unreal.log(f"  {type_name}: {len(actors)} 个 -> {folder}")


# ─────────────────────────────────────────────────────────
# 6. 复制和删除 Actor
# ─────────────────────────────────────────────────────────


def duplicate_actor(actor, offset=None):
    """复制一个 Actor"""
    # 【修改前】
    # new_actor = unreal.EditorLevelLibrary.duplicate_actor(actor)
    # if new_actor:
    #     loc = actor.get_actor_location() + offset
    #     new_actor.set_actor_location(loc)
    #
    # 【问题分析】
    # EditorLevelLibrary 上根本没有 duplicate_actor 这个方法（stub 里查无此名），
    # 复制 Actor 的 API 在 EditorActorSubsystem 上，而且形态不同：
    #   duplicate_actors(actors_to_duplicate, to_world=None, offset=Vector) -> Array[Actor]
    #   - 传的是"Actor 列表"不是单个 Actor；返回的也是列表
    #   - offset 参数直接就是"复制体相对原位的偏移"，不用再手动 set_actor_location
    if offset is None:
        offset = unreal.Vector(100, 0, 0)

    # get_editor_subsystem 获取编辑器子系统
    # EditorActorSubsystem 提供 Actor 级别的批量操作（复制、对齐等）
    # 返回类型是 Optional，所以必须先判空再用
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if actor_subsystem is None:
        unreal.log_error("取不到 EditorActorSubsystem，复制未执行")
        return None
    # 注意：duplicate_actors 的 actors_to_duplicate 要引擎 Array[Actor]，不是 Python list，
    # 用 unreal.Array.cast 转换；to_world 省略即可（默认复制到当前世界），
    # 显式传 None 会与桩里声明的 World 类型不匹配
    results = actor_subsystem.duplicate_actors(
        unreal.Array.cast(unreal.Actor, [actor]), offset=offset
    )
    new_actor = results[0] if results else None

    if new_actor:
        unreal.log(f"已复制: {actor.get_actor_label()}")
    return new_actor


def delete_actor(actor):
    """删除 Actor"""
    # 先保存名字再删除（删除后就拿不到了）
    label = actor.get_actor_label()
    # 【UE5】EditorLevelLibrary 已废弃，删除 Actor 用 EditorActorSubsystem.destroy_actor
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if actor_subsystem is None:
        unreal.log_error(f"取不到 EditorActorSubsystem，未删除: {label}")
        return False
    actor_subsystem.destroy_actor(actor)
    unreal.log(f"已删除: {label}")
    return True


def delete_actors_by_label(label_contains):
    """删除所有标签包含指定文本的 Actor"""
    # 注意：不能在遍历列表的同时删除元素（会导致索引错乱）
    # 先搜出来，再统一删除
    actors = get_actors_by_label(label_contains)
    count = len(actors)
    editor_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if editor_actors is None:
        unreal.log_error("取不到 EditorActorSubsystem，批量删除未执行")
        return 0
    for actor in actors:
        editor_actors.destroy_actor(actor)
    unreal.log(f"已删除 {count} 个标签包含 '{label_contains}' 的 Actor")
    return count


# ─────────────────────────────────────────────────────────
# 7. 距离和测量工具
# ─────────────────────────────────────────────────────────


def measure_distance(actor1, actor2):
    """测量两个 Actor 之间的距离"""
    loc1 = actor1.get_actor_location()
    loc2 = actor2.get_actor_location()
    # Vector 相减得到两点之间的向量，.length() 得到距离（单位：厘米）
    # UE 中 1 个单位 = 1 厘米，所以除以 100 得到米
    distance = (loc2 - loc1).length()

    unreal.log(
        f"距离: {actor1.get_actor_label()} <-> "
        f"{actor2.get_actor_label()} = {distance:.1f} 单位 "
        f"({distance / 100:.2f} 米)"
    )
    return distance


def find_nearest_actor(target_actor, candidate_actors):
    """找到离目标最近的 Actor"""
    target_loc = target_actor.get_actor_location()
    nearest = None
    min_dist = float("inf")

    for candidate in candidate_actors:
        if candidate == target_actor:
            continue
        # 每次计算候选 Actor 到目标的距离，保留最小的那个
        dist = (candidate.get_actor_location() - target_loc).length()
        if dist < min_dist:
            min_dist = dist
            nearest = candidate

    if nearest:
        unreal.log(f"最近的 Actor: {nearest.get_actor_label()} (距离: {min_dist:.1f})")
    return nearest, min_dist


# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 打印所有 Actor 的变换信息
# for actor in get_all_actors()[:5]:
#     print_actor_transform(actor)

# 按类型组织到文件夹
# organize_actors_into_folders()

unreal.log("关卡与Actor第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 【练习 1】选中两个 Actor，报告距离和方向
#   输入： 视口中恰好 2 个 Actor；少于或多于 2 个都提示后退出，不要偷偷取前两个
#   任务： 距离用 Vector 相减后取 length()（三维），
#          方向用 unreal.MathLibrary.find_look_at_rotation(起点, 终点) 得到 Rotator，
#          把 Yaw 单独打出来；不修改任何东西，所以不需要事务
#          其中俯仰角单独算：pitch = atan2(B.z-A.z, XY 平面距离)，或在关卡里
#          放一个临时 Actor、用 look_at 指向 B，再读它的 rotation
#   输出： 「A -> B 距离 500.0 cm，朝向 Yaw=90.0 度，俯仰 30.96 度」
#   验收： A 在 (0,0,0)、B 在 (0,500,0) → 距离 500.0、Yaw 90.0、Pitch 0；
#          B 改成 (0,500,300) → 距离 583.1（三维）、Yaw 仍是 90.0、Pitch 30.96；
#          若只打印 Yaw，B 抬高后你看不出变化，题目要求俯仰角就是为了让它暴露出来
#          （UE 5.8 编辑器实测：A(0,0,0)→B(0,500,300) 三维距离 583.0952、平面 500.0、
#            Yaw 90.0、Pitch 30.9638；B 在 (0,500,0) 时 Pitch 为 0）

# 【练习 2】批量把选中的 Actor 抬到同一高度
#   输入： 选中的 N 个 Actor、目标高度 target_z（默认 200.0）
#   任务： 保持每个 Actor 的 X/Y 不变，只把 Z 改成 target_z；
#          整段包在 editor_transaction 里，每个 Actor 改之前 transact_object
#   输出： 所有选中的 Actor 的定位点齐平在 Z=200 的平面上
#   验收： 选 5 个高低不一的 Actor → 跑完后它们的 get_actor_location().z 全是 200.0，
#          X/Y 一个都没变；Ctrl+Z 一次全部回原位

# 【练习 3】场景截图工具：在目标周围自动摆相机位置
#   输入： 1 个目标 Actor、相机数量 shots=8、距离 distance=800.0、高度 height=400.0
#   任务： 以目标位置为圆心，第 i 个相机放在
#          (目标X + distance*cos(i*360/shots), 目标Y + distance*sin(...), 目标Z + height)，
#          朝向用 find_look_at_rotation(相机位置, 目标位置) 让它看向目标；
#          用 spawn_actor_from_class(unreal.CineCameraActor.static_class(), ...) 生成
#          标签统一成 f"CAM_{i:02d}"
#   输出： 目标周围一圈 8 台相机，每台都对着目标
#   验收： shots=8 → 8 台相机均布（相邻夹角 45 度），且 Yaw 呈
#          Yaw = (θ + 180) mod 360 再归一化到 (-180, 180]（θ 是该相机所在的方位角）：
#            θ=0 → Yaw 180；θ=45 → Yaw -135；θ=90 → Yaw -90；θ=180 → Yaw 0；
#          不是 Yaw = θ —— 相机在圆周上，要「朝里看」目标，方向必然与方位角相反。
#          同时 8 台相机的 Pitch 都应为 -26.57 度（= -atan2(400, 800)），
#          因为相机比目标高 400、水平距 800，必须俯视；Pitch=0 说明朝向算错了

# 【练习 4】用蓝图 B 替换所有蓝图 A 的实例
#   输入： 两个蓝图资产路径 A 和 B
#   任务： 遍历 get_all_actors()，用 actor.get_class().get_name() 对比
#          A 编译后的类名（注意是 A_C 这种带 _C 后缀的名字，不是资产名），
#          命中就在同一位置同一旋转生成 B 的实例，再删掉旧 Actor；
#          整个过程包在一个事务里，这样 Ctrl+Z 能一次还原
#   输出： 关卡里 A 的实例全部变成 B，位置/旋转/标签保持原样
#   验收： 放 3 个 A、跑一次 → 3 个 A 全没了、3 个 B 出现在原位置；
#          按一次 Ctrl+Z → 3 个 A 回来、3 个 B 消失。
#          实测 _C 后缀确实存在：资产 /Game/.../BP_Cannon 编译出的类名是
#          "BP_Cannon_C"，spawn 之后 actor.get_class().get_name() 也是 "BP_Cannon_C"；
#          拿资产名（不带 _C）去比会一个都匹配不上 —— 这是本题最大的坑。
#          用 load_blueprint_class(路径) 直接拿这个类，别自己拼 "_C" 字符串
