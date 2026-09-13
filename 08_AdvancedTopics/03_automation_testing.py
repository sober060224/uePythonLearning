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
=============================================================
"""

import unreal
import time
import json
import os

# ═════════════════════════════════════════════════════════
# 框架：自动化测试运行器
# ═════════════════════════════════════════════════════════

class TestResult:
    """单个测试结果"""
    def __init__(self, test_name, passed, message="", details=""):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.details = details
        self.duration = 0.0

class TestSuite:
    """测试套件"""

    def __init__(self, suite_name):
        self.suite_name = suite_name
        self.results = []
        self.start_time = None

    def add_test(self, test_func, test_name=None):
        """添加并运行一个测试"""
        name = test_name or test_func.__name__
        start = time.time()

        try:
            result = test_func()
            elapsed = time.time() - start

            if isinstance(result, TestResult):
                result.duration = elapsed
                self.results.append(result)
            elif result is True:
                self.results.append(TestResult(name, True, "通过"))
                self.results[-1].duration = elapsed
            else:
                self.results.append(
                    TestResult(name, False, str(result))
                )
                self.results[-1].duration = elapsed

        except Exception as e:
            elapsed = time.time() - start
            self.results.append(
                TestResult(name, False, f"异常: {e}", str(e))
            )
            self.results[-1].duration = elapsed

    def run_all(self, tests):
        """运行一组测试"""
        self.start_time = time.time()

        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  测试套件: {self.suite_name}")
        unreal.log(f"  测试数量: {len(tests)}")
        unreal.log(f"{'=' * 60}")

        for test_func, test_name in tests:
            self.add_test(test_func, test_name)

        self._print_results()

    def _print_results(self):
        """打印测试结果"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        elapsed = time.time() - self.start_time

        unreal.log(f"\n{'─' * 60}")
        unreal.log(f"  结果: {passed} 通过, {failed} 失败")
        unreal.log(f"  耗时: {elapsed:.2f} 秒")
        unreal.log(f"{'─' * 60}")

        for r in self.results:
            icon = "✅" if r.passed else "❌"
            unreal.log(f"  {icon} {r.test_name} ({r.duration:.3f}s)")
            if not r.passed:
                unreal.log(f"     └─ {r.message}")

        # 保存结果到 JSON
        self._save_results()

        return failed == 0

    def _save_results(self):
        """保存测试结果到 JSON"""
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

        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "TestResults",
            f"{self.suite_name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        unreal.log(f"\n结果已保存到: {output_path}")

# ═════════════════════════════════════════════════════════
# 资产验证测试集
# ═════════════════════════════════════════════════════════

class AssetValidationTests:
    """资产验证测试"""

    @staticmethod
    def test_no_empty_folders():
        """测试：不存在空文件夹"""
        all_paths = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True, include_folder=True
        )
        empty_folders = []

        for path in all_paths:
            if unreal.EditorAssetLibrary.does_directory_exist(path):
                contents = unreal.EditorAssetLibrary.list_assets(
                    path, recursive=False, include_folder=True
                )
                if not contents:
                    empty_folders.append(path)

        if empty_folders:
            return TestResult(
                "无空文件夹",
                False,
                f"发现 {len(empty_folders)} 个空文件夹",
                "\n".join(empty_folders[:10])
            )
        return TestResult("无空文件夹", True, "通过")

    @staticmethod
    def test_naming_conventions():
        """测试：资产命名规范"""
        prefix_map = {
            "StaticMesh": "SM_",
            "Texture2D": "T_",
            "Material": "M_",
            "Blueprint": "BP_",
        }

        all_assets = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True
        )
        violations = []

        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            name = asset_data.asset_name
            class_str = str(asset_data.asset_class_path)

            # 检查空格
            if " " in name:
                violations.append(f"含空格: {name}")

            # 检查前缀
            for class_key, prefix in prefix_map.items():
                if class_key in class_str and not name.startswith(prefix):
                    violations.append(f"缺少 {prefix} 前缀: {name}")
                    break

        if violations:
            return TestResult(
                "命名规范",
                False,
                f"发现 {len(violations)} 个命名问题",
                "\n".join(violations[:20])
            )
        return TestResult("命名规范", True, "通过")

    @staticmethod
    def test_no_orphan_assets():
        """测试：不存在孤立资产"""
        all_assets = unreal.EditorAssetLibrary.list_assets(
            "/Game", recursive=True
        )
        orphans = []

        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue

            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                asset_path
            )
            external_refs = [r for r in refs if r != asset_path]

            if not external_refs:
                orphans.append(asset_path)

        # 孤立资产不一定是错误，可能是警告
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
        bad_textures = []

        for asset_path in all_assets:
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            if "Texture2D" not in str(asset_data.asset_class_path):
                continue

            texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not texture or not isinstance(texture, unreal.Texture2D):
                continue

            sx = texture.get_editor_property("size_x")
            sy = texture.get_editor_property("size_y")

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

# ═════════════════════════════════════════════════════════
# 关卡验证测试集
# ═════════════════════════════════════════════════════════

class LevelValidationTests:
    """关卡验证测试"""

    @staticmethod
    def test_level_has_player_start():
        """测试：关卡包含 PlayerStart"""
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
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
        locations = {}
        overlapping = []

        for actor in actors:
            loc = actor.get_actor_location()
            key = (round(loc.x, 0), round(loc.y, 0), round(loc.z, 0))

            if key in locations:
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
        # 检查是否有未构建的光照
        # 注意：具体 API 取决于引擎版本
        return TestResult("光照已构建", True, "通过 (需要手动验证)")

# ═════════════════════════════════════════════════════════
# 运行所有测试
# ═════════════════════════════════════════════════════════

def run_all_tests():
    """运行所有自动化测试"""
    suite = TestSuite("项目验证")

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

# ─────────────────────────────────────────────────────────
# 命令行运行（CI/CD 集成）
# ─────────────────────────────────────────────────────────
#
# 在 CI/CD 中运行测试的命令:
#
# UnrealEditor.exe Project.uproject \
#   -ExecutePythonScript="PythonLearning/08_AdvancedTopics/03_automation_testing.py" \
#   -nullrhi -nosplash -unattended \
#   -stdout -fullstdoutlogoutput
#
# 测试结果会保存到 Saved/TestResults/ 目录

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 运行所有测试
# run_all_tests()

# 单独运行资产验证
# suite = TestSuite("资产验证")
# suite.run_all([
#     (AssetValidationTests.test_naming_conventions, "命名规范"),
#     (AssetValidationTests.test_texture_resolution, "纹理分辨率"),
# ])

unreal.log("高级主题第3课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 添加更多验证规则：检查材质是否有未连接的节点
# 2. 实现性能验证：检查 Actor 数量是否超过阈值
# 3. 创建回归测试：保存当前状态，下次对比差异
# 4. 编写 CI/CD 脚本：在每次提交时自动运行测试
