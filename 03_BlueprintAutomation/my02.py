import unreal

# 1. 批量创建 10 个 Actor 蓝图，并统计它们的父类
# def first(package_path):
#     factory = unreal.BlueprintFactory()
#     factory.set_editor_property("parent_class", unreal.Actor)
#     asset_tools = unreal.AssetToolsHelpers().get_asset_tools()

#     for i in range(10):
#         name = f"BP_MyActor{i}"
#         asset_tools.create_asset(name, package_path, unreal.Blueprint, factory)
# 2. 编写工具：列出项目中每个蓝图的父类关系
# 一二题重复了


# 3. 编写脚本，把一批蓝图的父类统一改成 Character
def third():
    selected_asset = unreal.EditorUtilityLibrary.get_selected_asset_data()

    for asset_data in selected_asset:
        if asset_data.asset_class_path.asset_name != "Blueprint":
            continue

        object = unreal.EditorAssetLibrary.load_asset(asset_data.package_name)
        if not isinstance(object, unreal.Blueprint):
            continue

        unreal.BlueprintEditorLibrary.reparent_blueprint(object, unreal.Character)


# 4. 研究：如何在 Python 中通过编辑器工具调用蓝图组件的增删
#    （提示：UE Python 无 SCS 接口，需要 C++ 编辑器扩展）
#
#   【结论】提示已过时：UE5.8 的 SubobjectDataSubsystem（桩路径
#   unreal.py:666504）已把蓝图组件树的增删改查全部暴露给 Python，
#   不需要写 C++ 编辑器扩展。
#
#   套路和 my01.py 第一题一样（"句柄"三步曲）：
#     ① k2_gather_subobject_data_for_blueprint(bp) 拿到组件树句柄列表
#     ② 用 AddNewSubobjectParams(父句柄, 组件类, 蓝图) 组增删请求
#     ③ add_new_subobject 增 / delete_subobject 删
def fourth(package_path="/Game/Test"):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    bp = asset_tools.create_asset(
        "BP_ComponentDemo", package_path, unreal.Blueprint, factory
    )
    if not isinstance(bp, unreal.Blueprint):
        unreal.log_error("创建蓝图失败")
        return None

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    if not subsystem:
        return

    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    root_handle = handles[0] if handles else None
    if not root_handle:
        unreal.log_error("取不到根组件句柄")
        return None

    # 增：给蓝图挂一个 StaticMeshComponent
    params = unreal.AddNewSubobjectParams(root_handle, unreal.StaticMeshComponent, bp)
    handle, err_text = subsystem.add_new_subobject(params)
    if not handle:
        unreal.log_error(f"新增组件失败:{err_text}")
        return None
    unreal.log("已新增 StaticMeshComponent")

    # 删：把刚才加的那个组件删掉
    deleted = subsystem.delete_subobject(root_handle, handle)
    unreal.log(f"已删除组件，返回 {deleted} 个")

    unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
    return bp


# fourth("/Game/Test")

# all_asset = unreal.EditorAssetLibrary.list_assets("/Game")
# asset_path = all_asset[0]
# asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
# object = unreal.EditorAssetLibrary.load_asset(asset_path)
# unreal.log(object.get_name())
# object = unreal.EditorAssetLibrary.load_asset(asset_data.package_name)
# unreal.log(object.get_name())
