"""
=============================================================
高级主题 第1课：大规模批量处理实战
=============================================================

学习目标：
  - 高效的批量处理模式
  - 进度跟踪和错误恢复
  - 实战：项目清理和优化工具

本课将创建多个生产级别的批量处理工具

本课可能用到的 API：
  unreal.log(arg: Any) -> None  —— 输出一般消息到日志
  unreal.log_warning(arg: Any) -> None  —— 输出警告消息到日志
  unreal.ScopedSlowTask(work: float, desc: Text = "", enabled: bool = True)  —— 创建慢任务进度条对象
  task.make_dialog(can_cancel: bool = False, allow_in_pie: bool = False) -> None  —— 为慢任务创建对话框
  task.should_cancel() -> bool  —— 用户是否请求取消任务
  task.enter_progress_frame(work: float = 1.0, desc: Text = "") -> None  —— 推进一个进度帧
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 递归列出目录下全部资产/文件夹
  unreal.EditorAssetLibrary.does_directory_exist(directory_path: str) -> bool  —— 判断路径是否为已存在文件夹
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  —— 查找引用该资产的全部包路径
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产元数据（类、名称等）
  asset_data.asset_name -> Name  —— 资产的短名称（不含包路径）
  asset_data.asset_class_path -> TopLevelAssetPath  —— 资产所属类的完整路径
  unreal.EditorAssetLibrary.delete_asset(asset_path_to_delete: str) -> bool  —— 删除指定资产
  unreal.EditorAssetLibrary.rename_asset(source_asset_path: str, destination_asset_path: str) -> bool  —— 重命名/移动资产到新路径
  unreal.EditorAssetLibrary.delete_directory(directory_path: str) -> bool  —— 删除空目录
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建目录
  unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool  —— 判断资产路径是否已存在
  unreal.Paths.project_saved_dir() -> str  —— 获取项目 Saved 目录的绝对路径
=============================================================
"""

import unreal
import time
import os

# ═════════════════════════════════════════════════════════
# 框架：通用批量处理器
# ═════════════════════════════════════════════════════════

class BatchProcessor:
    """
    通用批量处理框架
    支持：进度条、错误处理、取消、日志、统计
    """

    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }
        self.start_time = None

    def process(self, items, process_func, description="处理中..."):
        """
        批量处理一组项目

        参数:
            items: 要处理的项目列表
            process_func: 处理函数 (item) -> bool
            description: 进度条描述文本
        """
        self.start_time = time.time()

        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  {self.operation_name}")
        unreal.log(f"  处理 {len(items)} 个项目...")
        unreal.log(f"{'=' * 60}")

        task = unreal.ScopedSlowTask(len(items), description)
        task.make_dialog(True)

        for i, item in enumerate(items):
            if task.should_cancel():
                unreal.log("用户取消了操作")
                break

            item_name = str(item).split("/")[-1] if isinstance(item, str) else str(item)
            task.enter_progress_frame(1.0, f"[{i+1}/{len(items)}] {item_name}")

            try:
                result = process_func(item)
                if result is True:
                    self.results["success"] += 1
                elif result is False:
                    self.results["failed"] += 1
                else:
                    self.results["skipped"] += 1
            except Exception as e:
                self.results["failed"] += 1
                self.results["errors"].append({
                    "item": str(item),
                    "error": str(e)
                })
                unreal.log_warning(f"处理失败: {item} - {e}")

        self._print_summary()

    def _print_summary(self):
        """打印处理结果摘要"""
        elapsed = time.time() - self.start_time

        unreal.log(f"\n{'─' * 60}")
        unreal.log(f"  处理完成！")
        unreal.log(f"{'─' * 60}")
        unreal.log(f"  成功: {self.results['success']}")
        unreal.log(f"  失败: {self.results['failed']}")
        unreal.log(f"  跳过: {self.results['skipped']}")
        unreal.log(f"  耗时: {elapsed:.2f} 秒")

        if self.results["errors"]:
            unreal.log(f"\n  错误详情:")
            for err in self.results["errors"][:10]:
                unreal.log(f"    ❌ {err['item']}: {err['error']}")

        return self.results

# ═════════════════════════════════════════════════════════
# 工具 1: 项目资产清理器
# ═════════════════════════════════════════════════════════

class ProjectCleaner:
    """项目清理工具集"""

    @staticmethod
    def remove_unused_assets(search_path="/Game", dry_run=True):
        """删除未使用的资产"""
        all_assets = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True
        )

        def check_unused(asset_path):
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                return None  # 跳过文件夹

            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                asset_path
            )
            external_refs = [r for r in refs if r != asset_path]

            if not external_refs:
                if not dry_run:
                    unreal.EditorAssetLibrary.delete_asset(asset_path)
                unreal.log(f"  未使用: {asset_path}")
                return True
            return False

        processor = BatchProcessor("清理未使用资产")
        processor.process(all_assets, check_unused, "扫描引用...")

        if dry_run:
            unreal.log("\n(dry_run 模式，未实际删除)")

    @staticmethod
    def fix_naming_conventions(search_path="/Game"):
        """修复命名规范"""
        prefix_map = {
            "StaticMesh": "SM_",
            "Texture2D": "T_",
            "Material": "M_",
            "MaterialInstanceConstant": "MI_",
            "Blueprint": "BP_",
            "SoundWave": "S_",
        }

        all_assets = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True
        )

        def fix_name(asset_path):
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                return None

            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            name = asset_data.asset_name
            class_str = str(asset_data.asset_class_path)

            for class_key, prefix in prefix_map.items():
                if class_key in class_str and not name.startswith(prefix):
                    new_name = prefix + name
                    new_path = f"{os.path.dirname(asset_path)}/{new_name}"
                    success = unreal.EditorAssetLibrary.rename_asset(
                        asset_path, new_path
                    )
                    if success:
                        unreal.log(f"  {name} → {new_name}")
                        return True
            return False

        processor = BatchProcessor("修复命名规范")
        processor.process(all_assets, fix_name, "检查命名...")

    @staticmethod
    def empty_folders_cleanup(search_path="/Game"):
        """清理空文件夹"""
        all_paths = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True, include_folder=True
        )

        # 逆序遍历（先处理深层目录）
        folders = sorted(
            [p for p in all_paths
             if unreal.EditorAssetLibrary.does_directory_exist(p)],
            key=lambda x: -len(x.split("/"))
        )

        deleted = 0
        for folder in folders:
            contents = unreal.EditorAssetLibrary.list_assets(
                folder, recursive=False, include_folder=True
            )
            if not contents:
                unreal.EditorAssetLibrary.delete_directory(folder)
                unreal.log(f"  删除空目录: {folder}")
                deleted += 1

        unreal.log(f"已删除 {deleted} 个空文件夹")

# ═════════════════════════════════════════════════════════
# 工具 2: 资产迁移和重组
# ═════════════════════════════════════════════════════════

class AssetOrganizer:
    """资产重组工具"""

    @staticmethod
    def organize_by_type(source_path="/Game", target_base="/Game/_Organized"):
        """按类型组织资产到标准目录"""
        type_dirs = {
            "StaticMesh": "Meshes",
            "SkeletalMesh": "Characters",
            "Texture2D": "Textures",
            "Material": "Materials",
            "MaterialInstanceConstant": "Materials/Instances",
            "Blueprint": "Blueprints",
            "SoundWave": "Audio",
            "ParticleSystem": "FX",
            "NiagaraSystem": "FX/Niagara",
            "DataTable": "Data",
            "WidgetBlueprint": "UI",
            "LevelSequence": "Cinematics",
            "AnimSequence": "Animation",
            "AnimBlueprint": "Animation",
            "BlendSpace": "Animation",
        }

        all_assets = unreal.EditorAssetLibrary.list_assets(
            source_path, recursive=True
        )

        def organize_asset(asset_path):
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                return None

            # 跳过已在 _Organized 目录中的资产
            if "_Organized" in asset_path:
                return None

            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            class_str = str(asset_data.asset_class_path)

            target_subdir = None
            for class_key, subdir in type_dirs.items():
                if class_key in class_str:
                    target_subdir = subdir
                    break

            if not target_subdir:
                target_subdir = "Other"

            target_dir = f"{target_base}/{target_subdir}"
            unreal.EditorAssetLibrary.make_directory(target_dir)

            # 移动资产
            asset_name = asset_path.split("/")[-1]
            dest_path = f"{target_dir}/{asset_name}"

            if unreal.EditorAssetLibrary.does_asset_exist(dest_path):
                return None  # 目标已存在

            success = unreal.EditorAssetLibrary.rename_asset(
                asset_path, dest_path
            )
            if success:
                unreal.log(f"  → {dest_path}")
            return success

        processor = BatchProcessor("按类型组织资产")
        processor.process(all_assets, organize_asset, "重组中...")

    @staticmethod
    def batch_redirect_assets(old_base, new_base):
        """批量重定向资产路径"""
        assets = unreal.EditorAssetLibrary.list_assets(
            old_base, recursive=True
        )

        def redirect(asset_path):
            relative = asset_path.replace(old_base, "", 1)
            new_path = new_base + relative

            target_dir = os.path.dirname(new_path)
            unreal.EditorAssetLibrary.make_directory(target_dir)

            return unreal.EditorAssetLibrary.rename_asset(asset_path, new_path)

        processor = BatchProcessor("批量重定向")
        processor.process(assets, redirect, "重定向中...")

# ═════════════════════════════════════════════════════════
# 工具 3: 项目健康报告
# ═════════════════════════════════════════════════════════

class ProjectHealthReport:
    """项目健康报告生成器"""

    @staticmethod
    def generate_full_report(search_path="/Game"):
        """生成完整的项目健康报告"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("  UE 项目健康报告")
        report_lines.append("=" * 60)

        all_assets = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True
        )

        # 1. 基本统计
        report_lines.append(f"\n--- 资产统计 ---")
        report_lines.append(f"总资产数: {len(all_assets)}")

        type_counts = {}
        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            class_name = str(asset_data.asset_class_path).split(".")[-1]
            type_counts[class_name] = type_counts.get(class_name, 0) + 1

        for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
            report_lines.append(f"  {type_name}: {count}")

        # 2. 命名规范检查
        report_lines.append(f"\n--- 命名规范 ---")
        naming_issues = 0
        for asset_path in all_assets:
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue
            name = asset_path.split("/")[-1]
            if " " in name:
                naming_issues += 1
                report_lines.append(f"  ⚠️ 名称含空格: {name}")
        report_lines.append(f"命名问题总数: {naming_issues}")

        # 3. 目录结构
        report_lines.append(f"\n--- 顶级目录 ---")
        top_dirs = set()
        for asset_path in all_assets:
            parts = asset_path.split("/")
            if len(parts) >= 3:
                top_dirs.add(parts[2])

        for d in sorted(top_dirs):
            count = len([p for p in all_assets if f"/{d}/" in p])
            report_lines.append(f"  /Game/{d}: {count} 个资产")

        # 输出报告
        for line in report_lines:
            unreal.log(line)

        # 保存到文件
        report_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "ProjectHealthReport.txt"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        unreal.log(f"\n报告已保存到: {report_path}")

        return report_lines

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 生成项目健康报告
# ProjectHealthReport.generate_full_report("/Game")

# 清理未使用资产（预览模式）
# ProjectCleaner.remove_unused_assets("/Game", dry_run=True)

# 修复命名规范
# ProjectCleaner.fix_naming_conventions("/Game")

# 清理空文件夹
# ProjectCleaner.empty_folders_cleanup("/Game")

# 按类型组织资产
# AssetOrganizer.organize_by_type()

unreal.log("高级主题第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 扩展健康报告：添加文件大小统计
# 2. 创建一个 "资产迁移检查器"：在移动资产前预览影响
# 3. 实现增量处理：只处理上次运行后修改过的资产
# 4. 创建一个定时任务：每天自动生成项目报告
