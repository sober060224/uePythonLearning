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
=============================================================
"""

import unreal
import os

# ─────────────────────────────────────────────────────────
# 1. 查找项目中的纹理
# ─────────────────────────────────────────────────────────

def find_all_textures(search_path="/Game"):
    """查找项目中所有纹理"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    textures = []

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
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

    if not isinstance(texture, unreal.Texture2D):
        unreal.log_warning(f"不是 Texture2D: {texture_path}")
        return

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"纹理: {texture.get_name()}")
    unreal.log(f"路径: {texture_path}")

    # 分辨率
    size_x = texture.get_editor_property("size_x")
    size_y = texture.get_editor_property("size_y")
    unreal.log(f"分辨率: {size_x} x {size_y}")

    # sRGB
    srgb = texture.get_editor_property("s_rgb")
    unreal.log(f"sRGB: {srgb}")

    # 压缩设置
    compression = texture.get_editor_property("compression_settings")
    unreal.log(f"压缩设置: {compression}")

    # LOD Group
    lod_group = texture.get_editor_property("lod_group")
    unreal.log(f"LOD Group: {lod_group}")

    # 是否是 2 的幂
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

    texture.set_editor_property("s_rgb", srgb)

    # 压缩设置
    compression_map = {
        "TC_Default": unreal.TextureCompressionSettings.TC_Default,
        "TC_Normalmap": unreal.TextureCompressionSettings.TC_Normalmap,
        "TC_HDR": unreal.TextureCompressionSettings.TC_HDR,
        "TC_VectorDisplacementmap": unreal.TextureCompressionSettings.TC_VectorDisplacementmap,
    }
    if compression in compression_map:
        texture.set_editor_property(
            "compression_settings",
            compression_map[compression]
        )

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

    task = unreal.ScopedSlowTask(len(textures), "自动配置纹理...")
    task.make_dialog(True)

    configured = 0
    for tex_data in textures:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, tex_data.asset_name)
        name = tex_data.asset_name.lower()

        if any(suffix in name for suffix in ["_n", "_normal", "_nrm"]):
            configure_texture(
                tex_data.package_name,
                srgb=False,
                compression="TC_Normalmap"
            )
            configured += 1
            unreal.log(f"  法线贴图: {name}")

        elif any(suffix in name for suffix in ["_r", "_rough", "_roughness",
                                                 "_m", "_metal", "_metallic",
                                                 "_ao", "_mask"]):
            configure_texture(
                tex_data.package_name,
                srgb=False,
                compression="TC_Default"
            )
            configured += 1
            unreal.log(f"  数据贴图: {name}")

        elif any(suffix in name for suffix in ["_d", "_diffuse", "_albedo",
                                                 "_basecolor", "_color"]):
            configure_texture(
                tex_data.package_name,
                srgb=True,
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
        "non_power_of_two": [],
        "oversized": [],     # > 4096
        "undersized": [],    # < 64
        "no_srgb_color": [], # 颜色贴图但未启用 sRGB
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

        sx = texture.get_editor_property("size_x")
        sy = texture.get_editor_property("size_y")
        srgb = texture.get_editor_property("s_rgb")
        name = tex_data.asset_name.lower()

        # 检查分辨率
        if not ((sx & (sx-1) == 0) and (sy & (sy-1) == 0)):
            report["non_power_of_two"].append(tex_data.asset_name)

        if sx > 4096 or sy > 4096:
            report["oversized"].append(f"{tex_data.asset_name} ({sx}x{sy})")

        if sx < 64 or sy < 64:
            report["undersized"].append(f"{tex_data.asset_name} ({sx}x{sy})")

        # 颜色贴图检查
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

    # 支持的格式
    extensions = [".png", ".tga", ".jpg", ".jpeg", ".bmp", ".exr"]

    files = [
        os.path.join(source_folder, f)
        for f in os.listdir(source_folder)
        if os.path.splitext(f)[1].lower() in extensions
    ]

    if not files:
        unreal.log_warning("没有找到纹理文件")
        return []

    unreal.log(f"找到 {len(files)} 个纹理文件")

    # 批量导入
    tasks = []
    for file_path in files:
        task = unreal.AssetImportTask()
        task.filename = file_path
        task.destination_path = destination
        task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
        task.replace_existing = True
        task.automated = True
        task.save = True
        tasks.append(task)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks(tasks)

    # 汇总导入的资产
    imported = []
    for task in tasks:
        imported.extend(task.imported_object_paths)

    unreal.log(f"已导入 {len(imported)} 个纹理")

    # 自动配置
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
