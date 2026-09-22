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
  - unreal.AssetTools.create_asset(asset_name, package_path, asset_class, factory, ...) -> Object
  - seq.add_possessable(object_to_possess: Object) -> MovieSceneBindingProxy
  - binding.add_track(track_type: Class) -> MovieSceneTrack
  - unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor]
  - unreal.EditorAssetLibrary.list_assets(directory_path, recursive, include_folder) -> Array[str]
  - unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object
  - unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(level_sequence) -> bool
  - unreal.FrameRate(numerator: int = 0, denominator: int = 1)
=============================================================
"""

import unreal

# ============================================================
# 1. 创建 Level Sequence
# ============================================================

def create_level_sequence(name, destination="/Game/Cinematics",
                           frame_rate=30):
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
        unreal.LevelSequence,
        factory
    )

    if sequence:
        path = f"{destination}/{name}"

        # [UE概念] FrameRate(分子, 分母) 表示每秒帧数
        # FrameRate(30, 1) = 30fps，FrameRate(24, 1) = 24fps（电影标准）
        # hasattr 检查是为了兼容不同 UE 版本——某些老版本可能没有此方法
        if hasattr(sequence, 'set_display_rate'):
            sequence.set_display_rate(
                unreal.FrameRate(frame_rate, 1)
            )

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
    bindings = sequence.get_bindings()
    unreal.log(f"绑定数: {len(bindings)}")

    for binding in bindings:
        # get_name() 在某些绑定类型上可能不存在，所以用 hasattr 安全检查
        binding_name = binding.get_name() if hasattr(binding, 'get_name') else str(binding)
        unreal.log(f"  绑定: {binding_name}")

        # [UE概念] Track（轨道）挂在 Binding 下面，控制 Actor 的具体属性
        # 比如 Transform Track 控制位置/旋转/缩放，Material Track 控制材质
        tracks = binding.get_tracks()
        for track in tracks:
            track_name = track.get_display_name() if hasattr(track, 'get_display_name') else type(track).__name__
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
    if sequence:
        unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(
            sequence
        )
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

def create_shot_sequences(base_name, shot_count,
                           destination="/Game/Cinematics/Shots"):
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

def create_sequence_from_selection(name="LS_Animation",
                                     destination="/Game/Cinematics"):
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

    unreal.log(
        f"已创建序列 {name}，绑定了 {len(selected_actors)} 个 Actor"
    )

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
# 1. 创建一个序列，包含 5 个 Actor 的位移关键帧
# 2. 批量创建一组镜头序列并设置不同的时长
# 3. 编写工具：自动生成 Actor 从 A 点到 B 点的移动动画
# 4. 创建一个序列管理面板，列出所有序列及其绑定信息
