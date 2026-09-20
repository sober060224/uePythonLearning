"""
=============================================================
编辑器脚本 第3课：构建自定义编辑器工具
=============================================================

学习目标：
  - 组合前两课的知识构建完整的编辑器工具
  - 实战：资产检查器工具
  - 实战：关卡布局工具

本课将创建两个完整的、可直接使用的编辑器工具

本课可能用到的 API：
  unreal.get_editor_subsystem(subsystem: Class) -> EditorSubsystem  —— 获取指定类型的编辑器子系统实例
  unreal.EditorActorSubsystem.get_selected_level_actors() -> Array[Actor]  —— 获取当前关卡选中的 Actor 列表
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出目录下所有资产路径
  unreal.EditorAssetLibrary.does_directory_exist(directory_path: str) -> bool  —— 判断指定目录是否存在
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 依据资产路径查询资产数据
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  —— 查找引用该资产的其他包路径
  unreal.ScopedSlowTask(work: float, desc: Union[Text, str] = "", enabled: bool = True)  —— 创建进度任务以显示进度
  scoped_slow_task.make_dialog(can_cancel: bool = False, allow_in_pie: bool = False) -> None  —— 创建进度对话框
  scoped_slow_task.enter_progress_frame(work: float = 1.0, desc: Union[Text, str] = "") -> None  —— 推进一帧进度并更新描述
  scoped_slow_task.should_cancel() -> bool  —— 查询用户是否取消该任务
  unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int  —— 开启一个可撤销事务并返回其索引
  unreal.SystemLibrary.end_transaction() -> int  —— 结束并提交当前事务
  unreal.SystemLibrary.cancel_transaction(index: int) -> None  —— 取消指定索引的事务并回滚
  asset_data.asset_name -> Name  —— 资产的名称
  asset_data.asset_class_path -> TopLevelAssetPath  —— 资产所属类的完整路径
  actor.get_actor_location() -> Vector  —— 获取 Actor 的世界坐标位置
  actor.set_actor_location(new_location: Vector, sweep: bool, teleport: bool) -> Optional[HitResult]  —— 设置 Actor 的世界坐标位置
  actor.get_actor_rotation() -> Rotator  —— 获取 Actor 的旋转角度
  actor.set_actor_rotation(new_rotation: Rotator, teleport_physics: bool) -> bool  —— 设置 Actor 的旋转角度
  unreal.log(arg: Any) -> None  —— 输出一般消息到日志
  unreal.log_warning(arg: Any) -> None  —— 输出警告到日志
=============================================================
"""

import unreal
import math
import random

# ═════════════════════════════════════════════════════════
# 工具 1: 资产健康检查器 (Asset Health Checker)
# ═════════════════════════════════════════════════════════

class AssetHealthChecker:
    """
    项目资产健康检查工具
    检查命名规范、引用、文件大小等问题
    """

    def __init__(self):
        self.issues = []
        self.stats = {
            "total_assets": 0,
            "warnings": 0,
            "errors": 0,
            "passed": 0,
        }

    def check_project(self, search_path="/Game"):
        """对整个项目执行健康检查"""
        self.issues = []
        assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
        self.stats["total_assets"] = len(assets)

        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  资产健康检查 - {search_path}")
        unreal.log(f"  扫描 {len(assets)} 个资产...")
        unreal.log(f"{'=' * 60}")

        task = unreal.ScopedSlowTask(len(assets), "资产健康检查...")
        task.make_dialog(True)

        for asset_path in assets:
            if task.should_cancel():
                break

            task.enter_progress_frame(1.0, asset_path.split("/")[-1])

            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            self._check_single_asset(asset_path)

        self._print_report()
        return self.issues

    def _check_single_asset(self, asset_path):
        """检查单个资产"""
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        name = asset_data.asset_name
        class_str = str(asset_data.asset_class_path)

        # 检查1: 命名规范
        self._check_naming(name, asset_path, class_str)

        # 检查2: 孤立资产（无引用）
        self._check_references(asset_path, name)

        # 检查3: 路径深度
        self._check_path_depth(asset_path, name)

    def _check_naming(self, name, path, class_str):
        """检查命名规范"""
        prefix_map = {
            "StaticMesh": "SM_",
            "Texture2D": "T_",
            "Material": "M_",
            "MaterialInstanceConstant": "MI_",
            "Blueprint": "BP_",
            "ParticleSystem": "PS_",
            "SoundWave": "S_",
            "WidgetBlueprint": "WBP_",
        }

        for class_key, expected_prefix in prefix_map.items():
            if class_key in class_str and not name.startswith(expected_prefix):
                self._add_issue(
                    "warning",
                    f"命名不规范",
                    f"{name} 应使用 {expected_prefix} 前缀",
                    path
                )
                break

    def _check_references(self, asset_path, name):
        """检查引用情况"""
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )
        external_refs = [r for r in refs if r != asset_path]

        if len(external_refs) == 0:
            self._add_issue(
                "warning",
                "孤立资产",
                f"{name} 没有被任何其他资产引用",
                asset_path
            )

    def _check_path_depth(self, asset_path, name):
        """检查路径深度"""
        depth = len(asset_path.split("/"))
        if depth > 6:
            self._add_issue(
                "info",
                "路径过深",
                f"{name} 的路径有 {depth} 层，建议简化目录结构",
                asset_path
            )

    def _add_issue(self, severity, category, message, path):
        """添加一个问题记录"""
        self.issues.append({
            "severity": severity,
            "category": category,
            "message": message,
            "path": path,
        })

        if severity == "error":
            self.stats["errors"] += 1
        elif severity == "warning":
            self.stats["warnings"] += 1
        else:
            self.stats["passed"] += 1

    def _print_report(self):
        """打印检查报告"""
        unreal.log(f"\n{'─' * 60}")
        unreal.log(f"  检查报告")
        unreal.log(f"{'─' * 60}")
        unreal.log(f"  扫描资产: {self.stats['total_assets']}")
        unreal.log(f"  错误:     {self.stats['errors']}")
        unreal.log(f"  警告:     {self.stats['warnings']}")
        unreal.log(f"{'─' * 60}")

        if self.issues:
            # 按严重度排序
            severity_order = {"error": 0, "warning": 1, "info": 2}
            sorted_issues = sorted(
                self.issues,
                key=lambda x: severity_order.get(x["severity"], 3)
            )

            for issue in sorted_issues[:50]:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                    issue["severity"], "?"
                )
                unreal.log(
                    f"  {icon} [{issue['category']}] {issue['message']}"
                )
                unreal.log(f"     路径: {issue['path']}")

        else:
            unreal.log("  ✅ 没有发现问题！")

# ═════════════════════════════════════════════════════════
# 工具 2: 关卡布局工具 (Level Layout Tool)
# ═════════════════════════════════════════════════════════

class LevelLayoutTool:
    """
    关卡布局辅助工具
    提供排列、分布、对齐等功能
    """

    @staticmethod
    def arrange_in_circle(radius=500.0, z_height=0.0):
        """将选中的 Actor 排列成圆形"""
        # 【修改前】unreal.EditorLevelLibrary.get_selected_level_actors()
        # 【问题分析】EditorLevelLibrary 已废弃（DeprecationWarning），
        # 选 Actor 的操作搬到了 EditorActorSubsystem。
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if len(actors) < 2:
            unreal.log_warning("请至少选中 2 个 Actor")
            return

        count = len(actors)
        angle_step = 360.0 / count

        # 【修改前】unreal.Transactions.begin_transaction("排列为圆形")
        # 【问题分析】unreal.Transactions 类在 stub 里不存在 —— 事务方法在
        # SystemLibrary 上，而且签名不同：
        #   begin_transaction(context, description, primary_object) -> int
        #     3 个参数：context 写脚本名；description 写操作名（进撤销历史）；
        #     primary_object 写被修改的主对象（这里拿第一个 Actor）
        #   end_transaction() / cancel_transaction(索引)
        # 本文件 4 个工具函数原来全是错误写法，下面不再重复解释。
        token = unreal.SystemLibrary.begin_transaction("Python脚本", "排列为圆形", actors[0])

        for i, actor in enumerate(actors):
            angle = math.radians(i * angle_step)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            new_loc = unreal.Vector(x, y, z_height)
            actor.set_actor_location(new_loc, False, False)

            # 让 Actor 朝向圆心
            look_at = unreal.Vector(0, 0, z_height)
            direction = look_at - new_loc
            yaw = math.degrees(math.atan2(direction.y, direction.x))
            actor.set_actor_rotation(unreal.Rotator(0, yaw, 0), False)

        unreal.SystemLibrary.end_transaction()
        unreal.log(f"已将 {count} 个 Actor 排列为半径 {radius} 的圆形")

    @staticmethod
    def arrange_in_line(start_pos=None, direction="x",
                         spacing=200.0):
        """将选中的 Actor 排列成直线"""
        # 【修改前】unreal.EditorLevelLibrary.get_selected_level_actors()（已废弃）
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if len(actors) < 2:
            unreal.log_warning("请至少选中 2 个 Actor")
            return

        if start_pos is None:
            start_pos = actors[0].get_actor_location()

        # 【修改前】unreal.Transactions.begin_transaction("排列为直线")
        # （Transactions 类不存在，正确用法见 arrange_in_circle 的注释）
        token = unreal.SystemLibrary.begin_transaction("Python脚本", "排列为直线", actors[0])

        axis_map = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
        dx, dy, dz = axis_map.get(direction.lower(), (1, 0, 0))

        for i, actor in enumerate(actors):
            new_loc = unreal.Vector(
                start_pos.x + dx * spacing * i,
                start_pos.y + dy * spacing * i,
                start_pos.z + dz * spacing * i,
            )
            actor.set_actor_location(new_loc, False, False)

        unreal.SystemLibrary.end_transaction()
        unreal.log(f"已将 {len(actors)} 个 Actor 排列为直线")

    @staticmethod
    def scatter_randomly(bounds_min, bounds_max,
                          random_rotation=True):
        """在指定范围内随机散布 Actor"""
        # 【修改前】unreal.EditorLevelLibrary.get_selected_level_actors()（已废弃）
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if not actors:
            unreal.log_warning("请先选中 Actor")
            return

        # 【修改前】unreal.Transactions.begin_transaction("随机散布")
        # （Transactions 类不存在，正确用法见 arrange_in_circle 的注释）
        token = unreal.SystemLibrary.begin_transaction("Python脚本", "随机散布", actors[0])

        for actor in actors:
            loc = unreal.Vector(
                random.uniform(bounds_min.x, bounds_max.x),
                random.uniform(bounds_min.y, bounds_max.y),
                random.uniform(bounds_min.z, bounds_max.z),
            )
            actor.set_actor_location(loc, False, False)

            if random_rotation:
                rot = unreal.Rotator(
                    0,
                    random.uniform(0, 360),
                    0,
                )
                actor.set_actor_rotation(rot, False)

        unreal.SystemLibrary.end_transaction()
        unreal.log(f"已随机散布 {len(actors)} 个 Actor")

    @staticmethod
    def mirror_actors(axis="x"):
        """沿指定轴镜像选中的 Actor"""
        # 【修改前】unreal.EditorLevelLibrary.get_selected_level_actors()（已废弃）
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if not actors:
            unreal.log_warning("请先选中 Actor")
            return

        # 【修改前】unreal.Transactions.begin_transaction("镜像 Actor")
        # （Transactions 类不存在，正确用法见 arrange_in_circle 的注释）
        token = unreal.SystemLibrary.begin_transaction("Python脚本", "镜像 Actor", actors[0])

        for actor in actors:
            loc = actor.get_actor_location()
            if axis == "x":
                loc.x = -loc.x
            elif axis == "y":
                loc.y = -loc.y
            elif axis == "z":
                loc.z = -loc.z
            actor.set_actor_location(loc, False, False)

            # 镜像旋转
            rot = actor.get_actor_rotation()
            if axis == "x":
                rot.yaw = -rot.yaw
            elif axis == "y":
                rot.yaw = 180 - rot.yaw

            actor.set_actor_rotation(rot)

        unreal.SystemLibrary.end_transaction()
        unreal.log(f"已沿 {axis.upper()} 轴镜像 {len(actors)} 个 Actor")

# ═════════════════════════════════════════════════════════
# 使用示例
# ═════════════════════════════════════════════════════════

# 运行资产健康检查
# checker = AssetHealthChecker()
# checker.check_project("/Game")

# 关卡布局工具
# LevelLayoutTool.arrange_in_circle(500.0)
# LevelLayoutTool.arrange_in_line(direction="x", spacing=300.0)
# LevelLayoutTool.scatter_randomly(
#     unreal.Vector(-1000, -1000, 0),
#     unreal.Vector(1000, 1000, 0)
# )
# LevelLayoutTool.mirror_actors("x")

unreal.log("编辑器脚本第3课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 扩展 AssetHealthChecker：添加纹理分辨率检查
#    （是否有非2的幂次分辨率）
# 2. 为 LevelLayoutTool 添加 "排列为网格" 功能
# 3. 创建一个 "场景装饰器" 工具：沿路径散布装饰物
# 4. 将工具整合到一个 Editor Utility Widget 中
