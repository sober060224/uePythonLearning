import unreal

"""selected_assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
unreal.log(f"\nContent Browser 选中了 {len(selected_assets)} 个资产")

for asset_data in selected_assets:
    unreal.log(f"  资产: {asset_data.asset_name}")
    unreal.log(f"  路径: {asset_data.package_path}")
    unreal.log(f"  类型: {asset_data.asset_class_path}")"""

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个函数，打印当前关卡中所有 StaticMeshActor 的位置
# 2. 【跳过】用进度条遍历所有资产并统计每种类型的数量
#    —— ScopedSlowTask.make_dialog 在 Python 里几乎必定卡死 UI，
#    因为 Python 主线程和 UE 编辑器共享同一个线程，循环几千个资产
#    时 UI 来不及重绘，看起来就是"一直加载、进度一直是 0"。
#    真要干这个活得写 C++ 异步任务或者用 Editor Utility Widget（UMG）。
# 3. 编写一个工具，选中关卡中的 Actor 后自动在日志中打印
#    其详细信息（名称、位置、旋转、缩放）


# ═════════════════════════════════════════════════════════
# 第 1 题：打印所有 StaticMeshActor 的位置
# ═════════════════════════════════════════════════════════
# 【修改前】（if 没写完，语法错误）
# def print_position():
#     all_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
#     for actor in all_actor:
#         if
#
# 【问题分析】
# 1. if 后面啥也没有，直接 SyntaxError
# 2. 需要判断"这个 actor 是不是 StaticMeshActor" ——
#    用 isinstance(actor, unreal.StaticMeshActor)，Python 的 isinstance
#    对应 UE Python 里的类继承检查，unreal.StaticMeshActor 是 UE 暴露给 Python 的类
# 3. 位置用 actor.get_actor_location() 拿，返回 Vector(x, y, z)
#    如果想格式化好看点，可以拆成 x/y/z 三个分量
def print_static_mesh_positions():
    """打印当前关卡中所有 StaticMeshActor 的位置"""
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_subsystem.get_all_level_actors()

    count = 0
    for actor in all_actors:
        # isinstance 判断"是不是 StaticMeshActor 或它的子类"
        if isinstance(actor, unreal.StaticMeshActor):
            loc = actor.get_actor_location()
            unreal.log(
                f"[StaticMeshActor] {actor.get_actor_label()}: "
                f"X={loc.x:.1f}, Y={loc.y:.1f}, Z={loc.z:.1f}"
            )
            count += 1

    unreal.log(f"\n共找到 {count} 个 StaticMeshActor")


# ═════════════════════════════════════════════════════════
# 第 3 题：打印选中 Actor 的详细信息
# ═════════════════════════════════════════════════════════
# 【修改前】（基本正确，只补一个小细节）
# def print_actor():
#     selected_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
#     for actor in selected_actors:
#         unreal.log(
#             f"名称: {actor.get_actor_label()}\n"
#             f"位置: {actor.get_actor_location()}\n"
#             f"旋转: {actor.get_actor_rotation()}\n"
#             f"变换: {actor.get_actor_transform()}"
#         )
#
# 【问题分析】
# 1. 基本正确，但少了"缩放（Scale）" —— 题目要求打印位置/旋转/缩放，
#    变换(Transform) 里已经包含缩放了，不过单独打出来更直观
# 2. 没选中任何东西时 selected_actors 是空列表，for 循环直接跳过，
#    不会报错但也不会输出 —— 加个提示告诉用户"先选中几个 Actor"
def print_selected_actor_info():
    """打印选中 Actor 的详细信息（名称、位置、旋转、缩放）"""
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = actor_subsystem.get_selected_level_actors()

    if not selected_actors:
        unreal.log("⚠ 请先在关卡视口中选中几个 Actor，再运行这个函数")
        return

    for actor in selected_actors:
        loc = actor.get_actor_location()
        rot = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()

        unreal.log(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"名称: {actor.get_actor_label()} ({type(actor).__name__})\n"
            f"位置: X={loc.x:.1f}, Y={loc.y:.1f}, Z={loc.z:.1f}\n"
            f"旋转: P={rot.pitch:.1f}, Y={rot.yaw:.1f}, R={rot.roll:.1f}\n"
            f"缩放: X={scale.x:.2f}, Y={scale.y:.2f}, Z={scale.z:.2f}"
        )


# ─────────────────────────────────────────────────────────
# 测试调用（取消注释即可运行）
# ─────────────────────────────────────────────────────────
print_static_mesh_positions()
print_selected_actor_info()