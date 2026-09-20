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

本课可能用到的 API：
  unreal.log(arg: Any) -> None  —— 输出信息到输出日志
  unreal.log_error(arg: Any) -> None  —— 输出错误到输出日志
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建资产目录
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产对象
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例
  unreal.AssetTools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object  —— 用工厂创建新资产
  unreal.MaterialFactoryNew()  —— 创建材质资产的工厂对象
  unreal.MaterialEditingLibrary.create_material_expression(material: Material, expression_class: Class, node_pos_x: int = 0, node_pos_y: int = 0) -> MaterialExpression  —— 在材质中添加表达式节点
  unreal.MaterialEditingLibrary.connect_material_property(from_expression: MaterialExpression, from_output_name: str, property_: MaterialProperty) -> bool  —— 连接节点输出到材质属性输入
  unreal.MaterialEditingLibrary.connect_material_expressions(from_expression: MaterialExpression, from_output_name: str, to_expression: MaterialExpression, to_input_name: str) -> bool  —— 连接两个表达式节点
  unreal.MaterialEditingLibrary.recompile_material(material: Material) -> Array[str]  —— 重新编译（生成）材质
  obj.set_editor_property(name: str, value: object, notify_mode: PropertyAccessChangeNotifyMode = PropertyAccessChangeNotifyMode.DEFAULT) -> None  —— 设置对象编辑器属性
  obj.get_editor_property(name: str) -> object  —— 读取对象编辑器属性
  unreal.LinearColor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 0.0) -> None  —— 构造 0-1 范围线性颜色
  unreal.MaterialExpressionConstant3Vector / Constant / ScalarParameter / VectorParameter / Multiply / TextureSample 等  —— 作为 expression_class 传入的材质节点类
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
    # 【修改前】connect_material_property(color_node, "BaseColor") 只有 2 个参数。
    # 【问题分析】正确签名是 3 参 (from_expression, from_output_name, property_)，
    #   Constant3Vector 节点的输出引脚名是 "RGB"，目标材质属性用 MaterialProperty.MP_BASE_COLOR。
    unreal.MaterialEditingLibrary.connect_material_property(
        color_node,
        "RGB",
        unreal.MaterialProperty.MP_BASE_COLOR
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
        "RGB",
        unreal.MaterialProperty.MP_BASE_COLOR
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
    # 【修改前】connect_material_expressions(const_node, multiply, 0) 参数错位。
    # 【问题分析】正确 4 参签名是
    #   (from_expression, from_output_name, to_expression, to_input_name)：
    #   第 2 参是输出引脚名字符串（Constant 单通道输出名是 "R"），
    #   第 3 参是目标表达式对象（Multiply 的第一个输入引脚是 "A"）。
    unreal.MaterialEditingLibrary.connect_material_expressions(
        const_node,   # 输出节点
        "R",          # 输出引脚名
        multiply,     # 输入节点
        "A"           # 输入引脚名
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
        base_color_tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    )

    # Normal 纹理节点
    # 【修改前】unreal.MaterialExpressionTextureSampleParameterNormal
    # 【问题分析】stub 中不存在该节点类。普通采样改用
    #   MaterialExpressionTextureSample（普通 TextureSample 没有 parameter_name
    #   参数属性，也不作为"材质实例可调参数"，这里仅演示 Normal 连线）。
    normal_tex = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSample,
        -600, 0
    )
    unreal.MaterialEditingLibrary.connect_material_property(
        normal_tex, "RGB", unreal.MaterialProperty.MP_NORMAL
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
        roughness, "RGB", unreal.MaterialProperty.MP_ROUGHNESS
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
        metallic, "RGB", unreal.MaterialProperty.MP_METALLIC
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
    # 【修改前】material.get_editor_property("expressions")
    # 【问题分析】Material 类没有 expressions 属性。
    #   应使用 MaterialEditingLibrary.get_material_expressions(material) 读取。
    expressions = unreal.MaterialEditingLibrary.get_material_expressions(material)
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
