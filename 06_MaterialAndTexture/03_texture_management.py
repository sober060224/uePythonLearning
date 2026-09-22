"""
=============================================================
材质与纹理 第3课：纹理管理和批量处理
=============================================================

学习目标：
  - 纹理的导入和配置
  - 批量修改纹理设置
  - 纹理打包和优化

核心类：
  - unreal.Texture2D - 纹理资产
  - 纹理设置通过 set_editor_property 修改

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出路径下资产的路径数组
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产元数据（不加载资产）
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产对象
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  texture.blueprint_get_size_x() / blueprint_get_size_y() -> int  —— 读取纹理像素宽高
  texture.set_editor_property(name: str, value: object) -> None  —— 修改纹理编辑器属性
  unreal.TextureCompressionSettings.TC_DEFAULT / TC_NORMALMAP / TC_HDR  —— 纹理压缩方式枚举
  unreal.AssetImportTask()  —— 构建单个资产导入任务
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例
  unreal.AssetTools.import_asset_tasks(import_tasks: Array[AssetImportTask]) -> None  —— 批量执行导入任务
=============================================================
"""

import unreal
import os

# ─────────────────────────────────────────────────────────
# 1. 查找项目中的纹理
# ─────────────────────────────────────────────────────────

def find_all_textures(search_path="/Game"):
    """查找项目中所有纹理"""
    # list_assets 递归列出指定路径下的所有资产。
    # recursive=True 表示包含子目录，include_folder=False 表示只返回资产不返回文件夹。
    # 返回的是字符串数组（资产路径），不是资产对象——这样可以避免加载大量资产导致卡顿。
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    textures = []

    for asset_path in all_assets:
        # find_asset_data 获取资产的元数据（不加载资产本身）。
        # 这比 load_asset 快得多——元数据只包含名称、类型等基本信息，
        # 不需要加载资产的完整数据到内存。
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)

        # 判断是否是纹理类型：
        # asset_class_path 是一个 TopLevelAssetPath 对象，
        # 转成字符串后包含类名（如 "Texture2D"）。
        # 注意：用 "in str()" 的方式判断比精确比较更健壮，
        # 因为不同版本的 UE 可能返回不同的路径格式。
        if "Texture" in str(asset_data.asset_class_path):
            textures.append(asset_data)

    unreal.log(f"找到 {len(textures)} 个纹理")
    return textures

# ─────────────────────────────────────────────────────────
# 2. 检查纹理属性
# ─────────────────────────────────────────────────────────

def inspect_texture(texture_path):
    """详细检查纹理属性"""
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if not texture:
        unreal.log_error(f"无法加载纹理: {texture_path}")
        return

    # 类型检查：确保加载的确实是 Texture2D。
    # Unreal 中还有 TextureCube、RenderTexture 等其他纹理类型，
    # 它们的 API 不同，不能混用。
    if not isinstance(texture, unreal.Texture2D):
        unreal.log_warning(f"不是 Texture2D: {texture_path}")
        return

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"纹理: {texture.get_name()}")
    unreal.log(f"路径: {texture_path}")

    # 读取纹理分辨率：
    # 重要：Texture2D 没有 size_x/size_y 这样的编辑器属性！
    # 必须用 blueprint_get_size_x() / blueprint_get_size_y() 方法。
    # 这是 UE Python API 的常见陷阱——属性和方法要分清楚。
    size_x = texture.blueprint_get_size_x()
    size_y = texture.blueprint_get_size_y()
    unreal.log(f"分辨率: {size_x} x {size_y}")

    # sRGB 属性：决定纹理是否在 sRGB 颜色空间中。
    # 颜色贴图（Diffuse/BaseColor）应该开启 sRGB（True），
    # 数据贴图（法线、粗糙度、金属度等）应该关闭 sRGB（False）。
    # 错误的 sRGB 设置会导致颜色偏差或数据失真。
    srgb = texture.get_editor_property("srgb")
    unreal.log(f"sRGB: {srgb}")

    # 压缩设置：决定纹理在 GPU 上的存储格式。
    # TC_DEFAULT：通用压缩，适用于大多数颜色贴图
    # TC_NORMALMAP：法线贴图专用压缩（保留更多法线精度）
    # TC_HDR：高动态范围纹理（如环境探针）
    compression = texture.get_editor_property("compression_settings")
    unreal.log(f"压缩设置: {compression}")

    # LOD Group：控制纹理的流式加载 LOD 级别。
    # 不同用途的纹理应该放在不同的 LOD 组中，
    # 比如角色贴图比远景贴图需要更高的分辨率。
    lod_group = texture.get_editor_property("lod_group")
    unreal.log(f"LOD Group: {lod_group}")

    # 检查分辨率是否是 2 的幂（Power of Two）。
    # GPU 对 2 的幂纹理的压缩和采样效率更高。
    # 非 2 的幂纹理（NPOT）虽然 UE 支持，但会有性能损失和兼容性问题。
    # (x & (x-1) == 0) 是判断是否为 2 的幂的位运算技巧。
    is_pot = (size_x & (size_x - 1) == 0) and (size_y & (size_y - 1) == 0)
    if not is_pot:
        unreal.log_warning(f"⚠️ 非2的幂次分辨率!")

    return {
        "name": texture.get_name(),
        "size_x": size_x,
        "size_y": size_y,
        "srgb": srgb,
        "is_power_of_two": is_pot,
    }

# ─────────────────────────────────────────────────────────
# 3. 批量修改纹理设置
# ─────────────────────────────────────────────────────────

def configure_texture(texture_path, srgb=True,
                       compression="TC_Default",
                       lod_group="TEXTUREGROUP_World"):
    """
    配置纹理设置

    参数:
        texture_path: 纹理路径
        srgb: 是否启用 sRGB
        compression: 压缩类型
        lod_group: LOD 组
    """
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if not texture or not isinstance(texture, unreal.Texture2D):
        return False

    # 属性名是 "srgb"（不是 "s_rgb" 或 "SRGB"）。
    # UE 的属性名区分大小写，必须和引擎内部定义完全一致。
    texture.set_editor_property("srgb", srgb)

    # 压缩设置：枚举成员名必须全大写！
    # 常见错误：写成 TC_Default、TC_Normalmap 等驼峰形式，会报 AttributeError。
    # 正确写法：TC_DEFAULT、TC_NORMALMAP、TC_HDR、TC_VECTOR_DISPLACEMENTMAP。
    # 自查方法：在 PythonStub/unreal.py 中搜索 class TextureCompressionSettings 查看所有成员。
    compression_map = {
        "TC_Default": unreal.TextureCompressionSettings.TC_DEFAULT,
        "TC_Normalmap": unreal.TextureCompressionSettings.TC_NORMALMAP,
        "TC_HDR": unreal.TextureCompressionSettings.TC_HDR,
        "TC_VectorDisplacementmap": unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
    }
    if compression in compression_map:
        texture.set_editor_property(
            "compression_settings",
            compression_map[compression]
        )

    # 修改后保存——纹理修改不像材质那样需要 recompile，但需要 save 才会持久化
    unreal.EditorAssetLibrary.save_asset(texture_path)
    return True

# ─────────────────────────────────────────────────────────
# 4. 纹理类型自动配置
# ─────────────────────────────────────────────────────────

def auto_configure_textures(search_path="/Game"):
    """
    根据纹理名称自动配置压缩设置：
    - 法线贴图 (_N, _Normal) → TC_Normalmap, sRGB=False
    - 粗糙度/金属度 (_R, _M) → TC_Default, sRGB=False
    - 颜色贴图 (_D, _Diffuse, _BaseColor) → TC_Default, sRGB=True
    """
    textures = find_all_textures(search_path)

    # ScopedSlowTask 创建一个进度条对话框。
    # 参数：总工作量（这里是纹理数量）、描述文字。
    # 当处理大量资产时，显示进度条让用户知道程序在运行而不是卡死了。
    task = unreal.ScopedSlowTask(len(textures), "自动配置纹理...")

    # make_dialog 显示进度对话框。
    # can_cancel=True 允许用户点击取消按钮中断操作。
    task.make_dialog(True)

    configured = 0
    for tex_data in textures:
        # should_cancel 检查用户是否点了取消按钮。
        # 一旦取消，跳出循环停止处理。
        if task.should_cancel():
            break

        # enter_progress_frame 推进一步，并显示当前正在处理的纹理名。
        # work=1.0 表示完成 1 个工作单位。
        task.enter_progress_frame(1.0, tex_data.asset_name)
        name = tex_data.asset_name.lower()  # 转小写方便后缀匹配

        # 根据文件名后缀判断纹理类型——这是游戏行业的命名惯例：
        # _N/_Normal/_Nrm = 法线贴图，_R/_Roughness = 粗糙度，
        # _M/_Metallic = 金属度，_D/_Diffuse/_BaseColor = 颜色贴图。
        # 遵循命名规范可以让自动化工具有效工作。
        if any(suffix in name for suffix in ["_n", "_normal", "_nrm"]):
            configure_texture(
                tex_data.package_name,
                srgb=False,              # 法线贴图必须关闭 sRGB！
                compression="TC_Normalmap"  # 法线专用压缩
            )
            configured += 1
            unreal.log(f"  法线贴图: {name}")

        elif any(suffix in name for suffix in ["_r", "_rough", "_roughness",
                                                 "_m", "_metal", "_metallic",
                                                 "_ao", "_mask"]):
            configure_texture(
                tex_data.package_name,
                srgb=False,              # 数据贴图必须关闭 sRGB！
                compression="TC_Default"
            )
            configured += 1
            unreal.log(f"  数据贴图: {name}")

        elif any(suffix in name for suffix in ["_d", "_diffuse", "_albedo",
                                                 "_basecolor", "_color"]):
            configure_texture(
                tex_data.package_name,
                srgb=True,               # 颜色贴图需要开启 sRGB
                compression="TC_Default"
            )
            configured += 1
            unreal.log(f"  颜色贴图: {name}")

    unreal.log(f"已自动配置 {configured} 个纹理")

# ─────────────────────────────────────────────────────────
# 5. 纹理审计报告
# ─────────────────────────────────────────────────────────

def texture_audit(search_path="/Game"):
    """纹理质量审计"""
    textures = find_all_textures(search_path)

    report = {
        "total": len(textures),
        "non_power_of_two": [],  # 非 2 的幂分辨率
        "oversized": [],         # 超大纹理（> 4096）
        "undersized": [],        # 过小纹理（< 64）
        "no_srgb_color": [],     # 颜色贴图但未启用 sRGB
    }

    task = unreal.ScopedSlowTask(len(textures), "审计纹理...")
    task.make_dialog(True)

    for tex_data in textures:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, tex_data.asset_name)

        texture = unreal.EditorAssetLibrary.load_asset(tex_data.package_name)
        if not texture or not isinstance(texture, unreal.Texture2D):
            continue

        sx = texture.blueprint_get_size_x()
        sy = texture.blueprint_get_size_y()
        srgb = texture.get_editor_property("srgb")
        name = tex_data.asset_name.lower()

        # 检查分辨率是否为 2 的幂
        if not ((sx & (sx-1) == 0) and (sy & (sy-1) == 0)):
            report["non_power_of_two"].append(tex_data.asset_name)

        # 检查超大纹理（4K 以上）
        if sx > 4096 or sy > 4096:
            report["oversized"].append(f"{tex_data.asset_name} ({sx}x{sy})")

        # 检查过小纹理（64 以下）
        if sx < 64 or sy < 64:
            report["undersized"].append(f"{tex_data.asset_name} ({sx}x{sy})")

        # 颜色贴图检查：如果是颜色贴图但没开 sRGB，可能是配置错误
        if any(s in name for s in ["_d", "_diffuse", "_basecolor", "_albedo"]):
            if not srgb:
                report["no_srgb_color"].append(tex_data.asset_name)

    # 输出报告
    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"  纹理审计报告")
    unreal.log(f"{'=' * 50}")
    unreal.log(f"  总纹理数: {report['total']}")

    if report["non_power_of_two"]:
        unreal.log(f"\n  ⚠️ 非2的幂 ({len(report['non_power_of_two'])}):")
        for name in report["non_power_of_two"]:
            unreal.log(f"    {name}")

    if report["oversized"]:
        unreal.log(f"\n  ⚠️ 超大纹理 ({len(report['oversized'])}):")
        for name in report["oversized"]:
            unreal.log(f"    {name}")

    if report["no_srgb_color"]:
        unreal.log(f"\n  ⚠️ 颜色贴图未启用sRGB ({len(report['no_srgb_color'])}):")
        for name in report["no_srgb_color"]:
            unreal.log(f"    {name}")

    return report

# ─────────────────────────────────────────────────────────
# 6. 纹理导入辅助
# ─────────────────────────────────────────────────────────

def import_texture_pack(source_folder, destination="/Game/Textures",
                         auto_configure=True):
    """
    导入一个纹理包

    参数:
        source_folder: 包含纹理文件的文件夹
        destination: UE 项目中的目标路径
        auto_configure: 导入后自动配置
    """
    if not os.path.isdir(source_folder):
        unreal.log_error(f"文件夹不存在: {source_folder}")
        return []

    # UE 支持的纹理格式（按推荐程度排序）
    extensions = [".png", ".tga", ".jpg", ".jpeg", ".bmp", ".exr"]

    # 扫描文件夹中符合条件的文件
    files = [
        os.path.join(source_folder, f)
        for f in os.listdir(source_folder)
        if os.path.splitext(f)[1].lower() in extensions
    ]

    if not files:
        unreal.log_warning("没有找到纹理文件")
        return []

    unreal.log(f"找到 {len(files)} 个纹理文件")

    # 批量导入的核心：AssetImportTask 对象列表。
    # 每个 AssetImportTask 代表一个文件的导入任务。
    # 填好任务属性后，一次性提交给 import_asset_tasks 批量处理，
    # 比逐个导入效率高很多（减少编辑器开销）。
    tasks = []
    for file_path in files:
        task = unreal.AssetImportTask()
        task.filename = file_path                   # 源文件的磁盘路径
        task.destination_path = destination           # 导入到 UE 中的目标目录
        task.destination_name = os.path.splitext(os.path.basename(file_path))[0]  # 资产名（不含扩展名）
        task.replace_existing = True                 # 如果同名资产已存在则覆盖
        task.automated = True                        # 自动导入，不弹出导入选项对话框
        task.save = True                             # 导入后自动保存
        tasks.append(task)

    # import_asset_tasks 一次性执行所有导入任务
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks(tasks)

    # 汇总导入结果：
    # 每个 task 的 imported_object_paths 属性存储了导入后生成的资产路径。
    # 一个源文件可能生成多个资产（比如多通道 EXR 纹理）。
    imported = []
    for task in tasks:
        imported.extend(task.imported_object_paths)

    unreal.log(f"已导入 {len(imported)} 个纹理")

    # 自动配置：根据纹理名称后缀设置 sRGB 和压缩方式
    if auto_configure:
        for path in imported:
            auto_configure_textures(os.path.dirname(path))

    return imported

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 纹理审计
# texture_audit("/Game")

# 自动配置
# auto_configure_textures("/Game/Textures")

# 导入纹理包
# import_texture_pack("C:/Textures/Pack1", "/Game/Textures/Pack1")

unreal.log("材质与纹理第3课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写工具：找出所有分辨率超过 4K 的纹理并降低到 4K
# 2. 创建一个纹理命名检查器
# 3. 实现自动创建材质+材质实例的管线
#    （导入纹理 → 创建材质 → 创建实例 → 分配给 Actor）
# 4. 编写纹理图集打包工具（将多个小纹理合并为一张）
