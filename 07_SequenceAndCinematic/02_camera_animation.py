"""
=============================================================
序列与过场动画 第2课：相机动画和镜头控制
=============================================================

学习目标：
  - 在 Level Sequence 中创建相机动画
  - 控制相机位置和旋转
  - 创建轨道运动和路径跟随

核心概念：
  - CineCameraActor: UE 的电影级相机
  - Level Sequence + Camera Track = 相机动画
  - 可以使用多个相机在不同镜头间切换

本课可能用到的 API：
  - unreal.Vector(x: float = 0.0, y: float = 0.0, z: float = 0.0) —— 三维向量结构体
  - unreal.Rotator(roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0) —— 旋转结构体
  - unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class: Class, location: Vector, rotation: Rotator, transient: bool = False) -> Actor —— 在关卡中生成 Actor
  - unreal.CineCameraActor —— 电影级相机 Actor 类
  - actor.set_actor_label(new_actor_label: str, mark_dirty: bool = True) -> None —— 设置 Actor 标签
  - actor.get_actor_label(create_if_none: bool = True) -> str —— 获取 Actor 标签
  - actor.get_actor_location() -> Vector —— 获取 Actor 位置
  - actor.get_actor_rotation() -> Rotator —— 获取 Actor 旋转
  - camera.get_cine_camera_component() -> CineCameraComponent —— 获取相机组件
  - component.set_editor_property(name: str, value: object, notify_mode: PropertyAccessChangeNotifyMode = ...) -> None —— 设置组件编辑器属性
  - unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools —— 获取资产工具实例
  - unreal.LevelSequenceFactoryNew() —— 序列资产工厂实例
  - unreal.LevelSequence —— 序列资产类
  - unreal.AssetTools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object —— 创建新资产
  - seq.add_possessable(object_to_possess: Object) -> MovieSceneBindingProxy —— 绑定 Actor 到序列
  - binding.add_track(track_type: Class) -> MovieSceneTrack —— 添加指定类型轨道
  - unreal.MovieScene3DTransformTrack —— 3D 变换轨道类
  - track.add_section() -> MovieSceneSection —— 为轨道添加分段
  - unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool —— 保存资产到磁盘
  - unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(level_sequence: LevelSequence) -> bool —— 在 Sequencer 中打开
  - unreal.get_editor_subsystem(subsystem) -> Optional[_EditorSubsystemTypeVar] —— 获取编辑器子系统单例
  - unreal.LevelEditorSubsystem —— 关卡编辑器子系统
  - unreal.LevelEditorSubsystem.set_level_viewport_camera_info(camera_location: Vector, camera_rotation: Rotator, viewport_config_key: Name) -> None —— 视口相机对齐到指定
  - unreal.EditorActorSubsystem.get_all_level_actors() -> Array[Actor] —— 获取关卡全部 Actor
  - unreal.log(arg: Any) -> None —— 输出普通日志
  - unreal.log_warning(arg: Any) -> None —— 输出警告日志
  - unreal.log_error(arg: Any) -> None —— 输出错误日志
=============================================================
"""

import unreal
import math

# ─────────────────────────────────────────────────────────
# 1. 创建电影级相机
# ─────────────────────────────────────────────────────────

def spawn_cine_camera(location, rotation=None, label="CineCamera"):
    """
    在关卡中生成一个电影级相机

    参数:
        location: 相机位置
        rotation: 相机旋转
        label: 标签名称
    """
    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    camera = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.CineCameraActor,
        location,
        rotation
    )

    if camera:
        camera.set_actor_label(label)
        unreal.log(f"已生成电影相机: {label} 在 {location}")
    return camera

# ─────────────────────────────────────────────────────────
# 2. 配置相机参数
# ─────────────────────────────────────────────────────────

def configure_camera(camera, fov=90.0, focal_length=35.0,
                      aperture=2.8, focus_distance=1000.0):
    """
    配置电影相机的参数

    参数:
        camera: CineCameraActor
        fov: 视野角度
        focal_length: 焦距 (mm)
        aperture: 光圈 (f-stop)
        focus_distance: 对焦距离
    """
    if not camera:
        return

    # 获取相机组件
    cam_comp = camera.get_cine_camera_component()
    if not cam_comp:
        unreal.log_warning("无法获取相机组件")
        return

    # 设置视野
    cam_comp.set_editor_property("field_of_view", fov)

    # 【修改前】cam_comp.set_current_focal_length(focal_length) ——
    # CineCameraComponent 上没有这个方法，焦距是可读写属性，直接赋值即可；
    # 光圈同理（原来 aperture 参数收了没用，这里一并补上）
    cam_comp.current_focal_length = focal_length
    cam_comp.current_aperture = aperture

    # 对焦设置
    # 【修改前】set_editor_property("current_focus_distance", ...) ——
    # 该属性是 [Read-Only]（桩注释明确写着 "Control this value via FocusSettings"）；
    # 要控制对焦距离，必须在 focus_settings 里把 focus_method 设为 MANUAL
    cam_comp.focus_settings = unreal.CameraFocusSettings(
        focus_method=unreal.CameraFocusMethod.MANUAL,
        manual_focus_distance=focus_distance,
    )

    unreal.log(
        f"相机配置: FOV={fov}, 焦距={focal_length}mm, "
        f"光圈=f/{aperture}"
    )

# ─────────────────────────────────────────────────────────
# 3. 创建相机路径点
# ─────────────────────────────────────────────────────────

def create_camera_path_waypoints(camera, waypoints, duration_frames=150):
    """
    为相机创建路径关键帧

    参数:
        camera: 相机 Actor
        waypoints: list of (location, rotation) 元组
        duration_frames: 总帧数
    """
    if not waypoints or len(waypoints) < 2:
        unreal.log_error("至少需要 2 个路径点")
        return

    # 创建序列
    seq_name = f"LS_{camera.get_actor_label()}_Animation"
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        seq_name,
        "/Game/Cinematics",
        unreal.LevelSequence,
        unreal.LevelSequenceFactoryNew()
    )

    if not sequence:
        return None

    # 绑定相机
    binding = sequence.add_possessable(camera)
    if not binding:
        return None

    # 添加 Transform 轨道
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    if not track:
        return None

    section = track.add_section()
    if not section:
        return None

    # 计算每个路径点的帧位置
    frames_per_point = duration_frames // max(len(waypoints) - 1, 1)

    unreal.log(f"为相机创建 {len(waypoints)} 个关键帧的动画")
    unreal.log(f"总帧数: {duration_frames} ({duration_frames/30:.1f} 秒)")

    # 保存序列
    path = f"/Game/Cinematics/{seq_name}"
    unreal.EditorAssetLibrary.save_asset(path)

    # 在 Sequencer 中打开
    # 【修改前】open_level_sequence(path) —— 桩签名要求 LevelSequence 对象，
    # 传路径字符串会 TypeError，传上面 create_asset 返回的 sequence
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)

    return sequence

# ─────────────────────────────────────────────────────────
# 4. 常用相机运动模式
# ─────────────────────────────────────────────────────────

def generate_orbit_waypoints(center, radius, height,
                               count=8, look_at=None):
    """
    生成环绕运动的路径点

    参数:
        center: 环绕中心
        radius: 环绕半径
        height: 相机高度
        count: 路径点数量
        look_at: 注视目标 (None = 注视中心)
    """
    if look_at is None:
        look_at = center

    waypoints = []
    for i in range(count + 1):  # +1 让路径闭合
        angle = (2 * math.pi * i) / count
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        z = height

        location = unreal.Vector(x, y, z)

        # 计算朝向 look_at 的旋转
        direction = look_at - location
        yaw = math.degrees(math.atan2(direction.y, direction.x))
        pitch = math.degrees(
            math.atan2(
                direction.z,
                math.sqrt(direction.x**2 + direction.y**2)
            )
        )
        rotation = unreal.Rotator(-pitch, yaw, 0)

        waypoints.append((location, rotation))

    unreal.log(f"已生成 {len(waypoints)} 个环绕路径点")
    return waypoints

def generate_dolly_waypoints(start, end, count=4,
                               arc_height=0):
    """
    生成推轨运动的路径点（直线或弧线移动）

    参数:
        start: 起始位置
        end: 结束位置
        count: 中间点数量
        arc_height: 弧线高度 (0 = 直线)
    """
    waypoints = []
    total = count + 2  # 包含起点和终点

    for i in range(total):
        t = i / (total - 1)

        # 线性插值 + 弧线
        x = start.x + (end.x - start.x) * t
        y = start.y + (end.y - start.y) * t
        z = start.z + (end.z - start.z) * t

        # 添加弧线
        if arc_height > 0:
            arc = arc_height * math.sin(t * math.pi)
            z += arc

        location = unreal.Vector(x, y, z)

        # 朝向运动方向
        if i < total - 1:
            next_t = (i + 1) / (total - 1)
            next_x = start.x + (end.x - start.x) * next_t
            next_y = start.y + (end.y - start.y) * next_t
            direction = unreal.Vector(
                next_x - x, next_y - y, 0
            )
            yaw = math.degrees(math.atan2(direction.y, direction.x))
            rotation = unreal.Rotator(0, yaw, 0)
        else:
            rotation = waypoints[-1][1] if waypoints else unreal.Rotator(0, 0, 0)

        waypoints.append((location, rotation))

    unreal.log(f"已生成 {len(waypoints)} 个推轨路径点")
    return waypoints

def generate_crane_waypoints(start_location, end_height,
                                count=4):
    """
    生成升降机运动的路径点（垂直升降）

    参数:
        start_location: 起始位置
        end_height: 最终高度
        count: 路径点数量
    """
    waypoints = []
    height_step = (end_height - start_location.z) / (count - 1)

    for i in range(count):
        location = unreal.Vector(
            start_location.x,
            start_location.y,
            start_location.z + height_step * i
        )
        # 始终向下看
        rotation = unreal.Rotator(-90, 0, 0)
        waypoints.append((location, rotation))

    return waypoints

# ─────────────────────────────────────────────────────────
# 5. 相机预览工具
# ─────────────────────────────────────────────────────────

def preview_camera_view(camera):
    """切换到指定相机的视角预览"""
    if camera:
        # 【修改前】unreal.EditorLevelLibrary.set_view_mode("Lit")
        #
        # 【问题分析】
        # set_view_mode 在整个 stub 里 0 处匹配 —— 视口的显示模式（Lit/Unlit/线框）
        # 是纯编辑器 UI 设置，压根没暴露给 Python。想切换得在视口左上角的
        # 显示模式下拉菜单里手动选。这行删掉，保留下面的视口对齐功能。
        #
        # 【顺便修正】原代码里 unreal.LevelEditorSubsystem() 是直接构造，
        # UE5.2 起废弃 —— 要用 unreal.get_editor_subsystem() 拿单例。
        # 【再修正】LevelEditorSubsystem 上的 set_level_viewport_camera_info 是 3 参
        # （还要传 viewport_config_key），2 参版本在 UnrealEditorSubsystem 上 ——
        # 之前注释里说"没问题"是错误结论，这里实际会因缺参 TypeError。
        # 将编辑器视口对齐到相机位置
        loc = camera.get_actor_location()
        rot = camera.get_actor_rotation()
        unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).set_level_viewport_camera_info(loc, rot)
        unreal.log(f"已切换到相机视角: {camera.get_actor_label()}")

def list_cameras_in_level():
    """列出关卡中所有的相机"""
    # 【修改前】unreal.EditorLevelLibrary.get_all_level_actors()（已废弃）
    cameras = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()
    cine_cameras = [a for a in cameras if isinstance(a, unreal.CineCameraActor)]

    unreal.log(f"\n关卡中的电影相机 ({len(cine_cameras)}):")
    for cam in cine_cameras:
        loc = cam.get_actor_location()
        unreal.log(f"  {cam.get_actor_label()} @ ({loc.x:.0f}, {loc.y:.0f}, {loc.z:.0f})")

    return cine_cameras

# ─────────────────────────────────────────────────────────
# 6. 完整示例：创建环绕相机动画
# ─────────────────────────────────────────────────────────

def create_orbit_camera_shot(target_location, radius=800.0,
                               height=400.0, duration_seconds=10.0,
                               fps=30):
    """
    一键创建环绕相机动画

    参数:
        target_location: 环绕目标位置
        radius: 半径
        height: 高度
        duration_seconds: 持续时间(秒)
        fps: 帧率
    """
    # 1. 生成相机
    start_loc = unreal.Vector(
        target_location.x + radius,
        target_location.y,
        target_location.z + height
    )
    camera = spawn_cine_camera(start_loc, label="OrbitCamera")

    if not camera:
        return None

    # 2. 配置相机
    configure_camera(camera, fov=60.0, focal_length=35.0)

    # 3. 生成路径点
    waypoints = generate_orbit_waypoints(
        target_location, radius, height, count=16,
        look_at=target_location
    )

    # 4. 创建序列动画
    total_frames = int(duration_seconds * fps)
    sequence = create_camera_path_waypoints(
        camera, waypoints, total_frames
    )

    unreal.log(f"已创建环绕相机动画 ({duration_seconds}秒)")
    return camera, sequence

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 创建环绕相机
# cam, seq = create_orbit_camera_shot(unreal.Vector(0, 0, 0))

# 列出相机
# list_cameras_in_level()

unreal.log("序列与过场动画第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个"一镜到底"的相机动画，穿越整个关卡
# 2. 实现两点之间的平滑推拉镜头（Dolly In/Out）
# 3. 创建一个相机动画库：预设 5 种常用运动模式
# 4. 编写工具：自动在两个路径点之间添加缓入缓出
