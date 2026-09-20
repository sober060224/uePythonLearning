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

本课可能用到的 API：
  - unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool —— 创建资产保存目录
  - unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools —— 获取资产工具实例
  - unreal.LevelSequenceFactoryNew() —— 序列资产工厂实例
  - unreal.LevelSequence —— 序列资产类
  - unreal.AssetTools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object —— 创建新资产
  - seq.set_display_rate(display_rate: FrameRate) -> None —— 设置序列显示帧率
  - unreal.FrameRate(numerator: int = 0, denominator: int = 1) —— 帧率结构体
  - unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool —— 保存资产到磁盘
  - unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object —— 按路径加载资产
  - seq.get_name() -> str —— 获取序列名称
  - seq.get_bindings() -> Array[MovieSceneBindingProxy] —— 获取序列全部绑定
  - binding.get_name() -> str —— 获取绑定名称
  - binding.get_tracks() -> Array[MovieSceneTrack] —— 获取绑定下的轨道
  - track.get_display_name() -> Text —— 获取轨道显示名
  - seq.add_possessable(object_to_possess: Object) -> MovieSceneBindingProxy —— 绑定 Actor 到序列
  - binding.add_track(track_type: Class) -> MovieSceneTrack —— 添加指定类型轨道
  - unreal.MovieScene3DTransformTrack —— 3D 变换轨道类
  - track.add_section() -> MovieSceneSection —— 为轨道添加分段
  - unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(level_sequence: LevelSequence) -> bool —— 在 Sequencer 中打开
  - unreal.LevelSequenceEditorBlueprintLibrary.play() -> None —— 播放当前序列
  - unreal.LevelSequenceEditorBlueprintLibrary.pause() -> None —— 暂停当前序列
  - unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence() -> None —— 关闭当前序列
  - unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(new_frame: int) -> None —— 设置当前帧（已废弃）
  - unreal.FrameTime(frame_number: FrameNumber = [0], sub_frame: float = 0.0) —— 帧时刻结构体
  - unreal.LevelSequenceEditorBlueprintLibrary.get_current_time() -> int —— 获取当前帧号
  - unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor] —— 获取选中的 Actor
  - unreal.log(arg: Any) -> None —— 输出普通日志
  - unreal.log_warning(arg: Any) -> None —— 输出警告日志
  - unreal.log_error(arg: Any) -> None —— 输出错误日志
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 创建 Level Sequence
# ─────────────────────────────────────────────────────────

def create_level_sequence(name, destination="/Game/Cinematics",
                           frame_rate=30):
    """
    创建 Level Sequence 资产

    参数:
        name: 序列名称
        destination: 保存路径
        frame_rate: 帧率
    """
    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.LevelSequenceFactoryNew()

    sequence = asset_tools.create_asset(
        name,
        destination,
        unreal.LevelSequence,
        factory
    )

    if sequence:
        path = f"{destination}/{name}"

        # 设置帧率
        if hasattr(sequence, 'set_display_rate'):
            sequence.set_display_rate(
                unreal.FrameRate(frame_rate, 1)
            )

        unreal.EditorAssetLibrary.save_asset(path)
        unreal.log(f"已创建 Level Sequence: {path} (帧率: {frame_rate})")
        return sequence

    return None

# ─────────────────────────────────────────────────────────
# 2. 获取序列信息
# ─────────────────────────────────────────────────────────

def inspect_sequence(sequence_path):
    """检查 Level Sequence 的详细信息"""
    sequence = unreal.EditorAssetLibrary.load_asset(sequence_path)
    if not sequence:
        unreal.log_error(f"无法加载序列: {sequence_path}")
        return

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"序列: {sequence.get_name()}")
    unreal.log(f"路径: {sequence_path}")

    # 获取绑定信息
    bindings = sequence.get_bindings()
    unreal.log(f"绑定数: {len(bindings)}")

    for binding in bindings:
        binding_name = binding.get_name() if hasattr(binding, 'get_name') else str(binding)
        unreal.log(f"  绑定: {binding_name}")

        # 获取轨道
        tracks = binding.get_tracks()
        for track in tracks:
            track_name = track.get_display_name() if hasattr(track, 'get_display_name') else type(track).__name__
            unreal.log(f"    轨道: {track_name}")

    return sequence

# ─────────────────────────────────────────────────────────
# 3. 绑定 Actor 到序列
# ─────────────────────────────────────────────────────────

def bind_actor_to_sequence(sequence, actor):
    """
    将 Actor 绑定到 Level Sequence
    这样就可以在序列中为这个 Actor 添加动画轨道
    """
    if not sequence or not actor:
        return None

    # 使用 Sequencer 绑定 API
    binding = sequence.add_possessable(actor)
    if binding:
        unreal.log(f"已将 {actor.get_actor_label()} 绑定到序列")
    return binding

# ─────────────────────────────────────────────────────────
# 4. 使用 MovieSceneSection 添加关键帧
# ─────────────────────────────────────────────────────────

def add_transform_track(sequence, binding):
    """为绑定的 Actor 添加变换轨道"""
    if not binding:
        return None

    # 添加 Transform 轨道
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    if track:
        unreal.log("已添加 Transform 轨道")

        # 添加 Section
        section = track.add_section()
        if section:
            unreal.log("已添加 Transform Section")
            return track, section

    return None

# ─────────────────────────────────────────────────────────
# 5. 序列播放控制
# ─────────────────────────────────────────────────────────

def open_sequence_in_sequencer(sequence_path):
    """在 Sequencer 编辑器中打开序列"""
    sequence = unreal.EditorAssetLibrary.load_asset(sequence_path)
    if sequence:
        # 使用 LevelSequenceEditorBlueprint 打开
        # 【修改前】open_level_sequence(sequence_path) ——
        # 桩签名要求传 LevelSequence 对象（open_level_sequence(level_sequence: LevelSequence) -> bool），
        # 传路径字符串会 TypeError，传上面 load 出来的对象
        unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(
            sequence
        )
        unreal.log(f"已在 Sequencer 中打开: {sequence_path}")

def play_sequence():
    """播放当前打开的序列"""
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    unreal.log("开始播放序列")

def pause_sequence():
    """暂停当前序列"""
    unreal.LevelSequenceEditorBlueprintLibrary.pause()
    unreal.log("暂停序列")

def stop_sequence():
    """停止当前序列"""
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()

def set_current_frame(frame):
    """设置当前帧"""
    # 【修改前】set_current_time(unreal.FrameTime(frame)) ——
    # 桩签名是 set_current_time(new_frame: int)，参数就是整数，传 FrameTime 会 TypeError
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)

def get_current_frame():
    """获取当前帧"""
    return unreal.LevelSequenceEditorBlueprintLibrary.get_current_time()

# ─────────────────────────────────────────────────────────
# 6. 批量创建序列
# ─────────────────────────────────────────────────────────

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

    for i in range(1, shot_count + 1):
        name = f"{base_name}_{i:03d}"
        seq = create_level_sequence(name, destination)
        if seq:
            created.append(seq)

    unreal.log(f"已创建 {len(created)} 个镜头序列")
    return created

# ─────────────────────────────────────────────────────────
# 7. 从关卡中选中的 Actor 创建动画序列
# ─────────────────────────────────────────────────────────

def create_sequence_from_selection(name="LS_Animation",
                                     destination="/Game/Cinematics"):
    """
    用关卡中选中的 Actor 创建动画序列
    每个选中的 Actor 都会被绑定到序列中
    """
    selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
    if not selected_actors:
        unreal.log_warning("请先选中要添加动画的 Actor")
        return None

    # 创建序列
    sequence = create_level_sequence(name, destination)
    if not sequence:
        return None

    # 绑定所有选中的 Actor
    for actor in selected_actors:
        bind_actor_to_sequence(sequence, actor)

    # 保存
    path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(path)

    unreal.log(
        f"已创建序列 {name}，绑定了 {len(selected_actors)} 个 Actor"
    )

    # 在 Sequencer 中打开
    open_sequence_in_sequencer(path)

    return sequence

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个序列，包含 5 个 Actor 的位移关键帧
# 2. 批量创建一组镜头序列并设置不同的时长
# 3. 编写工具：自动生成 Actor 从 A 点到 B 点的移动动画
# 4. 创建一个序列管理面板，列出所有序列及其绑定信息
