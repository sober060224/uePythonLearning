"""
=============================================================
编辑器脚本 第3课：构建自定义编辑器工具
=============================================================

学习目标：
  - 组合前两课的知识构建完整的编辑器工具
  - 实战：资产检查器工具
  - 实战：关卡布局工具

本课将创建两个完整的、可直接使用的编辑器工具

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True) -> Array[str]  —— 递归列出目录下所有资产路径
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 依据资产路径查询资产数据
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str) -> Array[str]  —— 查找引用该资产的其他包
  unreal.EditorAssetLibrary.does_directory_exist(directory_path: str) -> bool  —— 判断目录是否存在
  unreal.ScopedSlowTask(work: float, desc: str)  —— 创建进度对话框（长时间操作必须有，否则编辑器会"卡死"）
  scoped_slow_task.enter_progress_frame(work: float, desc: str) -> None  —— 更新进度条和描述文字
  actor.duplicate_actor(offset_location: Vector) -> Actor  —— 复制 Actor 到指定偏移位置
  unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int  —— 开启可撤销事务
=============================================================
"""

import contextlib
import math
import random
import unreal

# ─────────────────────────────────────────────────────────
# 工具：编辑器事务上下文
# ─────────────────────────────────────────────────────────
@contextlib.contextmanager
def editor_transaction(description, context):
    """
    在编辑器事务里执行一段操作：

      - 正常结束    -> 提交事务（用户可以 Ctrl+Z 一次性撤销整段操作）
      - 抛异常      -> cancel_transaction 回滚，撤销栈不会留在"半开"状态
      - 中途 return -> __exit__ 照样执行，收尾不会漏
    """
    token = unreal.SystemLibrary.begin_transaction("Python脚本", description, context)
    try:
        yield token
    except BaseException:
        unreal.SystemLibrary.cancel_transaction(token)
        raise
    else:
        unreal.SystemLibrary.end_transaction()


# ═════════════════════════════════════════════════════════
# 工具 1: 资产健康检查器 (Asset Health Checker)
# ═════════════════════════════════════════════════════════
#
# 【这个工具解决什么问题？】
# 项目资产多了之后，手动检查命名规范、孤立引用等非常耗时。
# 这个工具自动扫描整个项目，列出所有潜在问题。

class AssetHealthChecker:
    """
    项目资产健康检查工具
    检查命名规范、引用、文件大小等问题
    """

    def __init__(self):
        # 问题列表：每次检查前会清空
        self.issues = []
        # 统计数据：记录各类问题的数量
        self.stats = {
            "total_assets": 0,
            "warnings": 0,
            "errors": 0,
            "passed": 0,
        }

    def check_project(self, search_path="/Game"):
        """
        对整个项目执行健康检查

        【search_path 参数】
        - "/Game" 是所有内容资产的根目录（对应磁盘上的 Content/ 文件夹）
        - 也可以指定子目录如 "/Game/Characters" 只检查特定目录
        """
        self.issues = []
        # list_assets 递归列出目录下所有资产路径
        # 返回值类似 ["/Game/MyFolder/Asset1", "/Game/MyFolder/Asset2", ...]
        assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
        self.stats["total_assets"] = len(assets)

        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  资产健康检查 - {search_path}")
        unreal.log(f"  扫描 {len(assets)} 个资产...")
        unreal.log(f"{'=' * 60}")

        # 【ScopedSlowTask：进度对话框】
        # 当操作耗时超过 1-2 秒时，必须显示进度条
        # 否则编辑器会"卡死"（主线程被占用，UI 不更新）
        # 参数：总工作量、描述文字
        task = unreal.ScopedSlowTask(len(assets), "资产健康检查...")
        # make_dialog(True): True = 允许用户点击"取消"按钮
        task.make_dialog(True)

        for asset_path in assets:
            # 【用户取消检测】
            # 每处理一个资产都要检查用户是否点了"取消"
            # 这是编辑器工具的礼仪——让用户能中断长时间操作
            if task.should_cancel():
                break

            # 进度条前进 1 单位，并更新显示文字
            # 只显示文件名（最后一个 / 后面的部分）而不是完整路径
            task.enter_progress_frame(1.0, asset_path.split("/")[-1])

            # 跳过目录（list_assets 会返回目录路径）
            # does_directory_exist 检查路径是否是目录
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            self._check_single_asset(asset_path)

        self._print_report()
        return self.issues

    def _check_single_asset(self, asset_path):
        """
        检查单个资产

        【find_asset_data vs load_asset】
        - find_asset_data: 只读取资产的元数据（名称、类型），不加载资产内容
        - load_asset: 会加载完整的资产到内存（慢，且可能失败）
        检查命名规范只需要元数据，用 find_asset_data 更高效
        """
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # asset_name: 资产的短名称（不含路径），如 "MyTexture"
        name = asset_data.asset_name
        # asset_class_path: 资产类型，如 "/Script/Engine.Texture2D"
        # str() 转为字符串后可以做字符串匹配
        class_str = str(asset_data.asset_class_path)

        # 检查1: 命名规范
        self._check_naming(name, asset_path, class_str)

        # 检查2: 孤立资产（无引用）
        self._check_references(asset_path, name)

        # 检查3: 路径深度
        self._check_path_depth(asset_path, name)

    def _check_naming(self, name, path, class_str):
        """
        检查命名规范

        【UE 项目的命名约定】
        不同类型的资产有不同的前缀要求：
        - StaticMesh → SM_（如 SM_Rock）
        - Texture2D → T_（如 T_Wood_D）
        - Material → M_（如 M_Wood）
        - Blueprint → BP_（如 BP_Player）
        这是行业标准，团队协作时非常重要。
        """
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
            # class_str 可能包含多个类名，用 "in" 做模糊匹配
            # 比如 MaterialInstanceConstant 的 class_str 里也有 "Material"
            if class_key in class_str and not name.startswith(expected_prefix):
                self._add_issue(
                    "warning",
                    f"命名不规范",
                    f"{name} 应使用 {expected_prefix} 前缀",
                    path
                )
                break

    def _check_references(self, asset_path, name):
        """
        检查引用情况

        【"孤立资产"是什么？】
        如果一个资产没有被任何其他资产引用，它可能是：
        1. 未使用的废资产（应该删除）
        2. 被硬引用但没被软引用（需要检查）
        3. 通过路径字符串动态加载（工具检测不出来）
        所以孤立资产只是"警告"，不是"错误"。
        """
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )
        # 排除自引用（资产引用自己）
        external_refs = [r for r in refs if r != asset_path]

        if len(external_refs) == 0:
            self._add_issue(
                "warning",
                "孤立资产",
                f"{name} 没有被任何其他资产引用",
                asset_path
            )

    def _check_path_depth(self, asset_path, name):
        """
        检查路径深度

        【为什么路径深度重要？】
        路径太深（层级太多）会导致：
        1. 资产浏览器里导航困难
        2. 资产迁移时容易出错
        3. 团队成员找不到资产
        建议不超过 4-5 层（/Game/Category/Type/Asset）。
        """
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
            # 按严重度排序：error > warning > info
            severity_order = {"error": 0, "warning": 1, "info": 2}
            sorted_issues = sorted(
                self.issues,
                key=lambda x: severity_order.get(x["severity"], 3)
            )

            # 只显示前 50 个问题（避免日志被刷屏）
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
#
# 【为什么需要布局工具？】
# 手动摆放几百个装饰物（树木、石头、路灯）非常低效。
# 布局工具可以一键完成圆形排列、直线排列、随机散布等操作。

class LevelLayoutTool:
    """
    关卡布局辅助工具
    提供排列、分布、对齐等功能
    """

    @staticmethod
    def arrange_in_circle(radius=500.0, z_height=0.0):
        """
        将选中的 Actor 排列成圆形

        【数学原理】
        圆上第 i 个点的坐标：
        x = radius × cos(angle)
        y = radius × sin(angle)
        其中 angle = i × (2π / count)
        count 是总点数，360° / count 就是每个点之间的角度差。
        """
        # 【编辑器 API 迁移】
        # UE5 中，get_selected_level_actors() 从 EditorLevelLibrary
        # 搬到了 EditorActorSubsystem。老写法还能跑但会有废弃警告。
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if len(actors) < 2:
            unreal.log_warning("请至少选中 2 个 Actor")
            return

        count = len(actors)
        angle_step = 360.0 / count

        # 【事务操作】
        # 排列多个 Actor 是可逆操作，必须包在事务里
        # primary_object 传第一个 Actor（它是被修改的主要对象之一）
        with editor_transaction("排列为圆形", actors[0]):
            for i, actor in enumerate(actors):
                # 【math.radians】
                # 角度 → 弧度转换。Python 的 math.cos/sin 接收弧度，不是角度。
                # 0° = 0 弧度，360° = 2π 弧度
                angle = math.radians(i * angle_step)
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)

                new_loc = unreal.Vector(x, y, z_height)
                # sweep=False: 不做碰撞检测（直接传送到目标位置）
                # teleport=False: 正常更新物理状态
                actor.set_actor_location(new_loc, False, False)

                # 【让 Actor 朝向圆心】
                # 计算从当前位置到圆心(0,0)的方向向量
                # 然后用 atan2 算出偏航角(Yaw)
                look_at = unreal.Vector(0, 0, z_height)
                direction = look_at - new_loc
                # atan2(y, x) 返回 [-π, π] 的弧度值
                # math.degrees 再转回角度
                yaw = math.degrees(math.atan2(direction.y, direction.x))
                # 【易错点】Rotator 的位置参数顺序其实是 (roll, pitch, yaw)，
                #   写成 Rotator(0, yaw, 0) 会把 yaw 塞进 pitch。这里用关键字参数最稳。
                actor.set_actor_rotation(unreal.Rotator(pitch=0, yaw=yaw, roll=0), False)
        unreal.log(f"已将 {count} 个 Actor 排列为半径 {radius} 的圆形")

    @staticmethod
    def arrange_in_line(start_pos=None, direction="x",
                         spacing=200.0):
        """
        将选中的 Actor 排列成直线

        【方向向量】
        direction="x" → 沿 X 轴正方向排列
        direction="y" → 沿 Y 轴正方向排列
        direction="z" → 沿 Z 轴正方向排列
        每个 Actor 的位置 = 起始位置 + 方向 × 间距 × 序号
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if len(actors) < 2:
            unreal.log_warning("请至少选中 2 个 Actor")
            return

        # 如果没指定起始位置，默认用第一个 Actor 的当前位置
        if start_pos is None:
            start_pos = actors[0].get_actor_location()

        with editor_transaction("排列为直线", actors[0]):
            # 方向向量：只在目标轴上为 1，其他为 0
            axis_map = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
            dx, dy, dz = axis_map.get(direction.lower(), (1, 0, 0))

            for i, actor in enumerate(actors):
                new_loc = unreal.Vector(
                    start_pos.x + dx * spacing * i,  # 起始 + 方向 × 间距 × 序号
                    start_pos.y + dy * spacing * i,
                    start_pos.z + dz * spacing * i,
                )
                actor.set_actor_location(new_loc, False, False)
        unreal.log(f"已将 {len(actors)} 个 Actor 排列为直线")

    @staticmethod
    def scatter_randomly(bounds_min, bounds_max,
                          random_rotation=True):
        """
        在指定范围内随机散布 Actor

        【应用场景】
        比如在一个区域内随机散布石头、树木、草丛等装饰物。
        bounds_min 和 bounds_max 定义了散布的边界框（Bounding Box）。
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if not actors:
            unreal.log_warning("请先选中 Actor")
            return

        with editor_transaction("随机散布", actors[0]):
            for actor in actors:
                # 在边界框内随机取点
                # random.uniform(a, b) 返回 [a, b] 之间的随机浮点数
                loc = unreal.Vector(
                    random.uniform(bounds_min.x, bounds_max.x),
                    random.uniform(bounds_min.y, bounds_max.y),
                    random.uniform(bounds_min.z, bounds_max.z),
                )
                actor.set_actor_location(loc, False, False)

                if random_rotation:
                    # 【易错点】Rotator 的位置参数顺序是 (roll, pitch, yaw)，必须用关键字参数。
                    rot = unreal.Rotator(
                        pitch=0,                     # 不抬头/低头
                        yaw=random.uniform(0, 360),  # 水平随机朝向
                        roll=0,                      # 不侧翻
                    )
                    actor.set_actor_rotation(rot, False)
        unreal.log(f"已随机散布 {len(actors)} 个 Actor")

    @staticmethod
    def mirror_actors(axis="x"):
        """
        沿指定轴镜像选中的 Actor

        【镜像原理】
        沿 X 轴镜像：x → -x, y → y, z → z
        沿 Y 轴镜像：x → x, y → -y, z → z
        沿 Z 轴镜像：x → x, y → y, z → -z

        【旋转镜像的特殊性】
        X 轴镜像：yaw → -yaw（左右反转）
        Y 轴镜像：yaw → 180 - yaw（前后反转，同时左右也反转）
        Z 轴镜像不需要改旋转（水平朝向不变）
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
        if not actors:
            unreal.log_warning("请先选中 Actor")
            return

        with editor_transaction("镜像 Actor", actors[0]):
            for actor in actors:
                loc = actor.get_actor_location()
                # 根据镜像轴翻转对应的坐标分量
                if axis == "x":
                    loc.x = -loc.x
                elif axis == "y":
                    loc.y = -loc.y
                elif axis == "z":
                    loc.z = -loc.z
                actor.set_actor_location(loc, False, False)

                # 镜像旋转（只有 X 和 Y 轴需要处理旋转）
                rot = actor.get_actor_rotation()
                if axis == "x":
                    rot.yaw = -rot.yaw
                elif axis == "y":
                    rot.yaw = 180 - rot.yaw
                # Z 轴镜像不改旋转

                actor.set_actor_rotation(rot, False)  # teleport_physics=False
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
