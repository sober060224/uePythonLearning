"""
=============================================================
资产管理 第2课：导入和导出资产
=============================================================

学习目标：
  - 使用 AssetTools 导入各种类型的资产
  - 批量导入和自动配置导入选项
  - 导出资产为外部文件

核心类：
  - unreal.AssetTools - 资产创建、导入、导出
  - unreal.AssetImportTask - 导入任务配置

本课可能用到的 API：
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取 AssetTools 实例以执行导入导出
  unreal.AssetImportTask()  —— 创建导入任务对象
  task.filename = ...  —— 源文件路径
  task.destination_path = ...  —— 目标包路径
  task.destination_name = ...  —— 资产名（不含扩展名）
  task.replace_existing = ...  —— 是否覆盖已有资产
  task.automated = ...  —— 是否启用自动化模式（无弹窗）
  task.save = ...  —— 导入后是否保存资产
  task.options = ...  —— 导入选项配置对象
  task.imported_object_paths -> Array[str]  —— 导入完成后产出的资产路径数组
  asset_tools.import_asset_tasks(import_tasks: Array[AssetImportTask]) -> None  —— 按导入任务列表批量导入资产
  asset_tools.export_assets(assets_to_export: Array[str], export_path: str) -> None  —— 导出资产到指定磁盘目录
  asset_tools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object  —— 用工厂在指定包路径创建资产
  unreal.FbxImportUI()  —— FBX 导入选项界面类
  unreal.AutomatedAssetImportData()  —— 自动化导入所需的数据容器类
  unreal.FbxExportOption()  —— FBX 导出选项类
  unreal.MaterialInstanceConstantFactoryNew()  —— 材质实例常量资产的创建工厂
  unreal.MaterialInstanceConstant  —— 材质实例常量资产类
  unreal.TextureGroup.TEXTUREGROUP_WORLD  —— 世界纹理组枚举成员
  obj.set_editor_property(name: str, value: object, notify_mode: PropertyAccessChangeNotifyMode = PropertyAccessChangeNotifyMode.DEFAULT) -> None  —— 设置对象的编辑器属性值
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产到内存并返回对象
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
=============================================================
"""

import unreal
import os

# ─────────────────────────────────────────────────────────
# 1. 基本导入流程
# ─────────────────────────────────────────────────────────
# UE 的导入使用 "任务" 模式：创建任务 → 配置选项 → 执行

def import_single_file(file_path, destination_path):
    """
    导入单个文件到 UE 项目

    参数:
        file_path: 磁盘上的文件路径 (如 "C:/Models/character.fbx")
        destination_path: 项目中的目标路径 (如 "/Game/Characters")
    """
    # 创建导入任务
    task = unreal.AssetImportTask()

    # 基本设置
    task.filename = file_path                              # 源文件
    task.destination_path = destination_path                # 目标目录
    task.destination_name = os.path.splitext(
        os.path.basename(file_path)
    )[0]                                                   # 资产名称（不含扩展名）
    task.replace_existing = True                           # 覆盖已有资产
    task.automated = True                                  # 自动化模式（无弹窗）
    task.save = True                                       # 导入后自动保存

    # 获取 AssetTools 并执行导入
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    # 返回导入的资产路径
    imported_paths = task.imported_object_paths
    for path in imported_paths:
        unreal.log(f"已导入: {path}")

    return imported_paths

# ─────────────────────────────────────────────────────────
# 2. FBX 导入（带详细选项）
# ─────────────────────────────────────────────────────────

def import_fbx(file_path, destination_path, import_type="static_mesh"):
    """
    导入 FBX 文件，支持不同类型的导入配置

    import_type: "static_mesh", "skeletal_mesh", "animation"
    """
    task = unreal.AssetImportTask()
    task.filename = file_path
    task.destination_path = destination_path
    task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
    task.replace_existing = True
    task.automated = True
    task.save = True

    # 根据类型配置 FBX 导入选项
    options = unreal.FbxImportUI()

    if import_type == "static_mesh":
        options.import_as_skeletal = False
        options.import_mesh = True
        options.import_animations = False

        # 静态网格体选项
        options.static_mesh_import_data.import_uniform_scale = 1.0
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.generate_lightmap_u_vs = True

    elif import_type == "skeletal_mesh":
        options.import_as_skeletal = True
        options.import_mesh = True
        options.import_animations = True
        options.import_materials = True
        options.import_textures = True

        # 骨骼网格体选项
        options.skeletal_mesh_import_data.import_uniform_scale = 1.0
        options.skeletal_mesh_import_data.import_morph_targets = True
        options.skeletal_mesh_import_data.update_skeleton_reference_pose = False

    elif import_type == "animation":
        options.import_as_skeletal = True
        options.import_mesh = False
        options.import_animations = True
        # 需要指定骨骼资产
        # options.skeleton = unreal.load_asset("/Game/Characters/Skeleton")

    task.options = options

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    return task.imported_object_paths

# ─────────────────────────────────────────────────────────
# 3. 批量导入
# ─────────────────────────────────────────────────────────

def batch_import(source_folder, destination_path, file_extensions=None):
    """
    批量导入文件夹中的所有文件

    参数:
        source_folder: 源文件夹路径 (如 "C:/Models/Batch")
        destination_path: 目标路径 (如 "/Game/BatchImport")
        file_extensions: 文件扩展名过滤 (如 [".fbx", ".obj"])
    """
    if file_extensions is None:
        file_extensions = [".fbx", ".obj", ".png", ".tga", ".wav"]

    # 收集文件
    files_to_import = []
    for filename in os.listdir(source_folder):
        ext = os.path.splitext(filename)[1].lower()
        if ext in file_extensions:
            files_to_import.append(os.path.join(source_folder, filename))

    if not files_to_import:
        unreal.log_warning("没有找到要导入的文件")
        return []

    unreal.log(f"找到 {len(files_to_import)} 个文件要导入")

    # 创建导入任务列表
    tasks = []
    for file_path in files_to_import:
        task = unreal.AssetImportTask()
        task.filename = file_path
        task.destination_path = destination_path
        task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
        task.replace_existing = True
        task.automated = True
        task.save = True
        tasks.append(task)

    # 批量执行
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks(tasks)

    # 汇总结果
    all_imported = []
    for task in tasks:
        all_imported.extend(task.imported_object_paths)

    unreal.log(f"成功导入 {len(all_imported)} 个资产")
    return all_imported

# ─────────────────────────────────────────────────────────
# 4. 导入纹理（带配置）
# ─────────────────────────────────────────────────────────

def import_texture(file_path, destination_path, compression="default",
                   srgb=True, texture_group="TEXTUREGROUP_World"):
    """
    导入纹理文件并配置压缩设置

    参数:
        file_path: 纹理文件路径 (.png, .tga, .jpg, .bmp)
        destination_path: 目标路径
        compression: 压缩设置 ("default", "normalmap", "ui", "skybox")
        srgb: 是否启用 sRGB
        texture_group: 纹理组
    """
    task = unreal.AssetImportTask()
    task.filename = file_path
    task.destination_path = destination_path
    task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
    task.replace_existing = True
    task.automated = True
    task.save = True

    # 纹理导入选项
    options = unreal.AutomatedAssetImportData()
    # 注意：具体可用的导入选项取决于引擎版本

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    # 导入后修改纹理设置
    imported_paths = task.imported_object_paths
    for path in imported_paths:
        texture = unreal.EditorAssetLibrary.load_asset(path)
        if texture and isinstance(texture, unreal.Texture2D):
            # 【修改前】texture.set_editor_property("s_rgb", srgb)
            # 【问题分析】纹理的 sRGB 属性名是 srgb（stub 里 Texture.srgb），不是 s_rgb。
            texture.set_editor_property("srgb", srgb)
            # 【修改前】unreal.TextureGroup.TEXTUREGROUP_World
            # 【问题分析】枚举成员名是全大写：stub 里写的是 TEXTUREGROUP_WORLD。
            #   Python 的枚举成员必须和 C++ 里完全一致，驼峰写法会报 AttributeError。
            #   自查方法：grep PythonStub/unreal.py 里 class TextureGroup 的成员。
            texture.set_editor_property(
                "lod_group",
                unreal.TextureGroup.TEXTUREGROUP_WORLD
            )

            # 保存修改
            unreal.EditorAssetLibrary.save_asset(path)
            unreal.log(f"已配置纹理: {path}")

    return imported_paths

# ─────────────────────────────────────────────────────────
# 5. 导出资产
# ─────────────────────────────────────────────────────────

def export_asset(asset_path, export_directory, export_type="fbx"):
    """
    导出资产到磁盘文件

    参数:
        asset_path: 项目中的资产路径 (如 "/Game/Meshes/MyMesh")
        export_directory: 导出到的磁盘目录
        export_type: 导出格式 ("fbx", "obj", "png")
    """
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # 导出选项
    exporter = None
    if export_type == "fbx":
        exporter = unreal.FbxExportOption()
        exporter.set_editor_property("ascii", False)
        exporter.set_editor_property("level_of_detail", True)

    # 确保导出目录存在
    os.makedirs(export_directory, exist_ok=True)

    # 执行导出
    asset_tools.export_assets(
        [asset_path],
        export_directory
    )

    unreal.log(f"已导出 {asset_path} 到 {export_directory}")

def export_all_assets_of_type(class_name, export_directory):
    """导出指定类型的所有资产"""
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)

    matching = []
    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if class_name.lower() in str(asset_data.asset_class_path).lower():
            matching.append(asset_path)

    if not matching:
        unreal.log_warning(f"没有找到类型为 {class_name} 的资产")
        return

    unreal.log(f"找到 {len(matching)} 个资产要导出")

    os.makedirs(export_directory, exist_ok=True)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.export_assets(matching, export_directory)

    unreal.log(f"已导出 {len(matching)} 个资产到 {export_directory}")

# ─────────────────────────────────────────────────────────
# 6. 创建程序化资产（不导入外部文件）
# ─────────────────────────────────────────────────────────

def create_material_instance(base_material_path, new_asset_name, destination_path):
    """创建材质实例（不需要外部文件）"""
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # 加载基础材质
    base_material = unreal.EditorAssetLibrary.load_asset(base_material_path)
    if not base_material:
        unreal.log_error(f"无法加载基础材质: {base_material_path}")
        return None

    # 创建材质实例
    factory = unreal.MaterialInstanceConstantFactoryNew()

    # 使用 AssetTools 创建
    new_asset = asset_tools.create_asset(
        new_asset_name,
        destination_path,
        unreal.MaterialInstanceConstant,
        factory
    )

    if new_asset:
        # 【修改前】factory.set_editor_property("initial_parent", base_material)
        # 【问题分析】MaterialInstanceConstantFactoryNew 没有 initial_parent 属性，
        #   父材质需在创建后通过 MaterialEditingLibrary.set_material_instance_parent 设置。
        unreal.MaterialEditingLibrary.set_material_instance_parent(
            new_asset, base_material
        )
        unreal.log(f"已创建材质实例: {destination_path}/{new_asset_name}")
    return new_asset

# ─────────────────────────────────────────────────────────
# 使用示例（取消注释来运行）
# ─────────────────────────────────────────────────────────

# 示例1: 导入单个 FBX
# import_fbx("C:/Models/character.fbx", "/Game/Characters", "skeletal_mesh")

# 示例2: 批量导入
# batch_import("C:/Models/Batch", "/Game/BatchImport")

# 示例3: 导出资产
# export_asset("/Game/Meshes/MyMesh", "C:/ExportedAssets")

# 示例4: 导出所有纹理
# export_all_assets_of_type("Texture2D", "C:/ExportedTextures")

unreal.log("资产管理第2课完成！（导入导出）")
unreal.log("提示：取消注释示例代码来实际运行")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写一个自动导入管线：监控文件夹，自动导入新文件
# 2. 编写一个工具，将所有纹理按分辨率分类导出到不同文件夹
# 3. 批量导入 FBX 后自动创建材质并分配
# 4. 实现一个"资产迁移"工具：导出选中资产及其所有依赖
