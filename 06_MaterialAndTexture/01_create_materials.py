"""
=============================================================
材质与纹理 第1课：创建和编辑材质
=============================================================

学习目标：
  - 通过 Python 创建材质资产
  - 添加材质表达式节点
  - 连接节点构建材质图

核心类：
  - unreal.Material - 材质资产
  - unreal.MaterialEditingLibrary - 材质编辑工具
  - unreal.MaterialExpression* - 各种材质节点
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 创建基本材质
# ─────────────────────────────────────────────────────────

def create_basic_material(name, destination="/Game/Materials"):
    """
    创建一个基本的材质资产

    参数:
        name: 材质名称 (如 "M_BasicRed")
        destination: 保存路径
    """
    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialFactoryNew()

    material = asset_tools.create_asset(
        name,
        destination,
        unreal.Material,
        factory
    )

    if material:
        path = f"{destination}/{name}"
        unreal.log(f"已创建材质: {path}")
        unreal.EditorAssetLibrary.save_asset(path)
        return material

    return None

# ─────────────────────────────────────────────────────────
# 2. 创建纯色材质
# ─────────────────────────────────────────────────────────

def create_solid_color_material(name, color, destination="/Game/Materials"):
    """
    创建一个纯色材质

    参数:
        name: 材质名称
        color: (R, G, B) 颜色元组，值范围 0-1
        destination: 保存路径
    """
    # 创建材质
    material = create_basic_material(name, destination)
    if not material:
        return None

    # 创建 Constant3Vector 节点（颜色值）
    color_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant3Vector,
        -400,  # X 位置
        0      # Y 位置
    )

    # 设置颜色值
    color_node.set_editor_property(
        "constant",
        unreal.LinearColor(color[0], color[1], color[2], 1.0)
    )

    # 连接到 Base Color
    unreal.MaterialEditingLibrary.connect_material_property(
        color_node,
        "BaseColor"
    )

    # 编译材质
    unreal.MaterialEditingLibrary.recompile_material(material)

    # 保存
    path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(f"已创建纯色材质: {name} 颜色={color}")

    return material

# ─────────────────────────────────────────────────────────
# 3. 创建带纹理的材质
# ─────────────────────────────────────────────────────────

def create_textured_material(name, texture_path, destination="/Game/Materials"):
    """
    创建使用纹理的材质

    参数:
        name: 材质名称
        texture_path: 纹理资产路径
        destination: 保存路径
    """
    # 加载纹理
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if not texture:
        unreal.log_error(f"无法加载纹理: {texture_path}")
        return None

    # 创建材质
    material = create_basic_material(name, destination)
    if not material:
        return None

    # 创建 TextureSample 节点
    tex_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSample,
        -400,
        0
    )

    # 设置纹理
    tex_node.set_editor_property("texture", texture)

    # 连接到 Base Color
    unreal.MaterialEditingLibrary.connect_material_property(
        tex_node,
        "BaseColor"
    )

    # 编译并保存
    unreal.MaterialEditingLibrary.recompile_material(material)
    path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(path)

    unreal.log(f"已创建纹理材质: {name}")
    return material

# ─────────────────────────────────────────────────────────
# 4. 添加各种材质节点
# ─────────────────────────────────────────────────────────

def add_material_nodes(material):
    """演示添加各种材质表达式节点"""

    # 常量节点
    const_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant,
        -400, -200
    )
    const_node.set_editor_property("r", 0.5)

    # 标量参数（可在材质实例中调节）
    scalar_param = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,
        -400, -100
    )
    scalar_param.set_editor_property("parameter_name", "Roughness")
    scalar_param.set_editor_property("default_value", 0.5)

    # 向量参数
    vector_param = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionVectorParameter,
        -400, 100
    )
    vector_param.set_editor_property("parameter_name", "TintColor")
    vector_param.set_editor_property(
        "default_value",
        unreal.LinearColor(1.0, 1.0, 1.0, 1.0)
    )

    # 乘法节点
    multiply = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionMultiply,
        -200, 0
    )

    # 连接节点
    # connect_material_expressions(output_of_node, input_of_node)
    unreal.MaterialEditingLibrary.connect_material_expressions(
        const_node,   # 输出
        multiply,     # 输入
        0             # 输入索引
    )

    unreal.log("已添加材质节点")
    unreal.MaterialEditingLibrary.recompile_material(material)

# ─────────────────────────────────────────────────────────
# 5. 创建常用材质模板
# ─────────────────────────────────────────────────────────

def create_pbr_material(name, destination="/Game/Materials"):
    """
    创建标准 PBR 材质模板
    包含 BaseColor, Normal, Roughness, Metallic 参数
    """
    material = create_basic_material(name, destination)
    if not material:
        return None

    # BaseColor 纹理参数
    base_color_tex = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSampleParameter2D,
        -600, -200
    )
    base_color_tex.set_editor_property("parameter_name", "BaseColorTexture")
    unreal.MaterialEditingLibrary.connect_material_property(
        base_color_tex, "BaseColor"
    )

    # Normal 纹理参数
    normal_tex = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSampleParameterNormal,
        -600, 0
    )
    normal_tex.set_editor_property("parameter_name", "NormalTexture")
    unreal.MaterialEditingLibrary.connect_material_property(
        normal_tex, "Normal"
    )

    # Roughness 标量参数
    roughness = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,
        -400, 200
    )
    roughness.set_editor_property("parameter_name", "Roughness")
    roughness.set_editor_property("default_value", 0.5)
    unreal.MaterialEditingLibrary.connect_material_property(
        roughness, "Roughness"
    )

    # Metallic 标量参数
    metallic = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,
        -400, 300
    )
    metallic.set_editor_property("parameter_name", "Metallic")
    metallic.set_editor_property("default_value", 0.0)
    unreal.MaterialEditingLibrary.connect_material_property(
        metallic, "Metallic"
    )

    unreal.MaterialEditingLibrary.recompile_material(material)

    path = f"{destination}/{name}"
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(f"已创建 PBR 材质模板: {name}")
    return material

# ─────────────────────────────────────────────────────────
# 6. 修改现有材质
# ─────────────────────────────────────────────────────────

def inspect_material(material_path):
    """检查材质的节点结构"""
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material or not isinstance(material, unreal.Material):
        unreal.log_error(f"无法加载材质: {material_path}")
        return

    unreal.log(f"\n材质: {material.get_name()}")
    unreal.log(f"路径: {material_path}")

    # 获取表达式列表
    expressions = material.get_editor_property("expressions")
    unreal.log(f"节点数: {len(expressions)}")

    for expr in expressions:
        expr_type = type(expr).__name__
        unreal.log(f"  [{expr_type}]")

    return expressions

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 创建纯色材质
# create_solid_color_material("M_TestRed", (0.8, 0.1, 0.1))
# create_solid_color_material("M_TestGreen", (0.1, 0.8, 0.1))
# create_solid_color_material("M_TestBlue", (0.1, 0.1, 0.8))

# 创建 PBR 模板
# create_pbr_material("M_PBR_Template")

unreal.log("材质与纹理第1课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一组交通灯材质（红、黄、绿）
# 2. 创建一个发光材质（使用 EmissiveColor）
# 3. 创建一个材质，使用世界位置偏移实现顶点动画
# 4. 批量为所有纹理创建对应的材质
