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
        # 【同前】import_uniform_scale 有文档但无 @property，需走 set_editor_property
        options.static_mesh_import_data.set_editor_property("import_uniform_scale", 1.0)
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
        # 【Pylance 易错点】FbxSkeletalMeshImportData 桩文件里只暴露了
        #   vertex_color_import_option / vertex_override_color 两个属性，
        #   import_uniform_scale / import_morph_targets / update_skeleton_reference_pose
        #   虽然在 docstring 里有文档，但没有 @property，直接赋值会报
        #   "属性未知"。这类"有文档没属性"的设置必须走 set_editor_property。
        skeletal = options.skeletal_mesh_import_data
        skeletal.set_editor_property("import_uniform_scale", 1.0)  # 导入缩放比例
        skeletal.set_editor_property(
            "import_morph_targets",
            True,  # 导入变形目标（表情等）
        )
        skeletal.set_editor_property(
            "update_skeleton_reference_pose",
            False,  # 不更新骨骼参考姿势
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
# _demo_source = r"C:\Path\To\Your\Textures\example.png"  # ← 改成你的文件路径
# if os.path.exists(_demo_source):
#     imported_paths = import_texture(_demo_source, "/Game/Textures")
# else:
#     unreal.log_warning(
#         f"示例导入已跳过：找不到文件 {_demo_source}（请改成你自己的路径）"
#     )
# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────

# 练习 1：自动导入管线 —— 扫描文件夹，把新出现的文件导入项目（已见过的自动跳过）
#
# 【深入浅出】"监控文件夹"听着高大上，拆开其实就是三个问题：
#   ① 文件夹里有什么？      → os.listdir(folder)
#   ② 哪些是没见过的新文件？ → 拿去和"已处理名单" _seen_files 比对
#   ③ 新文件怎么进 UE？     → 复用文件上方写好的 import_fbx / import_texture
#
# 【UE 概念】编辑器 Python 没有给我们"文件夹变了就通知我"的事件监听器，
#   所以最朴素可靠的方案是：**反复调用同一个扫描函数**，每调用一次就
#   处理一遍"名单之外的新文件"。想做成定时器，配合 utils/helpers.py
#   里的 Timer 周期性调用 scan_watch_folder() 即可。
#
# 【注意】_seen_files 是模块级变量，它的生命周期 = 这段脚本的运行会话：
#   · 同一次执行后多次调用 scan_watch_folder() → 名单一直有效，只导新文件
#   · 重新 exec 整个文件 → `_seen_files = set()` 会再次执行，名单清零
#   · 用 import my02 加载 → 模块只初始化一次，名单跨调用保留
_seen_files = set()  # 模块级状态：记录已经处理过的文件完整路径（去重的关键）

_WATCH_EXTS = {
    ".fbx": "fbx",
    ".png": "texture",
    ".jpg": "texture",
    ".jpeg": "texture",
    ".tga": "texture",
    ".bmp": "texture",
}


def scan_watch_folder(folder, destination_path="/Game/AutoImport"):
    """
    扫描 folder 一次，把上次扫描之后新增的文件导入项目。

    参数:
        folder: 要"监控"的磁盘文件夹
        destination_path: 导入目标路径
    返回: 本次新导入的资产路径列表

    【深入浅出】函数主流程就像过安检：
        列出所有文件 → 过滤掉子文件夹/见过的/不支持的 → 只处理剩下的新文件
    """
    if not os.path.isdir(folder):
        unreal.log_warning(f"文件夹不存在: {folder}")
        return []

    imported = []
    # 【注意】sorted 保证处理顺序稳定，方便对照日志排查问题
    for name in sorted(os.listdir(folder)):
        file_path = os.path.join(folder, name)
        # 【易错点】os.listdir 连子文件夹的名字也会返回，
        #   不加 os.path.isfile 判断就导入，遇到子目录会直接报错。
        #   而 `file_path in _seen_files` 是"只导入新文件"的核心：
        #   名单里有 → 见过 → 跳过；没有 → 新文件 → 处理。
        if not os.path.isfile(file_path) or file_path in _seen_files:
            continue

        ext = os.path.splitext(name)[1].lower()  # splitext 返回 (主名, 扩展名)，取后者
        if ext not in _WATCH_EXTS:
            unreal.log_warning(f"跳过不支持的格式: {name}")
            continue

        # 【设计取舍】先记名单再导入（顺序不能反）：
        #   就算这个文件导入失败，也已经进名单了，
        #   下次扫描不会反复重试坏文件刷屏 —— 换来的是"坏文件需手动处理"。
        _seen_files.add(file_path)
        if _WATCH_EXTS[ext] == "fbx":
            imported += import_fbx(file_path, destination_path)
        else:
            imported += import_texture(file_path, destination_path)

    for path in imported:
        unreal.log(f"自动导入: {path}")
    if not imported:
        unreal.log("没有新文件需要导入")
    return imported


# scan_watch_folder(r"D:\IncomingAssets", "/Game/AutoImport")


# 练习 2：把 /Game 下所有纹理按分辨率分类，导出到不同文件夹
#
# 【深入浅出】思路分四步：
#   ① list_assets 列出 /Game 下所有资产 —— 只拿到路径字符串，不加载任何资产
#   ② 用 find_asset_data 做"预筛"，只留 Texture2D —— 轻量、几乎零开销，
#      相当于查数据库先走索引过滤，而不是把整库读进内存
#   ③ 命中的才 load_asset 读取宽高，按 "1024x1024" 这样的 key 分组到字典
#   ④ 每个分组建一个子文件夹，调 export_assets 导出
#
# 【易错点】一个项目动辄上千个资产，如果②③写反（先 load 再判断类型），
#   等于把所有资产全部加载进内存，脚本会慢到像卡死。


def export_textures_by_resolution(export_root):
    """
    扫描 /Game 下所有 Texture2D，按 "宽x高" 分组，
    分别导出到 export_root/1024x1024/、export_root/512x512/ 等子文件夹。

    参数:
        export_root: 磁盘上的导出根目录（不存在会自动创建）
    返回: {分辨率字符串: [资产路径列表]}
    """
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    groups = {}

    # 【UE 概念】两步走：先用 AssetData（轻量，不加载资产）按类过滤，
    #   命中的才 load_asset 读取分辨率。直接 load 全项目资产会非常慢。
    for path in unreal.EditorAssetLibrary.list_assets(
        "/Game", recursive=True, include_folder=False
    ):
        data = unreal.EditorAssetLibrary.find_asset_data(path)
        # 【易错点】asset_class_path.asset_name 返回的是 unreal.Name，
        #   不是 str —— 直接和字符串比较会得到 False，必须先 str() 转换。
        if str(data.asset_class_path.asset_name) != "Texture2D":
            continue

        texture = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(texture, unreal.Texture2D):
            continue
        # blueprint_get_size_x/y 返回像素尺寸（int）
        # 【Python 语法】setdefault(key, 默认值)：
        #   字典里有 key → 直接返回已有的值；没有 → 先塞入默认值再返回。
        #   一行就实现"没有就建列表，有就追加"，不用写 if 判断。
        key = f"{texture.blueprint_get_size_x()}x{texture.blueprint_get_size_y()}"
        groups.setdefault(key, []).append(path)

    # 分组完成，现在按组导出：一组 = 一个分辨率文件夹
    for resolution, paths in groups.items():
        # 【Python 语法】exist_ok=True：目录已存在时不抛 FileExistsError
        out_dir = os.path.join(export_root, resolution)
        os.makedirs(out_dir, exist_ok=True)
        # 【UE 概念】export_assets(资产路径列表, 导出目录)：
        #   文件名由引擎按资产名自动决定，导出格式按资产类型自动选择。
        #   每组传不同的 out_dir，就实现了"按分辨率分类导出"。
        asset_tools.export_assets(paths, out_dir)
        unreal.log(f"[{resolution}] 已导出 {len(paths)} 张纹理到 {out_dir}")

    return groups


# export_textures_by_resolution(r"D:\ExportedTextures")


# 练习 3：批量导入 FBX 后，自动创建材质实例并分配到网格体的所有插槽
#
# 【深入浅出】思路分两段：
#   A. 导入 —— 扫描文件夹里的 .fbx，逐个复用前面写好的 import_fbx
#   B. 配材质 —— 对每个导入的 StaticMesh 走固定四步：
#      create_asset 造 MI → set_material_instance_parent 指定父材质
#      → set_material 逐插槽分配 → save_asset 保存
#
# 【UE 概念】为什么创建**材质实例（MI）**而不是新建一个母材质（Material）？
#   · 母材质要在节点图里连节点，Python 脚本操作繁琐且易错
#   · MI 继承父材质、创建成本极低、每个网格体一个互不干扰
#   · 这正是工业界标准做法：一个母材质 + 场景里成百上千个 MI


def batch_import_fbx_and_create_material(
    folder,
    destination_path="/Game/Meshes",
    parent_material_path="/Engine/EngineMaterials/DefaultMaterial",
):
    """
    批量导入 folder 里的 .fbx（按静态网格体），并给每个网格体
    创建一个材质实例（MI），分配到它的全部材质插槽。

    参数:
        folder: 存放 FBX 的磁盘文件夹
        destination_path: 网格体导入目标路径
        parent_material_path: 新材质实例的父材质（默认引擎默认材质）
    返回: 创建出来的材质实例路径列表
    """
    if not os.path.isdir(folder):
        unreal.log_warning(f"文件夹不存在: {folder}")
        return []

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    # 父材质只加载一次，循环里复用 —— load_asset 有开销，别放进循环
    parent = unreal.EditorAssetLibrary.load_asset(parent_material_path)
    created = []

    for name in sorted(os.listdir(folder)):
        # 【注意】Windows 上文件名大小写不统一（.FBX / .fbx），
        #   统一转小写再比对，避免漏掉文件
        if not name.lower().endswith(".fbx"):
            continue

        # 复用练习之前的 import_fbx，按静态网格体导入
        mesh_paths = import_fbx(os.path.join(folder, name), destination_path)
        for mesh_path in mesh_paths:
            mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
            # 【注意】imported_object_paths 里可能混入贴图等非网格体资产，
            #   用 isinstance 把目标（StaticMesh）筛出来，别假设返回的都是网格
            if not isinstance(mesh, unreal.StaticMesh):
                continue

            # 【UE 概念】create_asset(名字, 目录, 资产类, 工厂) 是创建资产的通用套路：
            #   工厂（Factory）决定"怎么造"，MaterialInstanceConstantFactoryNew
            #   专门负责造材质实例。注意 package_path 只写到文件夹，不含资产名。
            # 【易错点】get_name() 返回的是不含路径的短名（如 "SM_Rock"），
            #   想拿完整路径要用 get_path_name()（返回 /Game/....SM_Rock）。
            mi = asset_tools.create_asset(
                "MI_" + mesh.get_name(),  # 资产名：MI_ + 网格体名，一眼看出对应关系
                destination_path + "/Materials",
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
            if not isinstance(mi, unreal.MaterialInstanceConstant):
                # create_asset 撞名时不报错、返回 None —— 不判断会把 None 当对象用而崩溃
                unreal.log_warning(f"材质实例创建失败（可能重名）: {mesh.get_name()}")
                continue

            # 【UE 概念】新建的 MI 是"空壳"，没有父材质就什么都显示不出来。
            #   必须先 set_material_instance_parent，它才知道继承哪些参数。
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)

            # 把 MI 分配到网格体的每一个材质插槽（下标 0, 1, 2 ...）。
            #   static_materials 是这个网格体的插槽列表，长度 = 插槽数量。
            for i in range(len(mesh.static_materials)):
                mesh.set_material(i, mi)

            # 【注意】改动资产后要保存，否则只存在于内存，编辑器关闭就丢了。
            #   save_asset 参数是资产路径（/Game/... 形式），不是对象本身。
            unreal.EditorAssetLibrary.save_asset(mi.get_path_name())
            created.append(mi.get_path_name())
            unreal.log(
                f"已创建并分配材质实例: {mi.get_path_name()} -> {mesh.get_name()}"
            )

    return created


# batch_import_fbx_and_create_material(r"D:\Models")


# 练习 4："资产迁移"工具 —— 导出当前在内容浏览器里选中的资产及其所有依赖
#
# 【深入浅出】为什么需要 **两个容器**（stack 和 pkgs）？
#   资产引用是链式的，还可能成环：
#       角色 → 贴图 → 母材质 → 另一张贴图 → ……（甚至绕回角色）
#   而 get_dependencies 一次只能拿到"下一层"引用，
#   要拿全就必须对**每个新发现的包再查一次** —— 这是典型的图遍历问题。
#   · stack（栈）   ＝ 待查询清单：里面每个包都还没查过它的依赖
#   · pkgs（集合）  ＝ 成果袋，同时充当"已经查过"的标记
#
#   ❓ 只把依赖 pkgs.add() 不入栈行不行？
#      不行。新包进不了"待查询清单"，就没人查它的依赖，
#      结果永远只有第一层直接依赖，深层引用全部漏掉。
#   ❓ 那直接 for pkg in pkgs 遍历这个不断增长的集合呢？
#      不行。Python 禁止遍历过程中修改集合，会抛 RuntimeError。
#
#   防环秘诀：入栈前查 `dep not in pkgs`，取出来后再查 `pkg in pkgs` ——
#   A→B→A 这种循环引用，第二次遇到 A 时它已在成果袋里，直接跳过。


def export_selected_with_dependencies(export_dir):
    """
    把内容浏览器中选中的资产，连同它们引用到的所有依赖（递归）
    一起导出到 export_dir，便于迁移到其他项目。

    参数:
        export_dir: 磁盘导出目录（不存在会自动创建）
    返回: 实际导出的包路径集合
    """
    os.makedirs(export_dir, exist_ok=True)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # 【UE 概念】AssetRegistry 是资产注册表：不用加载资产就能查询
    #   "谁引用了谁"这类关系信息，是做依赖分析的标准入口。
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    # 【UE 概念】依赖选项：要把哪些类型的引用算作"依赖"。
    #   软引用（软对象路径）和硬引用都要算上，迁移才完整。
    options = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=True,
        include_hard_package_references=True,
        include_game_package_references=True,
        include_editor_only_package_references=True,
    )

    # 【深入浅出】图遍历的标准开场：先把"起点"放进待查询清单。
    #   这里起点 = 用户在内容浏览器里选中的资产。
    stack = [
        str(ad.package_name)  # AssetData.package_name 是 unreal.Name，转 str
        for ad in unreal.EditorUtilityLibrary.get_selected_asset_data()
    ]
    if not stack:
        # 没选资产时直接返回，避免后面空转一圈
        unreal.log_warning("请先在内容浏览器里选中至少一个资产")
        return set()

    pkgs = set()  # 成果袋 + "已查过"标记，一物两用
    while stack:
        pkg = stack.pop()  # 弹出一个"还没查过依赖"的包（.pop() 默认弹栈尾，LIFO）
        if pkg in pkgs:
            # 已经收过 = 它的依赖也查过了 → 跳过。
            # 这一行同时挡住两件事：重复劳动 和 循环引用死循环。
            continue
        pkgs.add(pkg)  # 收进成果袋，说明"处理过"

        # get_dependencies 返回该包引用到的包路径（Name 列表），可能为 None
        # 【易错点】`or []` 是给 None 兜底：None 不能 for 遍历，会 TypeError。
        for dep in registry.get_dependencies(unreal.Name(pkg), options) or []:
            dep_str = str(dep)
            # 只追项目内的包（/Game/ 开头）；引擎自带的（/Engine/ 等）
            # 不需要迁移，目标项目里本来就有。
            # 新包必须**入栈排队**，轮到它时才会查它的下一层依赖 ——
            # 这就是"递归展开"靠循环+栈实现，而不是靠函数自己调自己。
            if dep_str.startswith("/Game/") and dep_str not in pkgs:
                stack.append(dep_str)

    # 一次性导出所有包。export_assets 会按资产类型自动选导出器
    # （网格体→.psk/.fbx、纹理→.tga 等）。
    asset_tools.export_assets(sorted(pkgs), export_dir)
    unreal.log(f"已导出 {len(pkgs)} 个包到 {export_dir}")
    for pkg in sorted(pkgs):
        unreal.log(f"  - {pkg}")
    return pkgs


# 在内容浏览器里选中资产后运行：
# export_selected_with_dependencies(r"D:\MigratedAssets")
