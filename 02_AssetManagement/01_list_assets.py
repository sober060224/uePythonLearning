"""
=============================================================
资产管理 第1课：列出和搜索资产
=============================================================

学习目标：
  - 掌握 EditorAssetLibrary 的资产查询功能
  - 学会按类型、路径搜索资产
  - 获取资产的详细元数据

核心类：unreal.EditorAssetLibrary
  - 不需要加载资产到内存即可查询
  - 适合批量操作和项目管理工具
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 列出指定路径下的所有资产
# ─────────────────────────────────────────────────────────

# list_assets(path, recursive=True, include_folder=False)
# path: Content 下的路径，如 "/Game/Characters"
# recursive: 是否递归搜索子目录
# include_folder: 是否包含文件夹本身

# 列出 /Game 下所有资产
all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)
unreal.log(f"项目共有 {len(all_assets)} 个资产")

# 只列出 /Game/Characters 下的直接资产（不递归）
if unreal.EditorAssetLibrary.does_directory_exist("/Game/Characters"):
    direct_assets = unreal.EditorAssetLibrary.list_assets(
        "/Game/Characters",
        recursive=False,
        include_folder=False
    )
    unreal.log(f"\n/Game/Characters 目录下有 {len(direct_assets)} 个资产:")
    for asset in direct_assets:
        unreal.log(f"  {asset}")

# ─────────────────────────────────────────────────────────
# 2. 列出目录结构
# ─────────────────────────────────────────────────────────

def print_directory_tree(path, indent=0, max_depth=3):
    """打印资产目录树"""
    if indent > max_depth:
        return

    # 获取子目录
    sub_dirs = unreal.EditorAssetLibrary.list_assets(
        path, recursive=False, include_folder=True
    )

    for item in sub_dirs:
        item_name = item.split("/")[-1]
        is_folder = unreal.EditorAssetLibrary.does_directory_exist(item)

        if is_folder:
            unreal.log(f"{'  ' * indent}📁 {item_name}/")
            print_directory_tree(item, indent + 1, max_depth)
        else:
            unreal.log(f"{'  ' * indent}📄 {item_name}")

unreal.log("\n--- 项目目录结构 (前3层) ---")
print_directory_tree("/Game", max_depth=3)

# ─────────────────────────────────────────────────────────
# 3. 按类型搜索资产
# ─────────────────────────────────────────────────────────

def find_assets_by_class(class_name, search_path="/Game"):
    """
    按类名搜索资产
    class_name: 如 "Texture2D", "StaticMesh", "Blueprint" 等
    """
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    matching = []

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        asset_class = str(asset_data.asset_class_path)
        if class_name.lower() in asset_class.lower():
            matching.append(asset_data)

    return matching

# 搜索所有纹理
textures = find_assets_by_class("Texture2D")
unreal.log(f"\n找到 {len(textures)} 个纹理:")
for tex in textures[:10]:
    unreal.log(f"  {tex.package_name} - {tex.asset_name}")

# 搜索所有静态网格体
meshes = find_assets_by_class("StaticMesh")
unreal.log(f"\n找到 {len(meshes)} 个静态网格体:")
for mesh in meshes[:10]:
    unreal.log(f"  {mesh.package_name} - {mesh.asset_name}")

# ─────────────────────────────────────────────────────────
# 4. 获取资产详细信息
# ─────────────────────────────────────────────────────────

def inspect_asset(asset_path):
    """打印资产的详细信息"""
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.log_warning(f"资产不存在: {asset_path}")
        return

    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"资产: {asset_data.asset_name}")
    unreal.log(f"路径: {asset_data.package_name}")
    unreal.log(f"类型: {asset_data.asset_class_path}")

    # 获取标签
    tags = asset_data.tags_and_values
    if tags:
        unreal.log(f"标签数量: {len(tags)}")
        for tag_name, tag_value in tags.items():
            unreal.log(f"  {tag_name}: {tag_value}")

    # 获取引用信息
    references = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
        asset_path
    )
    unreal.log(f"被 {len(references)} 个资产引用:")
    for ref in references[:5]:
        unreal.log(f"  ← {ref}")

# 测试（替换为你项目中的实际资产路径）
if all_assets:
    inspect_asset(all_assets[0])

# ─────────────────────────────────────────────────────────
# 5. 查找未使用的资产
# ─────────────────────────────────────────────────────────

def find_unused_assets(search_path="/Game"):
    """查找没有被任何其他资产引用的资产（可能是废弃资产）"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    unused = []

    task = unreal.ScopedSlowTask(len(all_assets), "正在查找未使用的资产...")
    task.make_dialog(True)

    for asset_path in all_assets:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, f"检查: {asset_path.split('/')[-1]}")

        # 跳过文件夹
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )

        # 过滤掉自身引用
        external_refs = [r for r in referencers if r != asset_path]

        if len(external_refs) == 0:
            unused.append(asset_path)

    return unused

# 取消注释以运行（可能需要较长时间）
# unused = find_unused_assets("/Game")
# unreal.log(f"\n找到 {len(unused)} 个未使用的资产:")
# for path in unused[:20]:
#     unreal.log(f"  {path}")

# ─────────────────────────────────────────────────────────
# 6. 资产统计报告
# ─────────────────────────────────────────────────────────

def generate_asset_report(search_path="/Game"):
    """生成项目资产统计报告"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    type_counts = {}
    folder_counts = {}

    task = unreal.ScopedSlowTask(len(all_assets), "正在生成资产报告...")
    task.make_dialog(True)

    for asset_path in all_assets:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0)

        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        class_name = str(asset_data.asset_class_path).split(".")[-1]
        type_counts[class_name] = type_counts.get(class_name, 0) + 1

        # 统计每个顶级文件夹
        parts = asset_path.split("/")
        if len(parts) >= 3:
            folder = parts[2]  # /Game/Folder/...
            folder_counts[folder] = folder_counts.get(folder, 0) + 1

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"  资产统计报告")
    unreal.log(f"{'=' * 50}")

    unreal.log(f"\n--- 按类型统计 ---")
    for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        unreal.log(f"  {type_name}: {count}")

    unreal.log(f"\n--- 按文件夹统计 ---")
    for folder, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
        unreal.log(f"  /Game/{folder}: {count}")

    unreal.log(f"\n总资产数: {len(all_assets)}")

generate_asset_report("/Game")

unreal.log("\n资产管理第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写函数，找出项目中最大的10个资产（按文件大小）
# 2. 搜索所有使用了特定材质的网格体
# 3. 编写一个资产搜索工具，支持按名称、类型、路径的组合搜索
# 4. 生成一份 Markdown 格式的项目资产报告
