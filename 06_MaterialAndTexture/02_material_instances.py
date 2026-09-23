"""
=============================================================
材质与纹理 第2课：材质实例和参数控制
=============================================================

学习目标：
  - 创建材质实例 (Material Instance)
  - 修改实例参数（标量、向量、纹理）
  - 批量创建和管理材质实例

材质实例的优势：
  - 不需要重新编译材质（实时预览）
  - 非技术美术也能调整参数
  - 一个基础材质可以派生出无数变体

习题可能用到的 API：
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产对象
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建资产目录
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出目录下所有资产路径
  unreal.MaterialEditingLibrary.set_material_instance_parent(instance: MaterialInstanceConstant, new_parent: MaterialInterface) -> None  —— 设置材质实例的父材质
  unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: float) -> bool  —— 设置标量参数
  unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: LinearColor) -> bool  —— 设置向量（颜色）参数
  unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: Texture) -> bool  —— 设置纹理参数值
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 创建材质实例
# ─────────────────────────────────────────────────────────

def create_material_instance(parent_material_path, name,
                              destination="/Game/Materials/Instances"):
    """
    创建材质实例

    参数:
        parent_material_path: 父材质路径
        name: 实例名称
        destination: 保存路径
    """
    # 加载父材质——材质实例必须绑定一个父材质才能工作。
    # 父材质定义了参数（颜色、粗糙度等），实例只负责调参数值。
    parent_material = unreal.EditorAssetLibrary.load_asset(parent_material_path)
    if not parent_material:
        unreal.log_error(f"无法加载父材质: {parent_material_path}")
        return None

    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # MaterialInstanceConstantFactoryNew 是材质实例的工厂。
    # 注意和 MaterialFactoryNew 的区别——后者创建基础材质，前者创建材质实例。
    factory = unreal.MaterialInstanceConstantFactoryNew()

    # create_asset 创建资产，类型是 MaterialInstanceConstant（材质实例类）。
    # MaterialInstanceConstant 是运行时材质实例的编辑器表示。
    instance = asset_tools.create_asset(
        name,
        destination,
        unreal.MaterialInstanceConstant,  # 材质实例类
        factory
    )

    if instance:
        # 重要：父材质不能在 Factory 中设置，必须在创建后单独绑定！
        # set_material_instance_parent 是唯一正确的设置父材质方式。
        # 常见错误：尝试在 factory 上 set_editor_property("initial_parent", ...)，
        # 但 MaterialInstanceConstantFactoryNew 根本没有这个属性。
        unreal.MaterialEditingLibrary.set_material_instance_parent(
            instance, parent_material
        )
        path = f"{destination}/{name}"
        unreal.EditorAssetLibrary.save_asset(path)
        unreal.log(f"已创建材质实例: {path}")
        return instance

    return None

# ─────────────────────────────────────────────────────────
# 2. 修改材质实例参数
# ─────────────────────────────────────────────────────────

def set_scalar_parameter(instance, param_name, value):
    """设置标量参数（浮点数，如 Roughness、Metallic）"""
    # 注意：不能直接在 instance 对象上调用 set_scalar_parameter_value！
    # 材质实例的参数修改必须通过 MaterialEditingLibrary 的静态方法。
    # 这是 UE Python API 的一个常见"陷阱"——很多操作需要通过 Library 类调用，
    # 而不是直接在 UObject 上调用。
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        instance, param_name, value
    )
    unreal.log(f"  标量 {param_name} = {value}")

def set_vector_parameter(instance, param_name, color):
    """
    设置向量参数（颜色）

    参数:
        color: (R, G, B, A) 或 (R, G, B) 元组，值范围 0-1
    """
    # 支持 3 分量和 4 分量两种传入方式
    if len(color) == 3:
        color = (*color, 1.0)  # 补上不透明度 1.0

    # 向量参数必须用 unreal.LinearColor 对象传递。
    # UE 内部统一使用线性颜色空间（0-1 浮点数），不使用 0-255 整数。
    linear_color = unreal.LinearColor(color[0], color[1], color[2], color[3])
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        instance, param_name, linear_color
    )
    unreal.log(f"  向量 {param_name} = {color}")

def set_texture_parameter(instance, param_name, texture_path):
    """设置纹理参数"""
    # 纹理参数允许在材质实例中替换不同的纹理。
    # 比如一个"武器材质"可以有 BaseColor 参数，不同武器传入不同纹理。
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if not texture:
        unreal.log_error(f"无法加载纹理: {texture_path}")
        return False

    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
        instance, param_name, texture
    )
    unreal.log(f"  纹理 {param_name} = {texture_path}")
    return True

def set_static_switch(instance, param_name, value):
    """设置静态开关参数（布尔值，控制材质分支）"""
    # 静态开关在编译时确定，运行时不可更改。
    # 常用于"开/关"某种效果（如是否使用法线贴图、是否启用自发光等）。
    # 与普通标量/向量参数不同，静态开关会改变材质的着色器结构。
    unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(
        instance, param_name, value
    )
    unreal.log(f"  开关 {param_name} = {value}")

# ─────────────────────────────────────────────────────────
# 3. 读取材质实例参数
# ─────────────────────────────────────────────────────────

def list_instance_parameters(instance_path):
    """列出材质实例的所有可修改参数"""
    instance = unreal.EditorAssetLibrary.load_asset(instance_path)
    if not instance:
        unreal.log_error(f"无法加载材质实例: {instance_path}")
        return

    unreal.log(f"\n材质实例参数: {instance.get_name()}")
    unreal.log("-" * 40)

    # 通过 get_editor_property("parent") 获取父材质引用。
    # 材质实例的 parent 属性存储了它继承的父材质。
    # 如果 parent 是 None，说明实例没有正确绑定父材质。
    parent = instance.get_editor_property("parent")
    if parent:
        unreal.log(f"父材质: {parent.get_name()}")

    # 列出参数：MaterialEditingLibrary 能直接查询参数名，不用打开材质编辑器。
    # 【修改前】这里用 hasattr(instance, 'get_scalar_parameter_value') 做判断，
    #   但 UE 的 Python 包装对象对"未知属性"也返回 True —— 判断永远成立，等于没写。
    scalar_names = unreal.MaterialEditingLibrary.get_scalar_parameter_names(instance)
    vector_names = unreal.MaterialEditingLibrary.get_vector_parameter_names(instance)
    if scalar_names:
        unreal.log(f"  标量参数: {', '.join(str(n) for n in scalar_names)}")
    if vector_names:
        unreal.log(f"  向量参数: {', '.join(str(n) for n in vector_names)}")
    if not scalar_names and not vector_names:
        unreal.log("  （该实例没有覆盖参数，全部继承父材质）")

    return instance

# ─────────────────────────────────────────────────────────
# 4. 批量创建材质实例变体
# ─────────────────────────────────────────────────────────

def create_color_variants(parent_material_path, base_name,
                           colors, destination="/Game/Materials/Instances"):
    """
    从父材质创建一组颜色变体

    参数:
        parent_material_path: 父材质路径
        base_name: 基础名称
        colors: dict, {variant_name: (r, g, b)}
        destination: 保存路径

    示例:
        create_color_variants(
            "/Game/Materials/M_PBR_Template",
            "MI_Car",
            {
                "Red": (0.8, 0.1, 0.1),
                "Blue": (0.1, 0.1, 0.8),
                "Green": (0.1, 0.8, 0.1),
                "Yellow": (0.8, 0.8, 0.1),
            }
        )
    """
    created = []

    for variant_name, color in colors.items():
        # 拼接完整名称，如 "MI_Car_Red"
        full_name = f"{base_name}_{variant_name}"
        instance = create_material_instance(
            parent_material_path, full_name, destination
        )

        if instance:
            # 设置颜色参数——同一个父材质的不同实例可以有不同的颜色
            set_vector_parameter(instance, "BaseColor", color)

            # 每次修改后都要保存，否则编辑器关闭后参数修改会丢失
            path = f"{destination}/{full_name}"
            unreal.EditorAssetLibrary.save_asset(path)
            created.append(instance)

    unreal.log(f"已创建 {len(created)} 个颜色变体")
    return created

# ─────────────────────────────────────────────────────────
# 5. 材质实例链（父子关系）
# ─────────────────────────────────────────────────────────

def create_instance_chain(parent_path, chain_defs,
                           destination="/Game/Materials/Instances"):
    """
    创建材质实例链（多层继承）

    材质实例可以多层继承：基础材质 → 中间实例 → 最终实例。
    每一层都可以覆盖上一层的参数值。
    好处：修改基础材质会级联影响所有子实例，方便全局调整。

    参数:
        parent_path: 最顶层材质路径
        chain_defs: list of (name, {param: value})

    示例:
        create_instance_chain(
            "/Game/Materials/M_Wood",
            [
                ("MI_WoodBase", {"Roughness": 0.7}),
                ("MI_OakWood", {"TintColor": (0.6, 0.4, 0.2)}),
                ("MI_PineWood", {"TintColor": (0.8, 0.7, 0.4)}),
            ]
        )
    """
    current_parent = parent_path

    for name, params in chain_defs:
        # 每次迭代时，上一轮创建的实例变成新的父材质
        instance = create_material_instance(
            current_parent, name, destination
        )

        if instance:
            # 根据值的类型自动选择参数设置方法
            for param_name, value in params.items():
                if isinstance(value, (int, float)):
                    set_scalar_parameter(instance, param_name, value)
                elif isinstance(value, tuple):
                    set_vector_parameter(instance, param_name, value)

            path = f"{destination}/{name}"
            unreal.EditorAssetLibrary.save_asset(path)
            # 关键：把当前实例的路径作为下一轮的父材质路径
            # 这样就形成了 MI_WoodBase → MI_OakWood → MI_PineWood 的继承链
            current_parent = path

    unreal.log("材质实例链创建完成")

# ─────────────────────────────────────────────────────────
# 6. 批量修改材质实例
# ─────────────────────────────────────────────────────────

def batch_update_scalar(instance_paths, param_name, new_value):
    """批量更新多个材质实例的标量参数"""
    updated = 0
    for path in instance_paths:
        instance = unreal.EditorAssetLibrary.load_asset(path)
        # isinstance 检查确保确实是材质实例，避免在其他资产类型上误操作
        if instance and isinstance(instance, unreal.MaterialInstanceConstant):
            try:
                # 这个函数返回 bool：参数不存在时返回 False（而不是抛异常），
                # 所以要检查返回值，否则会把"没改成功"也算进 updated。
                ok = unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, param_name, new_value
                )
                if ok:
                    unreal.EditorAssetLibrary.save_asset(path)
                    updated += 1
                else:
                    unreal.log_warning(f"  {path} 上没有标量参数 {param_name}，已跳过")
            except Exception as e:
                # 不要用裸 except：至少把原因打出来，否则出错时完全查不到线索
                unreal.log_warning(f"  设置 {path} 的 {param_name} 失败: {e}")

    unreal.log(f"已更新 {updated} 个材质实例的 {param_name}")

# ─────────────────────────────────────────────────────────
# 7. 为关卡中的 Actor 分配材质
# ─────────────────────────────────────────────────────────

def assign_material_to_actors(material_path, actor_label_contains=None,
                                material_slot=0):
    """
    为关卡中的 Actor 分配材质

    参数:
        material_path: 材质路径
        actor_label_contains: 按标签过滤 (None = 选中 Actor)
        material_slot: 材质插槽索引（一个 Mesh 可以有多个材质槽）
    """
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material:
        unreal.log_error(f"无法加载材质: {material_path}")
        return

    if actor_label_contains:
        # 直接在关卡里按标签过滤。
        # 【易错点】这里原来写的是 from utils.helpers import get_actors_by_label，
        #   但本课没有把 PythonLearning 加进 sys.path，单独运行会 ModuleNotFoundError。
        #   课程要求"每个脚本都能独立运行"，所以这里内联实现。
        actors = [
            a for a in unreal.get_editor_subsystem(
                unreal.EditorActorSubsystem
            ).get_all_level_actors()
            if actor_label_contains in str(a.get_actor_label())
        ]
    else:
        # get_selected_level_actors 返回编辑器视口中当前选中的 Actor 列表
        # 如果没有选中任何 Actor，返回空列表
        # （EditorLevelLibrary 已废弃，改用 EditorActorSubsystem）
        actors = unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).get_selected_level_actors()

    count = 0
    for actor in actors:
        # get_component_by_class 获取 Actor 上指定类型的组件。
        # StaticMeshComponent 是静态网格组件，所有静态网格 Actor 都有这个组件。
        mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp:
            # set_material 将材质分配到指定的材质插槽。
            # material_slot=0 是第一个（也是最常见的）材质槽。
            # 一个网格可以有多个材质槽（比如人物模型：身体、衣服、头发各一个槽）。
            mesh_comp.set_material(material_slot, material)
            count += 1

    unreal.log(f"已为 {count} 个 Actor 分配材质: {material_path}")

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 创建材质实例
# mi = create_material_instance(
#     "/Game/Materials/M_PBR_Template",
#     "MI_TestInstance"
# )
# if mi:
#     set_scalar_parameter(mi, "Roughness", 0.3)
#     set_scalar_parameter(mi, "Metallic", 1.0)
#     set_vector_parameter(mi, "BaseColor", (0.8, 0.2, 0.2))

unreal.log("材质与纹理第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个材质变体系统：一键生成同一材质的 10 种配色
# 2. 编写工具：根据一天中的时间自动调整材质的颜色参数
# 3. 创建一个"材质库"工具：浏览和预览所有材质实例
# 4. 实现材质参数随机化工具（用于场景变化）
