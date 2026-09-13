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
# EditorLevelLibrary 提供关卡相关的操作
current_level = unreal.EditorLevelLibrary.get_editor_world()
if current_level:
    unreal.log(f"当前关卡: {current_level.get_name()}")
    unreal.log(f"关卡路径: {current_level.get_path_name()}")

# 获取关卡中的所有 Actor
all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
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
combined = unreal.Paths.combine([
    unreal.Paths.project_dir(),
    "Content",
    "Characters"
])
unreal.log(f"\n拼接路径示例: {combined}")

# 路径标准化
messy_path = "/Game//Characters/../Materials/MyMaterial"
normalized = unreal.Paths.normalize_path_name(messy_path)
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
# 对于耗时操作，使用进度条给用户反馈

# 使用 ScopedSlowTask 创建进度条
task = unreal.ScopedSlowTask(5.0, "正在执行操作...")
task.make_dialog(True)  # True = 允许取消

for i in range(5):
    # 检查用户是否点击了取消
    if task.should_cancel():
        unreal.log("用户取消了操作")
        break

    # 更新进度
    task.enter_progress_frame(1.0, f"处理第 {i+1} 步...")

    # 模拟工作（实际项目中替换为真实操作）
    import time
    time.sleep(0.5)

unreal.log("操作完成！")

# ─────────────────────────────────────────────────────────
# 6. 编辑器通知
# ─────────────────────────────────────────────────────────
# 在编辑器右下角显示通知

# 简单通知
unreal.EditorUtilityLibrary.show_notification(
    "Python 脚本执行完成！",
    unreal.NotificationType.SUCCESS
)

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
selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
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

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个函数，打印当前关卡中所有 StaticMeshActor 的位置
# 2. 编写一个脚本，用进度条遍历所有资产并统计每种类型的数量
# 3. 编写一个工具，选中关卡中的 Actor 后自动在日志中打印
#    其详细信息（名称、位置、旋转、缩放）
