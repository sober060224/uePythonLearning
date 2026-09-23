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

习题可能用到的 API：
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取 AssetTools 实例以执行导入导出
  unreal.AssetImportTask()  —— 创建导入任务对象（配置源文件、目标路径等）
  asset_tools.import_asset_tasks(import_tasks: Array[AssetImportTask]) -> None  —— 按导入任务列表批量导入资产
  asset_tools.export_assets(assets_to_export: Array[str], export_path: str) -> None  —— 导出资产到指定磁盘目录
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出资产路径（用于筛选待导入/导出文件）
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产元数据（用于按类型分类）
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  asset_tools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object  —— 用工厂在指定包路径创建资产
=============================================================
"""

import unreal
import os

# ─────────────────────────────────────────────────────────
# 1. 基本导入流程
# ─────────────────────────────────────────────────────────
# 【UE 概念】UE 的导入使用"任务"模式：先创建一个 AssetImportTask 对象，
#   填好各项配置，然后把任务交给 AssetTools 执行。
#   这种设计支持批量操作——你可以创建多个任务一起执行。
#   相比逐个导入，批量导入效率更高（减少磁盘 I/O 和引擎开销）。


def import_single_file(file_path, destination_path):
    """
    导入单个文件到 UE 项目

    参数:
        file_path: 磁盘上的文件路径 (如 "C:/Models/character.fbx")
        destination_path: 项目中的目标路径 (如 "/Game/Characters")
    """
    # 【UE 概念】AssetImportTask 是一个"任务描述"对象，包含导入所需的全部配置。
    #   它不会立即执行导入，只是告诉引擎"我要做什么"。
    task = unreal.AssetImportTask()

    # 基本设置
    task.filename = file_path  # 源文件：磁盘上的完整路径
    task.destination_path = destination_path  # 目标目录：/Game/ 下的路径
    # 【注意】destination_name 不包含路径，也不包含文件扩展名。
    #   比如导入 "C:/Models/hero.fbx"，资产名就是 "hero"。
    #   os.path.splitext(os.path.basename(file_path))[0] 就是取文件名去掉扩展名。
    task.destination_name = os.path.splitext(os.path.basename(file_path))[
        0
    ]  # 资产名称（不含扩展名）
    task.replace_existing = True  # 覆盖已有资产（避免重复导入产生冲突）
    task.automated = True  # 自动化模式：跳过所有弹窗确认，适合脚本批量操作
    task.save = True  # 导入后自动保存到磁盘（否则资产在内存中未保存，关闭编辑器会丢失）

    # 【UE 概念】AssetTools 是 UE 的资产管理工具类，提供导入、导出、创建等功能。
    #   不能直接实例化，必须通过 AssetToolsHelpers.get_asset_tools() 获取。
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    # 导入任务列表可以包含多个任务，一次性执行比逐个调用更高效
    asset_tools.import_asset_tasks([task])

    # 【注意】imported_object_paths 只有在导入成功后才有值。
    #   如果文件格式不支持或导入失败，这个列表会为空。
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

    # 【UE 概念】FbxImportUI 是 FBX 专用的导入选项类。
    #   它控制导入行为：是当静态网格体导入还是骨骼网格体？要不要导入动画？
    #   不同类型的资产有不同的子选项（static_mesh_import_data, skeletal_mesh_import_data 等）。
    #   设置错误会导致导入结果不符合预期（比如骨骼网格体被当静态网格体导入）。
    options = unreal.FbxImportUI()

    if import_type == "static_mesh":
        # 【初学者易错点】import_as_skeletal 是关键开关：
        #   False = 作为静态网格体导入（没有骨骼，不能播放动画）
        #   True = 作为骨骼网格体导入（有骨骼，支持动画）
        options.import_as_skeletal = False
        options.import_mesh = True
        options.import_animations = False

        # 静态网格体选项
        options.static_mesh_import_data.import_uniform_scale = 1.0  # 导入缩放比例
        # combine_meshes=True 会把 FBX 中所有网格体合并成一个，减少 DrawCall
        options.static_mesh_import_data.combine_meshes = True
        # 生成光照贴图 UV（用于静态光照烘焙）
        options.static_mesh_import_data.generate_lightmap_u_vs = True

    elif import_type == "skeletal_mesh":
        options.import_as_skeletal = True  # 这是骨骼网格体的关键！
        options.import_mesh = True
        options.import_animations = True
        options.import_materials = True  # 一起导入材质
        options.import_textures = True  # 一起导入纹理

        # 骨骼网格体选项
        options.skeletal_mesh_import_data.import_uniform_scale = 1.0
        options.skeletal_mesh_import_data.import_morph_targets = (
            True  # 导入变形目标（表情等）
        )
        options.skeletal_mesh_import_data.update_skeleton_reference_pose = (
            False  # 不更新骨骼参考姿势
        )

    elif import_type == "animation":
        options.import_as_skeletal = True
        options.import_mesh = False  # 动画导入不需要网格体
        options.import_animations = True
        # 【重要】导入动画需要指定一个已有的骨骼资产（Skeleton）。
        #   引擎需要知道这个动画绑定在哪套骨骼上。
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
    # 【为什么设置默认值要用 None？】Python 的可变默认参数（如 []）是"陷阱"：
    #   函数只会在定义时创建一次这个列表，后续调用会共享同一个对象。
    #   用 None 作为默认值，在函数内部再创建新列表是安全的做法。
    if file_extensions is None:
        file_extensions = [".fbx", ".obj", ".png", ".tga", ".wav"]

    # 收集文件：用 os.listdir 遍历磁盘目录，按扩展名过滤
    files_to_import = []
    for filename in os.listdir(source_folder):
        ext = os.path.splitext(filename)[1].lower()  # .lower() 统一大小写
        if ext in file_extensions:
            files_to_import.append(os.path.join(source_folder, filename))

    if not files_to_import:
        unreal.log_warning("没有找到要导入的文件")
        return []

    unreal.log(f"找到 {len(files_to_import)} 个文件要导入")

    # 【效率技巧】批量导入的关键：先创建所有任务，再一次性交给引擎执行。
    #   引擎内部会优化批量操作的内存和 I/O，比逐个导入快很多。
    tasks: list[unreal.AssetImportTask] = []
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

    # 汇总结果：每个 task 有自己的 imported_object_paths
    all_imported = []
    for task in tasks:
        all_imported.extend(task.imported_object_paths)

    unreal.log(f"成功导入 {len(all_imported)} 个资产")
    return all_imported


# ─────────────────────────────────────────────────────────
# 4. 导入纹理（带配置）
# ─────────────────────────────────────────────────────────


def import_texture(
    file_path,
    destination_path,
    compression="default",
    srgb=True,
    texture_group="TEXTUREGROUP_WORLD",
):
    """
    导入纹理文件并配置压缩设置

    参数:
        file_path: 纹理文件路径 (.png, .tga, .jpg, .bmp)
        destination_path: 目标路径
        compression: 压缩设置 ("default", "normalmap", "ui", "skybox")
        srgb: 是否启用 sRGB
        texture_group: 纹理组 ("TEXTUREGROUP_WORLD", "TEXTUREGROUP_UI", "TEXTUREGROUP_CHARACTER", "TEXTUREGROUP_SKYBOX")
    """
    task = unreal.AssetImportTask()
    task.filename = file_path
    task.destination_path = destination_path
    task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
    task.replace_existing = True
    task.automated = True
    task.save = True

    # 【注意】这里用 AutomatedAssetImportData 作为通用导入选项容器。
    #   纹理导入的大部分选项可以在导入后通过 set_editor_property 修改。
    # options = unreal.AutomatedAssetImportData()

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    # 【易错点】compression_settings / lod_group 都是枚举属性，不能直接赋字符串
    #   （会报 TypeError），先把"好记的字符串"映射成枚举成员再赋值。
    compression_map = {
        "default": unreal.TextureCompressionSettings.TC_DEFAULT,
        "normalmap": unreal.TextureCompressionSettings.TC_NORMALMAP,
        "ui": unreal.TextureCompressionSettings.TC_EDITOR_ICON,
        "skybox": unreal.TextureCompressionSettings.TC_HDR,
    }
    texture_group_map = {
        "TEXTUREGROUP_WORLD": unreal.TextureGroup.TEXTUREGROUP_WORLD,
        "TEXTUREGROUP_UI": unreal.TextureGroup.TEXTUREGROUP_UI,
        "TEXTUREGROUP_CHARACTER": unreal.TextureGroup.TEXTUREGROUP_CHARACTER,
        "TEXTUREGROUP_SKYBOX": unreal.TextureGroup.TEXTUREGROUP_SKYBOX,
    }

    # 【UE 概念】导入纹理后，引擎会用默认设置创建纹理资产。
    #   但很多时候默认设置不够用——比如法线贴图需要特殊压缩，
    #   UI 纹理需要禁用 sRGB，不同用途的纹理属于不同的纹理组（LOD 分组）。
    #   所以我们导入后再通过代码修改这些属性。
    imported_paths = task.imported_object_paths
    for path in imported_paths:
        # 【UE 概念】load_asset 把资产从磁盘加载到内存，返回对象引用。
        #   只有加载后才能读取和修改资产的属性。
        #   【注意】load_asset 有性能开销，不要在大循环里反复调用。
        texture = unreal.EditorAssetLibrary.load_asset(path)
        if texture and isinstance(texture, unreal.Texture2D):
            # 【初学者易错点】set_editor_property 的属性名必须和 C++/Python 桩里完全一致。
            #   纹理的 sRGB 属性名是 "srgb"（全小写），不是 "s_rgb"。
            #   如果写错会报 AttributeError。
            texture.set_editor_property("srgb", srgb)
            # 【初学者易错点】枚举成员名必须全大写：TEXTUREGROUP_WORLD，不是 TEXTUREGROUP_World。
            #   不确定时可以用 dir(unreal.TextureGroup) 查看所有成员。
            texture.set_editor_property(
                "lod_group",
                texture_group_map.get(
                    texture_group, unreal.TextureGroup.TEXTUREGROUP_WORLD
                ),
            )
            # compression_settings 是 TextureCompressionSettings 枚举，不能直接赋字符串
            texture.compression_settings = compression_map.get(
                compression, unreal.TextureCompressionSettings.TC_DEFAULT
            )

            # 修改后必须保存，否则更改不会写入磁盘
            unreal.EditorAssetLibrary.save_asset(path)
            unreal.log(f"已配置纹理: {path}")

    return imported_paths


# ─────────────────────────────────────────────────────────
# 5. 导出资产
# ─────────────────────────────────────────────────────────


# ============================================================
# 导出资产到磁盘文件
# 用 AssetExportTask + Exporter 的组合，才能挂自定义导出选项
# ============================================================


def export_asset(asset_path, export_directory, export_type="fbx"):
    # --------------------------------------------------------
    # 第一步：把 UE 里的资产加载到内存
    # asset_path 形如 "/Game/Meshes/MyMesh"，这是"包路径"，不是磁盘路径
    # load_asset 返回的是 UE 对象（UObject），拿不到就返回 None
    # --------------------------------------------------------
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)

    # 加载失败（路径写错、资产不存在）就直接退出，避免后面拿着 None 去操作
    if not asset:
        unreal.log_error(f"找不到资产: {asset_path}")
        return

    # --------------------------------------------------------
    # 第二步：确保导出目录存在
    # exist_ok=True 表示"目录已存在也别报错"，让脚本可以反复运行
    # 没有这一句，第二次导出到同一目录时会抛 FileExistsError 中断
    # --------------------------------------------------------
    os.makedirs(export_directory, exist_ok=True)

    # --------------------------------------------------------
    # 第三步：拼出导出文件的完整路径（不含扩展名）
    # 注意：导出器会根据资产类型和选项自动补上 .fbx / .obj / .png
    #       所以这里只给"目录 + 资产名"，不要自己写扩展名
    # 例：C:/ExportedAssets/MyMesh
    # --------------------------------------------------------
    filename = os.path.join(export_directory, asset.get_name())

    # --------------------------------------------------------
    # 第四步：创建"导出任务"对象
    # AssetExportTask 是一个容器，把"导谁、导到哪、用什么选项"打包起来
    # --------------------------------------------------------
    task = unreal.AssetExportTask()

    task.object = asset  # 要导出的资产对象（不是路径字符串）
    task.filename = filename  # 目标文件路径（不含扩展名）
    task.automated = True  # 自动化模式：不弹任何对话框
    task.prompt = False  # 不询问用户确认（无人值守脚本必备）
    task.replace_identical = True  # 目标文件已存在时直接覆盖

    # --------------------------------------------------------
    # 第五步：根据导出格式挂不同的选项
    # 只有 FBX 需要自定义选项；obj/png 等走默认即可
    # --------------------------------------------------------
    if export_type == "fbx":
        # FbxExportOption 专门控制 FBX 导出的细节
        fbx_opts = unreal.FbxExportOption()
        fbx_opts.ascii = False
        fbx_opts.level_of_detail = True
        task.options = fbx_opts  # 把选项挂到任务上
    # 非 FBX 时 task.options 留空，导出器会用默认配置

    # --------------------------------------------------------
    # 第六步：真正执行导出
    # 关键点：AssetTools.export_assets 不接受自定义选项，
    #         想用 FbxExportOption 必须走 Exporter.run_asset_export_task
    # --------------------------------------------------------
    unreal.Exporter.run_asset_export_task(task)

    unreal.log(f"已导出 {asset_path} 到 {export_directory}")


def export_all_assets_of_type(class_name, export_directory):
    """导出指定类型的所有资产"""
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)

    matching = []
    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # 用 find_asset_data 获取资产类型，模糊匹配
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

    # 【UE 概念】材质实例（Material Instance）是基于父材质创建的"衍生品"。
    #   它可以覆盖父材质的参数（颜色、纹理等），而不需要重新创建材质。
    #   这是一种高效的材质管理方式——多个物体共享一个父材质，但外观各不相同。

    # load_asset 把材质从磁盘加载到内存
    base_material = unreal.EditorAssetLibrary.load_asset(base_material_path)
    if not base_material:
        unreal.log_error(f"无法加载基础材质: {base_material_path}")
        return None

    # 【UE 概念】Factory（工厂）是 UE 创建资产的"模板"。
    #   MaterialInstanceConstantFactoryNew 是专门创建材质实例的工厂。
    #   每种资产类型都有对应的 Factory 类。
    factory = unreal.MaterialInstanceConstantFactoryNew()

    # 【初学者易错点】create_asset 的参数：
    #   - asset_name: 新资产名称（不含路径）
    #   - package_path: /Game/ 下的目标目录
    #   - asset_class: 资产类（如 unreal.MaterialInstanceConstant）
    #   - factory: 创建资产的工厂对象
    #   返回值是创建成功的资产对象，失败返回 None。
    new_asset = asset_tools.create_asset(
        new_asset_name, destination_path, unreal.MaterialInstanceConstant, factory
    )

    if new_asset:
        # 【初学者易错点】Factory 不负责设置父材质。
        #   MaterialInstanceConstantFactoryNew 没有 initial_parent 属性。
        #   父材质必须在资产创建后，通过 MaterialEditingLibrary 设置。
        #   这是 UE API 设计的一个"分步"模式：先创建，再配置。
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
# batch_import(r"D:\Users\26800\Downloads\fbx", "/Game/Textures")

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
