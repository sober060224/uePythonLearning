"""
=============================================================
高级主题 第1课：大规模批量处理实战
=============================================================

学习目标：
  - 高效的批量处理模式
  - 进度跟踪和错误恢复
  - 实战：项目清理和优化工具

本课将创建多个生产级别的批量处理工具

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 递归列出目录下全部资产/文件夹
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产元数据（类、名称等）
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  —— 查找引用该资产的全部包路径
  unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool  —— 判断资产路径是否已存在
  unreal.Paths.project_saved_dir() -> str  —— 获取项目 Saved 目录的绝对路径
  unreal.ScopedSlowTask(work: float, desc: Text = "", enabled: bool = True)  —— 创建慢任务进度条对象
  unreal.log(arg: Any) -> None  —— 输出一般消息到日志
  unreal.log_warning(arg: Any) -> None  —— 输出警告消息到日志
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
        # 操作名称，用于日志输出，方便追踪是哪个操作在执行
        self.operation_name = operation_name
        # 结果统计字典，用于记录成功、失败、跳过的数量以及错误详情
        # 为什么用字典？因为后续需要动态增加计数，字典比多个变量更清晰
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],  # 存储具体的错误信息，方便排查问题
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
        # 记录开始时间，用于计算总耗时
        self.start_time = time.time()

        # 输出操作开始的日志，方便在编辑器日志窗口中快速定位
        unreal.log(f"\n{'=' * 60}")
        unreal.log(f"  {self.operation_name}")
        unreal.log(f"  处理 {len(items)} 个项目...")
        unreal.log(f"{'=' * 60}")

        # ScopedSlowTask 是 UE 提供的慢任务进度条对象
        # 第一个参数是总工作量（这里是项目数量），第二个是描述文本
        # 为什么用 ScopedSlowTask？因为批量操作可能耗时较长，需要给用户视觉反馈
        task = unreal.ScopedSlowTask(len(items), description)
        # make_dialog(True) 会显示一个带取消按钮的对话框
        # allow_in_pie 参数控制是否允许在 PIE（Play In Editor）模式下运行
        task.make_dialog(True)

        # 遍历所有项目进行处理
        for i, item in enumerate(items):
            # should_cancel() 检查用户是否点击了取消按钮
            # 这是良好的用户体验设计：长时间操作必须支持取消
            if task.should_cancel():
                unreal.log("用户取消了操作")
                break

            # 从路径中提取文件名用于显示（只取最后一段）
            # 为什么用 split("/")[-1]？因为 UE 资产路径使用斜杠分隔
            item_name = str(item).split("/")[-1] if isinstance(item, str) else str(item)
            # enter_progress_frame 推进进度条，显示当前处理的是哪个项目
            # 格式 [1/100] 表示第1个，共100个
            task.enter_progress_frame(1.0, f"[{i+1}/{len(items)}] {item_name}")

            try:
                # 调用用户提供的处理函数
                # 返回 True 表示成功，False 表示失败，None 表示跳过
                result = process_func(item)
                if result is True:
                    self.results["success"] += 1
                elif result is False:
                    self.results["failed"] += 1
                else:
                    self.results["skipped"] += 1
            except Exception as e:
                # 捕获异常，记录错误但不中断整个流程
                # 为什么这样设计？批量处理中单个项目失败不应影响其他项目
                self.results["failed"] += 1
                self.results["errors"].append({
                    "item": str(item),
                    "error": str(e)
                })
                # 使用 log_warning 而不是 log_error，因为这是预期中的错误
                unreal.log_warning(f"处理失败: {item} - {e}")

        # 处理完成后打印摘要
        self._print_summary()

    def _print_summary(self):
        """打印处理结果摘要"""
        # 计算总耗时
        elapsed = time.time() - self.start_time

        # 使用分隔线和对齐格式输出，让日志更易读
        unreal.log(f"\n{'─' * 60}")
        unreal.log(f"  处理完成！")
        unreal.log(f"{'─' * 60}")
        unreal.log(f"  成功: {self.results['success']}")
        unreal.log(f"  失败: {self.results['failed']}")
        unreal.log(f"  跳过: {self.results['skipped']}")
        # :.2f 表示保留两位小数
        unreal.log(f"  耗时: {elapsed:.2f} 秒")

        # 如果有错误，输出详细信息（最多显示10条，避免日志过多）
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
        """
        删除未使用的资产

        参数:
            search_path: 搜索路径，默认从 /Game 根目录开始
            dry_run: 预览模式，True 时不实际删除，只列出将被删除的资产
        """
        # list_assets 返回指定目录下所有资产的路径列表
        # recursive=True 表示递归搜索子目录
        all_assets = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True
        )

        def check_unused(asset_path):
            # does_directory_exist 检查路径是否为文件夹
            # 文件夹不需要检查引用，直接跳过
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                return None  # 跳过文件夹

            # find_package_referencers_for_asset 查找所有引用该资产的包
            # 这是判断资产是否被使用的标准方法
            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                asset_path,
                load_assets_to_confirm=True,  # 删除/判定前把需要加载才能确认的引用也算进来
            )
            # 排除自身引用（资产自身会引用自身）
            external_refs = [r for r in refs if r != asset_path]

            # 如果没有外部引用，说明资产未被使用
            if not external_refs:
                if not dry_run:
                    # 实际删除资产
                    unreal.EditorAssetLibrary.delete_asset(asset_path)
                # 无论是否删除，都记录日志
                unreal.log(f"  未使用: {asset_path}")
                return True
            return False

        processor = BatchProcessor("清理未使用资产")
        processor.process(all_assets, check_unused, "扫描引用...")

        if dry_run:
            unreal.log("\n(dry_run 模式，未实际删除)")

    @staticmethod
    def fix_naming_conventions(search_path="/Game"):
        """
        修复命名规范

        UE 项目通常有命名规范：
        - SM_ 开头：静态网格体 (Static Mesh)
        - T_ 开头：纹理 (Texture)
        - M_ 开头：材质 (Material)
        - BP_ 开头：蓝图 (Blueprint)
        """
        # 定义资产类到前缀的映射
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
            # list_assets 默认 include_folder=False，返回的都是资产路径，
            # 不需要再判断"是不是文件夹"（原判断永远不会成立）。
            # find_asset_data 获取资产的元数据，包括类名和短名称
            # 为什么不用 load_asset？因为 load_asset 会加载资产到内存，对于大量资产太慢
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            # 【易错点】asset_name 是 unreal.Name，不是 str —— 它没有 startswith，
            #   必须先 str() 转成普通字符串。
            name = str(asset_data.asset_name)
            # asset_class_path 是资产类的完整路径，转为字符串后可以包含类名
            class_str = str(asset_data.asset_class_path)

            # 【易错点】不要用 "class_key in class_str" 做子串匹配：
            #   class_str 形如 "/Script/Engine.MaterialInstanceConstant"，
            #   字典里 "Material" 排在前面，于是 MI_Foo 会被当成材质改成 M_MI_Foo。
            #   正确做法是取出 "." 之后真正的类名，做精确比较。
            class_name = class_str.split(".")[-1]

            for class_key, prefix in prefix_map.items():
                if class_name == class_key and not name.startswith(prefix):
                    new_name = prefix + name
                    # 构建新路径：保持原目录，只改文件名
                    new_path = f"{os.path.dirname(asset_path)}/{new_name}"
                    # rename_asset 同时支持重命名和移动
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
        # include_folder=True 让结果也包含文件夹路径
        all_paths = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True, include_folder=True
        )

        # 逆序遍历（先处理深层目录）
        # 为什么？因为删除空文件夹时，必须先删除子文件夹，再删除父文件夹
        # 例如：/Game/A/B/C 必须先删 C，再删 B，最后删 A
        folders = sorted(
            [p for p in all_paths
             if unreal.EditorAssetLibrary.does_directory_exist(p)],
            # key=lambda x: -len(x.split("/")) 按路径深度降序排列
            key=lambda x: -len(x.split("/"))
        )

        deleted = 0
        for folder in folders:
            # recursive=False 表示只列出直接子项
            contents = unreal.EditorAssetLibrary.list_assets(
                folder, recursive=False, include_folder=True
            )
            # 如果目录为空（没有资产也没有子文件夹），则删除
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
        """
        按类型组织资产到标准目录

        这是项目管理的最佳实践：将不同类型的资产放到对应目录
        """
        # 定义资产类到目标子目录的映射
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

            # 跳过已在 _Organized 目录中的资产，避免重复处理
            if "_Organized" in asset_path:
                return None

            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            class_str = str(asset_data.asset_class_path)

            # 查找资产类型对应的目标子目录
            target_subdir = None
            for class_key, subdir in type_dirs.items():
                if class_key in class_str:
                    target_subdir = subdir
                    break

            # 未匹配的类型放到 Other 目录
            if not target_subdir:
                target_subdir = "Other"

            target_dir = f"{target_base}/{target_subdir}"
            # make_directory 会自动创建多级目录（如果不存在）
            unreal.EditorAssetLibrary.make_directory(target_dir)

            # 移动资产（通过 rename_asset 实现移动）
            asset_name = asset_path.split("/")[-1]
            dest_path = f"{target_dir}/{asset_name}"

            # 检查目标是否已存在，避免覆盖
            if unreal.EditorAssetLibrary.does_asset_exist(dest_path):
                return None

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
        """
        批量重定向资产路径

        当项目结构调整时，需要将资产从旧路径迁移到新路径
        """
        assets = unreal.EditorAssetLibrary.list_assets(
            old_base, recursive=True
        )

        def redirect(asset_path):
            # 计算相对路径，然后拼接新基础路径
            # 例如：old_base="/Game/Old"，asset_path="/Game/Old/Assets/SM_Cube"
            # relative="/Assets/SM_Cube"，new_path="/Game/New/Assets/SM_Cube"
            relative = asset_path.replace(old_base, "", 1)
            new_path = new_base + relative

            # 确保目标目录存在
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
        """
        生成完整的项目健康报告

        报告包含：资产统计、命名规范检查、目录结构分析
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("  UE 项目健康报告")
        report_lines.append("=" * 60)

        all_assets = unreal.EditorAssetLibrary.list_assets(
            search_path, recursive=True
        )

        # 1. 基本统计：按类型分类计数
        report_lines.append(f"\n--- 资产统计 ---")
        report_lines.append(f"总资产数: {len(all_assets)}")

        type_counts = {}
        for asset_path in all_assets:
            # 跳过文件夹，只统计资产
            if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
                continue
            asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            # 从完整类路径中提取短类名（取最后一个 '.' 之后的部分）
            class_name = str(asset_data.asset_class_path).split(".")[-1]
            type_counts[class_name] = type_counts.get(class_name, 0) + 1

        # 按数量降序排列，只显示前15种类型
        for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
            report_lines.append(f"  {type_name}: {count}")

        # 2. 命名规范检查：检查资产名称是否包含空格
        # 空格在资产名称中可能导致路径问题，是常见的命名违规
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

        # 3. 目录结构：统计顶级目录下的资产数量
        report_lines.append(f"\n--- 顶级目录 ---")
        top_dirs = set()
        for asset_path in all_assets:
            parts = asset_path.split("/")
            # 资产路径格式：/Game/目录/文件，至少需要3段
            if len(parts) >= 3:
                top_dirs.add(parts[2])

        for d in sorted(top_dirs):
            # 计算每个顶级目录下的资产数量
            count = len([p for p in all_assets if f"/{d}/" in p])
            report_lines.append(f"  /Game/{d}: {count} 个资产")

        # 输出报告到日志
        for line in report_lines:
            unreal.log(line)

        # 保存报告到文件
        # project_saved_dir() 返回项目的 Saved 目录路径
        # 为什么保存到这里？因为 Saved 目录不会被版本控制，适合存放生成的文件
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
