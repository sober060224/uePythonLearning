import unreal


# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 创建一个蓝图，它继承自 Character，并包含一个
#    StaticMeshComponent 作为视觉表示
# ─────────────────────────────────────────────────────────
# 解题思路：
#   ① 先"造外壳"：用 BlueprintFactory 生成一张继承自 Character 的蓝图资产
#      （工厂 = 流水线，告诉引擎"我要生产什么类型的东西"）
#   ② 再"往里装组件"：用 SubobjectDataSubsystem 往蓝图的组件树里
#      添加一个 StaticMeshComponent（游戏里角色的可见身体）
#   ③ 最后保存资产
#
# 为什么加组件不用"直接 new 一个组件对象"？
#   蓝图组件树的增删改，底层由编辑器统一管理，路径是：
#       要改谁 → 通过"句柄(handle)"定位 → 再操作
#   句柄就像"图书馆的索书号 / 快递单号"：
#       它不是一个组件对象本身，而是一张"找得到它"的凭证。
#       你拿着索书号去书架拿书；书架挪了，书号不变，照样找得到。
#
# 小坑：AssetToolsHelpers / AssetRegistryHelpers 的 get_* 方法是"类方法"，
#       可以不加括号直接通过类调用，例如 unreal.AssetToolsHelpers.get_asset_tools()。
def first(asset_name, package_path):
    # (1) 造外壳：用工厂创建一张蓝图资产
    #     create_asset 返回的是 Object，所以要用 isinstance 确认它确实是蓝图。
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Character)
    bp = asset_tools.create_asset(asset_name, package_path, unreal.Blueprint, factory)
    if not isinstance(bp, unreal.Blueprint):
        unreal.log_error(f"创建蓝图失败：{asset_name}")
        return

    # (2) 装组件：先拿到编辑蓝图组件树的总管
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    if not subsystem:
        unreal.log_error("未取到引擎子系统实例")
        return

    # 收集蓝图目前的组件树，第一个(索引0)一般是根节点(场景根组件)
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    root_handle = handles[0] if handles else None
    if not root_handle:
        unreal.log_error("未取到根组件句柄")
        return

    # 组装"加组件请求"：挂在哪个父节点下 + 什么类型的组件 + 属于哪张蓝图
    params = unreal.AddNewSubobjectParams(root_handle, unreal.StaticMeshComponent, bp)
    # 返回值：(新组件句柄, 错误描述文本)
    new_handle, text = subsystem.add_new_subobject(params)
    if not new_handle:
        unreal.log_error(f"添加组件失败:{text}")
        return

    # (3) 保存。save_asset 需要"对象路径"(带最后一个点 + 资产名)，
    #     get_path_name() 返回的正是这种格式。
    if unreal.EditorAssetLibrary.save_asset(bp.get_path_name()):
        unreal.log(f"保存成功：{bp.get_name()}")


# resource_name = "BP_MyCharacter"
# package_path = "/Game/Character"
# first(resource_name, package_path)


# ─────────────────────────────────────────────────────────
# 2. 批量创建 10 个不同的 Actor 蓝图，每个都有独特名称
# ─────────────────────────────────────────────────────────
# 解题思路：
#   ① 复用同一个工厂：父类类型是一样的话，工厂可以只配置一次，
#      循环里反复调用 create_asset 即可
#   ② create_asset 返回 None 表示创建失败（最常见原因是名字已存在），
#      所以每次都要判空，别让 None 一路传到后面
#   ③ 引擎创建资产只是"放进了内存 + 标记脏"，磁盘上的 .uasset
#      是创建后你自己 save 出来的
#
# 小坑：蓝图资产默认创建后不会自动保存；批量创建后一定要记得逐一保存。
def second(package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)

    for i in range(10):
        name = f"BP_MyActor{i}"
        bp = asset_tools.create_asset(name, package_path, unreal.Blueprint, factory)
        if not isinstance(bp, unreal.Blueprint):
            unreal.log_error(f"第{i}个蓝图创建失败：{name}（可能已存在）")
            continue
        # 校验通过才保存；写成一行能读，但先 if 后 save 更清晰
        unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
        unreal.log(f"已创建并保存：{name}")


# second("/Game/Actors")


# ─────────────────────────────────────────────────────────
# 3. 编写一个工具，列出项目中所有蓝图的父类关系图
# ─────────────────────────────────────────────────────────
# 解题思路：
#   ① 先用 find_asset_data 拿到 AssetData（只读元数据，不加载资产体），
#      按"资产类名是否等于 Blueprint"快速过滤，跳过海量非蓝图资产
#      —— UE5 的类名要读 asset_class_path.asset_name（UE4 的 asset_class 已废弃）
#   ② 被过滤后的少量蓝图才 load_asset 加载（加载很贵，能少加载就少加载）
#   ③ 蓝图对象可以直接调用 get_blueprint_parent_class() 拿到父类 Class，
#      再把 Class 转成可读的类名打印出来
#
# 注意：这里必须加载蓝图，因为"父类"信息只存在蓝图本体里，
#       AssetData 的注册元数据里没有直接的"父类"字段。
def third():
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")

    # 先只挑出蓝图，避免把几千个素材全部加载一遍
    blueprint_paths = []
    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # Name 是"特殊字符串"，比较前先 str() 转成真正的字符串更稳
        if str(asset_data.asset_class_path.asset_name) != "Blueprint":
            continue
        blueprint_paths.append(asset_path)

    unreal.log(f"共找到 {len(blueprint_paths)} 张蓝图，开始解析父类…")

    for path in blueprint_paths:
        bp = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(bp, unreal.Blueprint):
            continue

        # 父类 Class → 顶资产路径(TopLevelAssetPath) → 取其中的 asset_name
        parent_class = bp.get_blueprint_parent_class()
        parent_name = parent_class.get_class_path_name().asset_name
        unreal.log(f"{path}  ←  BP_XXX 的父类：{parent_name}")


# third()


# ─────────────────────────────────────────────────────────
# 4. 查找所有编译有错误的蓝图（提示：检查编译状态）
# ─────────────────────────────────────────────────────────
# 解题思路：
#   ① 蓝图有个只读属性 status（BlueprintStatus 枚举）：
#        BS_UP_TO_DATE / BS_UP_TO_DATE_WITH_WARNINGS / BS_DIRTY / BS_ERROR …
#      只要等于 BS_ERROR 就是"上次编译失败"，不用真的去重新编译它
#   ② 判断对象是不是蓝图、以及类名过滤，都用 isinstance / str()，
#      不要拿"编译去试"，编译是有副作用的操作，会真的改刷新蓝图状态
def fourth():
    unreal.log("所有编译错误的蓝图：")
    all_assets = unreal.EditorAssetLibrary.list_assets("/Game")
    bad_bt = 0

    for asset_path in all_assets:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if str(asset_data.asset_class_path.asset_name) != "Blueprint":
            continue

        obj = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not isinstance(obj, unreal.Blueprint):
            continue

        # 编译失败 = 状态为 BS_ERROR —— 读状态，不触发编译
        if obj.status == unreal.BlueprintStatus.BS_ERROR:
            bad_bt += 1
            unreal.log(f"  ✗ {obj.get_path_name()}")

    unreal.log(f"完成，共发现 {bad_bt} 张编译错误的蓝图。")


# fourth()
