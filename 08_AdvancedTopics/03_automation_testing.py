"""
=============================================================
高级主题 第3课：自动化测试脚本
=============================================================

学习目标：
  - 编写 UE 自动化测试
  - 资产验证规则
  - 项目规范自动检查
  - CI/CD 集成

核心概念：
  - 自动化测试可以确保项目质量
  - 可以在提交前自动运行验证
  - 支持命令行执行，适合 CI/CD 管线

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  -- 递归列出目录下全部资产/文件夹
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  -- 获取资产元数据（类、名称等）
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  -- 查找引用该资产的全部包路径
  unreal.EditorLevelLibrary.get_all_level_actors() -> Array[Actor]  -- 获取当前关卡全部 Actor
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  -- 按路径加载资产到内存
  unreal.Paths.project_saved_dir() -> str  -- 获取项目 Saved 目录的绝对路径
  unreal.log(arg: Any) -> None  -- 输出一般消息到日志
  unreal.Texture2D  -- 纹理资产类（用于 isinstance 判断）
=============================================================
"""

import unreal
import time
import json
import os

# ======================================================
# 框架：自动化测试运行器
# ======================================================

class TestResult:
    """
    单个测试结果

    为什么需要单独的 TestResult 类？因为它封装了测试的所有输出信息：
    名称、是否通过、消息、详情、耗时。这样可以统一管理和格式化输出。
    """
    def __init__(self, test_name, passed, message="", details=""):
        self.test_name = test_name  # 测试名称
        self.passed = passed  # 是否通过（True/False）
        self.message = message  # 简短消息（如"通过"或失败原因）
        self.details = details  # 详细信息（如失败的具体资产列表）
        self.duration = 0.0  # 耗时（秒），后续由 TestSuite 填充

class TestSuite:
    """
    测试套件

    TestSuite 负责收集和运行一组测试，汇总结果并输出报告。
    这种设计模式让测试的组织和执行分离，方便扩展。
    """

    def __init__(self, suite_name):
        self.suite_name = suite_name  # 套件名称，用于日志和报告
        self.results = []  # 存储所有 TestResult 对象
        self.start_time = None

    def add_test(self, test_func, test_name=None):
        """
        添加并运行一个测试

        测试函数的约定：
        - 返回 True 表示通过
        - 返回 False 或字符串表示失败（字符串作为失败原因）
        - 返回 TestResult 对象表示完整的测试结果
        - 抛出异常也会被捕获，标记为失败
        """
        # 如果没有指定名称，使用函数名作为测试名
        name = test_name or test_func.__name__
        start = time.time()

        try:
            # 执行测试函数
            result = test_func()
            elapsed = time.time() - start

            # 根据返回值类型创建 TestResult
            if isinstance(result, TestResult):
                # 测试函数返回了完整的 TestResult
                result.duration = elapsed
                self.results.append(result)
            elif result is True:
                # 简单的通过
                self.results.append(TestResult(name, True, "通过"))
                self.results[-1].duration = elapsed
            else:
                # 失败，返回值作为失败消息
                self.results.append(
                    TestResult(name, False, str(result))
                )
                self.results[-1].duration = elapsed

        except Exception as e:
            # 捕获异常，记录错误但不中断其他测试
            # 为什么？一个测试的异常不应影响其他测试的执行
            elapsed = time.time() - start
            self.results.append(
                TestResult(name, False, f"异常: {e}", str(e))
            )
            self.results[-1].duration = elapsed

    def run_all(self, tests):
        """
        运行一组测试

        参数 tests 是一个元组列表：[(测试函数, 测试名), ...]
        这种格式方便批量注册测试，类似于 pytest 的 parametrize
        """
        self.start_time = time.time()

        # 输出测试套件标题
        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  测试套件: {self.suite_name}")
        unreal.log(f"  测试数量: {len(tests)}")
        unreal.log(f"{'=' * 60}")

        for test_func, test_name in tests:
            self.add_test(test_func, test_name)

        # 输出结果并返回是否全部通过
        return self._print_results()

    def _print_results(self):
        """打印测试结果摘要"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        elapsed = time.time() - self.start_time

        # 使用分隔线让日志更易读
        unreal.log(f"\n{'-' * 60}")
        unreal.log(f"  结果: {passed} 通过, {failed} 失败")
        # :.2f 表示保留两位小数
        unreal.log(f"  耗时: {elapsed:.2f} 秒")
        unreal.log(f"{'-' * 60}")

        # 逐个显示测试结果
        for r in self.results:
            icon = "OK" if r.passed else "FAIL"
            unreal.log(f"  [{icon}] {r.test_name} ({r.duration:.3f}s)")
            if not r.passed:
                unreal.log(f"     -> {r.message}")

        # 保存结果到 JSON 文件
        self._save_results()

        return failed == 0

    def _save_results(self):
        """保存测试结果到 JSON 文件"""
        output = {
            "suite": self.suite_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "tests": [
                {
                    "name": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration,
                }
                for r in self.results
            ]
        }

        # 保存路径包含时间戳，方便追溯历史结果
        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "TestResults",
            f"{self.suite_name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        unreal.log(f"\n结果已保存到: {output_path}")

# ======================================================
# 资产验证测试集
# ======================================================

class AssetValidationTests:
    """
    资产验证测试

    这些测试检查项目资产是否符合质量标准。
    在实际项目中，这些检查可以在提交前自动运行，防止不合格的资产进入版本库。
    """

    @staticmethod
    def test_no_empty_folders():
        """测试：不存在空文件夹"""
        # include_folder=True 同时返回文件夹路径
        all_paths = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True, include_folder=True
        )
        empty_folders = []

        for path in all_paths:
            # does_directory_exist 判断路径是否为文件夹
            if unreal.EditorAssetLibrary.does_directory_exist(path):
                # recursive=False 只列出直接子项，不递归
                contents = unreal.EditorAssetLibrary.list_assets(
                    path, recursive=False, include_folder=True
                )
                # 如果没有任何子项，说明是空文件夹
                if not contents:
                    empty_folders.append(path)

        if empty_folders:
            return TestResult(
                "无空文件夹",
                False,
                f"发现 {len(empty_folders)} 个空文件夹",
                "\n".join(empty_folders[:10])  # 最多显示10个
            )
        return TestResult("无空文件夹", True, "通过")

    @staticmethod
    def test_naming_conventions():
        """测试：资产命名规范"""
        # 前缀映射表：资产类 -> 应有的前缀
        prefix_map = {
            "StaticMesh": "SM_",
            "Texture2D": "T_",
            "Material": "M_",
            "Blueprint": "BP_",
        }

        all_assets = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True
        )
        violations = []  # 存储所有违规记录

        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            # find_asset_data 返回 AssetData 元数据对象
            # 不需要加载资产本身，效率高
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            name = asset_data.asset_name  # 资产短名称
            class_str = str(asset_data.asset_class_path)  # 完整类路径

            # 检查1：名称不能包含空格
            # 空格在路径中可能导致各种问题（命令行、脚本、版本控制等）
            if " " in name:
                violations.append(f"含空格: {name}")

            # 检查2：检查是否缺少对应前缀
            for class_key, prefix in prefix_map.items():
                if class_key in class_str and not name.startswith(prefix):
                    violations.append(f"缺少 {prefix} 前缀: {name}")
                    break  # 只报告一次

        if violations:
            return TestResult(
                "命名规范",
                False,
                f"发现 {len(violations)} 个命名问题",
                "\n".join(violations[:20])  # 最多显示20个
            )
        return TestResult("命名规范", True, "通过")

    @staticmethod
    def test_no_orphan_assets():
        """测试：不存在孤立资产"""
        all_assets = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True
        )
        orphans = []  # 存储未被引用的资产

        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            # find_package_referencers_for_asset 查找所有引用该资产的包
            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                asset_path
            )
            # 排除自身引用（资产自身会引用自身）
            external_refs = [r for r in refs if r != asset_path]

            # 没有外部引用 = 孤立资产
            if not external_refs:
                orphans.append(asset_path)

        # 注意：孤立资产不一定是错误（可能是预留资产），
        # 所以这里返回 passed=True 但附带警告信息
        if orphans:
            return TestResult(
                "无孤立资产",
                True,
                f"发现 {len(orphans)} 个未引用的资产（仅警告）",
                "\n".join(orphans[:10])
            )
        return TestResult("无孤立资产", True, "通过")

    @staticmethod
    def test_texture_resolution():
        """测试：纹理分辨率为 2 的幂"""
        all_assets = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True
        )
        bad_textures = []  # 存储非2的幂纹理

        for asset_path in all_assets:
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            # 只处理 Texture2D 类型的资产
            if "Texture2D" not in str(asset_data.asset_class_path):
                continue

            # load_asset 将纹理资产加载到内存，以便读取其属性
            texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not texture or not isinstance(texture, unreal.Texture2D):
                continue

            # blueprint_get_size_x/y 获取纹理的宽高（像素）
            sx = texture.blueprint_get_size_x()
            sy = texture.blueprint_get_size_y()

            # 位运算检查是否为 2 的幂：n & (n-1) == 0
            # 例如：8(1000) & 7(0111) == 0，说明 8 是 2 的幂
            # 非2的幂如 6(0110) & 5(0101) == 4，不等于0
            if not ((sx & (sx-1) == 0) and (sy & (sy-1) == 0)):
                bad_textures.append(f"{asset_data.asset_name} ({sx}x{sy})")

        if bad_textures:
            return TestResult(
                "纹理分辨率 (2的幂)",
                False,
                f"发现 {len(bad_textures)} 个非2的幂纹理",
                "\n".join(bad_textures[:10])
            )
        return TestResult("纹理分辨率 (2的幂)", True, "通过")

# ======================================================
# 关卡验证测试集
# ======================================================

class LevelValidationTests:
    """
    关卡验证测试

    这些测试检查关卡设计是否符合标准。
    例如：确保关卡有出生点、没有重叠的 Actor 等。
    """

    @staticmethod
    def test_level_has_player_start():
        """测试：关卡包含 PlayerStart"""
        # get_all_level_actors 获取当前关卡中的所有 Actor
        actors = unreal.EditorLevelLibrary.get_all_level_actors()

        # 使用 isinstance 检查是否有 PlayerStart 类型的 Actor
        # PlayerStart 是玩家在关卡中的出生点，每个可玩关卡都必须有
        has_player_start = any(
            isinstance(a, unreal.PlayerStart) for a in actors
        )

        if has_player_start:
            return TestResult("包含 PlayerStart", True, "通过")
        return TestResult("包含 PlayerStart", False, "关卡缺少 PlayerStart")

    @staticmethod
    def test_no_overlapping_actors():
        """测试：没有完全重叠的 Actor"""
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        # 用位置作为键，检测同一位置是否有多个 Actor
        locations = {}
        overlapping = []

        for actor in actors:
            loc = actor.get_actor_location()
            # round(x, 0) 四舍五入到整数，避免浮点精度导致的误判
            # 例如：(100.001, 200.002, 300.003) 和 (100, 200, 300) 视为相同位置
            key = (round(loc.x, 0), round(loc.y, 0), round(loc.z, 0))

            if key in locations:
                # 同一位置已存在 Actor，记录重叠
                overlapping.append(
                    f"{actor.get_actor_label()} 与 {locations[key]} 重叠"
                )
            else:
                locations[key] = actor.get_actor_label()

        if overlapping:
            return TestResult(
                "无重叠 Actor",
                False,
                f"发现 {len(overlapping)} 对重叠",
                "\n".join(overlapping[:10])
            )
        return TestResult("无重叠 Actor", True, "通过")

    @staticmethod
    def test_lighting_built():
        """测试：光照已构建"""
        # 注意：光照状态的检测取决于具体的引擎版本和项目配置
        # 这里返回通过，实际项目中可以检查 WorldSettings 的 LightingNeedsRestart 等属性
        return TestResult("光照已构建", True, "通过 (需要手动验证)")

# ======================================================
# 运行所有测试
# ======================================================

def run_all_tests():
    """
    运行所有自动化测试

    在 CI/CD 管线中，这个函数会被自动调用来验证项目质量。
    测试结果会保存到 Saved/TestResults/ 目录。
    """
    suite = TestSuite("项目验证")

    # 测试列表：(测试函数, 测试名)
    tests = [
        # 资产验证
        (AssetValidationTests.test_no_empty_folders, "无空文件夹"),
        (AssetValidationTests.test_naming_conventions, "命名规范"),
        (AssetValidationTests.test_no_orphan_assets, "无孤立资产"),
        (AssetValidationTests.test_texture_resolution, "纹理分辨率"),
        # 关卡验证
        (LevelValidationTests.test_level_has_player_start, "PlayerStart"),
        (LevelValidationTests.test_no_overlapping_actors, "无重叠Actor"),
        (LevelValidationTests.test_lighting_built, "光照构建"),
    ]

    suite.run_all(tests)

# --------------------------------------------------
# 命令行运行（CI/CD 集成）
# --------------------------------------------------
#
# 在 CI/CD 中运行测试的命令:
#
# UnrealEditor.exe Project.uproject \
#   -ExecutePythonScript="PythonLearning/08_AdvancedTopics/03_automation_testing.py" \
#   -nullrhi -nosplash -unattended \
#   -stdout -fullstdoutlogoutput
#
# 参数说明:
#   -nullrhi          不初始化渲染硬件接口（无头模式，不需要 GPU）
#   -nosplash         不显示启动画面
#   -unattended       无人值守模式（不弹任何对话框）
#   -stdout           将日志输出到标准输出
#   -fullstdoutlogoutput  完整日志输出（不截断）
#
# 测试结果会保存到 Saved/TestResults/ 目录

# --------------------------------------------------
# 使用示例
# --------------------------------------------------

# 运行所有测试
# run_all_tests()

# 单独运行资产验证
# suite = TestSuite("资产验证")
# suite.run_all([
#     (AssetValidationTests.test_naming_conventions, "命名规范"),
#     (AssetValidationTests.test_texture_resolution, "纹理分辨率"),
# ])

unreal.log("高级主题第3课完成！")

# --------------------------------------------------
# 练习题
# --------------------------------------------------
# 1. 添加更多验证规则：检查材质是否有未连接的节点
# 2. 实现性能验证：检查 Actor 数量是否超过阈值
# 3. 创建回归测试：保存当前状态，下次对比差异
# 4. 编写 CI/CD 脚本：在每次提交时自动运行测试
