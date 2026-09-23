"""
=============================================================
通用辅助函数库
=============================================================

提供整个学习项目中复用的工具函数。
可以在其他脚本中通过以下方式导入:

    import sys
    sys.path.append("/path/to/PythonLearning")
    from utils.helpers import *

=============================================================
"""

import unreal
import math
import time
import os


# ─────────────────────────────────────────────────────────
# 日志工具
# ─────────────────────────────────────────────────────────


def log_section(title):
    """输出带标题的分隔区域"""
    line = "=" * 50
    unreal.log(f"\n{line}")
    unreal.log(f"  {title}")
    unreal.log(f"{line}")


def log_info(message):
    """信息级别日志"""
    unreal.log(f"[INFO] {message}")


def log_warn(message):
    """警告级别日志"""
    unreal.log_warning(f"[WARN] {message}")


def log_err(message):
    """错误级别日志"""
    unreal.log_error(f"[ERROR] {message}")


def show_screen(message, color=None, duration=3.0):
    """在屏幕上显示消息（编辑器内 print_string 需要有效的 world_context）"""
    if color is None:
        color = [1.0, 1.0, 1.0, 1.0]
    # 【修改前】print_string 第一个参数传 None —— 编辑器里会静默无输出。
    # 【问题分析】print_string 的签名是 (world_context_object, string, ...)，
    #   这里先从 UnrealEditorSubsystem 取编辑器 World 作为 world_context；
    #   取不到 World 时退化为 unreal.log 输出，保证 helper 不崩。
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world:
        unreal.SystemLibrary.print_string(world, message, True, True, color, duration)
    else:
        unreal.log(message)


# ─────────────────────────────────────────────────────────
# 资产查询工具
# ─────────────────────────────────────────────────────────


def get_all_assets(search_path="/Game", recursive=True):
    """获取所有资产路径列表"""
    return unreal.EditorAssetLibrary.list_assets(search_path, recursive=recursive)


def get_assets_by_type(class_name, search_path="/Game"):
    """按类型查找资产"""
    all_assets = get_all_assets(search_path)
    matching = []
    for path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(path)
        if class_name.lower() in str(asset_data.asset_class_path).lower():
            matching.append(asset_data)
    return matching


def load_asset_safe(asset_path):
    """安全加载资产"""
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        log_warn(f"资产不存在: {asset_path}")
        return None
    return unreal.EditorAssetLibrary.load_asset(asset_path)


def asset_exists(asset_path):
    """检查资产是否存在"""
    return unreal.EditorAssetLibrary.does_asset_exist(asset_path)


# ─────────────────────────────────────────────────────────
# Actor 查询工具
# ─────────────────────────────────────────────────────────


def get_all_actors():
    """获取关卡中所有 Actor"""
    # 【UE5】EditorLevelLibrary 属于已废弃的 Editor Scripting Utilities 插件，
    #   Actor 查询统一走 EditorActorSubsystem（调用旧 API 会打 DeprecationWarning）。
    return unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()


def get_selected_actors():
    """获取选中的 Actor"""
    return unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_selected_level_actors()


def get_actors_by_label(label_contains):
    """按标签搜索 Actor"""
    all_actors = get_all_actors()
    # get_actor_label() 返回的是 unreal.Name，不是 str —— 没有 .lower()，
    #   先 str() 转换再比较。
    return [
        a
        for a in all_actors
        if label_contains.lower() in str(a.get_actor_label()).lower()
    ]


def get_actors_by_class(actor_class):
    """按类型搜索 Actor"""
    return [a for a in get_all_actors() if isinstance(a, actor_class)]


def find_actor(label):
    """通过精确标签查找 Actor"""
    for actor in get_all_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


# ─────────────────────────────────────────────────────────
# 数学工具
# ─────────────────────────────────────────────────────────


def vector_from_dict(d):
    """从 dict 创建 Vector"""
    return unreal.Vector(d.get("x", 0), d.get("y", 0), d.get("z", 0))


def rotator_from_dict(d):
    """从 dict 创建 Rotator"""
    # 【易错点】Rotator 的 Python 构造函数按 (roll, pitch, yaw) 取位置参数，
    #   写成 Rotator(pitch, yaw, roll) 会让三个角度整体串位，所以这里用关键字参数。
    return unreal.Rotator(
        pitch=d.get("pitch", 0), yaw=d.get("yaw", 0), roll=d.get("roll", 0)
    )


def distance_between(actor1, actor2):
    """计算两个 Actor 之间的距离"""
    loc1 = actor1.get_actor_location()
    loc2 = actor2.get_actor_location()
    return (loc2 - loc1).length()


def lerp_vector(v1, v2, t):
    """线性插值两个 Vector"""
    return v1 * (1 - t) + v2 * t


def direction_to_rotation(direction):
    yaw = math.degrees(math.atan2(direction.y, direction.x))
    pitch = math.degrees(
        math.atan2(direction.z, math.sqrt(direction.x**2 + direction.y**2))
    )
    return unreal.Rotator(pitch=-pitch, yaw=yaw, roll=0)


# ─────────────────────────────────────────────────────────
# 路径工具
# ─────────────────────────────────────────────────────────


def get_project_dir():
    """获取项目根目录"""
    return unreal.Paths.project_dir()


def get_saved_dir():
    """获取 Saved 目录"""
    return unreal.Paths.project_saved_dir()


def get_content_dir():
    """获取 Content 目录"""
    return unreal.Paths.project_content_dir()


def make_project_path(relative_path):
    """构建项目内完整路径"""
    return os.path.join(get_project_dir(), relative_path)


# ─────────────────────────────────────────────────────────
# 事务工具
# ─────────────────────────────────────────────────────────

# 【修改前】本节三个函数都调用了 unreal.Transactions.xxx —— 这个类根本不存在。
#
# 【问题分析】
# 翻 Intermediate/PythonStub/unreal.py：事务相关的方法其实在 SystemLibrary 上，
# 而且签名和原来写的完全不同：
#   begin_transaction(context: str, description: Text, primary_object: Object) -> int
#     - 3 个参数：上下文（一般写脚本/工具名）、描述、被修改的主对象（撤销时定位用）
#     - 返回值是"事务索引"，cancel 时必须传回去
#   end_transaction() -> int
#   cancel_transaction(index: int) -> None
#     - 必须传 begin_transaction 返回的索引，不是零参数调用
# 原来的写法不仅类名错了（Transactions 不存在），连参数个数都不对。


def begin_transaction(name, primary_object=None):
    """开始一个撤销事务，返回事务索引（cancel 时要用）。

    参数:
        name: 事务描述（会出现在编辑器撤销历史里）
        primary_object: 被修改的主对象；不传就用编辑器 world 顶上
    """
    if primary_object is None:
        primary_object = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()
    return unreal.SystemLibrary.begin_transaction("Python脚本", name, primary_object)


def end_transaction():
    """结束事务（把这一段操作提交进撤销栈）"""
    unreal.SystemLibrary.end_transaction()


def cancel_transaction(token):
    """取消事务。token 是 begin_transaction 的返回值"""
    unreal.SystemLibrary.cancel_transaction(token)


class TransactionContext:
    """事务上下文管理器"""

    def __init__(self, name, primary_object=None):
        self.name = name
        self.primary_object = primary_object
        self.token = None

    def __enter__(self):
        self.token = begin_transaction(self.name, self.primary_object)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            cancel_transaction(self.token)
            log_err(f"事务 '{self.name}' 失败: {exc_val}")
        else:
            end_transaction()
            log_info(f"事务 '{self.name}' 完成")
        return False  # 不抑制异常


# 使用示例:
# with TransactionContext("批量移动"):
#     for actor in actors:
#         actor.set_actor_location(new_loc)


# ─────────────────────────────────────────────────────────
# 计时工具
# ─────────────────────────────────────────────────────────


class Timer:
    """简单的计时器"""

    def __init__(self, label=""):
        self.label = label
        self.start_time = None
        self.elapsed = 0.0

    def start(self):
        self.start_time = time.time()

    def stop(self):
        if self.start_time:
            self.elapsed = time.time() - self.start_time
            log_info(f"{self.label}: {self.elapsed:.3f} 秒")
            return self.elapsed
        return 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# 使用示例:
# with Timer("处理资产"):
#     for asset in assets:
#         process(asset)
