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

习题可能用到的 API：
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例，用于创建/导入/导出资产
  asset_tools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory) -> Object  —— 用指定工厂创建新资产
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 在内容浏览器中创建目录
  unreal.EditorUtilityLibrary.get_selected_asset_data() -> Array[AssetData]  —— 获取内容浏览器中选中的资产数据
  unreal.Paths.project_saved_dir() -> str  —— 获取项目 Saved 目录的绝对路径（用于存储配置文件）
  unreal.ScopedSlowTask(work: float, desc: str)  —— 创建进度任务以显示进度对话框
  scoped_slow_task.make_dialog(can_cancel: bool) -> None  —— 显示进度对话框
  scoped_slow_task.enter_progress_frame(work: float, desc: str) -> None  —— 推进一帧进度并更新描述
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
# 【什么是 Editor Utility Widget？】
# UE5 提供的可视化编辑器扩展方式。你可以：
# 1. 在内容浏览器右键 → Editor Utilities → Editor Utility Widget
# 2. 在 UMG 设计器里拖拽按钮、文本框等控件
# 3. 每个按钮绑定一个 Python 函数（或蓝图函数）
# 这样就能做出带 UI 的编辑器工具，而不需要写 C++。
#
# 【create_asset 的参数详解】
# - asset_name: 新资产的名称（不含路径）
# - destination: 存放目录（如 /Game/EditorUtilities）
# - asset_class: 资产类型（如 EditorUtilityWidgetBlueprint）
# - factory: 工厂对象（告诉 UE "用什么方式创建这个资产"）
#
# 【为什么需要 Factory？】
# UE 的资产系统是"工厂模式"：每种资产类型对应一个工厂类。
# 比如 Blueprint 资产用 BlueprintFactory，Texture 用 TextureFactory。
# Factory 负责初始化新资产的默认属性。

def create_editor_utility_widget(name, destination="/Game/EditorUtilities"):
    """
    创建 Editor Utility Widget 资产

    注意：这个函数创建资产框架，
    具体的 UI 布局需要在编辑器中手动编辑
    """
    # 先确保目录存在（如果目录不存在，create_asset 会失败）
    # make_directory 是幂等的：目录已存在时返回 True 而不是报错
    unreal.EditorAssetLibrary.make_directory(destination)

    # AssetTools 是 UE 管理所有资产操作的核心服务
    # 包括：创建、重命名、移动、删除、导入、导出等
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # EditorUtilityWidgetBlueprintFactory 是专门用来创建
    # Editor Utility Widget 资产的工厂类
    factory = unreal.EditorUtilityWidgetBlueprintFactory()

    widget = asset_tools.create_asset(
        name,
        destination,
        unreal.EditorUtilityWidgetBlueprint,  # 资产类型
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
#
# 【设计模式】
# Editor Utility Widget 的 UI 层（UMG）只负责显示，
# Python 类只负责逻辑——这就是 MVC 模式的简化版。
# UI 按钮点击时，调用 Python 类的方法（如 on_button_click("batch_rename")）。
# Python 方法处理完逻辑后，更新状态变量，UI 刷新时读取这些变量。

class EditorToolBackend:
    """编辑器工具的 Python 后端"""

    def __init__(self):
        # 状态变量：UI 可以读取这些值来更新显示
        self.status_message = "就绪"
        self.progress = 0.0

    def on_button_click(self, button_id):
        """
        处理按钮点击——用字典做"路由分发"

        【为什么用字典而不是 if-else？】
        1. 可读性更好：一眼就能看到所有按钮及其处理函数
        2. 易扩展：新增按钮只需在字典里加一行
        3. 避免长长的 if-else 链
        """
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
        # get_selected_asset_data() 返回 AssetData 对象数组
        # AssetData 不是资产本身，只是资产的"元数据"（名称、类型、路径等）
        # 好处：不需要加载资产就能获取信息，速度快
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
    """
    通过 ID 运行已注册的脚本

    【exec() 的用法】
    exec(open(path).read()) 会：
    1. 读取文件内容为字符串
    2. 把字符串当作 Python 代码执行
    3. 执行的代码在当前作用域内运行（可以访问当前的变量）

    【安全注意】
    exec() 会执行任意代码，只应该用于你信任的脚本。
    这里用法正确——脚本都是项目内自己写的。
    """
    info = SCRIPT_REGISTRY.get(script_id)
    if not info:
        unreal.log_error(f"未知脚本: {script_id}")
        unreal.log(f"可用脚本: {list(SCRIPT_REGISTRY.keys())}")
        return

    import os
    # unreal.Paths.project_dir() 返回项目根目录（包含 .uproject 文件的目录）
    # 例如：C:/Users/xxx/MyProject/
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
#
# 【为什么用 JSON 文件而不是 Editor Preferences？】
# 1. Editor Preferences 是 UE 原生的配置系统，但 Python 访问不方便
# 2. JSON 文件简单直观，任何文本编辑器都能查看/修改
# 3. Saved 目录在 .gitignore 里，不会污染版本控制
# 4. 可以在 Python 和蓝图之间共享配置

import json
import os

class ToolConfig:
    """
    工具配置管理器

    配置保存在 ProjectSaved/PythonToolConfigs/{tool_name}.json
    """

    def __init__(self, tool_name):
        self.tool_name = tool_name
        # 配置目录：在项目的 Saved 文件夹下
        # Saved 文件夹是 UE 项目存放生成文件的地方（日志、配置、缓存等）
        config_dir = os.path.join(
            unreal.Paths.project_saved_dir(),
            "PythonToolConfigs"
        )
        # exist_ok=True: 目录已存在时不报错
        os.makedirs(config_dir, exist_ok=True)
        self.config_path = os.path.join(config_dir, f"{tool_name}.json")
        self.config = {}
        self.load()

    def load(self):
        """加载配置"""
        if os.path.exists(self.config_path):
            # json.load 从文件读取 JSON 并转为 Python 字典
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            unreal.log(f"已加载配置: {self.config_path}")
        else:
            self.config = {}

    def save(self):
        """保存配置"""
        # json.dump 写入文件，indent=2 让 JSON 有缩进，方便人读
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置值并保存"""
        self.config[key] = value
        # 每次 set 都保存，确保不会因为崩溃丢失配置
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
