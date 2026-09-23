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
    # 【易错点】destination_path 是属性，不是方法 —— 写成 task.destination_path(...)
    #   等于把属性当函数调用，会 TypeError。正确写法是直接赋值。
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
        texture_group: 纹理组
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
    compression_map = {
        "default": unreal.TextureCompressionSettings.TC_DEFAULT,
        "normalmap": unreal.TextureCompressionSettings.TC_NORMALMAP,
        "ui": unreal.TextureCompressionSettings.TC_EDITOR_ICON,
        "skybox": unreal.TextureCompressionSettings.TC_BC7,
    }

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

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
            #   Python 的 UE 枚举值必须和 C++ 定义完全一致。
            #   不确定时可以用 dir(unreal.TextureGroup) 查看所有成员。
            texture.set_editor_property("lod_group", texture_group)

            texture.compression_settings = compression_map[compression]
    return imported_paths


# 【注意】下面是示例调用：路径要换成你自己机器上的真实文件。
#   原代码直接写死了别人电脑上的路径，而且文件一加载就立刻执行 ——
#   所以这里先判断文件是否存在，不存在就只给提示，不让脚本报错。
_demo_source = r"C:\Path\To\Your\Textures\example.png"  # ← 改成你的文件路径
if os.path.exists(_demo_source):
    imported_paths = import_texture(_demo_source, "/Game/Textures")
else:
    unreal.log_warning(f"示例导入已跳过：找不到文件 {_demo_source}（请改成你自己的路径）")
