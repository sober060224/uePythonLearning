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

    # 设置焦距
    cam_comp.set_current_focal_length(focal_length)

    # 对焦设置
    cam_comp.set_editor_property(
        "current_focus_distance",
        focus_distance
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
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(path)

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
        unreal.EditorLevelLibrary.set_view_mode("Lit")
        # 将编辑器视口对齐到相机位置
        loc = camera.get_actor_location()
        rot = camera.get_actor_rotation()
        unreal.LevelEditorSubsystem().set_level_viewport_camera_info(
            loc, rot
        )
        unreal.log(f"已切换到相机视角: {camera.get_actor_label()}")

def list_cameras_in_level():
    """列出关卡中所有的相机"""
    cameras = unreal.EditorLevelLibrary.get_all_level_actors()
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
