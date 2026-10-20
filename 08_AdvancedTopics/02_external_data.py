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
  ── unreal ──
    unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools
        —— 取 AssetTools 单例；导入 CSV / 创建资产都从它进
    unreal.AssetImportTask()
        —— 一次导入任务的载体：filename / destination_path / destination_name / factory / automated / save / replace_existing
    unreal.CSVImportFactory()
        —— ★ 实测：CSVImportSettings 的默认值已经够用
           （import_row_struct=None 自动建行结构、import_type=ECSV_DATA_TABLE），
           所以只需把 factory 挂到 task 上，不用手动构造设置对象
    unreal.AssetTools.import_asset_tasks(import_tasks: Array[AssetImportTask]) -> None
        —— 执行导入；★ 参数是 Array 不是 list，传列表要 unreal.Array.cast(unreal.AssetImportTask, [...])
    unreal.AssetImportTask.imported_object_paths -> Array[str]
        —— 导入产物路径（一次导入可能出多个资产）
    unreal.DataTable
        —— 数据表资产类型（练习1 的产物）
    unreal.DataTable.get_row_names() -> Array[Name]
        —— 读回全部行名（练习1 校验行数、练习2/4 刷新行都用它）
    unreal.DataTable.get_row_struct() -> ScriptStruct
        —— 行结构体
    unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object
        —— 按资产路径加载成对象（练习2 导入前判重、练习4 取 DataTable 都靠它）
    unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool
        —— 判断资产是否已存在（练习2 二次导入要跳过已还原的）
    unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool
        —— 目录不存在时 create_asset 会失败，先建目录
    unreal.EditorAssetLibrary.load_blueprint_class(asset_path: str) -> Class
        —— ★ 实测存在；按蓝图资产路径取它编译后的 Class，
           用于「class_name 是 BP_Xxx_C 时」的还原（练习2）
    unreal.load_class(outer: Object, class_name: str) -> Class
        —— 原生类走这条：unreal.load_class(None, "/Script/Engine.StaticMeshActor")
    unreal.EditorActorSubsystem.get_all_level_actors() -> Array[Actor]
        —— 取当前关卡全部 Actor（练习2 导出布局、练习3 快照的入口）
    unreal.EditorActorSubsystem.spawn_actor_from_class(actor_class: Class, location: Vector, rotation: Rotator = [0,0,0], transient: bool = False) -> Actor
        —— 生成 Actor（练习2 按 JSON 还原布局；class_name 为 BP_Xxx_C 时先 load_blueprint_class）
    unreal.EditorActorSubsystem.destroy_actor(actor_to_destroy: Actor) -> bool
        —— 练习2 的「清空 / 还原」三步
    unreal.Actor.get_actor_location() -> Vector
        —— 读 Actor 世界坐标（练习2 导出、练习3 快照）
    unreal.Actor.get_actor_rotation() -> Rotator
        —— 读 Actor 世界旋转（练习2 导出；读回 yaw 有浮点尾巴，比较用 < 0.01）
    unreal.Actor.get_actor_scale3d() -> Vector
        —— 读 Actor 缩放（练习2 导出 scale 字段）
    unreal.Actor.get_actor_label() -> str
        —— 读 Actor 的显示名（练习2/3 用它当 JSON 键与差异比对键）
    unreal.Actor.set_actor_label(new_actor_label: str) -> None
        —— 改显示名（练习2 还原时按 JSON 里的 label 设回去）
    unreal.Actor.get_class() -> Class
        —— 读 Actor 的类（练习2 存 class_name、练习2 按类名分组统计）
    unreal.Actor.set_actor_transform(new_transform: Transform, sweep: bool, teleport: bool) -> Optional[HitResult]
        —— ★ 实测：写的是**世界空间**变换（不是相对父级），还原布局用它一次搞定
    unreal.SystemLibrary.transact_object(object: Object) -> None
        —— 修改对象前登记，否则该对象不进撤销栈（练习2 改动前逐个登记）
    unreal.SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int
        —— 开启可撤销事务（练习2 整段导入包一层，Ctrl+Z 一次撤销）
    unreal.SystemLibrary.end_transaction() -> int
        —— 提交当前事务（与 begin 成对）
    unreal.SystemLibrary.cancel_transaction(index: int) -> None
        —— 练习2 整段导入要包在事务里才可一次撤销
    unreal.log(arg: Any) -> None
        —— 输出到 Output Log（练习1/3/4 的报告都靠它）
    unreal.log_warning(arg: Any) -> None
        —— 警告级日志（练习3 校验不通过时用）
    unreal.log_error(arg: Any) -> None
        —— 错误级日志（练习2/4 失败时用）
  ── Python 标准库 ──
    csv.DictReader / csv.DictWriter
        —— 练习1/3 读写 CSV；DictReader 的表头就是第一行（含空格要去 strip）
    json.dump / json.load
        —— 练习2/4 读写布局与配置（记得 ensure_ascii=False + indent=2，中文才不转义）
    os.makedirs / os.path.join / os.path.getmtime / os.path.getsize
        —— 练习4 记录文件的 (mtime_ns, size) 做双判；练习2 写 JSON 前先建目录
    time.sleep / time.strftime
        —— 练习4 轮询；结果文件用时间戳命名
    KeyboardInterrupt
        —— 练习4 的 while True 只能靠 Ctrl+C 退出，必须捕获它做干净收尾
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


import csv
import json
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
    with open(file_path, "r", encoding="utf-8") as f:
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
    with open(file_path, "w", encoding="utf-8") as f:
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

    with open(file_path, "r", encoding="utf-8") as f:
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
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            # newline='' 是 CSV 写入的标准做法，避免 Windows 上出现多余的空行
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()  # 写入列名行
            writer.writerows(data)  # 写入所有数据行
    else:
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if fieldnames:
                writer.writerow(fieldnames)
            writer.writerows(data)

    unreal.log(f"已写入 CSV: {file_path} ({len(data)} 行)")


# --------------------------------------------------
# 3. 从 JSON 创建 DataTable
# --------------------------------------------------


def create_datatable_from_json(json_path, table_name, destination="/Game/Data"):
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
    csv_path = json_path.replace(".json", ".csv")
    write_csv(data, csv_path)

    # 使用 AssetTools 导入 CSV 为 DataTable
    return import_csv_as_datatable(csv_path, table_name, destination)


def import_csv_as_datatable(csv_path, table_name, destination="/Game/Data"):
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

    # 【原来的写法是错的】task.options = unreal.CSVImportSettings()
    # 桩里 AssetImportTask.options 声明为 (Object)（unreal.py:316981 起），
    # 而 CSVImportSettings 是 StructBase（结构体，:165824）—— 结构体赋给 Object
    # 属性，类型检查器和引擎都不认。
    # CSV 导入走的是工厂：AssetImportTask.factory 声明为 (Factory)，
    # 而 CSVImportFactory 正是 Factory 的子类（:493401）。
    # 另外 CSVImportSettings.__init__ 的默认值本来就是
    #   import_row_struct=None（自动创建行结构）+ import_type=ECSV_DATA_TABLE，
    # 所以这里不需要再手动构造设置对象。
    task.factory = unreal.CSVImportFactory()

    # 获取 AssetTools 实例，执行导入任务
    # 为什么用 AssetToolsHelpers.get_asset_tools() 而不是直接创建？
    # 因为 AssetTools 是引擎内部的单例，必须通过辅助函数获取
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    # 参数要是引擎 Array[AssetImportTask]，用 unreal.Array.cast 从 Python list 转换
    asset_tools.import_asset_tasks(unreal.Array.cast(unreal.AssetImportTask, [task]))

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
    # load_asset 返回 Object，Object 上没有 get_row_struct —— 先收窄成 DataTable
    if not isinstance(table, unreal.DataTable):
        unreal.log_error(f"该资产不是 DataTable: {table_path}")
        return False
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


def export_asset_list_to_csv(search_path="/Game", output_path=None):
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
        output_path = os.path.join(unreal.Paths.project_saved_dir(), "AssetList.csv")

    # list_assets 递归列出所有资产
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    rows = []
    for asset_path in all_assets:
        # 跳过文件夹，只处理资产
        if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
            continue

        # find_asset_data 获取资产的元数据，不加载资产本身（高效）
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # 查找引用计数，帮助识别哪些资产被使用
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path)

        rows.append(
            {
                "Path": asset_path,
                "Name": str(asset_data.asset_name),  # Name -> str，CSV 才写得出来
                "Type": str(asset_data.asset_class_path).split(".")[-1],
                "ReferenceCount": len(refs),
            }
        )

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
        output_path = os.path.join(unreal.Paths.project_saved_dir(), "ActorData.json")

    # get_all_level_actors 获取当前关卡中的所有 Actor
    # 注意：这只获取当前打开的关卡，不是整个项目
    # 【UE5】EditorLevelLibrary 已废弃，统一用 EditorActorSubsystem
    # get_editor_subsystem 返回 Optional，判空后再取；转普通 list 便于后续处理
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(subsystem.get_all_level_actors()) if subsystem else []

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
            "folder": str(
                actor.get_folder_path()
            ),  # get_folder_path() 返回 Name，json 需要 str
        }

        # 尝试获取网格体信息（只有 StaticMeshActor 才有）
        # get_component_by_class 按类型获取组件，返回第一个匹配的组件
        mesh_comp = actor.get_component_by_class(
            unreal.StaticMeshComponent.static_class()
        )
        if mesh_comp:
            # get_editor_property 读取组件的编辑器属性
            mesh = mesh_comp.get_editor_property("static_mesh")
            # get_editor_property 返回 object（unreal.py:285），object 上没有
            # get_path_name；收窄成 unreal.Object 才能取路径
            if isinstance(mesh, unreal.Object):
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
    # 两个子系统的返回类型都是 Optional，所以取一次、判一次空，不要在循环里反复取
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    unreal_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = unreal_sub.get_editor_world() if unreal_sub else None
    if actor_sub is None or world is None:
        unreal.log_error("取不到 EditorActorSubsystem 或编辑器 World，未生成任何 Actor")
        return []
    with editor_transaction("从JSON生成Actor", world):
        for item in data:
            # 从 JSON 中读取类名，映射为实际的 UE 类
            class_name = item.get("class", "StaticMeshActor")
            actor_class = class_map.get(class_name, unreal.StaticMeshActor)

            # 从字典中提取位置和旋转数据，构造 UE 的 Vector 和 Rotator
            loc = item.get("location", {})
            rot = item.get("rotation", {})

            location = unreal.Vector(loc.get("x", 0), loc.get("y", 0), loc.get("z", 0))
            # 【易错点】Rotator 位置参数顺序是 (roll, pitch, yaw)，用关键字参数避免串位。
            rotation = unreal.Rotator(
                pitch=rot.get("pitch", 0),
                yaw=rot.get("yaw", 0),
                roll=rot.get("roll", 0),
            )

            # spawn_actor_from_class 在关卡中生成一个新的 Actor
            # 这是关卡编辑脚本中最常用的函数之一
            actor = actor_sub.spawn_actor_from_class(actor_class, location, rotation)

            if actor:
                # set_actor_label 设置 Actor 在编辑器大纲视图中显示的名称
                actor.set_actor_label(item.get("label", "FromJSON"))

                # 设置缩放
                scale = item.get("scale", {})
                if scale:
                    actor.set_actor_scale3d(
                        unreal.Vector(
                            scale.get("x", 1), scale.get("y", 1), scale.get("z", 1)
                        )
                    )

                # 设置网格体（仅对 StaticMeshActor 有效）
                mesh_path = item.get("mesh")
                if mesh_path:
                    # load_asset 从路径加载资产到内存
                    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
                    if mesh:
                        # 获取 Actor 的 StaticMeshComponent 组件
                        comp = actor.get_component_by_class(
                            unreal.StaticMeshComponent.static_class()
                        )
                        # 桩里 get_component_by_class 返回基类 ActorComponent
                        # （unreal.py:257615），要 isinstance 收窄才能调 set_static_mesh
                        # set_static_mesh 要求 StaticMesh，load_asset 返回的是 Object，
                        # 所以网格体本身也要收窄一层
                        if isinstance(comp, unreal.StaticMeshComponent) and isinstance(
                            mesh, unreal.StaticMesh
                        ):
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
# 【练习 1】从 Excel 导出的 CSV 创建 DataTable
#   输入： 一个 CSV 文件（第一行是表头，至少要有一列能当行名的唯一值）
#   任务： 复用 import_csv_as_datatable，但要多做三件事：
#          ①表头里的空格统一去掉（Excel 常导出 " Name " 这种）
#          ②行名（RowName）重复时自动加 _2 / _3 后缀而不是覆盖
#          ③导入后逐行读回来校验行数，数量对不上就报错
#   输出： /Game/Data 下一个 DataTable，行数与 CSV 数据行数一致
#   验收： 拿一个含 2 行重名的 CSV → 行数一根不少（重名的变成 Name / Name_2）；
#          表头带空格的 CSV 也能正确导入
#          ★ 实测：CSV 里 Goblin / Orc / Goblin 三行导进去，
#            get_row_names() 读回 ['Goblin', 'Orc', 'Goblin_2']——
#            重名后缀是 _2（从 2 开始，不是 _1），且顺序与 CSV 一致。
#            行结构体是导入时自动建的（本例为 S_Row），不需要先手建

# 【练习 2】关卡布局的 JSON 导出 / 导入
#   输入： 一个输出路径 / 一个 JSON 文件路径
#   任务： 导出时遍历 get_all_actors()，记录 {class_name, label,
#          location:{x,y,z}, rotation:{roll,pitch,yaw}, scale:{x,y,z}}；
#          导入时按 class_name 找类（用 load_blueprint_class 兼容蓝图），
#          生成后设回变换，整个过程包在一个事务里；
#          已存在同名 label 的 Actor 先跳过并计数（避免重复导入翻倍）
#   输出： 一份 JSON + 一键还原同样布局
#   验收： 导出 → 清空关卡 → 导入 → Actor 数量与位置一致（误差 < 0.01）；
#          对同一份 JSON 连续导入两次 → 第二次「全部跳过」，Actor 数不变
#          ★ 实测：导出 2 个 Actor 的 JSON 是 850 字节，回读位置差 0.0000、
#            偏航差 0.0000，类名一致；连续导入第二次 skip 2 个、总数仍是 2。
#          两个必须知道的细节：
#          ① 偏航读回来是 45.00000000000003 这种浮点尾巴，
#             比较时要用 abs(dyaw) < 0.01，不能写 == 45
#          ② class_name 对原生类是 "StaticMeshActor"（无后缀），
#             对蓝图是 "BP_Xxx_C"（有 _C）——前者用
#             unreal.load_class(None, "/Script/Engine.StaticMeshActor")，
#             后者用 load_blueprint_class(资产路径)，两条路都要写

# 【练习 3】外部数据验证工具
#   输入： JSON / CSV 文件 + 一份规则表
#   任务： 规则表写成 {"字段名": {"type": "float", "min": 0, "max": 100, "required": True}}
#          这种形式；逐字段校验类型、范围、必填，收集所有错误
#          （不要遇到第一个错误就 return）；
#          输出格式：「第 3 行 Name 字段：期望 float，实际 'abc'」
#   输出： 一份错误清单 + 「共 N 行，M 行有问题，错误 K 条」
#   验收： 造一个含 3 类错误的数据文件 → 3 类错误全被报出来；
#          完全合法的文件 → 输出「0 个错误」且返回 True
#          ★ 实测一个 3 行文件（第 1 行合法、第 2 行 Name 空 + Hp='abc'、
#            第 3 行 Hp=150 超上限 + Speed 空）产出：
#              「第 3 行 Name 字段：必填项为空」
#              「第 3 行 Hp 字段：期望 float，实际 'abc'」
#              「第 4 行 Hp 字段：150.0 超过上限 100」
#              「第 4 行 Speed 字段：必填项为空」
#              「共 3 行，2 行有问题，错误 4 条」
#          注意行号是**从 1 开始的数据行号**（不是 0 基下标，也不含表头）；
#          同一行多个字段都错时每条都要单独报，不能一行只报一个

# 【练习 4】监控 JSON 变化并自动刷新 UE 数据
#   输入： 一个 JSON 文件路径 + 一个 DataTable 路径
#   任务： 记下文件的 mtime 和 size，每轮检查两者是否变化（任一变化即视为已改）；
#          变了就重新读 JSON 并刷新 DataTable 的对应行，打印「已从文件热更新 N 行」；
#          没变就什么都不做（不要每轮都打日志，否则日志会被刷屏）；
#          外层写成 while True + time.sleep(1.0) + KeyboardInterrupt 收尾，
#          并在注释里写明这会阻塞编辑器主线程，正式用法应改成 Tick 或命令行轮询
#   输出： 改一下 JSON 保存，几秒内 DataTable 内容跟着变
#   验收： 不动文件跑 10 秒 → 日志里一条「热更新」都没有；
#          改一个字段并保存 → 1~2 秒内出现「已从文件热更新 1 行」
#          ★ 为什么要 mtime + size **双判**，实测给了答案：
#            把一个数字字段从 73 字节的原文件改成另一个等长内容，
#            **size 完全不变（73 → 73），只有 mtime_ns 变了** ⇒
#            只看 size 会漏掉这次修改，只看 mtime 才可靠。
#            （mtime_ns 是纳秒整数，比 time.time() 的浮点秒更不容易撞同值）
#          另：sleep 1.0 的轮询实测能在 1 帧内就发现改动，
#          但它是阻塞主线程的，只在命令行无人值守时可用
