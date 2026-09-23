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

习题可能用到的 API：
  unreal.log(arg: Any) -> None  —— 输出信息到输出日志
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建资产目录
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产对象
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出目录下所有资产路径
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  unreal.MaterialEditingLibrary.create_material_expression(material: Material, expression_class: Class, node_pos_x: int = 0, node_pos_y: int = 0) -> MaterialExpression  —— 在材质中添加表达式节点
  unreal.MaterialEditingLibrary.connect_material_property(from_expression: MaterialExpression, from_output_name: str, property_: MaterialProperty) -> bool  —— 连接节点输出到材质属性输入
  unreal.MaterialEditingLibrary.recompile_material(material: Material) -> Array[str]  —— 重新编译材质
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
    # make_directory 会自动创建多级目录，类似 mkdir -p。
    # 如果目录已存在则不报错，返回 True。这是创建资产前的标准操作——
    # 不先建目录的话，create_asset 会因为目标路径不存在而失败。
    unreal.EditorAssetLibrary.make_directory(destination)

    # AssetToolsHelpers.get_asset_tools() 返回 UE 编辑器的资产工具单例，
    # 所有资产创建/导入操作都需要通过它来完成。
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # MaterialFactoryNew 是材质资产的工厂对象。
    # UE 创建资产的模式是「工厂模式」：先创建工厂，再由工厂生产资产。
    # 不同资产类型需要不同的 Factory（如 TextureFactory、BlueprintFactory 等）。
    factory = unreal.MaterialFactoryNew()

    # create_asset 参数：资产名、包路径、资产类型、工厂对象。
    # 返回值是创建好的 UObject，如果同名资产已存在且 overwrite_existing=False（默认），
    # 则会返回 None。所以创建前一定要 make_directory 保证路径正确。
    material = asset_tools.create_asset(
        name,
        destination,
        unreal.Material,  # 资产类型——材质类
        factory
    )

    if material:
        path = f"{destination}/{name}"
        unreal.log(f"已创建材质: {path}")
        # 新创建的资产在内存中是「脏」的（dirty），需要 save_asset 才会写入磁盘。
        # 不保存的话，关闭编辑器后资产会丢失。
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
    # 先调用上面的函数创建一个空白材质——代码复用的好习惯
    material = create_basic_material(name, destination)
    if not material:
        return None

    # Constant3Vector 节点：输出一个三维向量（RGB 三通道）。
    # 在材质图中，这就是一个"常量颜色"节点。
    # 参数 (material, 表达式类, X坐标, Y坐标)：
    #   X/Y 坐标决定了节点在材质编辑器图表中的位置（像素单位），
    #   负数在左边，正数在右边，这只是编辑器里的视觉位置，不影响运行时逻辑。
    color_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant3Vector,  # 三维常量节点（颜色）
        -400,  # X 位置（放在左侧，方便连线）
        0      # Y 位置
    )

    # set_editor_property 用于修改对象在编辑器中的属性。
    # "constant" 是 Constant3Vector 节点存储颜色值的属性名。
    # 注意：颜色必须用 unreal.LinearColor 对象，不能直接传元组。
    # LinearColor 的四个分量范围都是 0.0~1.0，最后一个 a 是透明度。
    color_node.set_editor_property(
        "constant",
        unreal.LinearColor(color[0], color[1], color[2], 1.0)
    )

    # connect_material_property 将节点的输出引脚连接到材质的某个属性。
    # 三个参数：(源节点, 源输出引脚名, 目标材质属性)。
    # Constant3Vector 的输出引脚名是 "RGB"（也可以用 "R"、"G"、"B" 单独取通道）。
    # MP_BASE_COLOR 是材质的「基础颜色」属性——PBR 材质最核心的输入。
    unreal.MaterialEditingLibrary.connect_material_property(
        color_node,
        "RGB",                        # 源输出引脚名
        unreal.MaterialProperty.MP_BASE_COLOR  # 目标：基础颜色
    )

    # recompile_material 触发材质重新编译。
    # 材质编辑器中的每次修改都需要编译才能在视口中生效。
    # 编译相当于把材质图节点网络翻译成 GPU 可执行的着色器代码。
    unreal.MaterialEditingLibrary.recompile_material(material)

    # 保存到磁盘
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
    # load_asset 加载指定路径的资产。
    # 注意：路径必须是 UE 资产路径（以 /Game 开头），不是磁盘文件路径。
    # 返回的是 UObject 对象，如果路径无效或资产不存在则返回 None。
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if not texture:
        unreal.log_error(f"无法加载纹理: {texture_path}")
        return None

    material = create_basic_material(name, destination)
    if not material:
        return None

    # TextureSample 节点：采样一张纹理并输出颜色值。
    # 它有一个 "texture" 属性需要设置为实际的 Texture2D 对象，
    # 还有一个 "sampler_type" 属性决定采样方式（通常保持默认即可）。
    tex_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSample,  # 纹理采样节点
        -400,
        0
    )

    # 把加载好的纹理资产赋给节点的 texture 属性
    tex_node.set_editor_property("texture", texture)

    # 将纹理采样结果的 RGB 输出连接到基础颜色
    unreal.MaterialEditingLibrary.connect_material_property(
        tex_node,
        "RGB",
        unreal.MaterialProperty.MP_BASE_COLOR
    )

    # 编译并保存——这是创建材质的标准收尾操作
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

    # Constant 节点：输出一个浮点数（单通道）。
    # 常用于控制 Roughness、Metallic 等标量属性。
    const_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant,  # 单值常量节点
        -400, -200  # 位置放在上方
    )
    # "r" 属性存储常量值（虽然叫 r，但它就是单通道的值）
    const_node.set_editor_property("r", 0.5)

    # ScalarParameter：标量参数节点。
    # 与 Constant 的区别：参数可以在「材质实例」中被外部修改，
    # 而 Constant 是写死的、不可在实例中调节的。
    # 这是材质系统的核心概念：基础材质定义参数 → 材质实例调节参数。
    scalar_param = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,  # 标量参数节点
        -400, -100
    )
    # parameter_name 是参数的显示名，在材质实例编辑器中会看到这个名字
    scalar_param.set_editor_property("parameter_name", "Roughness")
    # default_value 是默认值，如果材质实例不覆盖则使用此值
    scalar_param.set_editor_property("default_value", 0.5)

    # VectorParameter：向量参数节点，通常用来表示颜色。
    # 可以在材质实例中通过颜色选择器调节。
    vector_param = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionVectorParameter,  # 向量参数节点
        -400, 100
    )
    vector_param.set_editor_property("parameter_name", "TintColor")
    # 默认白色（1,1,1,1），在材质实例中可以改成任意颜色
    vector_param.set_editor_property(
        "default_value",
        unreal.LinearColor(1.0, 1.0, 1.0, 1.0)
    )

    # Multiply 节点：将两个输入相乘。
    # 常见用途：用颜色参数乘以纹理颜色，实现"着色纹理"效果。
    # 它有两个输入引脚 "A" 和 "B"，一个输出引脚 "Result"。
    multiply = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionMultiply,  # 乘法节点
        -200, 0
    )

    # connect_material_expressions 连接两个表达式节点之间的引脚。
    # 四个参数：(源节点, 源输出引脚名, 目标节点, 目标输入引脚名)。
    # Constant 节点的输出引脚名是 "R"（单通道），
    # Multiply 节点的输入引脚名是 "A"（第一个乘数）和 "B"（第二个乘数）。
    # 注意：输出引脚名和输入引脚名都是字符串，写错会静默失败不报错！
    unreal.MaterialEditingLibrary.connect_material_expressions(
        const_node,   # 源节点
        "R",          # 源输出引脚名（Constant 只有一个输出 "R"）
        multiply,     # 目标节点
        "A"           # 目标输入引脚名（Multiply 的第一个输入）
    )

    # 【修改前】只连了 const -> multiply.A，另外三个节点全是"孤岛"：
    #   VectorParameter 没接、Multiply 的结果也没接到材质输出，等于白建。
    # 把颜色参数接到 Multiply 的第二个输入 B：
    #   输出引脚名传 "" 表示"该节点的默认输出"（Epic 官方 Python 示例的写法）。
    unreal.MaterialEditingLibrary.connect_material_expressions(
        vector_param,  # 源节点：颜色参数
        "",            # 默认输出（VectorParameter 是一个 4 分量向量）
        multiply,      # 目标节点
        "B"            # Multiply 的第二个输入
    )

    # 最后一步最关键：把 Multiply 的结果接到材质的 Base Color 属性上。
    # 只有连到 MaterialProperty，材质才会有实际效果。
    connected = unreal.MaterialEditingLibrary.connect_material_property(
        multiply,                            # 源节点
        "",                                  # 默认输出
        unreal.MaterialProperty.MP_BASE_COLOR  # 目标材质属性
    )
    if not connected:
        unreal.log_warning("连接 Base Color 失败，请在材质编辑器里手动检查")

    unreal.log(f"已添加材质节点（共 {len(unreal.MaterialEditingLibrary.get_material_expressions(material))} 个）")
    # 每次修改材质图后都要重新编译，否则视口不会更新
    unreal.MaterialEditingLibrary.recompile_material(material)

# ─────────────────────────────────────────────────────────
# 5. 创建常用材质模板
# ─────────────────────────────────────────────────────────

def create_pbr_material(name, destination="/Game/Materials"):
    """
    创建标准 PBR 材质模板
    包含 BaseColor, Normal, Roughness, Metallic 参数

    PBR（基于物理的渲染）是现代游戏引擎的标准材质模型。
    四个核心属性：
      - BaseColor：物体的基础颜色
      - Normal：表面凹凸细节（法线贴图）
      - Roughness：表面粗糙度（0=镜面，1=磨砂）
      - Metallic：金属度（0=非金属，1=金属）
    """
    material = create_basic_material(name, destination)
    if not material:
        return None

    # TextureSampleParameter2D：带参数名的纹理采样节点。
    # 与普通 TextureSample 的区别：它可以在材质实例中替换纹理！
    # 这样一个基础材质就能派生出无数纹理变体。
    base_color_tex = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSampleParameter2D,  # 可参数化的纹理采样
        -600, -200
    )
    base_color_tex.set_editor_property("parameter_name", "BaseColorTexture")
    unreal.MaterialEditingLibrary.connect_material_property(
        base_color_tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    )

    # Normal（法线）纹理节点：
    # 法线贴图存储表面凹凸信息，让低面数模型看起来有高面数的细节。
    # 这里用普通 TextureSample 而不是参数化版本（教学简化），
    # 实际项目中通常也用 TextureSampleParameter2D 以便实例中替换。
    normal_tex = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionTextureSample,  # 普通纹理采样（不可实例替换）
        -600, 0
    )
    # 法线贴图的输出要连到 MP_NORMAL 属性，引擎会自动将其解释为法线数据
    unreal.MaterialEditingLibrary.connect_material_property(
        normal_tex, "RGB", unreal.MaterialProperty.MP_NORMAL
    )

    # Roughness 标量参数：控制表面粗糙度
    # 0.0 = 完全光滑（镜面反射），1.0 = 完全粗糙（漫反射）
    roughness = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,
        -400, 200
    )
    roughness.set_editor_property("parameter_name", "Roughness")
    roughness.set_editor_property("default_value", 0.5)  # 默认中等粗糙度
    # 标量参数连接到 MP_ROUGHNESS 属性
    # 注意：ScalarParameter 只有一个输出引脚 "Result"（默认），可以省略不写
    unreal.MaterialEditingLibrary.connect_material_property(
        roughness, "RGB", unreal.MaterialProperty.MP_ROUGHNESS
    )

    # Metallic 标量参数：控制金属度
    # 0.0 = 非金属（塑料、木头等），1.0 = 金属（钢铁、铜等）
    # 注意：金属和非金属的渲染方式完全不同，中间值（0.5）在 PBR 中是不物理正确的！
    metallic = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionScalarParameter,
        -400, 300
    )
    metallic.set_editor_property("parameter_name", "Metallic")
    metallic.set_editor_property("default_value", 0.0)  # 默认非金属
    unreal.MaterialEditingLibrary.connect_material_property(
        metallic, "RGB", unreal.MaterialProperty.MP_METALLIC
    )

    # 编译材质——所有节点连接完成后必须编译
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
    # isinstance 检查确保加载的确实是 Material 类型，
    # 避免后续操作在错误类型的资产上执行
    if not material or not isinstance(material, unreal.Material):
        unreal.log_error(f"无法加载材质: {material_path}")
        return

    unreal.log(f"\n材质: {material.get_name()}")
    unreal.log(f"路径: {material_path}")

    # get_material_expressions 获取材质中所有表达式节点的列表。
    # 注意：Material 对象本身没有 "expressions" 属性，
    # 必须通过 MaterialEditingLibrary 的静态方法来获取。
    # 返回的是 MaterialExpression 数组，每个元素代表材质图中的一个节点。
    expressions = unreal.MaterialEditingLibrary.get_material_expressions(material)
    unreal.log(f"节点数: {len(expressions)}")

    for expr in expressions:
        # type(expr).__name__ 获取节点的类名，如 MaterialExpressionConstant3Vector
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
