"""
=============================================================
高级主题 第2课：与外部数据交互
=============================================================

学习目标：
  - 读取 CSV/JSON 数据并在 UE 中使用
  - 创建和修改 DataTable
  - 导出项目数据到外部格式
  - 与外部工具的数据交换

应用场景：
  - 从策划表格导入游戏数据
  - 导出项目报告
  - 与外部工具（如 Excel、数据库）集成
=============================================================
"""

import unreal
import json
import csv
import os

# ─────────────────────────────────────────────────────────
# 1. 读取 JSON 数据
# ─────────────────────────────────────────────────────────

def read_json(file_path):
    """读取 JSON 文件"""
    if not os.path.exists(file_path):
        unreal.log_error(f"文件不存在: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    unreal.log(f"已读取 JSON: {file_path} ({type(data).__name__})")
    return data

def write_json(data, file_path):
    """写入 JSON 文件"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    unreal.log(f"已写入 JSON: {file_path}")

# ─────────────────────────────────────────────────────────
# 2. 读取 CSV 数据
# ─────────────────────────────────────────────────────────

def read_csv(file_path, has_header=True):
    """
    读取 CSV 文件

    返回:
        如果 has_header: list of dict
        否则: list of list
    """
    if not os.path.exists(file_path):
        unreal.log_error(f"文件不存在: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        if has_header:
            reader = csv.DictReader(f)
            data = list(reader)
        else:
            reader = csv.reader(f)
            data = list(reader)

    unreal.log(f"已读取 CSV: {file_path} ({len(data)} 行)")
    return data

def write_csv(data, file_path, fieldnames=None):
    """
    写入 CSV 文件

    参数:
        data: list of dict 或 list of list
        file_path: 文件路径
        fieldnames: 列名 (当 data 是 list of list 时需要)
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    if data and isinstance(data[0], dict):
        fieldnames = list(data[0].keys())

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    unreal.log(f"已写入 CSV: {file_path} ({len(data)} 行)")

# ─────────────────────────────────────────────────────────
# 3. 从 JSON 创建 DataTable
# ─────────────────────────────────────────────────────────

def create_datatable_from_json(json_path, table_name,
                                 destination="/Game/Data"):
    """
    从 JSON 文件创建 UE DataTable

    JSON 格式示例:
    [
        {"Name": "Sword", "Damage": 10, "Weight": 3.0},
        {"Name": "Shield", "Damage": 0, "Weight": 5.0}
    ]
    """
    data = read_json(json_path)
    if not data or not isinstance(data, list):
        unreal.log_error("JSON 必须是数组格式")
        return None

    unreal.log(f"从 JSON 创建 DataTable: {len(data)} 行")

    # 注意：UE 的 DataTable 需要一个 Row Structure (UScriptStruct)
    # 直接用 Python 创建 DataTable 比较复杂
    # 推荐使用 CSV 导入方式

    # 先将 JSON 转为 CSV，再导入
    csv_path = json_path.replace('.json', '.csv')
    write_csv(data, csv_path)

    # 使用 AssetTools 导入 CSV 为 DataTable
    return import_csv_as_datatable(csv_path, table_name, destination)

def import_csv_as_datatable(csv_path, table_name,
                              destination="/Game/Data"):
    """
    导入 CSV 文件为 DataTable

    CSV 第一行必须是列名
    第一列通常作为行名 (Row Name)
    """
    if not os.path.exists(csv_path):
        unreal.log_error(f"CSV 文件不存在: {csv_path}")
        return None

    unreal.EditorAssetLibrary.make_directory(destination)

    # 使用 import 方式创建 DataTable
    task = unreal.AssetImportTask()
    task.filename = csv_path
    task.destination_path = destination
    task.destination_name = table_name
    task.replace_existing = True
    task.automated = True
    task.save = True

    # 设置 DataTable 导入选项
    import_data = unreal.CSVImportSettings()
    import_data.set_editor_property("import_row_struct", None)  # 会自动创建

    task.options = import_data

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    if task.imported_object_paths:
        unreal.log(f"已创建 DataTable: {task.imported_object_paths[0]}")
    return task.imported_object_paths

# ─────────────────────────────────────────────────────────
# 4. 读取和修改 UE DataTable
# ─────────────────────────────────────────────────────────

def read_datatable(table_path):
    """
    读取 UE DataTable 的数据

    返回: dict of {row_name: row_data}
    """
    table = unreal.EditorAssetLibrary.load_asset(table_path)
    if not table or not isinstance(table, unreal.DataTable):
        unreal.log_error(f"无法加载 DataTable: {table_path}")
        return None

    # 获取所有行名
    row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(table)
    unreal.log(f"DataTable {table.get_name()} 有 {len(row_names)} 行")

    data = {}
    for row_name in row_names:
        # 获取行数据
        row = unreal.DataTableFunctionLibrary.get_data_table_row_from_name(
            table, row_name
        )
        data[row_name] = row

    return data

def add_row_to_datatable(table_path, row_name, row_data):
    """
    向 DataTable 添加一行数据

    参数:
        table_path: DataTable 路径
        row_name: 行名
        row_data: dict, 列名→值
    """
    table = unreal.EditorAssetLibrary.load_asset(table_path)
    if not table:
        return False

    # 注意：直接操作 DataTable 行需要匹配 Row Structure
    # 这里使用通用的方法
    unreal.log(f"添加行: {row_name} 到 {table_path}")

    # 实际操作中，可能需要：
    # 1. 获取 Row Structure
    # 2. 创建新的 Structure 实例
    # 3. 填充数据
    # 4. 添加到 DataTable

    unreal.EditorAssetLibrary.save_asset(table_path)
    return True

# ─────────────────────────────────────────────────────────
# 5. 导出项目数据
# ─────────────────────────────────────────────────────────

def export_asset_list_to_csv(search_path="/Game",
                               output_path=None):
    """
    导出资产列表到 CSV

    参数:
        search_path: 搜索路径
        output_path: 输出文件路径 (默认 Saved 目录)
    """
    if output_path is None:
        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "AssetList.csv"
        )

    all_assets = unreal.EditorAssetLibrary.list_assets(
        search_path, recursive=True
    )

    rows = []
    for asset_path in all_assets:
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )

        rows.append({
            "Path": asset_path,
            "Name": asset_data.asset_name,
            "Type": str(asset_data.asset_class_path).split(".")[-1],
            "ReferenceCount": len(refs),
        })

    write_csv(rows, output_path)
    unreal.log(f"已导出 {len(rows)} 个资产到: {output_path}")
    return output_path

def export_actor_data_to_json(output_path=None):
    """
    导出关卡中所有 Actor 数据到 JSON

    包含：位置、旋转、缩放、类型、标签
    """
    if output_path is None:
        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "ActorData.json"
        )

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    data = []
    for actor in actors:
        loc = actor.get_actor_location()
        rot = actor.get_actor_rotation()
        scale = actor.get_actor_scale3D()

        actor_data = {
            "label": actor.get_actor_label(),
            "class": type(actor).__name__,
            "location": {"x": loc.x, "y": loc.y, "z": loc.z},
            "rotation": {"pitch": rot.pitch, "yaw": rot.yaw, "roll": rot.roll},
            "scale": {"x": scale.x, "y": scale.y, "z": scale.z},
            "folder": actor.get_folder_path() if hasattr(actor, 'get_folder_path') else "",
        }

        # 尝试获取网格体信息
        mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp:
            mesh = mesh_comp.get_editor_property("static_mesh")
            if mesh:
                actor_data["mesh"] = mesh.get_path_name()

        data.append(actor_data)

    write_json(data, output_path)
    unreal.log(f"已导出 {len(data)} 个 Actor 到: {output_path}")
    return output_path

# ─────────────────────────────────────────────────────────
# 6. 从外部数据生成关卡内容
# ─────────────────────────────────────────────────────────

def spawn_actors_from_json(json_path):
    """
    从 JSON 文件生成 Actor

    JSON 格式:
    [
        {
            "class": "StaticMeshActor",
            "label": "Box1",
            "location": {"x": 0, "y": 0, "z": 100},
            "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
            "scale": {"x": 1, "y": 1, "z": 1},
            "mesh": "/Game/Meshes/SM_Cube"
        }
    ]
    """
    data = read_json(json_path)
    if not data:
        return []

    spawned = []
    class_map = {
        "StaticMeshActor": unreal.StaticMeshActor,
        "PointLight": unreal.PointLight,
        "SpotLight": unreal.SpotLight,
        "CineCameraActor": unreal.CineCameraActor,
    }

    unreal.Transactions.begin_transaction("从JSON生成Actor")

    for item in data:
        class_name = item.get("class", "StaticMeshActor")
        actor_class = class_map.get(class_name, unreal.StaticMeshActor)

        loc = item.get("location", {})
        rot = item.get("rotation", {})

        location = unreal.Vector(
            loc.get("x", 0), loc.get("y", 0), loc.get("z", 0)
        )
        rotation = unreal.Rotator(
            rot.get("pitch", 0), rot.get("yaw", 0), rot.get("roll", 0)
        )

        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, location, rotation
        )

        if actor:
            actor.set_actor_label(item.get("label", "FromJSON"))

            # 设置缩放
            scale = item.get("scale", {})
            if scale:
                actor.set_actor_scale3D(unreal.Vector(
                    scale.get("x", 1),
                    scale.get("y", 1),
                    scale.get("z", 1)
                ))

            # 设置网格体
            mesh_path = item.get("mesh")
            if mesh_path:
                mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
                if mesh:
                    comp = actor.get_component_by_class(
                        unreal.StaticMeshComponent
                    )
                    if comp:
                        comp.set_static_mesh(mesh)

            spawned.append(actor)

    unreal.Transactions.end_transaction()
    unreal.log(f"从 JSON 生成了 {len(spawned)} 个 Actor")
    return spawned

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 导出资产列表
# export_asset_list_to_csv()

# 导出 Actor 数据
# export_actor_data_to_json()

# 从 JSON 生成 Actor
# spawn_actors_from_json("C:/data/actors.json")

unreal.log("高级主题第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写工具：从 Excel 导出的 CSV 创建 UE DataTable
# 2. 实现关卡布局的 JSON 导出/导入（保存/恢复场景）
# 3. 创建一个数据验证工具：检查外部数据是否符合规范
# 4. 编写热更新工具：监控 JSON 文件变化并自动更新 UE 数据
