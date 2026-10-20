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

习题可能用到的 API：
  ── unreal ──
    unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, location, rotation) -> Actor
        —— 已废弃的生成写法（桩里还在；新代码用 EditorActorSubsystem 同名方法）
    unreal.CineCameraActor - 电影级相机 Actor 类
        —— 带焦距/光圈等电影参数的相机（练习1/2 的拍摄主体）
    camera.get_cine_camera_component() -> CineCameraComponent
        —— 取相机组件，改焦距/光圈走它（练习2 dolly 时调当前焦距）
    unreal.EditorAssetLibrary.save_asset(asset_to_save: str) -> bool
        —— 保存资产（序列建完必须保存才落盘）
    unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object
        —— 按路径加载资产（练习1/3 取序列与相机）
    unreal.EditorAssetLibrary.list_assets(directory_path, recursive, include_folder) -> Array[str]
        —— 列目录下的资产路径（练习3 找相机、练习4 找序列）
    unreal.EditorActorSubsystem.get_all_level_actors() -> Array[Actor]
        —— 取全部 Actor（练习1 挑拍摄主体、练习3 选路径 actor）
    unreal.get_editor_subsystem(subsystem) -> Optional
        —— 取编辑器子系统；返回 Optional，必须先判空再调方法
    unreal.MathLibrary.find_look_at_rotation(cls, start: Vector, target: Vector) -> Rotator
        —— 让相机始终看向目标（练习1、2 的核心；桩 377312）
    unreal.MovieSceneTrack.add_section() -> MovieSceneSection
        —— 轨道建好后必须 add_section()，否则 get_all_channels() 永远是 0 条
           （实测：实例方法 track.add_section() 与静态方法
           MovieSceneTrackExtensions.add_section(track) 都可用，
           都返回 MovieScene3DTransformSection）
    unreal.MovieSceneSectionExtensions.get_all_channels(section: MovieSceneSection) -> Array[MovieSceneScriptingChannel]
        —— 取 Section 上全部通道。Transform 轨道会给出 9 条，名字形如
           "Location.X_0" / "Rotation.Z_0" / "Scale.Y_0"（编辑器实测；练习2/4）
    unreal.MovieSceneSectionExtensions.get_channels_by_type(section: MovieSceneSection, channel_type: Class) -> Array[MovieSceneScriptingChannel]
        —— 按类型筛通道（练习4 只想操作 Location.X 时用）
           get_channel(section, channel_name: Name) -> MovieSceneScriptingChannel
               —— 按名字精确取一条通道
        ★ 注意：**用 FloatChannel 筛 Transform 轨道会得到 0 条**（编辑器实测）。
          Transform 轨道的通道是 MovieSceneScriptingDoubleChannel，
          所以要么用 get_all_channels()，要么筛 DoubleChannel.static_class()。
    unreal.MovieSceneScriptingDoubleChannel.add_key(time: FrameNumber, new_value: float, sub_frame: float = 0.0, time_unit: MovieSceneTimeUnit = DISPLAY_RATE, interpolation: MovieSceneKeyInterpolation = AUTO) -> MovieSceneScriptingDoubleKey
        —— 写关键帧（练习1/2/3/4）。实测 add_key(FrameNumber(0), 0.0) +
           add_key(FrameNumber(90), 500.0) → get_keys() 返回 2 个键，
           get_value() 分别是 0.0 / 500.0，get_time().frame_number.value 是 0 / 90；
           interpolation=MovieSceneKeyInterpolation.LINEAR 写进去后
           get_interpolation_mode() 读回 <RichCurveInterpMode.RCIM_LINEAR: 0>
    unreal.MovieSceneScriptingDoubleKey.set_interpolation_mode(new_value: RichCurveInterpMode) -> None
        —— 改已有键的插值曲线（RCIM_LINEAR / RCIM_CUBIC；桩 478507）
    unreal.MovieSceneScriptingDoubleKey.set_tangent_mode(new_value: RichCurveTangentMode) -> None
        —— 缓入缓出的核心（练习4）。实测 RichCurveTangentMode 只有 4 个成员：
           RCTM_AUTO / RCTM_USER / RCTM_BREAK / RCTM_SMART_AUTO
    unreal.MovieSceneScriptingDoubleKey.set_arrive_tangent(new_value: float) -> None
        —— 设入切线斜率（练习4 缓入缓出，配合 set_arrive_tangent_weight）
    unreal.MovieSceneScriptingDoubleKey.set_leave_tangent(new_value: float) -> None
        —— 缓入的起点 arrive_tangent=0、缓出的终点 leave_tangent=0（练习4）。
           实测都写得进、get_arrive_tangent()/get_leave_tangent() 读回一致
    unreal.MovieSceneScriptingDoubleKey.get_tangent_mode() -> RichCurveTangentMode
        —— 读切线模式（练习4 验收只能靠 getter 读实际状态）
    unreal.MovieSceneScriptingDoubleKey.get_interpolation_mode() -> RichCurveInterpMode
        —— 验收练习4 只能靠这两个 getter 读实际状态，不能看你传了什么
    ★ 实测澄清：unreal.MovieSceneKeyInterpolation 的**全部**成员是
      AUTO / USER / BREAK / LINEAR / CONSTANT / SMART_AUTO —— **没有 EaseIn / EaseOut**；
      RichCurveInterpMode 也只有 RCIM_LINEAR / RCIM_CONSTANT / RCIM_CUBIC。
      「缓入缓出」在 Python 里只能靠上面三个 set_tangent* 实现。
  ── Python 标准库 ──
    math.atan / math.cos / math.sin / math.degrees / math.pi
        —— 练习2 的 arc_height = h*sin(t*pi) 弧线抬升
           （实测 t=0/0.2/0.4/0.6/0.8/1 时 z 偏移 0/117.6/190.2/190.2/117.6/0）
=============================================================
"""

import math

import unreal

# ============================================================
# 1. 创建电影级相机
# ============================================================


def spawn_cine_camera(location, rotation=None, label="CineCamera"):
    """
    在关卡中生成一个电影级相机

    参数:
        location: 相机位置（unreal.Vector）
        rotation: 相机旋转（unreal.Rotator）
        label: 标签名称
    """
    # [UE概念] Rotator 默认是零旋转，表示相机朝向 X 轴正方向
    # UE 中的坐标系：X 前、Y 右、Z 上（左手坐标系）
    if rotation is None:
        rotation = unreal.Rotator(0, 0, 0)

    # [UE概念] spawn_actor_from_class 在编辑器关卡中生成一个 Actor
    # 与运行时 SpawnActor 不同，这是编辑器操作，生成的 Actor 会出现在关卡中
    # CineCameraActor 自带 CineCameraComponent，比普通 Camera 更适合过场动画
    camera = unreal.EditorLevelLibrary.spawn_actor_from_class(
        # actor_class 要「类对象」，所以要 .static_class()
        unreal.CineCameraActor.static_class(),
        location,
        rotation,
    )

    if camera:
        # [UE概念] Actor Label 是编辑器中显示的名称，不影响运行时
        # 它只是方便你在编辑器中识别 Actor，类似于文件的显示名
        camera.set_actor_label(label)
        unreal.log(f"已生成电影相机: {label} 在 {location}")
    return camera


# ============================================================
# 2. 配置相机参数
# ============================================================


def configure_camera(
    camera, fov=90.0, focal_length=35.0, aperture=2.8, focus_distance=1000.0
):
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

    # [UE概念] CineCameraActor 的核心组件是 CineCameraComponent
    # 所有相机参数（FOV、焦距、光圈等）都通过这个组件来设置
    # get_cine_camera_component() 是 CineCameraActor 专有的方法
    cam_comp = camera.get_cine_camera_component()
    if not cam_comp:
        unreal.log_warning("无法获取相机组件")
        return

    # [UE概念] set_editor_property 用于设置组件的编辑器属性
    # field_of_view 是一个浮点数属性，单位是度
    # 注意：FOV 和焦距是联动的——设置其中一个会影响另一个
    cam_comp.set_editor_property("field_of_view", fov)

    # [常见陷阱] 焦距和光圈是可读写属性，直接赋值即可
    # 不要尝试调用 set_current_focal_length()——CineCameraComponent 上没有这个方法
    # 这是新手常犯的错误，会得到 AttributeError
    cam_comp.current_focal_length = focal_length
    cam_comp.current_aperture = aperture

    # [UE概念] 对焦设置比想象的复杂：
    # current_focus_distance 是只读属性，不能直接 set_editor_property
    # 必须通过 focus_settings 结构体来控制对焦
    # 先把 focus_method 设为 MANUAL，再设置 manual_focus_distance
    # 如果用 AUTO 模式，对焦距离由相机自动计算
    cam_comp.focus_settings = unreal.CameraFocusSettings(
        focus_method=unreal.CameraFocusMethod.MANUAL,
        manual_focus_distance=focus_distance,
    )

    unreal.log(f"相机配置: FOV={fov}, 焦距={focal_length}mm, 光圈=f/{aperture}")


# ============================================================
# 3. 创建相机路径点
# ============================================================


def create_camera_path_waypoints(camera, waypoints, duration_frames=150):
    """
    为相机创建路径关键帧

    参数:
        camera: 相机 Actor
        waypoints: list of (location, rotation) 元组
        duration_frames: 总帧数
    """
    # [常见陷阱] 至少需要 2 个路径点——起点和终点
    # 1 个点无法形成有意义的运动
    if not waypoints or len(waypoints) < 2:
        unreal.log_error("至少需要 2 个路径点")
        return

    # 创建序列——用相机标签自动生成序列名，方便管理
    seq_name = f"LS_{camera.get_actor_label()}_Animation"
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        seq_name,
        "/Game/Cinematics",
        unreal.LevelSequence.static_class(),
        unreal.LevelSequenceFactoryNew(),
    )

    # 【为什么用 isinstance 而不是 if not sequence】create_asset 的返回类型在桩里是
    # Object，Object 上没有 add_possessable；isinstance 收窄之后类型才成立，
    # 同时 None（创建失败）也会走进这个分支，一个判断解决两件事。
    # 收窄成 LevelSequence 而不是 MovieSceneSequence：后者是基类，
    # 而后面 open_level_sequence 的参数要求的是 LevelSequence。
    if not isinstance(sequence, unreal.LevelSequence):
        unreal.log_error(f"序列创建失败: {seq_name}")
        return None

    # [核心概念] 把相机绑定到序列的 Possessable
    # Possessable 意味着序列"借用"关卡中的相机，不会自己创建/销毁
    # 绑定成功后返回一个 binding 对象，后续的轨道都挂在 binding 上
    binding = sequence.add_possessable(camera)
    if not binding:
        return None

    # [UE概念] MovieScene3DTransformTrack 控制 Actor 的位移/旋转/缩放
    # 这是相机动画最常用的轨道类型——相机的运动就是 Transform 变化
    # add_track 的 track_type 参数要「类对象」，所以要 .static_class()
    track = binding.add_track(unreal.MovieScene3DTransformTrack.static_class())
    if not track:
        return None

    # [UE概念] Section 是 Track 的时间片段
    # 一个 Track 默认就加一个 Section，它覆盖整个序列的时间范围
    section = track.add_section()
    if not section:
        return None

    # [数学概念] 均匀分配路径点到时间轴上
    # 例如 150 帧放 3 个点，每 75 帧一个关键帧
    frames_per_point = duration_frames // max(len(waypoints) - 1, 1)

    # 【重要】这一步只创建了"轨道 + Section"，还没有写入任何关键帧。
    #   写关键帧的正确顺序（编辑器实测确认）：
    #     channels = MovieSceneSectionExtensions.get_all_channels(section)
    #     loc_x = [c for c in channels if c.get_name().startswith("Location.X")][0]
    #     loc_x.add_key(unreal.FrameNumber(frame), value)
    #   ⚠️ 不要用 get_channels_by_type(..., FloatChannel.static_class()) 来筛 Transform 轨道，
    #   实测返回 0 条 —— 它的通道是 MovieSceneScriptingDoubleChannel。
    #   本课先不写关键帧（练习2/4 会写），所以下面的日志只描述"已经做了什么"，
    #   不假装动画已经生成。
    unreal.log(
        f"已创建相机 Transform 轨道 + Section：{len(waypoints)} 个路径点，间隔 {frames_per_point} 帧"
    )
    unreal.log(f"总帧数: {duration_frames} ({duration_frames / 30:.1f} 秒)")
    unreal.log("【练习】参考文件末尾的说明，把路径点写进关键帧通道")

    # 保存序列资产——序列创建后必须保存才能持久化
    path = f"/Game/Cinematics/{seq_name}"
    unreal.EditorAssetLibrary.save_asset(path)

    # [常见陷阱] open_level_sequence 需要 LevelSequence 对象，不是路径字符串
    # 传字符串会 TypeError——这是新手最常犯的错误之一
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)

    return sequence


# ============================================================
# 4. 常用相机运动模式
# ============================================================


def generate_orbit_waypoints(center, radius, height, count=8, look_at=None):
    """
    生成环绕运动的路径点

    参数:
        center: 环绕中心（unreal.Vector）
        radius: 环绕半径
        height: 相机高度
        count: 路径点数量
        look_at: 注视目标 (None = 注视中心)
    """
    # 默认注视环绕中心——这是最常见的环绕拍摄方式
    if look_at is None:
        look_at = center

    waypoints = []
    # +1 让路径闭合——最后一个点回到起点，形成完整圆环
    # 如果不加 1，最后一段会缺少过渡，相机会突然跳回起点
    for i in range(count + 1):
        # [数学概念] 用三角函数在圆上均匀取点
        # angle 从 0 到 2*PI，cos 算 x、sin 算 y
        angle = (2 * math.pi * i) / count
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        z = height

        location = unreal.Vector(x, y, z)

        # [数学概念] 计算朝向注视点的旋转角度
        # 方向向量 = 目标点 - 当前点
        # atan2(y, x) 得到水平面的角度（yaw）
        # atan2(z, sqrt(x^2+y^2)) 得到俯仰角（pitch）
        direction = look_at - location
        yaw = math.degrees(math.atan2(direction.y, direction.x))
        pitch = math.degrees(
            math.atan2(direction.z, math.sqrt(direction.x**2 + direction.y**2))
        )
        # [UE概念] Rotator(pitch, yaw, roll)——注意顺序是 Pitch 在前
        # pitch 用负值是因为 UE 中正 pitch 是抬头，我们要向下看
        rotation = unreal.Rotator(pitch=-pitch, yaw=yaw, roll=0)

        waypoints.append((location, rotation))

    unreal.log(f"已生成 {len(waypoints)} 个环绕路径点")
    return waypoints


def generate_dolly_waypoints(start, end, count=4, arc_height=0):
    """
    生成推轨运动的路径点（直线或弧线移动）

    参数:
        start: 起始位置
        end: 结束位置
        count: 中间点数量
        arc_height: 弧线高度 (0 = 直线)
    """
    waypoints = []
    # total 包含起点和终点，所以是 count + 2
    total = count + 2

    for i in range(total):
        # [数学概念] t 是 0 到 1 之间的参数，控制插值比例
        # t=0 是起点，t=1 是终点，中间值按比例分布
        t = i / (total - 1)

        # 线性插值：在 start 和 end 之间按比例取点
        x = start.x + (end.x - start.x) * t
        y = start.y + (end.y - start.y) * t
        z = start.z + (end.z - start.z) * t

        # [数学概念] 用正弦函数叠加弧线
        # sin(t * PI) 在 t=0 和 t=1 时为 0，t=0.5 时为 1（最大弧高）
        # 这样弧线从起点平滑上升到最高点，再平滑下降到终点
        if arc_height > 0:
            arc = arc_height * math.sin(t * math.pi)
            z += arc

        location = unreal.Vector(x, y, z)

        # 朝向运动方向——让相机始终"面朝"前进方向
        if i < total - 1:
            next_t = (i + 1) / (total - 1)
            next_x = start.x + (end.x - start.x) * next_t
            next_y = start.y + (end.y - start.y) * next_t
            direction = unreal.Vector(next_x - x, next_y - y, 0)
            yaw = math.degrees(math.atan2(direction.y, direction.x))
            rotation = unreal.Rotator(pitch=0, yaw=yaw, roll=0)
        else:
            # 最后一个点：沿用上一个点的旋转，保持一致
            rotation = waypoints[-1][1] if waypoints else unreal.Rotator(0, 0, 0)

        waypoints.append((location, rotation))

    unreal.log(f"已生成 {len(waypoints)} 个推轨路径点")
    return waypoints


def generate_crane_waypoints(start_location, end_height, count=4):
    """
    生成升降机运动的路径点（垂直升降）

    参数:
        start_location: 起始位置
        end_height: 最终高度
        count: 路径点数量
    """
    waypoints = []
    # 均匀分配高度变化——每一步上升相同的距离
    height_step = (end_height - start_location.z) / (count - 1)

    for i in range(count):
        location = unreal.Vector(
            start_location.x, start_location.y, start_location.z + height_step * i
        )
        # [UE概念] Rotator(-90, 0, 0) 表示相机朝下看
        # Pitch=-90 就是正下方，这是升降机拍摄的经典角度
        rotation = unreal.Rotator(pitch=-90, yaw=0, roll=0)
        waypoints.append((location, rotation))

    return waypoints


# ============================================================
# 5. 相机预览工具
# ============================================================


def preview_camera_view(camera):
    """切换到指定相机的视角预览"""
    if camera:
        # [UE概念] 把编辑器视口对齐到相机的视角
        # UnrealEditorSubsystem 提供编辑器级别的全局操作
        # set_level_viewport_camera_info 将视口相机移到指定位置
        # 注意：这和 Sequencer 里的 Camera Cuts 不同——
        # 这里只是让编辑器视口"看"到相机的视角，不会创建任何动画
        loc = camera.get_actor_location()
        rot = camera.get_actor_rotation()
        # get_editor_subsystem 返回 Optional，判空后再调用
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is None:
            unreal.log_error("取不到 UnrealEditorSubsystem，无法切换视口视角")
            return
        subsystem.set_level_viewport_camera_info(loc, rot)
        unreal.log(f"已切换到相机视角: {camera.get_actor_label()}")


def list_cameras_in_level():
    """列出关卡中所有的相机"""
    # [UE概念] 获取关卡中所有 Actor——用 EditorActorSubsystem 而不是 EditorLevelLibrary
    # EditorLevelLibrary.get_all_level_actors() 已废弃，不要再用
    # get_editor_subsystem 返回 Optional，判空后再取；转普通 list 便于后续切片
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cameras = list(subsystem.get_all_level_actors()) if subsystem else []
    # [Python技巧] 列表推导式 + isinstance 过滤出 CineCameraActor
    # isinstance 检查继承关系——CineCameraActor 是 Actor 的子类
    cine_cameras = [a for a in cameras if isinstance(a, unreal.CineCameraActor)]

    unreal.log(f"\n关卡中的电影相机 ({len(cine_cameras)}):")
    for cam in cine_cameras:
        loc = cam.get_actor_location()
        # :.0f 格式化为不带小数的浮点数，输出更整洁
        unreal.log(
            f"  {cam.get_actor_label()} @ ({loc.x:.0f}, {loc.y:.0f}, {loc.z:.0f})"
        )

    return cine_cameras


# ============================================================
# 6. 完整示例：创建环绕相机动画
# ============================================================


def create_orbit_camera_shot(
    target_location, radius=800.0, height=400.0, duration_seconds=10.0, fps=30
):
    """
    一键创建环绕相机动画

    参数:
        target_location: 环绕目标位置
        radius: 半径
        height: 高度
        duration_seconds: 持续时间(秒)
        fps: 帧率
    """
    # 1. 生成相机——放在环绕轨道的起点（右侧）
    start_loc = unreal.Vector(
        target_location.x + radius, target_location.y, target_location.z + height
    )
    camera = spawn_cine_camera(start_loc, label="OrbitCamera")

    if not camera:
        return None

    # 2. 配置相机参数——FOV=60 比默认的 90 更窄，适合特写环绕
    configure_camera(camera, fov=60.0, focal_length=35.0)

    # 3. 生成 16 个均匀分布的环绕路径点
    # 16 个点足够让动画平滑，同时不会让 Sequencer 过于复杂
    waypoints = generate_orbit_waypoints(
        target_location, radius, height, count=16, look_at=target_location
    )

    # 4. 秒数转帧数：总帧数 = 秒数 x 帧率
    total_frames = int(duration_seconds * fps)
    sequence = create_camera_path_waypoints(camera, waypoints, total_frames)

    unreal.log(f"已创建环绕相机动画 ({duration_seconds}秒)")
    return camera, sequence


# ============================================================
# 使用示例
# ============================================================

# 创建环绕相机
# cam, seq = create_orbit_camera_shot(unreal.Vector(0, 0, 0))

# 列出相机
# list_cameras_in_level()

unreal.log("序列与过场动画第2课完成！")

# ============================================================
# 练习题
# ============================================================
# 【练习 1】一镜到底：相机从关卡一头飞到另一头
#   输入： 起点 Vector、终点 Vector、总时长秒数（如 15 秒）、fps=30
#   任务： 用 generate_dolly_waypoints 在起终点之间取 8 个路径点
#          （注意它的 count 是**中间点数量**，函数返回 count+2 个点，
#            所以取 8 个点要传 count=6）；
#          每个路径点都用 find_look_at_rotation(该点位置, 终点) 重算朝向，
#          （generate_dolly_waypoints 内部给的是"沿运动方向"的朝向，
#            本题要求的是"始终看向终点"，两者不同，要覆盖掉）；
#          再调 create_camera_path_waypoints 建序列/绑定/加轨道，
#          ⚠️ 实测它只建轨道 + Section、**不写关键帧**（函数里明说了本课先不写），
#          所以本题要自己补：get_all_channels(section) → 按名字取 Location.X/Y/Z
#          与 Rotation.X/Y/Z 六条通道 → 逐个 waypoint 调 add_key；
#          全程不切镜头（只有一个相机、一条连续的轨道）
#   输出： 播放序列时相机从起点平滑飞到终点，中途不停顿
#   验收： 总帧数 == 15*30 == 450；播放时物体在画面里始终朝画面中心移动；
#          把总时长改成 30 秒 → 帧数变 900，飞行速度明显减半。
#          实测关键帧落点：8 个路径点、frames_per_point = 450 // 7 = 64，
#          所以 Location.X 的键落在 0/64/128/192/256/320/384/**448** 帧
#          （不是 450 —— 整数除法会把尾巴截掉 2 帧，最后一个点停在 448）。
#          如果起点和终点同在一条 ±X 直线上（如 (0,0,0)→(3000,0,0)），
#          8 个 waypoint 的 Yaw 全是 0.0（都在看向 +X），这是正确结果不是 bug

# 【练习 2】两点之间的平滑推拉（Dolly In / Dolly Out）
#   输入： 被拍摄目标位置 target、相机起点、相机终点、帧数
#   任务： 相机位置从起点线性插到终点（这就是 dolly），
#          但朝向必须每一帧都重新用 find_look_at_rotation(相机位置, target) 算，
#          否则推近之后目标会跑出画面；
#          generate_dolly_waypoints 的 arc_height 参数用来加一点弧线，别传 0
#   输出： 相机一边靠近一边始终锁定目标，画面里目标逐渐变满
#   验收： 首帧和末帧里目标都在画面中心（用 preview_camera_view 看）；
#          把朝向固定成首帧的 rotation 再看一遍 → 末帧目标明显偏出中心（对比实验）。
#          ★ 实测提醒：如果相机和目标都在 Y=0 平面上（如相机从 (0,0,500) 推到
#            (1800,0,500)、目标在 (2000,0,100)），**6 个 waypoint 的 Yaw 全是 0.0**，
#            变化全体现在 Pitch 上：-11.31 / -17.52 / -24.76 / -32.68 / -42.74 / -63.44。
#            所以「固定首帧朝向」的反证**必须比 Pitch**，只比 Yaw 会得到 0 差异、
#            误以为朝向根本没变。要么就把目标抬到 Y 偏离的位置制造 Yaw 变化

# 【练习 3】相机动画库：5 种预设运动模式
#   输入： 一个模式名字符串 + 目标位置
#   任务： 封装 5 个函数：orbit（环绕）、dolly（推拉）、crane（升降）、
#          pan（水平摇）、tilt（垂直俯仰）；
#          orbit 直接用 generate_orbit_waypoints、crane 直接用 generate_crane_waypoints，
#          pan/tilt 只改 rotation 不改位置；
#          写一个 dispatch(mode_name) 统一入口，未知名字报错并列出全部可用模式
#   输出： 一个 dispatcher，五个模式各生成一段相机动画
#   验收： dispatch("orbit") 能跑出环绕动画；dispatch("orbit2") → 报错并打印
#          ["orbit","dolly","crane","pan","tilt"]；pan 模式生成的动画里
#          相机位置一点没变（只有 rotation 有关键帧）。
#          ★ 实测判据写死：同一个 Section 上
#            get_all_channels() 逐条数 get_keys() —— Rotation.Z 通道有 5 个键、
#            Location.X 通道有 **0** 个键，才算对了。
#            （pan 只写 Rotation.Z 时，Location.X 通道依然存在但键数为 0）

# 【练习 4】在两个路径点之间自动加缓入缓出
#   输入： 一段已经写好的相机轨道、缓入帧数 ease_in=15、缓出帧数 ease_out=15
#   任务： 不改关键帧的位置，而改插值方式：前 ease_in 帧内的关键帧做成缓入、
#          最后 ease_out 帧做成缓出、中间匀速。关键帧数量少于 ease_in+ease_out 时
#          按比例缩小缓动区间，不要直接报错退出。
#          ★ 实测澄清（重要）：`unreal.MovieSceneKeyInterpolation` 里**没有
#            EaseIn / EaseOut 成员**，全部成员只有
#            AUTO / USER / BREAK / LINEAR / CONSTANT / SMART_AUTO；
#            `unreal.RichCurveInterpMode` 也只有 RCIM_LINEAR / RCIM_CONSTANT / RCIM_CUBIC。
#            所以「缓入缓出」在 Python 里只能用**切线**做：
#              插 key 时 interpolation=unreal.MovieSceneKeyInterpolation.USER，
#              然后对该键 set_tangent_mode(unreal.RichCurveTangentMode.RCTM_USER)、
#              set_interpolation_mode(unreal.RichCurveInterpMode.RCIM_CUBIC)、
#              set_arrive_tangent / set_leave_tangent（缓入的起点 arrive_tangent=0，
#              缓出的终点 leave_tangent=0，中间键给非零斜率）
#   输出： 播放时镜头起步和停止都是柔和的，中间匀速
#   验收： 检测键上的实际状态（不是检测你传了什么）：
#          get_keys() 后逐键 get_tangent_mode() == RCTM_USER、
#          get_interpolation_mode() == RCIM_CUBIC、get_arrive_tangent()/get_leave_tangent()
#          == 你要的值（实测 5 个键全部写成功、读回一致）；
#          不加缓动时这些键是 RCTM_AUTO + RCIM_LINEAR；
#          轨道只有 3 个关键帧、ease_in=15 → 函数正常运行，缓动区间自动缩到 1 帧
