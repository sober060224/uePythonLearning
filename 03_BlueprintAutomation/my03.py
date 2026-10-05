import unreal


# 1. 编写工具，批量修改所有蓝图的某个属性值
def first(property, value):
    all_asset = unreal.EditorAssetLibrary.list_assets("/Game")

    for asset_path in all_asset:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if asset_data.asset_class_path.asset_name != "Blueprint":
            continue

        object = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not isinstance(object, unreal.Blueprint):
            continue

        cls = object.generated_class()
        if not cls:
            unreal.log_error("未编译蓝图")
            continue

        cdo = unreal.get_default_object(cls)
        if not cdo:
            unreal.log_error("未获取到默认对象")
            continue

        cdo.set_editor_property(property, value)


# property = ""
# value = ""
# first(property, value)


# 2. 创建一个"蓝图对比"工具，比较两个蓝图的组件和属性差异
#
# 【解题思路】"对比"要拆成两块独立信息，分两条链路去拿：
#   ① 组件（结构）—— 两个蓝图"挂了哪些组件、组件类型是否一致"
#      用 SubobjectDataSubsystem 拿组件树。
#      【最大的坑】SubobjectDataHandle 在 Python 侧是个空壳，
#      类体里一个字段都没有，光打印 handle 只会得到一串一模一样的默认 repr。
#      必须先用 SubobjectDataBlueprintFunctionLibrary.get_data(handle)
#      把"句柄"换成 SubobjectData，才读得出变量名和组件类名。
#   ② 属性（数据）—— 两个蓝图同一批属性的默认值是否不同
#      从各自的 CDO（类默认对象）上读值。
#
# 【易错点】两条链路都可能空手而归，每一步都要判空：
#   · 蓝图没编译成功 → generated_class() 返回 None
#   · 类型是抽象类 / 没有 CDO → get_default_object() 返回 None
def get_component_map(bp):
    """取蓝图声明的组件，键是**层级路径**，值是组件信息字典

    【为什么不用变量名当键】变量名只是标签：改了名就配不上对，
    而两个结构完全相同的组件也可能叫不同名字。真正能代表"同一个组件"
    的是它的位置和配置，所以这里用「父组件名链 + 自身变量名」拼出的
    层级路径当键 —— 它同时表达了"挂在哪"和"叫什么"。
    """
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    if not subsystem:
        unreal.log_warning("未取到 SubobjectDataSubsystem")
        return {}

    # 【UE 概念】这批 get_xxx 都是 classmethod，写成"类名.方法()"调用
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    result = {}

    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        # 句柄 → SubobjectData，这一步是读出内容的前提
        data = lib.get_data(handle)
        # 组件树里混着蓝图自身、根 Actor 等非组件项，用 is_component 过滤
        if not lib.is_component(data):
            continue

        var_name = str(lib.get_variable_name(data))
        obj = lib.get_object(data)

        # 【UE 概念】往上回溯父组件，拼出层级路径（"Root/Arm/Hand" 这种）
        #   用 get_parent_handle 拿父句柄，再用 get_data 换成父的 SubobjectData
        #   —— 因为父组件不一定是组件，所以每一层都要判 is_component
        parent_path = []
        parent_handle = lib.get_parent_handle(data)
        while parent_handle:
            parent_data = lib.get_data(parent_handle)
            if not parent_data or not lib.is_component(parent_data):
                break
            parent_path.insert(0, str(lib.get_variable_name(parent_data)))
            parent_handle = lib.get_parent_handle(parent_data)

        path = "/".join(parent_path + [var_name])
        result[path] = {
            "var_name": var_name,
            "class_name": obj.get_class().get_name() if obj else "<无效对象>",
            # 【来源】原生组件(C++自带) / 继承来的 / 本蓝图自己声明的
            #   三者性质不同，混在一起对比会误报，所以先分清
            "origin": (
                "原生"
                if lib.is_native_component(data)
                else ("继承" if lib.is_inherited_component(data) else "本蓝图")
            ),
            # 【关键配置】光有类型不够：两个 StaticMeshComponent 指向
            #   不同网格体，在游戏里完全是两回事
            "config": read_component_config(obj),
        }

    return result


def read_component_config(comp):
    """读组件的关键配置项，用来判断"同一个组件"是不是配得一样"""
    if not comp:
        return {}

    config = {}
    # 【易错点】属性名必须用 UE 的 C++ 名（snake_case），
    #   而且不是每个组件都有这些属性，所以逐个试探、读不到就跳过。
    #   这也是 UE Python 没有"枚举属性"API 时的通用土办法。
    for prop in ("static_mesh", "skeletal_mesh", "mobility"):
        try:
            value = comp.get_editor_property(prop)
        except Exception:
            continue
        config[prop] = (
            value.get_path_name() if hasattr(value, "get_path_name") else value
        )

    # 相对变换决定组件在层级里的位置/大小/朝向，属于"同一个组件"的一部分
    try:
        config["relative_transform"] = comp.get_relative_transform()
    except Exception:
        pass

    return config


def get_property_map(bp):
    """取蓝图 CDO 上的属性默认值：{属性名: 值}"""
    # CDO = 类默认对象，引擎实例化蓝图时从这里拷贝初值
    cls = bp.generated_class()
    if not cls:
        unreal.log_warning(f"蓝图未编译成功，取不到属性: {bp.get_name()}")
        return {}

    # 【易错点】generated_class() 返回的是 unreal.Class 实例，不是 Python 类。
    #   Class 类里没有 get_default_object 方法，所以不能写 cls.get_default_object()，
    #   要用模块级的 unreal.get_default_object(cls)。
    cdo = unreal.get_default_object(cls)
    if not cdo:
        unreal.log_warning(f"该蓝图没有默认对象(CDO): {bp.get_name()}")
        return {}

    result = {}
    # 【易错点】dir() 返回的是 Python 层所有属性名，混着方法和 _ 开头的内部属性。
    #   而且"能在 dir() 里看到"不等于"是真 UPROPERTY"——方法名塞给
    #   get_editor_property 会抛异常，所以用 try/except 把它们筛掉，
    #   剩下的才是真正带默认值的属性。
    for name in dir(cdo):
        if name.startswith("_"):
            continue
        try:
            result[name] = cdo.get_editor_property(name)
        except Exception:
            continue  # 这是方法或不可读的属性，跳过
    return result


def same_value(value_1, value_2):
    """比较两个属性值。结构体/数组这类不好直接判等的，退化成比字符串形式"""
    if type(value_1) is not type(value_2):
        return False
    try:
        return bool(value_1 == value_2)
    except Exception:
        return str(value_1) == str(value_2)


def second(path_1, path_2):
    """比较两个蓝图的组件与属性差异"""
    object_1 = unreal.EditorAssetLibrary.load_asset(path_1)
    if not isinstance(object_1, unreal.Blueprint):
        unreal.log_warning(f"不是蓝图资产: {path_1}")
        return

    object_2 = unreal.EditorAssetLibrary.load_asset(path_2)
    if not isinstance(object_2, unreal.Blueprint):
        unreal.log_warning(f"不是蓝图资产: {path_2}")
        return

    name_1 = object_1.get_name()
    name_2 = object_2.get_name()

    # ---- ① 组件差异：结构指纹配对，再逐项比类型/来源/配置 ----
    comp_1 = get_component_map(object_1)
    comp_2 = get_component_map(object_2)

    unreal.log("=== 组件差异 ===")

    # 【难点】变量名可能被改过，光按层级路径配对会把"改名"误报成
    #   "删了旧的 + 加了新的"。所以分两步：
    #   第一步先按"去掉变量名的层级"配对 —— 同一个父下、类型也一样的
    #   两个组件，视作"同一个组件的不同名字"，报告为改名而不是增删。
    def fingerprint(info):
        # 身份指纹 = 变量名 + 类型，用来在两张蓝图之间认"同一个组件"
        return (info["var_name"], info["class_name"])

    keys_1 = set(comp_1)
    keys_2 = set(comp_2)

    for path_1 in sorted(keys_1 - keys_2):
        info_1 = comp_1[path_1]
        # 找一下：另一张蓝图里有没有"层级相同、类型相同"的组件？
        parent_1 = path_1.rsplit("/", 1)[0]
        renamed = None
        for path_2 in sorted(keys_2):
            info_2 = comp_2[path_2]
            if path_2.rsplit("/", 1)[0] != parent_1:
                continue
            if fingerprint(info_1) == fingerprint(info_2):
                renamed = (path_2, info_2)
                break

        if renamed:
            path_2, info_2 = renamed
            unreal.log(
                f"  [仅名字不同] {path_1} <-> {path_2}（同名层级、同类型，大概率是改过名）"
            )
        else:
            unreal.log(
                f"  [仅 {name_1} 有] {path_1} ({info_1['class_name']}, {info_1['origin']})"
            )

    for path_2 in sorted(keys_2 - keys_1):
        info_2 = comp_2[path_2]
        parent_2 = path_2.rsplit("/", 1)[0]
        renamed = any(
            path_1.rsplit("/", 1)[0] == parent_2
            and fingerprint(comp_1[path_1]) == fingerprint(info_2)
            for path_1 in keys_1
        )
        if not renamed:
            unreal.log(
                f"  [仅 {name_2} 有] {path_2} ({info_2['class_name']}, {info_2['origin']})"
            )

    # 两边路径都存在的组件，比类型 / 来源 / 配置三样
    for path in sorted(keys_1 & keys_2):
        info_1, info_2 = comp_1[path], comp_2[path]
        if info_1["class_name"] != info_2["class_name"]:
            unreal.log(
                f"  [类型不同] {path}: {info_1['class_name']} -> {info_2['class_name']}"
            )
            continue
        if info_1["origin"] != info_2["origin"]:
            unreal.log(f"  [来源不同] {path}: {info_1['origin']} -> {info_2['origin']}")

        # 配置逐项比：同一个组件类型，但配的资产/变换不一样，
        # 在游戏里的表现是不同的，必须报出来
        config_1, config_2 = info_1["config"], info_2["config"]
        for prop in sorted(set(config_1) | set(config_2)):
            if prop not in config_1:
                unreal.log(f"  [{name_2} 多出配置] {path}.{prop} = {config_2[prop]}")
            elif prop not in config_2:
                unreal.log(f"  [{name_1} 多出配置] {path}.{prop} = {config_1[prop]}")
            elif not same_value(config_1[prop], config_2[prop]):
                unreal.log(
                    f"  [配置不同] {path}.{prop}: {config_1[prop]} -> {config_2[prop]}"
                )

    # ---- ② 属性差异：有没有 + 默认值是否相同 ----
    prop_1 = get_property_map(object_1)
    prop_2 = get_property_map(object_2)

    unreal.log("=== 属性差异 ===")
    for prop_name in sorted(prop_1):
        if prop_name not in prop_2:
            unreal.log(f"  [仅 {name_1} 有] {prop_name} = {prop_1[prop_name]}")
        elif not same_value(prop_1[prop_name], prop_2[prop_name]):
            unreal.log(
                f"  [值不同] {prop_name}: {prop_1[prop_name]} -> {prop_2[prop_name]}"
            )
    for prop_name in sorted(prop_2):
        if prop_name not in prop_1:
            unreal.log(f"  [仅 {name_2} 有] {prop_name} = {prop_2[prop_name]}")


# second("/Game/Blueprints/BP_A", "/Game/Blueprints/BP_B")


def main():
    selected_asset = unreal.EditorUtilityLibrary.get_selected_asset_data()
    # 【易错点】get_selected_asset_data() 没选中东西时返回空列表，
    #   直接取 [0] 会 IndexError，先判空
    if not selected_asset:
        unreal.log_warning("请先在内容浏览器里选中一个蓝图")
        return

    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for asset_data in selected_asset:
        object = unreal.EditorAssetLibrary.load_asset(asset_data.package_name)
        if not isinstance(object, unreal.Blueprint):
            continue

        unreal.log(f"\n===== {object.get_name()} =====")
        subobject_subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not subobject_subsystem:
            return

        handles = subobject_subsystem.k2_gather_subobject_data_for_blueprint(object)
        for i in handles:
            # 【关键】handle 是空壳，get_data 换成 SubobjectData 才读得到内容
            data = lib.get_data(i)
            as_object = lib.get_associated_object(data)
            unreal.log(f"name: {lib.get_display_name(data)}")
            unreal.log(f"variable_name: {lib.get_variable_name(data)}")
            if as_object:
                unreal.log(f"as_object: {as_object.get_name()}")
            unreal.log("-" * 10)


if __name__ == "__main__":
    main()


# 3. 编写自动文档生成器，为所有蓝图生成 Markdown 文档
def third():
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if asset_data.asset_class_path.asset_name != "Blueprint":
            continue


# 4. 实现蓝图版本管理工具，记录每次修改的属性变化
    