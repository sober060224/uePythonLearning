"""
=============================================================
编辑器脚本 第2课：自定义菜单和工具栏扩展
=============================================================

学习目标：
  - 了解 UE 编辑器的扩展点
  - 使用 Python 注册自定义菜单项
  - 创建快捷工具栏按钮

核心概念：
  - Toolbar Extension: 在编辑器工具栏添加按钮
  - Menu Extension: 在编辑器菜单添加项
  - 这些通常通过 C++ 或 Editor Utility 实现
  - Python 脚本可以作为后端逻辑

本课可能用到的 API：
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例
  asset_tools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object  —— 用指定工厂创建资产并返回该资产
  unreal.EditorUtilityWidgetBlueprintFactory() -> EditorUtilityWidgetBlueprintFactory  —— 创建编辑器工具控件蓝图工厂
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 在内容浏览器中创建目录
  unreal.EditorUtilityLibrary.get_selected_asset_data() -> Array[AssetData]  —— 获取内容浏览器中选中的资产数据
  unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor]  —— 获取当前关卡选中的 Actor 列表
  unreal.Paths.project_dir() -> str  —— 获取项目根目录的绝对路径
  unreal.Paths.project_saved_dir() -> str  —— 获取项目 Saved 目录的绝对路径
  unreal.log(arg: Any) -> None  —— 输出一般消息到日志
  unreal.log_warning(arg: Any) -> None  —— 输出警告到日志
  unreal.log_error(arg: Any) -> None  —— 输出错误到日志
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 编辑器扩展概述
# ─────────────────────────────────────────────────────────
# UE 编辑器提供了多个扩展点：
#
# 菜单栏扩展:
#   - File 菜单
#   - Edit 菜单
#   - Window 菜单
#   - Help 菜单
#   - 自定义菜单
#
# 工具栏扩展:
#   - Level Editor 主工具栏
#   - Content Browser 工具栏
#   - Blueprint Editor 工具栏
#
# 右键菜单扩展:
#   - Content Browser 右键菜单
#   - Viewport 右键菜单
#   - Outliner 右键菜单

# ─────────────────────────────────────────────────────────
# 2. 使用 Editor Utility Widget 创建工具面板
# ─────────────────────────────────────────────────────────
# 最常用的方式：创建 Editor Utility Widget
# 然后用 Python 作为后端

def create_editor_utility_widget(name, destination="/Game/EditorUtilities"):
    """
    创建 Editor Utility Widget 资产

    注意：这个函数创建资产框架，
    具体的 UI 布局需要在编辑器中手动编辑
    """
    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    factory = unreal.EditorUtilityWidgetBlueprintFactory()

    widget = asset_tools.create_asset(
        name,
        destination,
        unreal.EditorUtilityWidgetBlueprint,
        factory
    )

    if widget:
        path = f"{destination}/{name}"
        unreal.log(f"已创建 Editor Utility Widget: {path}")
        unreal.log("请在编辑器中打开并设计 UI 布局")
        return widget

    return None

# ─────────────────────────────────────────────────────────
# 3. 为 Editor Utility 准备 Python 后端
# ─────────────────────────────────────────────────────────
# 下面是典型的 Python 后端模式

class EditorToolBackend:
    """编辑器工具的 Python 后端"""

    def __init__(self):
        self.status_message = "就绪"
        self.progress = 0.0

    def on_button_click(self, button_id):
        """处理按钮点击"""
        unreal.log(f"按钮 {button_id} 被点击")

        handlers = {
            "batch_rename": self._batch_rename,
            "align_actors": self._align_actors,
            "export_selected": self._export_selected,
            "cleanup_assets": self._cleanup_assets,
        }

        handler = handlers.get(button_id)
        if handler:
            handler()
        else:
            unreal.log_warning(f"未知的按钮: {button_id}")

    def _batch_rename(self):
        """批量重命名"""
        assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
        if not assets:
            self.status_message = "请先选择资产"
            return

        self.status_message = f"选中了 {len(assets)} 个资产"
        unreal.log(self.status_message)

    def _align_actors(self):
        """对齐 Actor"""
        actors = unreal.EditorLevelLibrary.get_selected_level_actors()
        if len(actors) < 2:
            self.status_message = "请至少选中 2 个 Actor"
            return

        self.status_message = f"对齐 {len(actors)} 个 Actor"
        unreal.log(self.status_message)

    def _export_selected(self):
        """导出选中的资产"""
        assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
        self.status_message = f"准备导出 {len(assets)} 个资产"
        unreal.log(self.status_message)

    def _cleanup_assets(self):
        """清理未使用资产"""
        self.status_message = "正在扫描未使用资产..."
        unreal.log(self.status_message)

    def get_status(self):
        """获取当前状态"""
        return self.status_message

# ─────────────────────────────────────────────────────────
# 4. 命令行方式注册和运行脚本
# ─────────────────────────────────────────────────────────

# UE 支持通过命令行运行 Python 脚本
# 可以将脚本注册为可重复执行的命令

SCRIPT_REGISTRY = {
    "project_report": {
        "path": "PythonLearning/02_AssetManagement/01_list_assets.py",
        "description": "生成项目资产报告",
        "category": "Tools",
    },
    "batch_rename": {
        "path": "PythonLearning/02_AssetManagement/03_asset_actions.py",
        "description": "批量重命名工具",
        "category": "Tools",
    },
    "cleanup": {
        "path": "PythonLearning/08_AdvancedTopics/01_batch_operations.py",
        "description": "批量清理工具",
        "category": "Tools",
    },
}

def list_available_scripts():
    """列出所有可用的脚本工具"""
    unreal.log("\n可用的 Python 工具脚本:")
    unreal.log("-" * 40)
    for script_id, info in SCRIPT_REGISTRY.items():
        unreal.log(f"  [{info['category']}] {script_id}")
        unreal.log(f"    描述: {info['description']}")
        unreal.log(f"    路径: {info['path']}")

def run_script(script_id):
    """通过 ID 运行已注册的脚本"""
    info = SCRIPT_REGISTRY.get(script_id)
    if not info:
        unreal.log_error(f"未知脚本: {script_id}")
        unreal.log(f"可用脚本: {list(SCRIPT_REGISTRY.keys())}")
        return

    import os
    project_dir = unreal.Paths.project_dir()
    script_path = os.path.join(project_dir, info["path"])

    if os.path.exists(script_path):
        unreal.log(f"正在运行: {info['description']}")
        exec(open(script_path).read())
    else:
        unreal.log_error(f"脚本文件不存在: {script_path}")

# ─────────────────────────────────────────────────────────
# 5. 使用 Editor Preferences 存储工具配置
# ─────────────────────────────────────────────────────────

# 可以创建一个配置文件来保存工具的持久化设置
import json
import os

class ToolConfig:
    """工具配置管理器"""

    def __init__(self, tool_name):
        self.tool_name = tool_name
        config_dir = os.path.join(
            unreal.Paths.project_saved_dir(),
            "PythonToolConfigs"
        )
        os.makedirs(config_dir, exist_ok=True)
        self.config_path = os.path.join(config_dir, f"{tool_name}.json")
        self.config = {}
        self.load()

    def load(self):
        """加载配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            unreal.log(f"已加载配置: {self.config_path}")
        else:
            self.config = {}

    def save(self):
        """保存配置"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置值并保存"""
        self.config[key] = value
        self.save()

# 使用示例
# config = ToolConfig("BatchRenamer")
# config.set("prefix", "SM_")
# config.set("suffix", "")
# prefix = config.get("prefix", "BP_")

# ─────────────────────────────────────────────────────────
# 6. 键盘快捷键
# ─────────────────────────────────────────────────────────
# UE 的快捷键系统主要通过 Editor Preferences 管理
# Python 脚本本身不能直接注册快捷键
# 但可以通过 Editor Utility Widget 的按钮绑定快捷键

# 推荐的快捷键方案：
SHORTCUT_SUGGESTIONS = {
    "Ctrl+Shift+R": "批量重命名",
    "Ctrl+Shift+A": "对齐工具",
    "Ctrl+Shift+E": "导出选中资产",
    "Ctrl+Shift+G": "对齐到网格",
    "Ctrl+Shift+D": "均匀分布",
}

unreal.log("编辑器脚本第2课完成！")
unreal.log("提示：创建 Editor Utility Widget 来制作可视化界面")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个 Editor Utility Widget，包含 3 个按钮，
#    每个按钮调用不同的 Python 工具函数
# 2. 实现一个配置系统，让工具记住用户的偏好设置
# 3. 创建一个 "最近使用的工具" 列表
# 4. 设计一个工具面板，包含进度条和状态文本
