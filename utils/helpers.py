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
    """在屏幕上显示消息"""
    if color is None:
        color = [1.0, 1.0, 1.0, 1.0]
    unreal.SystemLibrary.print_string(None, message, True, True, color, duration)


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
    return unreal.EditorLevelLibrary.get_all_level_actors()

def get_selected_actors():
    """获取选中的 Actor"""
    return unreal.EditorLevelLibrary.get_selected_level_actors()

def get_actors_by_label(label_contains):
    """按标签搜索 Actor"""
    all_actors = get_all_actors()
    return [
        a for a in all_actors
        if label_contains.lower() in a.get_actor_label().lower()
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
    return unreal.Rotator(d.get("pitch", 0), d.get("yaw", 0), d.get("roll", 0))

def distance_between(actor1, actor2):
    """计算两个 Actor 之间的距离"""
    loc1 = actor1.get_actor_location()
    loc2 = actor2.get_actor_location()
    return (loc2 - loc1).length()

def lerp_vector(v1, v2, t):
    """线性插值两个 Vector"""
    return v1 * (1 - t) + v2 * t

def direction_to_rotation(direction):
    """将方向向量转换为旋转"""
    yaw = math.degrees(math.atan2(direction.y, direction.x))
    pitch = math.degrees(math.atan2(
        direction.z,
        math.sqrt(direction.x**2 + direction.y**2)
    ))
    return unreal.Rotator(-pitch, yaw, 0)


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

def begin_transaction(name):
    """开始事务"""
    unreal.Transactions.begin_transaction(name)

def end_transaction():
    """结束事务"""
    unreal.Transactions.end_transaction()

def cancel_transaction():
    """取消事务"""
    unreal.Transactions.cancel_transaction()

class TransactionContext:
    """事务上下文管理器"""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        begin_transaction(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            cancel_transaction()
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
