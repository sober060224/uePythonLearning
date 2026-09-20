import os
import sys
import unreal

all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)


def print_directory_tree(path, indent=0, max_depth=3):
    """打印资产目录树"""
    if indent > max_depth:
        return

    # 获取子目录
    sub_dirs = unreal.EditorAssetLibrary.list_assets(
        path, recursive=False, include_folder=True
    )

    for item in sub_dirs:
        item_name = item.split("/")[-2]
        file_name = item.split("/")[-1]
        is_folder = unreal.EditorAssetLibrary.does_directory_exist(item)

        if is_folder:
            unreal.log(f"{'  ' * indent}📁 {item_name}/")
            print_directory_tree(item, indent + 1, max_depth)
        else:
            unreal.log(f"{'  ' * indent}📄 {file_name}")


# unreal.log("\n--- 项目目录结构 (前3层) ---")
# print_directory_tree("/Game", max_depth=3)

# assets = unreal.EditorAssetLibrary.list_assets("/Game", False)
# for asset_path in assets:
#     asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
#     print(f"asset_data.asset_class_path : {asset_data.asset_class_path}")


def find_assets_by_class(class_name, search_path="/Game"):
    """
    按类名搜索资产
    class_name: 如 "Texture2D", "StaticMesh", "Blueprint" 等
    """
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    matching = []

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        asset_class = str(asset_data.asset_class_path.asset_name)
        if class_name.lower() in asset_class.lower():
            matching.append(asset_data)

    return matching


# 搜索所有纹理
# textures = find_assets_by_class("Texture2D")
# unreal.log(f"\n找到 {len(textures)} 个纹理:")
# for tex in textures[:10]:
#     unreal.log(f"  {tex.package_name} - {tex.asset_name}")


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
    # 使用 EditorAssetLibrary.get_tag_values(asset_path) 获取所有标签
    # 返回类型是 Map[Name, str]，即字典
    tag_values = unreal.EditorAssetLibrary.get_tag_values(asset_path)
    if tag_values:
        unreal.log(f"标签数量: {len(tag_values)}")
        for tag_name, tag_value in tag_values.items():
            unreal.log(f"  {tag_name}: {tag_value}")

    # 获取引用信息
    references = list(
        unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path)
    )
    unreal.log(f"被 {len(references)} 个资产引用:")

    for ref in references[:5]:
        unreal.log(f"  ← {ref}")


# # 测试（替换为你项目中的实际资产路径）
# if all_assets:
#     inspect_asset(all_assets[0])

# ─────────────────────────────────────────────────────────
# 6. 资产统计报告
# ─────────────────────────────────────────────────────────


def generate_asset_report(search_path="/Game"):
    """生成项目资产统计报告"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    type_counts = {}
    folder_counts = {}

    for asset_path in all_assets:
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        unreal.log(str(asset_data.asset_class_path))
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


# generate_asset_report("/Game")
# unreal.log("\n资产管理第1课完成！")


# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写函数，找出项目中最大的10个资产（按文件大小）
def first(path):
    project_dir = r"C:\Users\sober\Documents\Unreal Projects\LyraStarterGame"
    assets = []

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        relative_path = str(asset_path).removeprefix("/Game").replace("/", os.sep)
        file_path = os.path.join(project_dir, "Content", relative_path + ".uasset")

        if os.path.isfile(file_path):
            assets.append(
                (asset_data.asset_name, file_path, os.path.getsize(file_path))
            )

    top_assets = sorted(assets, key=lambda item: item[2], reverse=True)[:10]

    for asset_name, file_path, file_size in top_assets:
        unreal.log(
            f"资产名：{asset_name}\t资产大小：{file_size} 字节\t路径：{file_path}"
        )


# first("/Game")


# assets_path = unreal.EditorAssetLibrary.list_assets("/Game")
# for asset_path in assets_path:
#     unreal.log(
#         str(
#             unreal.EditorAssetLibrary.find_asset_data(
#                 assets_path
#             ).asset_class_path.asset_name
#         )
#     )

"""asset_path = sys.argv[1]
target_material = "WorldGridMaterial"
asset = unreal.EditorAssetLibrary.find_asset_data(asset_path)
unreal.log(str(asset.asset_class_path.asset_name))
mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
static_materials = mesh.get_editor_property("static_materials")
for sm in static_materials:
    unreal.log(sm)
    mat = sm.material_interface
    mat_name = mat.get_name()
    if mat_name == target_material:
        unreal.log(mat_name)"""


# 2. 搜索所有使用了特定材质的网格体
def search_mesh(material):
    for asset_path in all_assets:
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        # 只有网格体资产才有 static_materials 属性；
        # 先用 find_asset_data 判断类型，避免对纹理、蓝图等资产 load 后取值崩溃
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if "StaticMesh" not in str(asset_data.asset_class_path):
            continue

        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        static_materials = mesh.get_editor_property("static_materials")
        for sm in static_materials:
            mat_name = sm.material_interface.get_name()
            if mat_name == material:
                unreal.log(mat_name)


# search_mesh("WorldGridMaterial")

"""# all_assets[0] 是字符串路径，字符串没有 get_name() 方法；
# 资产元数据要用 find_asset_data 读取，asset_name 才是资产短名
asset_path = all_assets[0]
asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
asset = unreal.EditorAssetLibrary.load_asset(asset_path)
unreal.log(f"asset_path:{asset_path}\nasset_data.asset_name:{asset_data.asset_name}\nasset_data.asset_class_path.asset_name:{asset_data.asset_class_path.asset_name}")
unreal.log(f"asset.get_name():{asset.get_name()}\nasset.get_path_name():{asset.get_path_name()}\n")"""


# 3. 编写一个资产搜索工具，支持按名称、类型、路径的组合搜索
def search_asset(name=None, type=None, path=None) -> list[unreal.AssetData]:
    if name is None and type is None and path is None:
        return []

    name_list: list[unreal.AssetData] = []
    type_list: list[unreal.AssetData] = []
    path_list: list[unreal.AssetData] = []

    if path is not None:
        # path 必须是 UE 内部路径，如 /Game/Effects/Meshes/box，
        # 不能传 Windows 磁盘路径；无效路径返回的 AssetData 无效，需跳过
        asset_data = unreal.EditorAssetLibrary.find_asset_data(path)
        if str(asset_data.package_name) != "None":
            path_list.append(asset_data)
        return path_list

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if name is not None and name == asset_data.asset_name:
            name_list.append(asset_data)
        if type is not None and type == asset_data.asset_class_path.asset_name:
            type_list.append(asset_data)

    if name is not None and type is None:
        return name_list
    elif name is None and type is not None:
        return type_list

    result_list: list[unreal.AssetData] = []
    for m_name in name_list:
        for m_type in type_list:
            # 用资产包路径比较，is 比较的是 Python 对象同一性，find_asset_data
            # 每次都返回新包装对象，is 恒为 False 会导致交集为空
            if m_name.package_name == m_type.package_name:
                result_list.append(m_type)
    return result_list


"""asset_list = search_asset(
    type = "StaticMesh"  # UE 内部路径，不是磁盘路径
)
for i in asset_list:
    unreal.log(i)"""


# 4. 生成一份 Markdown 格式的项目资产报告
def md_report():
    path = os.path.join(unreal.Paths.project_dir(), "my01.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("## 项目资产报告\n")
        f.write("|资产类|资产路径|资产名\n|-|-|-\n")

    for asset_path in list(all_assets)[:5]:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(
                f"|{asset_data.asset_class_path.asset_name}|{asset_data.package_path}|{asset_data.asset_name}\n"
            )


unreal.log(unreal.Paths.project_dir())
# md_report()


# def test():
#     notes_dir = os.path.join(
#         ".", "notes"
#     )  # 拼接路径，自动适配 Windows 的 \ 和 Mac 的 /
#     os.makedirs(notes_dir, exist_ok=True)  # 创建文件夹；已存在也不报错
#     path = os.path.join(notes_dir, "note.txt")
#     print(f"notes_dir = {notes_dir}\npath = {path}")
#     if os.path.exists(path):  # 判断路径是否存在，返回 True/False
#         print("笔记已存在：", path)


# test()
