import os
import unreal


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
    task.destination_path(destination_path)  # 目标目录：/Game/ 下的路径
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


# import_single_file(r"D:\Users\26800\Downloads\grass_ground_1k.blend\textures\grass_ground_diff_1k.jpg", "/Game/Textures")


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
