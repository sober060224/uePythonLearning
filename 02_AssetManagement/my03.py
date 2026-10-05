import queue
import datetime
import hashlib
import os
import unreal


# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个"资产清理向导"：找出未使用资产、重复资产、
#    命名不规范的资产，并生成报告
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


def first():
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")
    unused = []
    repeat = []
    non_standard = []
    size_map: dict[int, list[str]] = {}
    hash_map: dict[str, list[str]] = {}
    content_dir = os.path.abspath(unreal.Paths.project_content_dir())
    content_dir = os.path.normpath(content_dir)

    for asset_path in all_assets:
        references = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )
        real_path = [a for a in references if a != asset_path.split(".")[0]]
        # 未使用资产
        if not real_path:
            unused.append(asset_path)

        # 重复资产
        # 先用文件大小过滤，将文件大小相同的文件路径放在一起
        path = asset_path.removeprefix("/Game/").split(".")[0]
        path = os.path.normpath(path)
        path = os.path.join(content_dir, path)
        disk_dir = next(
            (a for a in [path + ".uasset", path + ".umap"] if os.path.exists(a)), None
        )
        if not disk_dir:
            continue

        # 系统路径
        size = os.path.getsize(disk_dir)
        size_map.setdefault(size, []).append(disk_dir)

        # 命名不规范资产
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        name = str(asset_data.asset_name)
        prefix = PREFIX_MAP.get(str(asset_data.asset_class_path.asset_name))
        if prefix and not name.startswith(prefix):
            non_standard.append(asset_path)

    # 再用哈希深度过滤
    for dist_dir in size_map.values():
        if len(dist_dir) < 2:
            continue

        for dir in dist_dir:
            with open(dir, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()

            # 移除前缀\，标准化引擎路径，添加前缀/Game/
            dir = dir.removeprefix(f"{content_dir}\\")  # 引擎路径
            dir = unreal.Paths.normalize_filename(dir)
            dir = unreal.Paths.combine(["/Game", dir])
            dir = dir.removesuffix(".umap")
            dir = dir.removesuffix(".uasset")

            hash_map.setdefault(h, []).append(dir)

    for size, dirs in hash_map.items():
        if len(dirs) > 1:
            repeat.extend(dirs)

    unreal.log("未使用的资产：\n-------------------------------")
    for i in unused:
        unreal.log(i)

    unreal.log("重复的资产：\n--------------------------------")
    for i in repeat:
        unreal.log(i)

    unreal.log("命名不规范资产的资产：\n-------------------------------------")
    for i in non_standard:
        unreal.log(i)


# first()

# path = r"abc\bbb\ccc"
# a = "abc"
# path = path.removeprefix(f"{a}\\")
# unreal.log(unreal.Paths.project_content_dir())
# content_dir = os.path.abspath(unreal.Paths.project_content_dir())
# content_dir = os.path.normpath(content_dir)
# unreal.log(content_dir)
# # dir = dir.removeprefix(content_dir)                      # 剩 "\A/B.uasset"（前导反斜杠）
# path = os.path.join(content_dir, path)
# unreal.log(path)
# path = str(path).removeprefix(content_dir + "\\")
# unreal.log(path)
# path = unreal.Paths.combine([path, "aaa"])
# path = unreal.Paths.normalize_filename(path)
# unreal.log(path)
# path = unreal.Paths.combine(["/Game", path])
# unreal.log(path)
# dir = unreal.Paths.combine(["/Game/", dir])


# 2. 编写一个工具，自动按命名规范重命名整个项目的资产
def second():
    all_asset = unreal.EditorAssetLibrary.list_assets("/Game")

    for asset_path in all_asset:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)

        # 把每个资产的名字的前缀改成标准的
        standard_prefix = PREFIX_MAP.get(str(asset_data.asset_class_path.asset_name))
        # 如果不在资产类名不在表里面返回空，跳过
        if not standard_prefix:
            continue

        # 资产名字可能有多个前缀，拿到第一个前缀，没有前缀会越界
        prefix = str(asset_data.asset_name).split("_", 1)
        if len(prefix) < 2:
            continue

        name = standard_prefix + prefix[1]  # 合成正确名称
        path = "/".join(asset_path.split("/")[:-1]) + f"/{name}"  # 路径名最好就是用包名
        if unreal.EditorAssetLibrary.rename_asset(asset_data.package_name, path):
            unreal.log("success")


# second()
# path = "sdf_asd_aaa"
# prefix = path.split("_", 1)
# unreal.log(prefix)


# 没有按日期组织
def third():
    # 在saved文件夹里面新建_Archive文件夹
    selected_asset = unreal.EditorUtilityLibrary.get_selected_asset_data()
    saved_dir = unreal.Paths.project_saved_dir()
    saved_dir = os.path.join(os.path.abspath(saved_dir), "_Archive")
    os.makedirs(saved_dir, exist_ok=True)

    # 将选中的所有资产都导出到文件夹里面
    # 先拿到资产的包名.资产名，再指定saved_dir路径

    # 按日期组织
    assets_to_export = []
    for asset_data in selected_asset:
        path = str(asset_data.package_name) + f".{asset_data.asset_name}"
        assets_to_export.append(path)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.export_assets(assets_to_export, saved_dir)


# third()


# 3. 实现一个"资产归档"功能：将选中的资产移动到一个 _Archive 文件夹并按日期组织
def aaa():
    # 在引擎内部新建文件夹_Archive
    unreal.EditorAssetLibrary.make_directory("/Game/_Archive")
    selected_data = unreal.EditorUtilityLibrary.get_selected_asset_data()
    content_dir = unreal.Paths.project_content_dir()
    content_dir = os.path.abspath(content_dir)

    # 每个文件拿到都是asset_data，整理出每个文件的系统路径，找到修改日期
    for asset_data in selected_data:
        package_name = str(asset_data.package_name)

        # 找出每个文件的系统路径，还有修改日期并新建文件夹
        ext = (
            ".umap"
            if str(asset_data.asset_class_path.asset_name) == "World"
            else ".uasset"
        )
        file_path = os.path.join(content_dir, package_name.removeprefix("/Game/")) + ext
        unreal.log(f"选中的资产路径：{file_path}")

        time = (
            datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            .astimezone()
            .strftime("%Y-%m-%d")
        )

        # 创建到_Archive文件夹里面
        direct_path = os.path.join(content_dir, "_Archive", time)
        os.makedirs(direct_path, exist_ok=True)

        # 用引擎路径rename_asset移动文件
        # 初始路径 = package_name
        name = asset_data.asset_name
        # 目标路径在_Archive/time文件夹内，/Game/_Archive + time + name
        file_path = unreal.Paths.combine(["/Game/_Archive", time, name])
        if unreal.EditorAssetLibrary.rename_asset(package_name, file_path):
            unreal.log(f"{file_path} ----> success")


# aaa()
# all_asset = unreal.EditorAssetLibrary.list_assets("/Game")
# content_dir = os.path.abspath(unreal.Paths.project_content_dir())
# unreal.log(content_dir)


# 4. 编写一个迁移工具：将资产从一个项目复制到另一个
#    项目并修复路径
def fourth(dest_path: str):
    """
    Args:
        dest_path: 另一个项目系统文件夹路径
    传入目标系统路径，直接将选中的资产导出到另一个项目里面，export_assets要拿所有资产的包名路径和目标系统文件夹路径名
    """
    selected_asset = unreal.EditorUtilityLibrary.get_selected_asset_data()
    selected_package = []
    q = queue.Queue()

    # 修复路径要将资产依赖一起导出
    for asset in selected_asset:
        q.put(asset.package_name)
    asset_registry = unreal.AssetRegistryHelpers().get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=True, include_soft_package_references=True
    )
    while not q.empty():
        t = q.get()
        if t in selected_package:
            continue
        selected_package.append(t)

        for i in asset_registry.get_dependencies(t, options) or []:
            # 不在/Game里面的和已经访问过的资产直接跳过
            if not str(i).startswith("/Game/") or i in selected_package:
                continue
            q.put(i)

    asset_tools = unreal.AssetToolsHelpers().get_asset_tools()
    asset_tools.export_assets(selected_package, dest_path)


# path = r"C:\Users\sober\Documents\Unreal Projects\LyraStarterGame\Content"
# fourth(path)
# q = queue.Queue()
# s = [[1, 3], [2, 3], [0], [3]]
# vis = [False] * 4
# q.put(0)
# vis[0] = True
# while not q.empty():
#     t = q.get()
#     unreal.log(t)
#     for i in s[t]:
#         if not vis[i]:
#             vis[i] = True
#             q.put(i)
