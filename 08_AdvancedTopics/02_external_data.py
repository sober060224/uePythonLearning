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

习题可能用到的 API：
  unreal.AssetImportTask()  -- 创建资产导入任务对象
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  -- 获取 AssetTools 实例以执行导入
  asset_tools.import_asset_tasks(import_tasks: Array[AssetImportTask]) -> None  -- 批量执行导入任务
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  -- 按路径加载资产到内存
  unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() -> Array[Actor]  -- 获取当前关卡全部 Actor
  unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(actor_class: Class, location: Vector, rotation: Rotator) -> Actor  -- 从类生成新 Actor
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  -- 创建目录
  unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int  -- 开启可撤销事务并返回索引
=============================================================
"""

import contextlib
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
import json
import csv
import os

# --------------------------------------------------
# 1. 读取 JSON 数据
# --------------------------------------------------

def read_json(file_path):
    """
    读取 JSON 文件

    JSON 是最常用的配置文件格式，UE 的很多数据交换也使用 JSON。
    在 Python 中，json.load() 会自动将 JSON 字符串解析为 Python 的字典或列表。
    """
    # 检查文件是否存在，避免后续操作报错
    # 为什么先检查？因为 open() 在文件不存在时会抛出 FileNotFoundError
    if not os.path.exists(file_path):
        unreal.log_error(f"文件不存在: {file_path}")
        return None

    # 使用 utf-8 编码读取，确保中文字符正确处理
    # json.load() 会自动解析 JSON 字符串为 Python 对象（字典或列表）
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # type(data).__name__ 返回对象类型的名称，如 'dict' 或 'list'
    # 这比直接打印 type(data) 更易读
    unreal.log(f"已读取 JSON: {file_path} ({type(data).__name__})")
    return data

def write_json(data, file_path):
    """写入 JSON 文件"""
    # os.makedirs 会自动创建多级目录（如果不存在）
    # exist_ok=True 表示目录已存在时不报错，比先检查再创建更简洁
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # ensure_ascii=False 确保中文字符直接写入，而不是转义为 \uXXXX
    # indent=2 使输出格式化，便于阅读和调试
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    unreal.log(f"已写入 JSON: {file_path}")

# --------------------------------------------------
# 2. 读取 CSV 数据
# --------------------------------------------------

def read_csv(file_path, has_header=True):
    """
    读取 CSV 文件

    CSV 是策划最常用的数据格式（Excel 导出）。UE 的 DataTable 也支持 CSV 导入。

    返回:
        如果 has_header: list of dict（每行是一个字典，列名作为键）
        否则: list of list（每行是一个列表）
    """
    if not os.path.exists(file_path):
        unreal.log_error(f"文件不存在: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        if has_header:
            # DictReader 会自动将第一行作为列名
            # 每行数据会变成一个字典：{"列名1": "值1", "列名2": "值2", ...}
            # 这种格式方便按列名访问数据
            reader = csv.DictReader(f)
            data = list(reader)
        else:
            # 普通 reader 返回列表，每行是一个列表
            # 适合没有表头的纯数据文件
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
        fieldnames: 列名（当 data 是 list of list 时需要手动指定）
    """
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if not data:
        unreal.log_warning(f"没有数据可写: {file_path}")
        return

    # 两种数据形态要分开处理（原来只处理了 dict 列表，
    # 传 list of list 时会用 DictWriter 去写列表，直接抛异常）：
    #   - list of dict  -> csv.DictWriter，列名从第一个字典的键提取
    #   - list of list  -> csv.writer，列名由调用方通过 fieldnames 给出
    if isinstance(data[0], dict):
        fieldnames = list(data[0].keys())
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            # newline='' 是 CSV 写入的标准做法，避免 Windows 上出现多余的空行
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()  # 写入列名行
            writer.writerows(data)  # 写入所有数据行
    else:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if fieldnames:
                writer.writerow(fieldnames)
            writer.writerows(data)

    unreal.log(f"已写入 CSV: {file_path} ({len(data)} 行)")

# --------------------------------------------------
# 3. 从 JSON 创建 DataTable
# --------------------------------------------------

def create_datatable_from_json(json_path, table_name,
                                 destination="/Game/Data"):
    """
    从 JSON 文件创建 UE DataTable

    UE DataTable 是结构化数据表，常用于游戏数据（物品表、怪物表等）。
    由于 UE Python 对 DataTable 的直接创建支持有限，我们采用 JSON -> CSV -> DataTable 的流程。

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
    # 直接用 Python 创建 DataTable 比较复杂，推荐使用 CSV 导入方式
    # UE 的 CSV 导入会自动根据列名推断 Row Structure

    # 先将 JSON 转为 CSV，再导入
    csv_path = json_path.replace('.json', '.csv')
    write_csv(data, csv_path)

    # 使用 AssetTools 导入 CSV 为 DataTable
    return import_csv_as_datatable(csv_path, table_name, destination)

def import_csv_as_datatable(csv_path, table_name,
                              destination="/Game/Data"):
    """
    导入 CSV 文件为 DataTable

    CSV 第一行必须是列名，第一列通常作为行名 (Row Name)。
    这是 UE 标准的 DataTable CSV 格式。
    """
    if not os.path.exists(csv_path):
        unreal.log_error(f"CSV 文件不存在: {csv_path}")
        return None

    # 确保目标目录存在
    unreal.EditorAssetLibrary.make_directory(destination)

    # AssetImportTask 是 UE 的资产导入任务对象
    # 它封装了导入所需的所有参数：源文件、目标路径、导入选项等
    task = unreal.AssetImportTask()
    task.filename = csv_path  # 源文件路径
    task.destination_path = destination  # 目标包路径（如 /Game/Data）
    task.destination_name = table_name  # 导入后的资产名
    task.replace_existing = True  # 如果已存在则覆盖
    task.automated = True  # 自动化模式，不显示进度对话框（适合脚本批量操作）
    task.save = True  # 导入后自动保存到磁盘

    # 设置 DataTable 导入选项
    import_data = unreal.CSVImportSettings()
    # import_row_struct 设为 None 表示自动创建行结构
    # UE 会根据 CSV 的列名和数据类型自动生成 UScriptStruct
    import_data.set_editor_property("import_row_struct", None)

    task.options = import_data

    # 获取 AssetTools 实例，执行导入任务
    # 为什么用 AssetToolsHelpers.get_asset_tools() 而不是直接创建？
    # 因为 AssetTools 是引擎内部的单例，必须通过辅助函数获取
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    # imported_object_paths 包含导入后生成的资产路径列表
    if task.imported_object_paths:
        unreal.log(f"已创建 DataTable: {task.imported_object_paths[0]}")
    return task.imported_object_paths

# --------------------------------------------------
# 4. 读取和修改 UE DataTable
# --------------------------------------------------

def read_datatable(table_path):
    """
    读取 UE DataTable 的数据

    返回: dict of {row_name: {column_name: value_string}}

    注意：UE Python stub 中 DataTable 的读取接口有限：
    - get_data_table_row_names(table) -> 所有行名
    - get_data_table_column_names(table) -> 所有列名
    - get_data_table_column_as_string(table, 列名) -> 某一列的全部值（字符串）
    没有"按行名取整行数据"的函数，只能按列取再按行拼。
    """
    # load_asset 将资产从磁盘加载到内存
    # 为什么不用 find_asset_data？因为 find_asset_data 只返回元数据，不返回资产内容
    table = unreal.EditorAssetLibrary.load_asset(table_path)
    if not table or not isinstance(table, unreal.DataTable):
        unreal.log_error(f"无法加载 DataTable: {table_path}")
        return None

    # 获取所有行名
    row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(table)
    unreal.log(f"DataTable {table.get_name()} 有 {len(row_names)} 行")

    # 获取所有列名
    column_names = unreal.DataTableFunctionLibrary.get_data_table_column_names(table)

    # 按列读取数据，再转置为按行组织的字典
    # 为什么这样做？因为 UE Python 没有直接按行读取的 API
    # 每列的值顺序和 row_names 是一一对应的，可以 zip 对齐
    data = {row_name: {} for row_name in row_names}
    for column in column_names:
        values = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(
            table, column
        )
        # zip 将列值和行名一一配对，注意：值全部被转成了字符串
        for row_name, value in zip(row_names, values):
            data[row_name][str(column)] = value

    return data

def add_row_to_datatable(table_path, row_name, row_data):
    """
    向 DataTable 添加一行数据

    参数:
        table_path: DataTable 路径
        row_name: 行名
        row_data: dict, 列名到值的映射

    注意：直接操作 DataTable 行需要匹配 Row Structure (UScriptStruct)。
    这里使用通用的方法，实际项目中可能需要根据具体的 Row Structure 进行调整。
    """
    table = unreal.EditorAssetLibrary.load_asset(table_path)
    if not table:
        return False

    # 【重要】UE 的 Python API 里没有 DataTable.add_row（在 PythonStub/unreal.py 中
    #   搜索 add_row 查不到），所以这个函数没法真正写入数据。
    #   与其 save_asset 一下就 return True 让调用方以为写成功了，不如如实返回 False。
    #
    # 想给 DataTable 加数据，可行路线是把数据写成 CSV，再整体导入：
    #   unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(table, csv_path)
    # （需要 CSV 的列名和 DataTable 的 Row Structure 完全对应）
    row_struct = table.get_row_struct()
    unreal.log_error(
        f"无法直接新增行: UE Python 没有 DataTable.add_row。"
        f"该表的行结构是 {row_struct.get_name() if row_struct else '未知'}；"
        f"请改用 CSV + fill_data_table_from_csv_file 导入。"
    )
    return False

# --------------------------------------------------
# 5. 导出项目数据
# --------------------------------------------------

def export_asset_list_to_csv(search_path="/Game",
                               output_path=None):
    """
    导出资产列表到 CSV

    这个工具可以帮助项目管理者快速了解项目资产状况。
    参数:
        search_path: 搜索路径
        output_path: 输出文件路径 (默认 Saved 目录)
    """
    if output_path is None:
        # project_saved_dir() 返回项目的 Saved 目录路径
        # 为什么保存到这里？因为 Saved 目录不会被版本控制
        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "AssetList.csv"
        )

    # list_assets 递归列出所有资产
    all_assets = unreal.EditorAssetLibrary.list_assets(
        search_path, recursive=True
    )

    rows = []
    for asset_path in all_assets:
        # 跳过文件夹，只处理资产
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        # find_asset_data 获取资产的元数据，不加载资产本身（高效）
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # 查找引用计数，帮助识别哪些资产被使用
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path
        )

        rows.append({
            "Path": asset_path,
            "Name": str(asset_data.asset_name),  # Name -> str，CSV 才写得出来
            "Type": str(asset_data.asset_class_path).split(".")[-1],
            "ReferenceCount": len(refs),
        })

    write_csv(rows, output_path)
    unreal.log(f"已导出 {len(rows)} 个资产到: {output_path}")
    return output_path

def export_actor_data_to_json(output_path=None):
    """
    导出关卡中所有 Actor 数据到 JSON

    包含：位置、旋转、缩放、类型、标签、网格体路径。
    适用于关卡布局的保存和恢复。
    """
    if output_path is None:
        output_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "ActorData.json"
        )

    # get_all_level_actors 获取当前关卡中的所有 Actor
    # 注意：这只获取当前打开的关卡，不是整个项目
    # 【UE5】EditorLevelLibrary 已废弃，统一用 EditorActorSubsystem
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

    data = []
    for actor in actors:
        # get_actor_location 返回 FVector（三维向量），包含 x, y, z 分量
        loc = actor.get_actor_location()
        # get_actor_rotation 返回 FRotator，包含 pitch（俯仰）、yaw（偏航）、roll（横滚）
        rot = actor.get_actor_rotation()
        # get_actor_scale3d 返回缩放向量
        scale = actor.get_actor_scale3d()

        actor_data = {
            # get_actor_label 返回 Actor 在编辑器中的显示名称
            "label": actor.get_actor_label(),
            # type(actor).__name__ 获取 Actor 的类名（如 "StaticMeshActor"）
            "class": type(actor).__name__,
            "location": {"x": loc.x, "y": loc.y, "z": loc.z},
            "rotation": {"pitch": rot.pitch, "yaw": rot.yaw, "roll": rot.roll},
            "scale": {"x": scale.x, "y": scale.y, "z": scale.z},
            # get_folder_path 获取 Actor 在大纲视图中的文件夹路径
            "folder": str(actor.get_folder_path()),  # get_folder_path() 返回 Name，json 需要 str
        }

        # 尝试获取网格体信息（只有 StaticMeshActor 才有）
        # get_component_by_class 按类型获取组件，返回第一个匹配的组件
        mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp:
            # get_editor_property 读取组件的编辑器属性
            mesh = mesh_comp.get_editor_property("static_mesh")
            if mesh:
                # get_path_name 返回资产的完整路径（如 /Game/Meshes/SM_Cube）
                actor_data["mesh"] = mesh.get_path_name()

        data.append(actor_data)

    write_json(data, output_path)
    unreal.log(f"已导出 {len(data)} 个 Actor 到: {output_path}")
    return output_path

# --------------------------------------------------
# 6. 从外部数据生成关卡内容
# --------------------------------------------------

def spawn_actors_from_json(json_path):
    """
    从 JSON 文件生成 Actor

    这是从外部数据驱动关卡设计的核心功能。
    例如：策划在 Excel 中设计关卡布局，导出 JSON 后由本脚本自动生成 Actor。

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

    # class_map 将字符串类名映射到实际的 UE 类
    # 为什么需要映射？因为 JSON 中只能存字符串，不能直接存 UE 类对象
    class_map = {
        "StaticMeshActor": unreal.StaticMeshActor,
        "PointLight": unreal.PointLight,
        "SpotLight": unreal.SpotLight,
        "CineCameraActor": unreal.CineCameraActor,
    }

    # 事务系统：让整个操作可以撤销（Ctrl+Z）
    # 为什么需要事务？批量操作后如果结果不满意，可以一次性撤销
    # 注意：unreal.Transactions 不存在，事务方法在 SystemLibrary 上
    # primary_object 用编辑器 World，因为生成 Actor 的操作作用于关卡
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    with editor_transaction("从JSON生成Actor", world):
        for item in data:
            # 从 JSON 中读取类名，映射为实际的 UE 类
            class_name = item.get("class", "StaticMeshActor")
            actor_class = class_map.get(class_name, unreal.StaticMeshActor)

            # 从字典中提取位置和旋转数据，构造 UE 的 Vector 和 Rotator
            loc = item.get("location", {})
            rot = item.get("rotation", {})

            location = unreal.Vector(
                loc.get("x", 0), loc.get("y", 0), loc.get("z", 0)
            )
            # 【易错点】Rotator 位置参数顺序是 (roll, pitch, yaw)，用关键字参数避免串位。
            rotation = unreal.Rotator(
                pitch=rot.get("pitch", 0), yaw=rot.get("yaw", 0), roll=rot.get("roll", 0)
            )

            # spawn_actor_from_class 在关卡中生成一个新的 Actor
            # 这是关卡编辑脚本中最常用的函数之一
            actor = unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).spawn_actor_from_class(
                actor_class, location, rotation
            )

            if actor:
                # set_actor_label 设置 Actor 在编辑器大纲视图中显示的名称
                actor.set_actor_label(item.get("label", "FromJSON"))

                # 设置缩放
                scale = item.get("scale", {})
                if scale:
                    actor.set_actor_scale3d(unreal.Vector(
                        scale.get("x", 1),
                        scale.get("y", 1),
                        scale.get("z", 1)
                    ))

                # 设置网格体（仅对 StaticMeshActor 有效）
                mesh_path = item.get("mesh")
                if mesh_path:
                    # load_asset 从路径加载资产到内存
                    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
                    if mesh:
                        # 获取 Actor 的 StaticMeshComponent 组件
                        comp = actor.get_component_by_class(
                            unreal.StaticMeshComponent
                        )
                        if comp:
                            # set_static_mesh 将网格体赋值给组件
                            comp.set_static_mesh(mesh)

                spawned.append(actor)

        # 结束事务，提交所有操作
        # 如果之后执行 SystemLibrary.cancel_transaction(token) 可以撤销
    unreal.log(f"从 JSON 生成了 {len(spawned)} 个 Actor")
    return spawned

# --------------------------------------------------
# 使用示例
# --------------------------------------------------

# 导出资产列表
# export_asset_list_to_csv()

# 导出 Actor 数据
# export_actor_data_to_json()

# 从 JSON 生成 Actor
# spawn_actors_from_json("C:/data/actors.json")

unreal.log("高级主题第2课完成！")

# --------------------------------------------------
# 练习题
# --------------------------------------------------
# 1. 编写工具：从 Excel 导出的 CSV 创建 UE DataTable
# 2. 实现关卡布局的 JSON 导出/导入（保存/恢复场景）
# 3. 创建一个数据验证工具：检查外部数据是否符合规范
# 4. 编写热更新工具：监控 JSON 文件变化并自动更新 UE 数据
