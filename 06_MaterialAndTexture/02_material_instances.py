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

本课可能用到的 API：
  unreal.EditorAssetLibrary.load_asset(asset_path: str) -> Object  —— 加载资产对象
  unreal.EditorAssetLibrary.make_directory(directory_path: str) -> bool  —— 创建资产目录
  unreal.EditorAssetLibrary.save_asset(asset_to_save: str, only_if_is_dirty: bool = True) -> bool  —— 保存指定资产
  unreal.AssetToolsHelpers.get_asset_tools() -> AssetTools  —— 获取资产工具实例
  unreal.AssetTools.create_asset(asset_name: str, package_path: str, asset_class: Class, factory: Factory, calling_context: Name = "None", overwrite_existing: bool = False) -> Object  —— 用工厂创建新资产
  unreal.MaterialInstanceConstantFactoryNew()  —— 创建材质实例资产的工厂对象
  obj.set_editor_property(name: str, value: object, notify_mode: PropertyAccessChangeNotifyMode = PropertyAccessChangeNotifyMode.DEFAULT) -> None  —— 设置对象编辑器属性
  unreal.MaterialEditingLibrary.set_material_instance_parent(instance: MaterialInstanceConstant, new_parent: MaterialInterface) -> None  —— 设置材质实例的父材质
  unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: float) -> bool  —— 设置标量参数
  unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: LinearColor) -> bool  —— 设置向量（颜色）参数
  unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: Texture) -> bool  —— 设置纹理参数值
  unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(instance: MaterialInstanceConstant, parameter_name: Name, value: bool) -> bool  —— 设置静态开关参数
  obj.get_editor_property(name: str) -> object  —— 读取对象编辑器属性（如 parent 父材质）
  unreal.LinearColor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 0.0) -> None  —— 构造 0-1 范围线性颜色
  unreal.EditorLevelLibrary.get_selected_level_actors() -> Array[Actor]  —— 获取当前选中的 Actor 列表
  actor.get_component_by_class(component_class: Class = None) -> ActorComponent  —— 按类获取 Actor 的组件
  obj.set_material(element_index: int, material: MaterialInterface) -> None  —— 设置网格指定插槽的材质（PrimitiveComponent）
  unreal.StaticMeshComponent  —— 静态网格组件类（用于查找组件和分配材质）
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
    # 加载父材质
    parent_material = unreal.EditorAssetLibrary.load_asset(parent_material_path)
    if not parent_material:
        unreal.log_error(f"无法加载父材质: {parent_material_path}")
        return None

    unreal.EditorAssetLibrary.make_directory(destination)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialInstanceConstantFactoryNew()

    instance = asset_tools.create_asset(
        name,
        destination,
        unreal.MaterialInstanceConstant,
        factory
    )

    if instance:
        # 【修改前】factory.set_editor_property("initial_parent", parent_material)
        # 【问题分析】MaterialInstanceConstantFactoryNew 没有 initial_parent 属性
        #   （见 Intermediate/PythonStub/unreal.py），父材质需要在创建后
        #   通过 MaterialEditingLibrary.set_material_instance_parent 设置。
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
    """设置标量参数"""
    # 【修改前】instance.set_scalar_parameter_value(param_name, value)
    # 【问题分析】MaterialInstanceConstant 上不存在该 Python 方法，
    #   改用 MaterialEditingLibrary.set_material_instance_scalar_parameter_value。
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
    if len(color) == 3:
        color = (*color, 1.0)

    linear_color = unreal.LinearColor(color[0], color[1], color[2], color[3])
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        instance, param_name, linear_color
    )
    unreal.log(f"  向量 {param_name} = {color}")

def set_texture_parameter(instance, param_name, texture_path):
    """设置纹理参数"""
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
    """设置静态开关参数"""
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

    # 获取父材质
    parent = instance.get_editor_property("parent")
    if parent:
        unreal.log(f"父材质: {parent.get_name()}")

    # 列出参数（通过检查表达式）
    # 注意：不同版本的 API 可能有差异
    if hasattr(instance, 'get_scalar_parameter_value'):
        unreal.log("  （使用材质编辑器查看完整参数列表）")

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
        full_name = f"{base_name}_{variant_name}"
        instance = create_material_instance(
            parent_material_path, full_name, destination
        )

        if instance:
            # 设置颜色参数
            set_vector_parameter(instance, "BaseColor", color)

            # 保存
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
        instance = create_material_instance(
            current_parent, name, destination
        )

        if instance:
            # 应用参数
            for param_name, value in params.items():
                if isinstance(value, (int, float)):
                    set_scalar_parameter(instance, param_name, value)
                elif isinstance(value, tuple):
                    set_vector_parameter(instance, param_name, value)

            path = f"{destination}/{name}"
            unreal.EditorAssetLibrary.save_asset(path)
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
        if instance and isinstance(instance, unreal.MaterialInstanceConstant):
            try:
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, param_name, new_value
                )
                unreal.EditorAssetLibrary.save_asset(path)
                updated += 1
            except:
                pass

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
        material_slot: 材质插槽索引
    """
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material:
        unreal.log_error(f"无法加载材质: {material_path}")
        return

    if actor_label_contains:
        from utils.helpers import get_actors_by_label
        actors = get_actors_by_label(actor_label_contains)
    else:
        actors = unreal.EditorLevelLibrary.get_selected_level_actors()

    count = 0
    for actor in actors:
        mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp:
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
