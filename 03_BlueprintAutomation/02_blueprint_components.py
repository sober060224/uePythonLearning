"""
=============================================================
蓝图自动化 第2课：蓝图组件管理
=============================================================

学习目标：
  - 在蓝图中添加和删除组件
  - 配置组件属性
  - 管理组件层级关系

核心类：
  - unreal.BlueprintEditorLibrary - 蓝图编辑器工具
  - unreal.SimpleConstructionScript - 组件树脚本
  - unreal.SCS_Node - 组件树节点
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 获取蓝图的组件列表
# ─────────────────────────────────────────────────────────

def list_blueprint_components(blueprint_path):
    """列出蓝图中所有组件"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return

    unreal.log(f"\n蓝图 {bp.get_name()} 的组件列表:")
    unreal.log("-" * 40)

    # 获取 SimpleConstructionScript (SCS)
    scs = bp.simple_construction_script
    if not scs:
        unreal.log("  没有 SimpleConstructionScript")
        return

    # 获取所有节点
    all_nodes = scs.get_all_nodes()
    unreal.log(f"  共 {len(all_nodes)} 个组件节点:")

    for node in all_nodes:
        component_class = node.component_class
        component_name = node.get_variable_name()
        unreal.log(f"  [{component_class.get_name()}] {component_name}")

    return all_nodes

# ─────────────────────────────────────────────────────────
# 2. 添加组件到蓝图
# ─────────────────────────────────────────────────────────

def add_component_to_blueprint(blueprint_path, component_class,
                                component_name, parent_name=None):
    """
    向蓝图添加新组件

    参数:
        blueprint_path: 蓝图路径
        component_class: 组件类 (如 unreal.StaticMeshComponent)
        component_name: 组件名称
        parent_name: 父组件名称 (None = 附加到根)
    """
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return None

    scs = bp.simple_construction_script
    if not scs:
        unreal.log_error("蓝图没有 SimpleConstructionScript")
        return None

    # 创建新的 SCS 节点
    new_node = scs.add_node(component_class, component_name)

    if not new_node:
        unreal.log_error(f"添加组件失败: {component_name}")
        return None

    # 设置父节点
    if parent_name:
        # 查找父节点
        all_nodes = scs.get_all_nodes()
        parent_node = None
        for node in all_nodes:
            if node.get_variable_name() == parent_name:
                parent_node = node
                break

        if parent_node:
            scs.add_node_as_child(new_node, parent_node)
            unreal.log(f"组件 {component_name} 已附加到 {parent_name}")
        else:
            unreal.log_warning(f"未找到父组件: {parent_name}，附加到根")
            scs.add_node_to_root(new_node)
    else:
        # 附加到根
        scs.add_node_to_root(new_node)
        unreal.log(f"组件 {component_name} 已附加到根")

    # 保存蓝图
    unreal.EditorAssetLibrary.save_asset(blueprint_path)
    unreal.log(f"已添加组件: {component_name} ({component_class.get_name()})")

    return new_node

# ─────────────────────────────────────────────────────────
# 3. 删除组件
# ─────────────────────────────────────────────────────────

def remove_component_from_blueprint(blueprint_path, component_name):
    """从蓝图中删除指定名称的组件"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        return False

    scs = bp.simple_construction_script
    if not scs:
        return False

    # 查找组件节点
    all_nodes = scs.get_all_nodes()
    target_node = None
    for node in all_nodes:
        if node.get_variable_name() == component_name:
            target_node = node
            break

    if not target_node:
        unreal.log_warning(f"未找到组件: {component_name}")
        return False

    # 删除节点
    scs.remove_node(target_node)
    unreal.EditorAssetLibrary.save_asset(blueprint_path)
    unreal.log(f"已删除组件: {component_name}")
    return True

# ─────────────────────────────────────────────────────────
# 4. 设置组件属性
# ─────────────────────────────────────────────────────────

def set_component_property(blueprint_path, component_name,
                           property_name, value):
    """
    设置蓝图组件的属性

    参数:
        blueprint_path: 蓝图路径
        component_name: 组件名称
        property_name: 属性名
        value: 属性值
    """
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        return False

    scs = bp.simple_construction_script
    all_nodes = scs.get_all_nodes()

    for node in all_nodes:
        if node.get_variable_name() == component_name:
            # 获取组件模板
            component_template = node.component_template
            if component_template:
                component_template.set_editor_property(property_name, value)
                unreal.log(
                    f"已设置 {component_name}.{property_name} = {value}"
                )
                unreal.EditorAssetLibrary.save_asset(blueprint_path)
                return True

    unreal.log_warning(f"未找到组件: {component_name}")
    return False

# ─────────────────────────────────────────────────────────
# 5. 实用组件操作封装
# ─────────────────────────────────────────────────────────

def setup_actor_blueprint(blueprint_path, mesh_path=None):
    """
    为 Actor 蓝图设置标准组件结构:
    - SceneComponent (根)
    - StaticMeshComponent (视觉)
    - 可选: 设置网格体
    """
    # 添加 StaticMeshComponent
    add_component_to_blueprint(
        blueprint_path,
        unreal.StaticMeshComponent,
        "Mesh"
    )

    # 设置网格体
    if mesh_path:
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
        if mesh:
            set_component_property(
                blueprint_path,
                "Mesh",
                "static_mesh",
                mesh
            )
            unreal.log(f"已设置网格体: {mesh_path}")

def add_collision_box(blueprint_path, name="CollisionBox",
                      extent=(50.0, 50.0, 50.0)):
    """添加 Box 碰撞组件"""
    node = add_component_to_blueprint(
        blueprint_path,
        unreal.BoxComponent,
        name
    )

    if node:
        set_component_property(
            blueprint_path, name,
            "box_extent",
            unreal.Vector(extent[0], extent[1], extent[2])
        )
    return node

def add_sphere_collision(blueprint_path, name="SphereCollision",
                          radius=100.0):
    """添加球形碰撞组件"""
    node = add_component_to_blueprint(
        blueprint_path,
        unreal.SphereComponent,
        name
    )

    if node:
        set_component_property(
            blueprint_path, name,
            "sphere_radius",
            radius
        )
    return node

def add_point_light(blueprint_path, name="PointLight",
                     intensity=5000.0, color=(1.0, 1.0, 1.0)):
    """添加点光源组件"""
    node = add_component_to_blueprint(
        blueprint_path,
        unreal.PointLightComponent,
        name
    )

    if node:
        set_component_property(
            blueprint_path, name,
            "intensity",
            intensity
        )
        set_component_property(
            blueprint_path, name,
            "light_color",
            unreal.Color(
                int(color[0] * 255),
                int(color[1] * 255),
                int(color[2] * 255),
                255
            )
        )
    return node

# ─────────────────────────────────────────────────────────
# 6. 完整的蓝图创建管线
# ─────────────────────────────────────────────────────────

def create_pickup_blueprint(name="BP_Pickup", destination="/Game/Blueprints"):
    """
    创建一个完整的拾取物蓝图:
    - StaticMeshComponent (视觉)
    - SphereComponent (触发区域)
    - PointLightComponent (视觉提示)
    - RotatingMovementComponent (旋转动画)
    """
    # 1. 创建蓝图
    bp = unreal.BlueprintFactory()
    bp.set_editor_property("ParentClass", unreal.Actor)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    unreal.EditorAssetLibrary.make_directory(destination)

    new_bp = asset_tools.create_asset(name, destination, unreal.Blueprint, bp)
    if not new_bp:
        unreal.log_error("创建蓝图失败")
        return None

    bp_path = f"{destination}/{name}"

    # 2. 添加组件
    add_component_to_blueprint(bp_path, unreal.SphereComponent, "TriggerZone")
    add_component_to_blueprint(bp_path, unreal.StaticMeshComponent, "Mesh")
    add_component_to_blueprint(bp_path, unreal.PointLightComponent, "GlowLight")

    # 3. 配置属性
    set_component_property(bp_path, "TriggerZone", "sphere_radius", 100.0)
    set_component_property(bp_path, "GlowLight", "intensity", 3000.0)

    # 4. 编译并保存
    compile_blueprint(bp_path)
    unreal.EditorAssetLibrary.save_asset(bp_path)

    unreal.log(f"已创建完整的拾取物蓝图: {bp_path}")
    return new_bp

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 示例: 创建拾取物蓝图
# create_pickup_blueprint("BP_CoinPickup", "/Game/Pickups")

unreal.log("蓝图自动化第2课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个 "灯笼" 蓝图：包含网格体、点光源、碰撞体
# 2. 批量为所有蓝图添加一个自定义组件
# 3. 编写工具：复制一个蓝图的组件结构到另一个蓝图
# 4. 创建一个组件模板库，快速搭建不同类型的蓝图
