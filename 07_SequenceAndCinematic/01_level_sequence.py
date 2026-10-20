"""
=============================================================
序列与过场动画 第1课：Level Sequence 基础
=============================================================

学习目标：
  - 创建 Level Sequence 资产
  - 添加和操控轨道 (Track)
  - 添加关键帧
  - 控制序列播放

核心类：
  - unreal.LevelSequence - Level Sequence 资产
  - Sequencer 相关 API

习题可能用到的 API：
  ── unreal ──
    unreal.AssetTools.create_asset(asset_name, package_path, asset_class, factory, ...) -> Object
        —— 用工厂创建序列资产（练习1/2 建新序列；asset_class 传 unreal.LevelSequence.static_class()）
    seq.add_possessable(object_to_possess: Object) -> MovieSceneBindingProxy
        —— 简写形式（seq 是 LevelSequence 实例）；与下面 set_ 那行等价
    binding.add_track(track_type: Class) -> MovieSceneTrack
        —— 给绑定加一条轨道（位移用 MovieSceneTransformTrack.static_class()）
    unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor]
        —— 已废弃的取选中写法（桩里还在，新代码改用 EditorActorSubsystem）
    unreal.EditorAssetLibrary.list_assets(directory_path, recursive, include_folder) -> Array[str]
        —— 列目录下的资产路径（练习4 统计序列；★ 返回对象路径，取包路径要 split(".")[0]）
    unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object
        —— 按路径加载资产（练习3 取序列、练习4 遍历序列都要先加载）
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(level_sequence) -> bool
        —— 在 Sequencer 面板里打开序列（练习4 管理面板双击打开）
    unreal.FrameRate(numerator: int = 0, denominator: int = 1)
        —— 构造帧率对象（30fps = FrameRate(30, 1)，练习2 set_display_rate 用）
    unreal.MovieSceneSequence.add_possessable(object_to_possess: Object) -> MovieSceneBindingProxy
        —— 把 Actor 绑进序列（练习1 每个 Actor 一条 binding；桩 457389）
    unreal.MovieSceneBindingProxy.add_track(track_type: Class) -> MovieSceneTrack
        —— 给绑定加轨道（练习1 传 unreal.MovieSceneTransformTrack.static_class()）
    unreal.MovieSceneTrackExtensions.add_section(track: MovieSceneTrack) -> MovieSceneSection
        —— ★ 光 add_track 是**写不了关键帧**的：编辑器实测
           add_track 之后 track.get_sections() 返回 **0 个** section，
           必须先 add_section 才会有通道。返回类型实测是 MovieScene3DTransformSection
           （track 实例上也有 get_sections() / add_section() 两个同名实例方法）
    unreal.MovieSceneSectionExtensions.get_all_channels(section) -> Array[MovieSceneScriptingChannel]
        —— 取 section 上全部通道（桩 480352）。Transform 轨道实测给 **9 条**：
           名字形如 "Location.X_5" / "Rotation.Z_7" / "Scale.Y_9" ——
           注意后面那个 **_N 后缀是 UE 内部生成的唯一序号，每次建资产都不一样**，
           所以不要写死 "Location.X_3"，用 endswith("Location.X") / 包含匹配
    unreal.MovieSceneSectionExtensions.get_channel(cls, section, channel_name: Name) -> MovieSceneScriptingChannel
        —— 按名字取单条通道（桩 480260）。实测传 "Location.X"（不带 _N 后缀）
           **能**取到对应的 "Location.X_8"；但传错后缀会抛
           RuntimeError: MovieSceneSectionExtensions: Cannot get channel with this name
    unreal.MovieSceneScriptingDoubleChannel.add_key(time: FrameNumber, new_value: float,
                                                    sub_frame=0.0, time_unit=DISPLAY_RATE,
                                                    interpolation=MovieSceneKeyInterpolation.AUTO) -> MovieSceneScriptingDoubleKey
        —— ★ Transform 轨道的通道类型是 **DoubleChannel**，不是 FloatChannel（桩 478422）。
           实测 add_key(FrameNumber(0), 0.0) + add_key(FrameNumber(90), 500.0)
           → get_keys() 返回 2 个键，get_value() = 0.0 / 500.0，
           get_time().frame_number.value = 0 / 90
    unreal.MovieSceneScriptingDoubleKey.set_interpolation_mode(new_value: RichCurveInterpMode) -> None
        —— 改键的插值曲线（桩 478507）。枚举是 RichCurveInterpMode
           （RCIM_LINEAR=0 / RCIM_CONSTANT=1 / RCIM_CUBIC=2），不是 MovieSceneKeyInterpolation；
           实测把 5 个键全改成 RCIM_CUBIC 成功
    unreal.MovieSceneScriptingDoubleKey.set_tangent_mode(new_value: RichCurveTangentMode) -> None
        —— 切线模式（RCTM_USER=1 等），配合 set_arrive_tangent / set_leave_tangent
           做真正的缓入缓出（桩 478507 附近）
    unreal.LevelSequence.set_playback_end(end_frame: int) -> None / get_playback_end() -> int
        —— 设置/读取序列总帧数（练习2 不同时长、练习4 统计表；桩 456806）
    unreal.LevelSequence.set_display_rate(display_rate: FrameRate) -> None / get_display_rate() -> FrameRate
        —— 设置/读取帧率（练习2、练习4；桩 456858 / 457147）
    unreal.LevelSequence.get_bindings() -> Array[MovieSceneBindingProxy]
        —— 列出序列里全部绑定（练习4 统计「绑了几个对象」；桩 457174）
=============================================================
"""

import unreal

# ============================================================
# 1. 创建 Level Sequence
# ============================================================


def create_level_sequence(name, destination="/Game/Cinematics", frame_rate=30):
    """
    创建 Level Sequence 资产

    参数:
        name: 序列名称
        destination: 保存路径
        frame_rate: 帧率
    """
    # [UE概念] 创建资产前必须确保目录存在，否则 create_asset 会失败
    # make_directory 是幂等操作——目录已存在时不会报错也不会重复创建
    unreal.EditorAssetLibrary.make_directory(destination)

    # [UE概念] AssetTools 是 UE 编辑器创建任何资产的统一入口
    # 无论创建 Texture、Blueprint 还是 Level Sequence，都要通过它
    # get_asset_tools() 返回的是一个全局单例，不需要自己实例化
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # [UE概念] 工厂模式：UE 创建资产必须提供 Factory 对象
    # Factory 决定了"怎么造"这个资产。不同资产类型有不同的 Factory，
    # 比如 UTextureFactory 用于创建纹理，UBlueprintFactory 用于创建蓝图
    # LevelSequenceFactoryNew 是 Level Sequence 的专用工厂
    factory = unreal.LevelSequenceFactoryNew()

    # create_asset 四个必选参数：资产名、包路径、资产类型、工厂
    # 注意：如果同名资产已存在，它会返回已有资产（不是报错）
    # 返回值可能是 None——务必做空值检查
    sequence = asset_tools.create_asset(
        name,
        destination,
        # Class 参数要「类对象」而非 Python 类，所以用 .static_class()
        unreal.LevelSequence.static_class(),
        factory,
    )

    if sequence:
        path = f"{destination}/{name}"

        # [UE概念] FrameRate(分子, 分母) 表示每秒帧数
        # FrameRate(30, 1) = 30fps，FrameRate(24, 1) = 24fps（电影标准）
        # 【用 isinstance 而不是 hasattr】create_asset 的返回类型在桩里是 Object，
        #   Object 上没有 set_display_rate；而 UE 的 Python 包装对象对未知属性
        #   hasattr 也返回 True，那个判断等于没写。收窄成 MovieSceneSequence
        #   （LevelSequence 的父类）之后类型和运行时都成立。
        if isinstance(sequence, unreal.MovieSceneSequence):
            sequence.set_display_rate(unreal.FrameRate(frame_rate, 1))

        # [常见陷阱] 创建后必须显式保存！
        # 不保存的话资产只存在于内存中，编辑器关闭后就丢失了
        # save_asset 的参数是资产的完整路径（包路径），不是对象
        unreal.EditorAssetLibrary.save_asset(path)
        unreal.log(f"已创建 Level Sequence: {path} (帧率: {frame_rate})")
        return sequence

    return None


# ============================================================
# 2. 获取序列信息
# ============================================================


def inspect_sequence(sequence_path):
    """检查 Level Sequence 的详细信息"""
    # [UE概念] load_asset 返回资产对象的引用（不是副本）
    # 你对返回对象的任何修改都会直接影响到原始资产
    # 如果路径不存在或资产损坏，返回 None
    sequence = unreal.EditorAssetLibrary.load_asset(sequence_path)
    if not sequence:
        # 常见原因：路径拼写错误、大小写不对、资产文件损坏
        unreal.log_error(f"无法加载序列: {sequence_path}")
        return

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"序列: {sequence.get_name()}")
    unreal.log(f"路径: {sequence_path}")

    # [核心概念] Binding（绑定）是 Sequencer 的核心组织结构：
    # - 每个被"绑定"到序列的 Actor 都对应一个 Binding 对象
    # - Binding 下面挂着各种 Track（轨道），如 Transform、Material 等
    # - 一个 Binding 可以有多个 Track，每个 Track 控制 Actor 的一个属性
    # - get_bindings() 返回所有绑定，包括 Master Binding 和 Possessable Binding
    # load_asset 返回 Object（桩里没有 get_bindings），所以先收窄成序列类型；
    # 万一路径指向的不是序列资产，也能给出明确报错而不是 AttributeError。
    if not isinstance(sequence, unreal.MovieSceneSequence):
        unreal.log_error(f"该资产不是序列（MovieSceneSequence）: {sequence_path}")
        return
    bindings = sequence.get_bindings()
    unreal.log(f"绑定数: {len(bindings)}")

    for binding in bindings:
        # get_name() 在某些绑定类型上可能不存在，所以用 hasattr 安全检查
        binding_name = (
            binding.get_name() if hasattr(binding, "get_name") else str(binding)
        )
        unreal.log(f"  绑定: {binding_name}")

        # [UE概念] Track（轨道）挂在 Binding 下面，控制 Actor 的具体属性
        # 比如 Transform Track 控制位置/旋转/缩放，Material Track 控制材质
        tracks = binding.get_tracks()
        for track in tracks:
            track_name = (
                track.get_display_name()
                if hasattr(track, "get_display_name")
                else type(track).__name__
            )
            unreal.log(f"    轨道: {track_name}")

    return sequence


# ============================================================
# 3. 绑定 Actor 到序列
# ============================================================


def bind_actor_to_sequence(sequence, actor):
    """
    将 Actor 绑定到 Level Sequence
    这样就可以在序列中为这个 Actor 添加动画轨道

    [核心概念] add_possessable 将关卡中的 Actor"借"给序列使用
    - Possessable：Actor 属于关卡，序列只是临时控制它
    - 与 Spawnable 不同：Spawnable 是序列自己生成和销毁 Actor
    - 大多数情况下用 Possessable 就够了
    """
    if not sequence or not actor:
        return None

    # [常见陷阱] 必须先传入 Actor 对象，不是字符串路径
    # 如果 Actor 已经绑定过，再次调用可能返回已有的 binding
    binding = sequence.add_possessable(actor)
    if binding:
        unreal.log(f"已将 {actor.get_actor_label()} 绑定到序列")
    return binding


# ============================================================
# 4. 使用 MovieSceneSection 添加关键帧
# ============================================================


def add_transform_track(sequence, binding):
    """为绑定的 Actor 添加变换轨道"""
    if not binding:
        return None

    # [UE概念] Track（轨道）的类型决定了它控制什么属性
    # MovieScene3DTransformTrack 控制位移、旋转、缩放
    # 其他常见轨道类型：MovieSceneFloatTrack（浮点数）、MovieSceneStringTrack（字符串）
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    if track:
        unreal.log("已添加 Transform 轨道")

        # [UE概念] Section 是 Track 内部的时间分段
        # 一个 Track 可以有多个 Section，每段可以有不同的动画数据
        # 大多数情况下一个 Track 只需要一个 Section
        section = track.add_section()
        if section:
            unreal.log("已添加 Transform Section")
            return track, section

    return None


# ============================================================
# 5. 序列播放控制
# ============================================================


def open_sequence_in_sequencer(sequence_path):
    """在 Sequencer 编辑器中打开序列"""
    # [常见陷阱] open_level_sequence 需要 LevelSequence 对象，不是字符串路径
    # 很多人会直接传路径字符串，这会导致 TypeError
    # 正确做法：先 load_asset 拿到对象，再传给 open_level_sequence
    sequence = unreal.EditorAssetLibrary.load_asset(sequence_path)
    # load_asset 返回的是 Object，open_level_sequence 要 LevelSequence，先收窄
    if isinstance(sequence, unreal.LevelSequence):
        unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
        unreal.log(f"已在 Sequencer 中打开: {sequence_path}")


def play_sequence():
    """播放当前打开的序列"""
    # [注意] play/pause/close 这些函数操作的是 Sequencer 面板中当前打开的序列
    # 如果没有序列被打开，调用 play 会静默失败（不会报错）
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    unreal.log("开始播放序列")


def pause_sequence():
    """暂停当前序列"""
    unreal.LevelSequenceEditorBlueprintLibrary.pause()
    unreal.log("暂停序列")


def stop_sequence():
    """停止当前序列"""
    # close_level_sequence 会关闭 Sequencer 面板中的序列
    # 注意：这不是删除序列，只是关闭编辑器面板
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()


def set_current_frame(frame):
    """设置当前帧"""
    # [常见陷阱] set_current_time 的参数是整数（帧号），不是 FrameTime 对象
    # 传 FrameTime 会导致 TypeError
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)


def get_current_frame():
    """获取当前帧"""
    return unreal.LevelSequenceEditorBlueprintLibrary.get_current_time()


# ============================================================
# 6. 批量创建序列
# ============================================================


def create_shot_sequences(base_name, shot_count, destination="/Game/Cinematics/Shots"):
    """
    批量创建镜头序列

    参数:
        base_name: 基础名称 (如 "Shot")
        shot_count: 镜头数量
        destination: 保存路径
    """
    created = []

    # [技巧] 使用 f-string 的 :03d 格式化，让数字自动补零
    # 比如 001, 002, 003... 这样在文件管理器中排序更方便
    for i in range(1, shot_count + 1):
        name = f"{base_name}_{i:03d}"
        seq = create_level_sequence(name, destination)
        if seq:
            created.append(seq)

    unreal.log(f"已创建 {len(created)} 个镜头序列")
    return created


# ============================================================
# 7. 从关卡中选中的 Actor 创建动画序列
# ============================================================


def create_sequence_from_selection(name="LS_Animation", destination="/Game/Cinematics"):
    """
    用关卡中选中的 Actor 创建动画序列
    每个选中的 Actor 都会被绑定到序列中
    """
    # [UE概念] get_selected_level_actors 返回编辑器中当前被选中的 Actor 列表
    # 只能在编辑器中使用，打包后的游戏里没有这个功能
    # 返回的是列表——如果没有 Actor 被选中，返回空列表（不是 None）
    selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
    if not selected_actors:
        # [常见陷阱] 忘记检查空列表是新手常犯的错误
        # 如果不检查，后面的 for 循环虽然不会报错，但会创建空序列
        unreal.log_warning("请先选中要添加动画的 Actor")
        return None

    # 创建序列（复用上面的函数）
    sequence = create_level_sequence(name, destination)
    if not sequence:
        return None

    # 逐个绑定选中的 Actor 到序列
    # [注意] 绑定顺序会影响 Sequencer 面板中的排列顺序
    for actor in selected_actors:
        bind_actor_to_sequence(sequence, actor)

    # 绑定完成后保存——每次修改序列后都应该保存
    path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(path)

    unreal.log(f"已创建序列 {name}，绑定了 {len(selected_actors)} 个 Actor")

    # 自动在 Sequencer 中打开，方便立即编辑
    open_sequence_in_sequencer(path)

    return sequence


# ============================================================
# 使用示例
# ============================================================

# 创建序列
# seq = create_level_sequence("LS_TestSequence")

# 从选中 Actor 创建动画
# create_sequence_from_selection("LS_MyAnimation")

# 批量创建镜头
# create_shot_sequences("Shot", 5)

# 控制播放
# play_sequence()
# set_current_frame(30)

unreal.log("序列与过场动画第1课完成！")

# ============================================================
# 练习题
# ============================================================
# 【练习 1】给 5 个 Actor 各加一条位移关键帧
#   输入： 视口中选中的 Actor（至少 1 个，最多取前 5 个）
#   任务： 建一个新序列，对每个 Actor 调 add_possessable 拿到 binding，
#          再 binding.add_track(unreal.MovieSceneTransformTrack.static_class())
#          拿到位移轨道；在第 0 帧和 duration_frames 帧各插一个 key，
#          起点就是 Actor 当前位置，终点是它沿 +X 平移 500 的位置
#   输出： 打开 Sequencer 能看到 5 条绑定，每条都有关键帧、播放时物体会移动
#   验收： 播放一次 → 5 个 Actor 同时沿 +X 平移 500 后停住；
#          把 duration_frames 改成 60（2 秒 @30fps）→ 播放时长明显变短。
#          ⚠️ 编辑器实测的必经三步（少一步就白干）：
#          ① add_possessable(actor) → MovieSceneBindingProxy（get_bindings() 能读出它，
#             get_name() 就是 Actor 的标签，实测建 1 条就是 1 条）
#          ② binding.add_track(MovieSceneTransformTrack.static_class())
#          ③ **track 上必须再 add_section()** —— 不调它 track.get_sections() 返回
#             0 个 section，一个通道都没有，关键帧根本无处可写。
#             返回的 section 是 MovieScene3DTransformSection

# 【练习 2】批量建一组镜头序列，时长各不同
#   输入： 基名 "Shot"、每个镜头的帧数列表（如 [60, 90, 120]）
#   任务： 复用 create_shot_sequences，但每个序列建好后要调
#          sequence.set_playback_end(对应帧数) 和
#          sequence.set_display_rate(unreal.FrameRate(30, 1))；
#          名称统一成 Shot_01 / Shot_02 / Shot_03
#   输出： /Game/Cinematics/Shots 下三个序列，各自时长不同
#   验收： 依次打开三个序列 → 结束帧分别是 60 / 90 / 120；
#          用 get_display_rate() 读回来都是 30fps（实测返回 FrameRate 的
#          numerator=30 / denominator=1，不是字符串也不是 float）
#          顺带验证：set_playback_start(0) 也有效，get_playback_start() 读回 0

# 【练习 3】自动生成「Actor 从 A 点走到 B 点」的动画
#   输入： 1 个 Actor、起点 Vector A、终点 Vector B、总帧数 90、中间帧数 4
#   任务： 在 A->B 之间线性插值出 5 个关键帧位置（含首尾），
#          位置比例 t = 帧号 / 90（不是 i/4 —— 帧号 22/45/67 并不等于 1/4、2/4、3/4，
#          t 分别是 0.2444 / 0.5 / 0.7444），位置 = A + (B-A) * t；
#          用 add_key 依次插入第 0 / 22 / 45 / 67 / 90 帧；
#          为了让运动不是机械直线，t=0.25 / 0.5 / 0.75 那三个中间关键帧
#          各加 amplitude*sin(π*t) 的 Z 方向偏移（首尾 sin=0，所以端点不动）
#   输出： 播放时 Actor 沿 A 到 B 移动，中途有轻微起伏
#   验收： 第 0 帧位置 == A、第 90 帧位置 == B（误差 < 0.01）；
#          中间帧的 X 单调递增并严格落在 A.x 与 B.x 之间；
#          中间帧的 Z 都高于 A→B 直线的对应值（起伏朝上，不是朝下）。
#          编辑器实测（A=0、B=1000、amplitude=50，直接读 get_keys()）：
#            X: 0 → 244.4444 → 500.0 → 744.4445 → 1000.0
#            Z: 0 → 34.7329  → 50.0  → 35.967   → 0
#          注意 X 的中间两点**不是** 250/500/750 —— 因为 t 取的是 22/90 和 67/90；
#          Z 的 22 帧和 67 帧也不对称（34.73 vs 35.97），这是 22≠67 的反向对称造成的，
#          不是 bug。想要对称就把中间帧改成 0/22.5/45/67.5/90，
#          或者接受这点小偏差并写进验收里

# 【练习 4】序列管理面板
#   输入： search_path（默认 "/Game/Cinematics"）下所有 LevelSequence 资产
#   任务： 用 list_assets 找到全部序列，逐个 load_asset 后统计：
#          序列名、总帧数（get_playback_end）、帧率（get_display_rate）、
#          绑定了几个对象（遍历 get_bindings 数长度）；
#          输出成一张按总帧数降序排的表，最后打印总数
#   输出： 一张能一眼看出「哪个镜头最长、哪个是空序列」的表
#   验收： 项目里有 N 个序列 → 表里正好 N 行；
#          刚建还没绑任何东西的序列，绑定数显示 0 而不是报错。
#          实测：get_bindings() 返回 Array[MovieSceneBindingProxy]，
#          空序列 len() == 0 不抛异常；绑了 1 个 Actor 就是 1，
#          proxy.get_name() 给出的是 Actor 的标签字符串
