import os
import unreal


# 1. 编写工具，批量修改所有蓝图的某个属性值
def first(property, value):
    all_asset = unreal.EditorAssetLibrary.list_assets("/Game")

    for asset_path in all_asset:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if str(asset_data.asset_class_path.asset_name) != "Blueprint":
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
# 【一句话理解】蓝图对比 = 把两张蓝图各自"翻译成文字套餐"，再逐项对答案。
#   翻译：把蓝图里看不见摸不着的东西，变成 Python 的 dict/list/str。
#   对答案：两个 dict 一减，多出来的、少掉的、值不一样的，就是差异。
#
# 【为什么不能直接 obj1 == obj2】
#   UObject 的 == 比的是"是不是同一个对象"，不是"内容像不像"。
#   两张不同蓝图永远是两个对象，直接比必然"不同"，但也说不出哪儿不同。
#   所以必须自己拆成可比的小项（字符串、数字、bool）再逐个比。
#
# 【三条链路】每条都用引擎现成的 API，别自己造轮子：
#   ① 父类 —— 父类不同是后面一切差异的根源，先单独报一句
#      BlueprintEditorLibrary.get_blueprint_parent_class
#   ② 组件（结构）—— 两个蓝图挂的组件、类型/来源/配置是否一致
#      用 SubobjectDataSubsystem 拿组件树。
#      【最大的坑】SubobjectDataHandle 和 SubobjectData 在 Python 侧都是 StructBase，
#      类体里一个字段都没有 —— 句柄必须先用 get_data 换成 SubobjectData，
#      内容只能用 SubobjectDataBlueprintFunctionLibrary 的 get_xxx 读出来。
#   ③ 变量（数据）—— 变量清单直接问引擎：
#      BlueprintEditorLibrary.list_member_variable_names
#      【为什么不用 dir(cdo)】dir() 里混着方法和内部属性，还得靠 try/except 筛，
#      而且拿不到变量类型。list_member_variable_names 返回的就是真正的变量名(str)。
#      默认值再去 CDO（类默认对象）上读：unreal.get_default_object(bp.generated_class())
#
# 【易错点】每条链路都可能空手而归，每一步都要判空：
#   · 蓝图没编译成功 → generated_class() 返回 None
#   · 抽象类 / 没有 CDO → get_default_object() 返回 None
#   · 组件条目里混着蓝图自身、根 Actor 等非组件项 → is_component() 过滤

LIB = unreal.SubobjectDataBlueprintFunctionLibrary  # 读组件树
BEL = unreal.BlueprintEditorLibrary  # 读蓝图资产本身（变量/图表/父类）


def load_blueprint(path):
    """加载并确认是蓝图资产，不是就返回 None

    【为什么要判 isinstance】load_asset 喂什么路径就能加载什么资产，
    传进来一个材质/贴图也会照样返回对象，后面调 blueprint 专属 API 才炸。
    在入口处一次性挡住，比在 20 个调用点各写一遍 try 划算。
    """
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"不是蓝图资产：{path}")
        return None
    return bp


def class_name(cls: unreal.Class):
    """Class → 可读名字

    【为什么要判空】get_blueprint_parent_class 对某些蓝图会返回 None，
    None.get_name() 直接 AttributeError，所以三元表达式兜一下。
    """
    return cls.get_name() if cls else "<无>"


def same_value(value_1, value_2):
    """比较两个属性值：类型不同直接算不同，结构体/数组退化成比字符串形式

    【为什么类型不同直接算不同】int 0 和 bool False 在 Python 里 == 为 True，
    但它们在蓝图里的含义完全不同（一个数字开关 vs 一个真假开关），
    报"无差异"会误导用户，所以先卡类型。
    """
    if type(value_1) is not type(value_2):
        return False
    # 【为什么不用 a == b】结构体/数组/枚举的 == 行为不一致，
    #   统一比字符串形式最省心（类型已经在上面比过了）
    return str(value_1) == str(value_2)


# ---- ① 组件（结构）----


def subobject_path(lib, data):
    """组件的层级路径键：从自身一路回溯父级，拼成「父/子」路径

    【为什么不能用变量名当键】test01 的输出证明了三点：
      1. 根 Actor 那条的 variable_name 是 None；
      2. 同一个 SCS 组件节点会被 k2_gather 输出两条（SCS 节点视图 + 实例化视图），
         两条的 variable_name 和关联对象完全相同，只有句柄/指针不同；
      3. 跨蓝图时，同一个变量名可能出现在不同的树层级上。
    变量名既不唯一也对不准"哪个组件"，当键必然丢数据/误配对。
    路径键天然唯一：同一节点重复输出 → 路径相同，覆盖即去重；
    同名但位置不同 → 路径不同，正确区分。
    """
    chain = []
    node = data
    while lib.is_valid(node):
        # 【为什么会 None】根 Actor 条目的 variable_name 是 None（不是空串），
        # str(None) 会得到 "None" 这个真字符串，if 判断永远成立，回退失效 ——
        # 必须先判 None 再 str，顺序不能反。
        if lib.get_variable_name(node) is None:
            break  # 到根 Actor 了：它不是组件，不进键，键只含组件路径
        name = str(lib.get_variable_name(node))
        chain.append(name)
        parent = lib.get_parent_handle(node)
        if not lib.is_handle_valid(parent):
            break
        node = lib.get_data(parent)
    return "/".join(reversed(chain))


def get_components(bp):
    """取蓝图声明的组件：{组件层级路径: {class, origin, config}}

    【输出为什么长这样】把每个组件拍平成三列，正好对应人看图时会问的三个问题：
      class  —— 这是什么东西？（StaticMeshComponent / PointLightComponent…）
      origin —— 哪来的？（引擎自带 / 父类传的 / 这个蓝图自己加的）
      config —— 配成什么样了？（网格体、变换、Mobility…）
    三列任一不同，就是一处真实差异；合起来看才能判断"是不是同一个组件被改了"。
    键用层级路径而不是变量名，原因见 subobject_path 的注释。
    """
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    if not subsystem:
        unreal.log_warning("取不到 SubobjectDataSubsystem")
        return {}

    result = {}
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        # 句柄 → SubobjectData，这一步是读出内容的前提
        data = LIB.get_data(handle)
        # 组件树里混着蓝图自身、根 Actor 等非组件项，用 is_component 过滤
        if not LIB.is_component(data):
            continue

        component = LIB.get_associated_object(data)
        result[subobject_path(LIB, data)] = {
            "class": class_name(component.get_class()) if component else "<无效对象>",
            # 【来源】原生组件(C++自带) / 继承来的 / 本蓝图自己声明的
            #   三者性质不同，混在一起对比会误报，所以先分清
            "origin": (
                "原生"
                if LIB.is_native_component(data)
                else ("继承" if LIB.is_inherited_component(data) else "本蓝图")
            ),
            # 【关键配置】光有类型不够：两个 StaticMeshComponent 指向
            #   不同网格体，在游戏里完全是两回事
            "config": read_component_config(component),
        }

    return result


def read_component_config(comp):
    """读组件的关键配置项，用来判断同一个组件是不是配得一样

    【为什么只挑几个属性】桩里没有枚举 UPROPERTY 的 API，
    所以按组件的真实类型，只读它一定有的属性：用 isinstance 判断类型，
    不需要 try/except 兜底。
    """
    if not comp:
        return {}

    config = {}
    # 资产引用(UObject)显示成路径信息量更大，枚举/变换保持原样
    if isinstance(comp, unreal.StaticMeshComponent):
        config["static_mesh"] = asset_path_text(comp.get_editor_property("static_mesh"))
    if isinstance(comp, unreal.SkeletalMeshComponent):
        config["skeletal_mesh"] = asset_path_text(
            comp.get_editor_property("skeletal_mesh")
        )
    if isinstance(comp, unreal.SceneComponent):
        # mobility 和相对变换都在 SceneComponent 上：
        # 相对变换决定组件在层级里的位置/大小/朝向，属于同一个组件的一部分
        config["mobility"] = comp.get_editor_property("mobility")
        config["relative_transform"] = comp.get_relative_transform()
    return config


def asset_path_text(value):
    """资产引用 → 显示成路径（比对象 repr 信息量大）；空引用给个明确占位

    【为什么要 isinstance】桩里 get_editor_property 的返回类型是 object，
    直接 .get_path_name() 类型检查器会报错；这样写也顺便说清了取到的是不是 UObject。
    """
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    return "<空>" if value is None else value


# ---- ② 变量（数据）----


def get_variables(bp):
    """取蓝图自己声明的变量：{变量名: {type, value}}

    【数据从哪来】变量名和类型属于"蓝图资产"，问 BlueprintEditorLibrary；
    默认值属于"运行时的类"，必须去 CDO 上读。
    这两处是不同层的东西，很多人在这里卡住——别在一个 API 上找全部信息。
    """
    cls = bp.generated_class()
    # 【易错点】类对象上没有 get_default_object()，要用模块级函数
    cdo = unreal.get_default_object(cls) if cls else None
    if not cdo:
        unreal.log_warning(f"蓝图未编译成功，取不到变量默认值: {bp.get_name()}")

    result = {}
    # 【关键】include_inherited_members=False：只比这个蓝图自己声明的变量。
    #   继承来的属性归父类管（父类上面已经单独比过一次），
    #   否则父类一改，两张蓝图会满屏属性差异噪音。
    for name in BEL.list_member_variable_names(bp, include_inherited_members=False):
        info = {
            # 【说明】EdGraphPinType 在桩里没暴露字段，直接 str() 看整体；
            #   要更规整可以用 BEL.pin_type_to_json_schema(pin_type, cls)
            "type": str(BEL.get_member_variable_type(bp, name)),
            "value": "<无 CDO>",
        }
        if cdo:
            try:
                # 变量名就是 UPROPERTY 的名字，可以直接喂给 get_editor_property
                info["value"] = cdo.get_editor_property(name)
            except Exception as e:  # noqa: BLE001 —— UE 读不到的属性抛的就是普通 Exception
                # 少数变量（事件派发器之类）不是可读的普通属性，记一句就行
                unreal.log_warning(f"读不到变量 {name} 的默认值：{e}")
        result[name] = info

    return result


# ---- ③ 主函数：对比 ----


def second(path_1, path_2):
    """比较两个蓝图的组件与属性差异

    【输出风格】全程用 unreal.log 打印成人话，而不是 return 一个大字典。
    这是给人在 Output Log 里看的工具，屏幕上的可读性 > 程序里的可解析性。

    【执行顺序】父类 → 组件 → 变量 → 图表。
    父类放最前面：父类不同意味着后面所有的"继承来的东西"都可能不同，
    先给用户一个总因，再看细节，不然满屏差异找不到原因。
    """
    object_1 = load_blueprint(path_1)
    object_2 = load_blueprint(path_2)
    if not object_1 or not object_2:
        return

    name_1 = object_1.get_name()
    name_2 = object_2.get_name()

    # 0) 父类差异：父类不同是后面一切差异的根源，先单独报
    parent_1 = BEL.get_blueprint_parent_class(object_1)
    parent_2 = BEL.get_blueprint_parent_class(object_2)
    if parent_1 != parent_2:
        unreal.log(f"父类不同：{class_name(parent_1)} -> {class_name(parent_2)}")

    # 1) 组件差异：按组件变量名配对，逐项比 类型 / 来源 / 配置
    #
    # 【核心套路】两次对比都用同一个三行公式，背下来就够用一辈子：
    #   set(A) - set(B)  只有 A 有（新增/删除）
    #   set(B) - set(A)  只有 B 有
    #   set(A) & set(B)  两边都有 → 才需要逐项比内容
    # 先用集合把"要不要比内容"筛出来，再对交集逐个比。
    comp_1 = get_components(object_1)
    comp_2 = get_components(object_2)

    unreal.log("=== 组件差异 ===")
    # 【写法】分成「只有 A 有 / 只有 B 有 / 两边都有」三组分别遍历：
    #   这样每组取出来的字典一定不是 None，就不用再写一堆判空分支了
    for key in sorted(set(comp_1) - set(comp_2)):
        info = comp_1[key]
        unreal.log(f"  [仅 {name_1} 有] {key} ({info['class']}, {info['origin']})")

    for key in sorted(set(comp_2) - set(comp_1)):
        info = comp_2[key]
        unreal.log(f"  [仅 {name_2} 有] {key} ({info['class']}, {info['origin']})")

    for key in sorted(set(comp_1) & set(comp_2)):
        info_1 = comp_1[key]
        info_2 = comp_2[key]

        if info_1["class"] != info_2["class"]:
            unreal.log(f"  [类型不同] {key}: {info_1['class']} -> {info_2['class']}")
        if info_1["origin"] != info_2["origin"]:
            unreal.log(f"  [来源不同] {key}: {info_1['origin']} -> {info_2['origin']}")

        # 配置逐项比：同一个组件类型，但配的资产/变换不一样，
        # 在游戏里的表现是不同的，必须报出来
        config_1, config_2 = info_1["config"], info_2["config"]
        for prop in sorted(set(config_1) | set(config_2)):
            if prop not in config_1:
                unreal.log(f"  [{name_2} 多出配置] {key}.{prop} = {config_2[prop]}")
            elif prop not in config_2:
                unreal.log(f"  [{name_1} 多出配置] {key}.{prop} = {config_1[prop]}")
            elif not same_value(config_1[prop], config_2[prop]):
                unreal.log(
                    f"  [配置不同] {key}.{prop}: {config_1[prop]} -> {config_2[prop]}"
                )

    # 2) 变量差异：有没有 + 类型 + 默认值
    #
    # 【为什么默认值也有意义】两个蓝图都叫 Health、都是 float，
    # 但一个默认 100 一个默认 200，游戏里就是坦克和脆皮的区别。
    # 变量名相同 ≠ 行为相同，默认值必须比。
    var_1 = get_variables(object_1)
    var_2 = get_variables(object_2)

    unreal.log("=== 变量差异 ===")
    for var_name in sorted(set(var_1) - set(var_2)):
        info = var_1[var_name]
        unreal.log(f"  [仅 {name_1} 有] {var_name} ({info['type']}) = {info['value']}")

    for var_name in sorted(set(var_2) - set(var_1)):
        info = var_2[var_name]
        unreal.log(f"  [仅 {name_2} 有] {var_name} ({info['type']}) = {info['value']}")

    for var_name in sorted(set(var_1) & set(var_2)):
        info_1 = var_1[var_name]
        info_2 = var_2[var_name]

        if info_1["type"] != info_2["type"]:
            unreal.log(f"  [类型不同] {var_name}: {info_1['type']} -> {info_2['type']}")
        if not same_value(info_1["value"], info_2["value"]):
            unreal.log(
                f"  [默认值不同] {var_name}: {info_1['value']} -> {info_2['value']}"
            )

    # 3) 图表差异：同一个库里就有，顺手一行
    graphs_1 = {str(g) for g in BEL.list_graph_names(object_1)}
    graphs_2 = {str(g) for g in BEL.list_graph_names(object_2)}
    for graph in sorted(graphs_1 - graphs_2):
        unreal.log(f"  [仅 {name_1} 有图表] {graph}")
    for graph in sorted(graphs_2 - graphs_1):
        unreal.log(f"  [仅 {name_2} 有图表] {graph}")


# second(
#     "/Game/BluePrintClass/BallAdventure/BP_Cannon",
#     "/Game/BluePrintClass/BallAdventure/BP_Cannon1",
# )


# ---- 下面这个 main() 是调试用的组件打印器，不属于第二题，留着方便对照 ----
def test01(selected_asset):
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
        # 用 subobject_path 当键存一遍，演示重复条目如何塌缩成一个节点
        by_path = {}
        for i in handles:
            # 【关键】handle 是空壳，get_data 换成 SubobjectData 才读得到内容
            data = lib.get_data(i)
            as_object = lib.get_associated_object(data)
            var_name = str(lib.get_variable_name(data))
            blueprint = lib.get_blueprint(data)

            # 【三选一全打出来】判断两条重复视图的来源标志是否一致
            origin = (
                f"原生={lib.is_native_component(data)} "
                f"继承={lib.is_inherited_component(data)} "
                f"实例视图={lib.is_instanced_component(data)}"
            )
            path = subobject_path(lib, data)
            by_path[path] = data  # 同路径重复条目 → 覆盖去重

            unreal.log(f"blueprint: {blueprint}")
            unreal.log(f"data: {data}")
            unreal.log(f"name: {lib.get_display_name(data)}")
            unreal.log(f"variable_name: {var_name}")
            unreal.log(f"origin: {origin}")
            if as_object:
                unreal.log(f"as_object: {as_object.get_name()}")
            unreal.log(f"path: {path}")
            unreal.log("-" * 10)

        unreal.log(
            f"→ 原始 {len(handles)} 行 / 去重后 {len(by_path)} 个节点: "
            f"{sorted(by_path)}"
        )


def test03(selected_asset):
    """演示：同一个组件打两遍，到底有什么用（本次实测得出结论）

    【实测结论】直接把两个视图的全部可观测标志打出来看：
      来源标志：原生组件 / 继承组件 / 实例化组件（Python 绑定的全部三个）
      能力标志：改名 / 拖层级 / 编值 / 复制
    实测 BP_Cannon 的重复两条在所有标志上完全一致（全是 True/False 相同），
    说明 Python API 层区分不了这两条 —— 引擎把它们当两个对象保留，
    是给编辑器"组件面板(SCS)"和"CDO 实例"两套 C++ 逻辑用的。
    对我们 Python 对比工具：两条等价 → 路径键塌缩成一个节点，无损。
    """
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for asset_data in selected_asset:
        object = unreal.EditorAssetLibrary.load_asset(asset_data.package_name)
        if not isinstance(object, unreal.Blueprint):
            continue

        unreal.log(f"\n===== {object.get_name()}：组件视图清单 =====")
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not subsystem:
            return

        path_views = {}  # 路径 -> 该路径的所有视图（正常是 1~2 条）
        for handle in subsystem.k2_gather_subobject_data_for_blueprint(object):
            data = lib.get_data(handle)
            if not lib.is_component(data):
                continue
            path_views.setdefault(subobject_path(lib, data), []).append(data)

        for path, views in sorted(path_views.items()):
            unreal.log(f"{path}: 共 {len(views)} 个视图")
            for data in views:
                unreal.log(
                    f"  原生={lib.is_native_component(data)} "
                    f"继承={lib.is_inherited_component(data)} "
                    f"实例化={lib.is_instanced_component(data)} | "
                    f"改名={lib.can_rename(data)} 拖层级={lib.can_reparent(data)} "
                    f"编值={lib.can_edit(data)} 复制={lib.can_duplicate(data)}"
                )


def test04(selected_asset):
    """演示 get_object_for_blueprint：同一个组件节点，用三种口径取对象，看差别

    【API 到底干什么】C++ 头文件 SubobjectData.h 的注释写得最直白：
        @param InBlueprint  在哪个蓝图里编辑
        @note  May not be the same as the value returned by GetObject()
        @return 该节点「在给定蓝图里可被修改」的那个对象
    一句话：它不返回「节点的对象」，而返回「该节点在某个蓝图上下文里的可编辑版本」。

    【三种口径的区别】同一个节点可以算出三个不同的对象：
      get_object(data)                     —— 节点缓存的原始对象。继承组件拿到的是父蓝图的模板
      get_associated_object(data)          —— 在「树根上下文」里重新解析（引擎内部就是这么调
                                              get_object_for_blueprint 的，见 SubobjectDataBlueprintFunctionLibrary.cpp）
      get_object_for_blueprint(data, bp)   —— 手动指定蓝图。本演示里 bp 就是树根蓝图，
                                              所以它应该与 get_associated_object 结果一致，
                                              而与 get_object 在「继承组件」上不一致。

    【什么时候必须用它】当你想解析的蓝图不是树根蓝图时。
      典型场景：拿子蓝图的组件树，却要读「父蓝图上下文里」那个模板的属性。
      get_associated_object 只会沿树根走，没法指定别的蓝图。

    【副作用·心里有数】对继承节点调用它，会顺手把 ICH 覆盖模板创建出来
      （SubobjectDataSubsystem.cpp 原文：This call creates ICH override templates
      for the current Blueprint），所以它是 BlueprintCallable 而不是 BlueprintPure。
      当只读用没问题，但它并非绝对无副作用。
    """
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for asset_data in selected_asset:
        bp = unreal.EditorAssetLibrary.load_asset(asset_data.package_name)
        if not isinstance(bp, unreal.Blueprint):
            continue

        unreal.log(f"\n===== {bp.get_name()}：三种口径取对象 =====")
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not subsystem:
            return

        for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
            data = lib.get_data(handle)
            if not lib.is_component(data):
                continue

            # 三个口径各取一个对象，转成路径名方便肉眼比对
            raw = object_path(lib.get_object(data))
            asso = object_path(lib.get_associated_object(data))
            by_bp = object_path(lib.get_object_for_blueprint(data, bp))

            unreal.log(
                f"{subobject_path(lib, data)} (继承={lib.is_inherited_component(data)})"
            )
            unreal.log(f"    get_object               = {raw}")
            unreal.log(f"    get_associated_object    = {asso}")
            unreal.log(f"    get_object_for_blueprint = {by_bp}")
            unreal.log(f"    → 与 fp 一致: asso={asso == by_bp} / raw={raw == by_bp}")


def object_path(value):
    """UObject → 路径名，方便直接比对是不是同一个对象；空值给个明确占位"""
    return value.get_path_name() if isinstance(value, unreal.Object) else "<空>"


def test02(selected_asset):
    object = unreal.EditorAssetLibrary.load_asset(selected_asset[0].package_name)
    unreal.log(object.get_path_name())
    unreal.log(object.get_name)
    unreal.log(object.get_package)
    unreal.log(object.get_full_name)
    unreal.log(object.get_class().get_name())


def main():
    selected_asset = unreal.EditorUtilityLibrary.get_selected_asset_data()
    # 【易错点】get_selected_asset_data() 没选中东西时返回空列表，
    #   直接取 [0] 会 IndexError，先判空
    if not selected_asset:
        unreal.log_warning("请先在内容浏览器里选中一个蓝图")
        return

    test04(selected_asset)


# if __name__ == "__main__":
#     main()


# 3. 编写自动文档生成器，为所有蓝图生成 Markdown 文档
def third():
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")

    path = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintMd.md")  # 文件路径
    with open(path, "w", encoding="utf-8") as f:
        f.write("## 所有蓝图Markdown文档\n|蓝图名字|类型|路径|\n|-|-|-\n")

    for asset_path in all_assets:
        unreal.log(asset_path)
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if "blueprint" not in str(asset_data.asset_class_path.asset_name).lower():
            unreal.log(f"{asset_data.asset_class_path.asset_name}不是蓝图类")
            continue

        name = asset_data.asset_name
        cls = asset_data.asset_class_path.asset_name
        package_name = asset_data.package_name
        unreal.log(name)

        with open(path, "a", encoding="utf-8") as f:
            f.write(f"|{name}|{cls}|{package_name}\n")

    unreal.log("已生成Markdown文档")


# third()

# data = unreal.EditorAssetLibrary.find_asset_data("/Game/StarterContent/Blueprints/Blueprint_Effect_Fire")
# name = data.asset_class_path.asset_name
# unreal.log(str(name).lower())
# path = r"C:\Users\sober\Documents\Unreal Projects\LyraStarterGame\03_my03.md"
# with open(path, "a", encoding="utf-8") as f:
#     f.write("abc")

# 4. 实现蓝图版本管理工具，记录每次修改的属性变化
def fourth():
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")