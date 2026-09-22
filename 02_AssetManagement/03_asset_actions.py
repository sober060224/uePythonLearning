"""
=============================================================
资产管理 第3课：资产操作 - 重命名、移动、删除等
=============================================================

学习目标：
  - 批量重命名资产
  - 移动和复制资产
  - 修复引用关系
  - 资产整合（Consolidate）

核心原则：
  - UE 会自动维护引用关系
  - 移动/重命名时引用会自动更新
  - 操作前先备份或使用版本控制

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出指定路径下的资产路径数组
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产的元数据（类型、名称等）
  unreal.EditorAssetLibrary.rename_asset(source_asset_path: str, destination_asset_path: str) -> bool  —— 重命名/移动资产并自动更新引用
  unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool  —— 判断指定资产是否存在
  unreal.EditorAssetLibrary.delete_asset(asset_path_to_delete: str) -> bool  —— 删除指定资产
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建指定内容目录
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  —— 查找引用该资产的所有包
  unreal.EditorAssetLibrary.save_directory(directory_path: str, only_if_is_dirty: bool = True, recursive: bool = True) -> bool  —— 保存目录下的所有资产
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 重命名资产
# ─────────────────────────────────────────────────────────

def rename_asset(current_path, new_name):
    """
    重命名单个资产

    参数:
        current_path: 当前路径 (如 "/Game/OldName")
        new_name: 新名称 (如 "NewName"，不包含路径)
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(current_path):
        unreal.log_warning(f"资产不存在: {current_path}")
        return False

    # 【初学者易错点】rename_asset 的第二个参数不是"新名称"，而是"完整的目标路径"。
    #   比如要把 /Game/OldName 重命名为 NewName，第二个参数要写 "/Game/NewName"，
    #   而不是只写 "NewName"。这是 UE API 的常见设计模式——路径参数都是完整的。
    #   先用 split + 切片提取当前目录部分，再拼上新名称。
    dest_dir = "/".join(current_path.split("/")[:-1])
    success = unreal.EditorAssetLibrary.rename_asset(
        current_path, dest_dir + "/" + new_name
    )

    # 【UE 概念】rename_asset 会自动更新所有引用该资产的地方。
    #   比如一个蓝图引用了 /Game/SM_Cube，你重命名后蓝图会自动指向新路径。
    #   这是 UE 资产系统的"自动引用维护"机制。
    if success:
        new_path = "/".join(current_path.split("/")[:-1]) + "/" + new_name
        unreal.log(f"重命名成功: {current_path} → {new_path}")
    else:
        unreal.log_error(f"重命名失败: {current_path}")

    return success

# ─────────────────────────────────────────────────────────
# 2. 批量重命名
# ─────────────────────────────────────────────────────────

def batch_rename(search_path, prefix="", suffix="",
                 find_text="", replace_text=""):
    """
    批量重命名指定路径下的资产

    参数:
        search_path: 搜索路径
        prefix: 添加前缀
        suffix: 添加后缀
        find_text: 查找文本
        replace_text: 替换文本
    """
    # recursive=False：只处理当前层级，不递归子目录
    # 【为什么不用 recursive=True？】批量重命名如果递归，可能会跨目录重命名，
    #   容易出问题。建议逐层操作，先处理一层确认无误再处理下一层。
    assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=False)

    if not assets:
        unreal.log_warning(f"路径下没有资产: {search_path}")
        return

    unreal.log(f"找到 {len(assets)} 个资产要重命名")

    # ScopedSlowTask 显示进度条，让用户知道重命名到哪了
    task = unreal.ScopedSlowTask(len(assets), "批量重命名...")
    task.make_dialog(True)

    renamed_count = 0
    for asset_path in assets:
        if task.should_cancel():
            break

        current_name = asset_path.split("/")[-1]

        # 跳过文件夹——文件夹不是资产，不能用 rename_asset 重命名
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            task.enter_progress_frame(1.0)
            continue

        new_name = current_name

        # 先执行查找替换（顺序很重要：先替换再加前后缀）
        if find_text and replace_text:
            new_name = new_name.replace(find_text, replace_text)

        if prefix:
            new_name = prefix + new_name

        if suffix:
            new_name = new_name + suffix

        task.enter_progress_frame(1.0, f"{current_name} → {new_name}")

        # 只有名称变化了才执行重命名，避免无意义的操作
        if new_name != current_name:
            if rename_asset(asset_path, new_name):
                renamed_count += 1

    unreal.log(f"批量重命名完成: {renamed_count} 个资产已重命名")

# ─────────────────────────────────────────────────────────
# 3. 添加命名前缀（UE 资产命名规范）
# ─────────────────────────────────────────────────────────
# 【UE 概念】UE 社区推荐使用资产前缀来快速识别资产类型：
#   比如看到 SM_Cube 就知道是静态网格体，看到 T_Wood 就知道是纹理。
#   这在大型项目中非常重要——团队成员能一眼看出资产类型，便于协作。

PREFIX_MAP = {
    "Blueprint": "BP_",
    "Material": "M_",
    "MaterialInstanceConstant": "MI_",
    "Texture2D": "T_",
    "StaticMesh": "SM_",
    "SkeletalMesh": "SK_",
    "AnimBlueprint": "ABP_",
    "AnimSequence": "AS_",
    "SoundWave": "S_",
    "WidgetBlueprint": "WBP_",
    "ParticleSystem": "PS_",
    "NiagaraSystem": "NS_",
    "DataTable": "DT_",
    "DataAsset": "DA_",
}

def add_standard_prefixes(search_path):
    """为资产添加标准命名前缀"""
    assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    renamed = 0
    for asset_path in assets:
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # 【注意】find_asset_data 返回的 asset_class_path 是一个 SoftClassPath 对象，
        #   str() 转换后可能包含模块前缀（如 "Engine.Texture2D"），
        #   所以用 split(".")[-1] 取最后一段，得到纯净的类名 "Texture2D"。
        class_name = str(asset_data.asset_class_path).split(".")[-1]
        current_name = asset_path.split("/")[-1]

        # 查找对应前缀，如果没有映射就跳过
        prefix = PREFIX_MAP.get(class_name, "")
        # 已经有正确前缀的资产不重复添加
        if prefix and not current_name.startswith(prefix):
            new_name = prefix + current_name
            unreal.log(f"  {current_name} → {new_name}")
            rename_asset(asset_path, new_name)
            renamed += 1

    unreal.log(f"已为 {renamed} 个资产添加前缀")

# ─────────────────────────────────────────────────────────
# 4. 移动资产
# ─────────────────────────────────────────────────────────

def move_asset(source_path, destination_directory):
    """
    移动资产到新目录（自动更新引用）

    参数:
        source_path: 源路径 (如 "/Game/OldFolder/MyMesh")
        destination_directory: 目标目录 (如 "/Game/NewFolder")
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(source_path):
        unreal.log_warning(f"源资产不存在: {source_path}")
        return False

    # make_directory 会递归创建多级目录（类似 os.makedirs）
    # 如果目录已存在，不会报错
    unreal.EditorAssetLibrary.make_directory(destination_directory)

    # 【UE 概念】UE 的移动操作实际上是"重命名"——把资产从一个路径重命名到另一个路径。
    #   rename_asset 同时也是移动函数，因为 UE 的资产路径就是它的"地址"。
    asset_name = source_path.split("/")[-1]
    dest_path = f"{destination_directory}/{asset_name}"

    # 【初学者易错点】如果目标路径已经有同名资产，rename_asset 会失败。
    #   先检查是否存在，避免静默失败。
    if unreal.EditorAssetLibrary.does_asset_exist(dest_path):
        unreal.log_warning(f"目标路径已存在资产: {dest_path}")
        return False

    success = unreal.EditorAssetLibrary.rename_asset(source_path, dest_path)

    if success:
        unreal.log(f"移动成功: {source_path} → {dest_path}")
    return success

def move_assets_to_folder(asset_paths, destination_directory):
    """批量移动多个资产"""
    unreal.EditorAssetLibrary.make_directory(destination_directory)

    task = unreal.ScopedSlowTask(len(asset_paths), "移动资产...")
    task.make_dialog(True)

    moved = 0
    for asset_path in asset_paths:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, f"移动: {asset_path}")

        if move_asset(asset_path, destination_directory):
            moved += 1

    unreal.log(f"已移动 {moved}/{len(asset_paths)} 个资产")

# ─────────────────────────────────────────────────────────
# 5. 删除资产
# ─────────────────────────────────────────────────────────

def safe_delete_asset(asset_path):
    """
    安全删除资产（先检查引用）

    返回: (是否可以安全删除, 引用列表)
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return False, []

    # 【UE 概念】在 UE 中删除资产前必须检查引用。
    #   如果一个纹理被某个材质引用，删除纹理会导致材质变黑（引用断裂）。
    #   find_package_referencers_for_asset 返回所有引用该资产的包路径。
    referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
        asset_path
    )

    # 【注意】资产可能自引用（比如蓝图的默认值引用自身），
    #   这不算"被外部使用"，所以要排除。
    external_refs = [r for r in referencers if r != asset_path]

    if external_refs:
        unreal.log_warning(
            f"资产 {asset_path} 被 {len(external_refs)} 个其他资产引用:"
        )
        for ref in external_refs[:5]:
            unreal.log(f"  ← {ref}")
        return False, external_refs

    # 没有外部引用，可以安全删除
    return True, []

def delete_asset(asset_path, force=False):
    """
    删除资产

    参数:
        asset_path: 资产路径
        force: 是否强制删除（忽略引用检查）
    """
    if not force:
        is_safe, refs = safe_delete_asset(asset_path)
        if not is_safe:
            unreal.log_error(
                f"拒绝删除 {asset_path}，有 {len(refs)} 个引用。"
                f"使用 force=True 强制删除"
            )
            return False

    success = unreal.EditorAssetLibrary.delete_asset(asset_path)
    if success:
        unreal.log(f"已删除: {asset_path}")
    return success

def cleanup_unused_assets(search_path="/Game", dry_run=True):
    """
    清理未使用的资产

    参数:
        search_path: 搜索路径
        dry_run: True = 只报告不删除，False = 实际删除
    """
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    unused = []

    task = unreal.ScopedSlowTask(len(all_assets), "检查引用...")
    task.make_dialog(True)

    for asset_path in all_assets:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, asset_path.split("/")[-1])

        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )
        external_refs = [r for r in referencers if r != asset_path]

        if not external_refs:
            unused.append(asset_path)

    unreal.log(f"\n找到 {len(unused)} 个未使用的资产:")
    for path in unused:
        unreal.log(f"  {path}")

    # 【初学者易错点】dry_run 模式是安全测试的好习惯：
    #   先用 dry_run=True 看看会删什么，确认没问题再用 dry_run=False 执行。
    #   这是防止误删的重要手段。
    if not dry_run and unused:
        unreal.log("\n正在删除...")
        for path in unused:
            delete_asset(path, force=True)
    elif dry_run:
        unreal.log("\n(dry_run 模式，未实际删除)")

    return unused

# ─────────────────────────────────────────────────────────
# 6. 资产整合（Consolidate）
# ─────────────────────────────────────────────────────────

def consolidate_assets(asset_to_keep, asset_to_replace):
    """
    将两个资产合并：所有引用 asset_to_replace 的地方
    都改为引用 asset_to_keep，然后删除 asset_to_replace

    用途：清理重复资产
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_to_keep):
        unreal.log_error(f"资产不存在: {asset_to_keep}")
        return False

    if not unreal.EditorAssetLibrary.does_asset_exist(asset_to_replace):
        unreal.log_error(f"资产不存在: {asset_to_replace}")
        return False

    # 【初学者易错点】consolidate_assets 要求传入"对象"，不是"路径字符串"。
    #   必须先用 load_asset 加载成对象再传入。
    #   传字符串会报 TypeError。
    keep_obj = unreal.EditorAssetLibrary.load_asset(asset_to_keep)
    replace_obj = unreal.EditorAssetLibrary.load_asset(asset_to_replace)
    if not keep_obj or not replace_obj:
        unreal.log_error("资产加载失败，无法整合")
        return False

    # 【UE 概念】Consolidate（整合）是 UE 的"资产替换"功能。
    #   它会把所有引用 replace_obj 的地方自动改成引用 keep_obj，
    #   然后删除 replace_obj。比手动查找引用再替换高效得多。
    #   常用于清理重复导入的资产（比如同一张纹理被导入了两次）。
    success = unreal.EditorAssetLibrary.consolidate_assets(
        keep_obj,
        [replace_obj]
    )

    if success:
        unreal.log(f"整合成功: {asset_to_replace} → {asset_to_keep}")
    else:
        unreal.log_error("整合失败")

    return success

# ─────────────────────────────────────────────────────────
# 7. 保存资产
# ─────────────────────────────────────────────────────────

def save_asset(asset_path):
    """保存单个资产"""
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        # save_asset 将内存中的修改写入磁盘
        # only_if_is_dirty=True 表示只保存"有修改"的资产，没改过的不保存
        unreal.EditorAssetLibrary.save_asset(asset_path)
        unreal.log(f"已保存: {asset_path}")

def save_all_dirty_assets():
    """保存所有未保存的资产"""
    # 【UE 概念】"脏资产"（dirty asset）是指修改过但还没保存到磁盘的资产。
    #   save_directory 会保存指定目录下所有"脏"资产。
    #   only_if_is_dirty 参数避免重新保存没修改过的资产，节省时间。
    unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=True)
    unreal.log("已保存所有脏资产")

def save_current_level():
    """保存当前关卡"""
    # 【UE 概念】关卡（Level）和普通资产的保存方式不同。
    #   普通资产用 EditorAssetLibrary.save_asset，
    #   关卡用 EditorLevelLibrary.save_current_level，因为关卡是特殊的持久化对象。
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log("关卡已保存")

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 示例1: 批量重命名（添加前缀）
# batch_rename("/Game/Meshes", prefix="SM_", find_text="mesh", replace_text="Mesh")

# 示例2: 添加标准前缀
# add_standard_prefixes("/Game/NewAssets")

# 示例3: 查找未使用的资产
# cleanup_unused_assets("/Game", dry_run=True)

# 示例4: 整合重复资产
# consolidate_assets("/Game/Materials/M_Wood", "/Game/Materials/M_Wood_Duplicate")

unreal.log("资产管理第3课完成！（资产操作）")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个"资产清理向导"：找出未使用资产、重复资产、
#    命名不规范的资产，并生成报告
# 2. 编写一个工具，自动按命名规范重命名整个项目的资产
# 3. 实现一个"资产归档"功能：将选中的资产移动到一个
#    _Archive 文件夹并按日期组织
# 4. 编写一个迁移工具：将资产从一个项目复制到另一个
#    项目并修复路径
