"""
=============================================================
第3课：编辑器基础交互 - 了解和控制 UE 编辑器
=============================================================

学习目标：
  - 获取编辑器的各种状态信息
  - 了解编辑器子系统
  - 学会基本的编辑器操作

运行方式：
  - 在 UE Python Console 中逐段执行

本课可能用到的 API：
  unreal.get_editor_subsystem(subsystem: Class) -> EditorSubsystem  —— 获取指定类型的编辑器子系统
  unreal.UnrealEditorSubsystem.get_editor_world() -> World  —— 获取编辑器当前打开的世界
  unreal.EditorActorSubsystem.get_all_level_actors() -> Array[Actor]  —— 获取关卡中的所有 Actor
  unreal.EditorActorSubsystem.get_selected_level_actors() -> Array[Actor]  —— 获取当前选中的 Actor
  obj.get_name() -> str  —— 获取对象的名称
  obj.get_path_name() -> str  —— 获取对象的完整路径名
  unreal.Paths.project_dir() -> str  —— 获取项目根目录路径
  unreal.Paths.project_content_dir() -> str  —— 获取项目 Content 目录路径
  unreal.Paths.project_config_dir() -> str  —— 获取项目 Config 目录路径
  unreal.Paths.project_saved_dir() -> str  —— 获取项目 Saved 目录路径
  unreal.Paths.project_plugins_dir() -> str  —— 获取项目插件目录路径
  unreal.Paths.combine(paths: Array[str]) -> str  —— 将路径数组拼接为一个路径
  unreal.Paths.normalize_filename(path: str) -> str  —— 标准化路径（统一斜杠、折叠冗余）
  unreal.Paths.get_project_file_path() -> str  —— 获取项目文件（.uproject）路径
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出指定目录下的资产路径
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 查找资产并返回元数据
  data.is_valid() -> bool  —— 判断资产数据是否有效
  data.asset_name -> Name  —— 获取资产名称
  data.package_path -> Name  —— 获取资产所在包路径
  data.asset_class_path -> TopLevelAssetPath  —— 获取资产的类路径
  data.asset_class_path.asset_name -> Name  —— 获取资产的类名
  unreal.EditorUtilityLibrary.get_selected_asset_data() -> Array[AssetData]  —— 获取内容浏览器中选中的资产
  unreal.EditorDialog.show_message(title: Text, message: Text, message_type: AppMsgType, default_value: AppReturnType = AppReturnType.NO, message_category: AppMsgCategory = AppMsgCategory.WARNING) -> AppReturnType  —— 弹对话框显示消息并返回用户选择
  unreal.ScopedSlowTask(work: float, desc: Text = "", enabled: bool = True)  —— 创建进度条任务上下文
  task.make_dialog(can_cancel: bool = False, allow_in_pie: bool = False) -> None  —— 让进度任务显示为对话框
  task.should_cancel() -> bool  —— 判断用户是否点击取消
  task.enter_progress_frame(work: float = 1.0, desc: Text = "") -> None  —— 推进一个进度帧并更新提示
  unreal.SystemLibrary.print_string(world_context_object: Object, string: str = "Hello", print_to_screen: bool = True, print_to_log: bool = True, text_color: LinearColor = [0.000000, 0.660000, 1.000000, 1.000000], duration: float = 2.000000) -> None  —— 在屏幕上显示文本消息
  unreal.SystemLibrary.get_engine_version() -> str  —— 获取当前引擎版本号
  unreal.SystemLibrary.get_command_line() -> str  —— 获取编辑器命令行参数
  unreal.LinearColor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 0.0)  —— 创建一个线性颜色对象
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 编辑器子系统
# ─────────────────────────────────────────────────────────
# UE5 使用子系统架构，可以通过子系统访问各种功能

# 获取编辑器子系统
editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor_subsystem:
    unreal.log("成功获取编辑器子系统")

# ─────────────────────────────────────────────────────────
# 2. 获取当前关卡信息
# ─────────────────────────────────────────────────────────
# 【修改前】（已废弃，会报 DeprecationWarning）
# current_level = unreal.EditorLevelLibrary.get_editor_world()
# all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
#
# 【问题分析】
# EditorLevelLibrary 属于老的 "Editor Scripting Utilities" 插件，
# 整个插件在 UE5 中已被废弃，功能拆散搬进了各个"子系统"：
#   - 拿编辑器世界  → UnrealEditorSubsystem.get_editor_world()
#   - 关卡 Actor 操作 → EditorActorSubsystem（获取/生成/销毁 Actor）
# 记忆方法：老 API 是一个大而全的静态库（EditorLevelLibrary），
# 新 API 按职责拆成多个子系统，统一用 get_editor_subsystem() 获取。
current_level = unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
).get_editor_world()  # 复用上面第 1 节拿到的子系统

if current_level:
    unreal.log(f"当前关卡: {current_level.get_name()}")
    unreal.log(f"关卡路径: {current_level.get_path_name()}")

# 获取关卡中的所有 Actor（EditorActorSubsystem 是新家）
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = actor_subsystem.get_all_level_actors()
unreal.log(f"\n当前关卡中有 {len(all_actors)} 个 Actor")

# 按类型统计 Actor
actor_types = {}
for actor in all_actors:
    type_name = type(actor).__name__
    actor_types[type_name] = actor_types.get(type_name, 0) + 1

unreal.log("\nActor 类型统计:")
for type_name, count in sorted(actor_types.items(), key=lambda x: -x[1]):
    unreal.log(f"  {type_name}: {count}")

# ─────────────────────────────────────────────────────────
# 3. 路径工具
# ─────────────────────────────────────────────────────────
# unreal.Paths 提供各种路径处理工具

unreal.log("\n--- 路径信息 ---")
unreal.log(f"项目目录: {unreal.Paths.project_dir()}")
unreal.log(f"Content 目录: {unreal.Paths.project_content_dir()}")
unreal.log(f"Config 目录: {unreal.Paths.project_config_dir()}")
unreal.log(f"Saved 目录: {unreal.Paths.project_saved_dir()}")
unreal.log(f"插件目录: {unreal.Paths.project_plugins_dir()}")

# 路径拼接
combined = unreal.Paths.combine([unreal.Paths.project_dir(), "Content", "Characters"])
unreal.log(f"\n拼接路径示例: {combined}")

# 路径标准化
# 【修改前】（AttributeError：Paths 上根本没有这个函数，脚本在这里崩了）
# normalized = unreal.Paths.normalize_path_name(messy_path)
#
# 【问题分析】
# C++ 里是 FPaths::NormalizeFilename()，转成 Python 是 normalize_filename，
# 不是 normalize_path_name —— 猜 API 名字会踩这种坑，报错时用
#   print([m for m in dir(unreal.Paths) if 'norm' in m])
# 自查即可。normalize_filename 会做两件事：
#   1. 统一斜杠（把 Windows 的 \ 转成 /）
#   2. 折叠冗余部分（"//" 变 "/"，"a/../b" 变 "b"）
messy_path = "/Game//Characters/../Materials/MyMaterial"
normalized = unreal.Paths.normalize_filename(messy_path)
unreal.log(f"标准化前: {messy_path}")
unreal.log(f"标准化后: {normalized}")

# ─────────────────────────────────────────────────────────
# 4. 编辑器用户交互
# ─────────────────────────────────────────────────────────
# 弹出对话框与用户交互

# 简单的消息对话框（注意：会阻塞脚本执行）
# unreal.EditorDialog.show_message(
#     "标题",
#     "这是一条来自 Python 的消息！",
#     unreal.AppMsgType.OK
# )

# 确认对话框
# result = unreal.EditorDialog.show_message(
#     "确认",
#     "是否继续执行？",
#     unreal.AppMsgType.YES_NO
# )
# if result == unreal.AppReturnType.YES:
#     unreal.log("用户选择了 YES")

# ─────────────────────────────────────────────────────────
# 5. 编辑器进度条
# ─────────────────────────────────────────────────────────
# 【修改前】—— 就是那个让编辑器"一直加载、进度一直是 0"的罪魁祸首
#
# task = unreal.ScopedSlowTask(5.0, "正在执行操作...")
# task.make_dialog(True)
# for i in range(5):
#     if task.should_cancel():
#         break
#     task.enter_progress_frame(1.0, f"处理第 {i+1} 步...")
#     import time
#     time.sleep(0.5)          # ← 这行是罪魁祸首
#
# 【问题分析】
# 1. UE 的编辑器 UI（包括 ScopedSlowTask 的进度弹窗）和 Python 脚本
#    跑在同一个"主线程"上。你调 time.sleep(0.5)，整个线程就睡 0.5 秒，
#    期间 Windows 消息循环被阻塞，进度条根本没时间重绘 ——
#    所以看起来就是"进度一直是 0、界面假死、鼠标转圈"。
# 2. 更严重的是，sleep 期间编辑器整体无响应，用户只能强杀进程。
# 3. 编辑器 Python 脚本里几乎永远不要用 time.sleep()；
#    如果真需要"做点事再等等"，用 tick 回调或者把等待拆到 C++ 异步任务里。
#
# 【修改后】用真实工作（扫描资产）驱动进度条，每步做一小点工作，
# enter_progress_frame 之间不阻塞，UI 就能流畅更新。
# ─────────────────────────────────────────────────────────

# 先拿一批真实数据做演示 —— 只扫描一个小目录，避免 Lyra 几千个资产把 UI 卡死
# ⚠️ 如果你把 scope 改成 "/Game"，循环几千次、每次都拼字符串 + 查资产类型，
#    UI 来不及重绘，看起来又会"卡死"。演示用小范围就行。
SCAN_SCOPE = "/Game/EditorWidgetUtilities"
all_asset_paths = unreal.EditorAssetLibrary.list_assets(
    SCAN_SCOPE, recursive=True, include_folder=False
)
total = len(all_asset_paths)
if total == 0:
    unreal.log(f"{SCAN_SCOPE} 下没有任何资产，跳过进度条演示")
else:
    # 进度条总量 = 资产数量
    task = unreal.ScopedSlowTask(float(total), "正在扫描资产...")
    # make_dialog(True) 弹出模态进度弹窗，参数表示"是否显示取消按钮"

    type_counts = {}
    for i, asset_path in enumerate(all_asset_paths):
        # 每次循环都检查"用户点了取消没" —— 响应式 UI 的关键
        if task.should_cancel():
            unreal.log("用户取消了操作")
            break

        # 这一帧的提示文字 —— 用简短路径，避免拼长字符串拖慢 UI
        task.enter_progress_frame(1.0, f"正在处理 {i + 1}/{total}")

        # 真实工作：查一下资产类型并统计（不会阻塞 UI）
        data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if data.is_valid():
            t = data.asset_class_path.asset_name
            type_counts[t] = type_counts.get(t, 0) + 1

    unreal.log(f"扫描完成！{SCAN_SCOPE} 类型统计：")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        unreal.log(f"  {t}: {c}")

# ─────────────────────────────────────────────────────────
# 6. 编辑器通知
# ─────────────────────────────────────────────────────────
# 【修改前】（AttributeError：UE5 Python API 里根本没有这个函数）
#
# unreal.EditorUtilityLibrary.show_notification(
#     "Python 脚本执行完成！",
#     unreal.NotificationType.SUCCESS
# )
#
# 【问题分析】
# 翻 Intermediate/PythonStub/unreal.py 就知道：
#   - EditorUtilityLibrary 没有 show_notification 这个方法
#   - 整个 unreal 模块也没有 NotificationInfo / NotificationManager 类
#   - 蓝图里的"通知"走的是 Slate UI 框架（FNotificationInfo），这套是纯 C++ 的，
#     没有暴露到 Python —— Python 绑定只导出 UObject 体系里的 UFUNCTION。
#   - UE5 Python 里"通知用户"只有两条路：
#     1. EditorDialog.show_message —— 模态弹窗，会阻塞脚本，用户点 OK 才继续
#     2. SystemLibrary.print_string —— 非阻塞，文字画在视口上，几秒后自动消失
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.print_string(
    world,
    "Python 脚本执行完成！",
    print_to_screen=True,
    print_to_log=True,
    text_color=unreal.LinearColor(0.2, 1.0, 0.2, 1.0),  # 绿色
    duration=3.0,
)
unreal.log("通知已显示在屏幕上（print_string 是 UE5 Python 里唯一的非阻塞通知方式）")

# 备选：如果你需要用户"看到并确认"，用模态弹窗（会阻塞脚本执行）
# unreal.EditorDialog.show_message(
#     "提示",
#     "Python 脚本执行完成！",
#     unreal.AppMsgType.OK,
#     message_category=unreal.AppMsgCategory.INFO,
# )

# ─────────────────────────────────────────────────────────
# 7. 获取选中的资产/Actor
# ─────────────────────────────────────────────────────────
# 这在编写编辑器工具时非常有用

# 获取 Content Browser 中选中的资产
selected_assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
unreal.log(f"\nContent Browser 选中了 {len(selected_assets)} 个资产")
for asset_data in selected_assets:
    unreal.log(f"  资产: {asset_data.asset_name}")
    unreal.log(f"  路径: {asset_data.package_path}")
    unreal.log(f"  类型: {asset_data.asset_class_path}")

# 获取关卡中选中的 Actor
# 【修改前】（同样是废弃的 EditorLevelLibrary，只是脚本之前在 73 行就崩了，没执行到这）
# selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
#
# 【修改后】直接复用第 2 节创建的 actor_subsystem（EditorActorSubsystem）
selected_actors = actor_subsystem.get_selected_level_actors()
unreal.log(f"\n关卡中选中了 {len(selected_actors)} 个 Actor")
for actor in selected_actors:
    unreal.log(f"  Actor: {actor.get_name()} ({type(actor).__name__})")

# ─────────────────────────────────────────────────────────
# 8. 编辑器偏好设置
# ─────────────────────────────────────────────────────────
# 读取和设置编辑器偏好

# 获取编辑器偏好设置子系统
# 注意：具体可用的偏好设置取决于引擎版本

unreal.log("\n--- 编辑器信息汇总 ---")
unreal.log(f"引擎版本: {unreal.SystemLibrary.get_engine_version()}")
unreal.log(f"项目文件: {unreal.Paths.get_project_file_path()}")
unreal.log(f"命令行: {unreal.SystemLibrary.get_command_line()}")

unreal.log("\n第3课完成！你现在可以与 UE 编辑器进行基本交互了")
