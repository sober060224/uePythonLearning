"""
=============================================================
资产管理 第1课：列出和搜索资产
=============================================================

学习目标：
  - 掌握 EditorAssetLibrary 的资产查询功能
  - 学会按类型、路径搜索资产
  - 获取资产的详细元数据

核心类：unreal.EditorAssetLibrary
  - 不需要加载资产到内存即可查询
  - 适合批量操作和项目管理工具

习题可能用到的 API：
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]  —— 列出指定路径下的所有资产路径
  unreal.EditorAssetLibrary.find_asset_data(asset_path: str) -> AssetData  —— 获取资产的元数据（类型、名称、路径等）
  unreal.EditorAssetLibrary.does_asset_exist(asset_path: str) -> bool  —— 判断指定资产是否存在
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]  —— 查找引用该资产的所有包
  unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).get_tag_values(asset_path: str) -> Map[Name, str]  —— 获取资产的所有标签值
    （注意：get_tag_values 只在 EditorAssetSubsystem 上，EditorAssetLibrary 没有这个方法）
  unreal.ScopedSlowTask(work: float, desc: Union[Text, str] = "", enabled: bool = True)  —— 创建耗时任务的进度条上下文
  task.enter_progress_frame(work: float = 1.0, desc: Union[Text, str] = "") -> None  —— 推进进度条并更新说明文字
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 列出指定路径下的所有资产
# ─────────────────────────────────────────────────────────

# 【UE 概念】UE 的所有资产都存放在 /Game/ 虚拟路径下，对应磁盘上的 Content/ 文件夹。
#   Python 脚本运行在编辑器中，通过 /Game/ 前缀访问项目资产，而不是用磁盘路径。
#   比如磁盘上的 Content/Characters/Hero.uasset 在 Python 里写成 "/Game/Characters/Hero"。

# list_assets(path, recursive=True, include_folder=False)
# path: /Game 下的路径，必须以 /Game 开头，如 "/Game/Characters"
# recursive: 是否递归搜索子目录，True 表示搜索所有嵌套的子文件夹
# include_folder: 是否包含文件夹本身（文件夹路径以 "/" 结尾）

# 【常见陷阱】初学者容易把磁盘路径写进去，比如 "Content/Characters"，
#   这样会找不到任何资产。一定要用 "/Game/..." 格式。

# 列出 /Game 下所有资产（递归搜索所有子目录）
all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)
unreal.log(f"项目共有 {len(all_assets)} 个资产")

# 只列出 /Game/Characters 下的直接资产（不递归，只看当前层级）
# 【为什么先检查 does_directory_exist？】如果路径不存在，list_assets 会返回空数组，
#   不会报错，但这样你就无法区分"目录为空"和"目录不存在"两种情况。
if unreal.EditorAssetLibrary.does_directory_exist("/Game/Characters"):
    direct_assets = unreal.EditorAssetLibrary.list_assets(
        "/Game/Characters", recursive=False, include_folder=False
    )
    unreal.log(f"\n/Game/Characters 目录下有 {len(direct_assets)} 个资产:")
    for asset in direct_assets:
        unreal.log(f"  {asset}")

# ─────────────────────────────────────────────────────────
# 2. 列出目录结构
# ─────────────────────────────────────────────────────────


def print_directory_tree(path, indent=0, max_depth=3):
    """打印资产目录树"""
    # 【为什么限制深度？】大型项目的 /Game 目录可能有几十层嵌套，
    #   不限制会导致输出海量信息甚至超时。max_depth 是个好习惯。
    if indent > max_depth:
        return

    # include_folder=True 表示把文件夹也作为结果返回
    # 【注意】文件夹路径以 "/" 结尾，比如 "/Game/Characters/"，
    #   而文件路径不带尾部斜杠，比如 "/Game/Characters/Hero"。
    #   这个区别在后面判断是文件还是文件夹时很重要。
    sub_dirs = unreal.EditorAssetLibrary.list_assets(
        path, recursive=False, include_folder=True
    )

    for item in sub_dirs:
        # 【初学者易错点】item 是完整路径字符串，如 "/Game/Characters/"。
        #   如果直接 item.split("/")[-1]，对带尾部 "/" 的路径会取到空字符串 ""。
        #   所以先 rstrip("/") 去掉尾部斜杠，再取最后一段作为名称。
        clean_path = item.rstrip("/")
        item_name = clean_path.split("/")[-1]
        # 【UE 概念】does_directory_exist 判断的是 UE 内容目录，不是磁盘目录。
        #   这个函数返回 True 说明这个路径在 UE 里是一个文件夹。
        is_folder = unreal.EditorAssetLibrary.does_directory_exist(item)

        if is_folder:
            unreal.log(f"{'  ' * indent}📁 {item_name}/")
            # 递归进入子文件夹，indent+1 让输出缩进更清晰
            print_directory_tree(item, indent + 1, max_depth)
        else:
            unreal.log(f"{'  ' * indent}📄 {item_name}")


unreal.log("\n--- 项目目录结构 (前3层) ---")
print_directory_tree("/Game", max_depth=3)

# ─────────────────────────────────────────────────────────
# 3. 按类型搜索资产
# ─────────────────────────────────────────────────────────


def find_assets_by_class(class_name, search_path="/Game"):
    """
    按类名搜索资产
    class_name: 如 "Texture2D", "StaticMesh", "Blueprint" 等
    """
    # 【UE 概念】每个资产都有一个类型（Class），比如纹理是 Texture2D，
    #   静态网格体是 StaticMesh，蓝图是 Blueprint。
    #   find_asset_data 返回的 AssetData 对象包含 asset_class_path 属性，
    #   它是一个 SoftClassPath 对象，其 asset_name 就是类型名称字符串。
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    matching = []

    for asset_path in all_assets:
        # find_asset_data 不需要把资产加载到内存，非常高效。
        # 它返回的是"元数据"——关于资产的信息，不是资产本身。
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        # 【UE5 注意】UE4 用 asset_data.asset_class，UE5 改成了 asset_class_path.asset_name。
        #   如果你看到 AttributeError: 'AssetData' has no attribute 'asset_class'，
        #   就是用了旧写法。现在要写 asset_class_path.asset_name。
        asset_class = str(asset_data.asset_class_path.asset_name)
        # 用 in 做模糊匹配，这样 "Mesh" 能匹配 "StaticMesh" 和 "SkeletalMesh"
        if class_name.lower() in asset_class.lower():
            matching.append(asset_data)

    return matching


# 搜索所有纹理
textures = find_assets_by_class("Texture2D")
unreal.log(f"\n找到 {len(textures)} 个纹理:")
for tex in textures[:10]:
    unreal.log(f"  {tex.package_name} - {tex.asset_name}")

# 搜索所有静态网格体
meshes = find_assets_by_class("StaticMesh")
unreal.log(f"\n找到 {len(meshes)} 个静态网格体:")
for mesh in meshes[:10]:
    unreal.log(f"  {mesh.package_name} - {mesh.asset_name}")

# ─────────────────────────────────────────────────────────
# 4. 获取资产详细信息
# ─────────────────────────────────────────────────────────


def inspect_asset(asset_path):
    """打印资产的详细信息"""
    # 【为什么先检查存在？】does_asset_exist 是防御性编程的好习惯。
    #   如果路径写错了，后续的 find_asset_data 会返回空的 AssetData，
    #   不会报错但会得到空值，调试起来很困惑。
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.log_warning(f"资产不存在: {asset_path}")
        return

    # 【UE 概念】AssetData 是资产的"身份证"，包含：
    #   - asset_name: 资产名称（不含路径），如 "Hero"
    #   - package_name: 完整的包路径，如 "/Game/Characters/Hero"
    #   - asset_class_path: 资产类型，如 Texture2D
    #   - 还有 group_path、tags 等信息
    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"资产: {asset_data.asset_name}")
    unreal.log(f"路径: {asset_data.package_name}")
    unreal.log(f"类型: {asset_data.asset_class_path}")

    # 【UE 概念】标签（Tags）是 UE 资产的自定义元数据。
    #   比如你可以在纹理上设置 "Author" 标签记录作者名。
    #   get_tag_values 返回一个字典：{标签名: 标签值}。
    #   标签是 Name 类型（不是 str），所以打印时需要转成字符串。
    # 【易错点】get_tag_values 定义在 EditorAssetSubsystem 上，不在 EditorAssetLibrary 上，
    #   调 EditorAssetLibrary.get_tag_values 会直接 AttributeError。
    tags = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).get_tag_values(asset_path)
    if tags:
        unreal.log(f"标签数量: {len(tags)}")
        for tag_name, tag_value in tags.items():
            unreal.log(f"  {tag_name}: {tag_value}")

    # 【UE 概念】引用关系是 UE 资产系统的核心概念。
    #   比如一个材质引用了一个纹理，那么这个纹理就被材质"引用"。
    #   find_package_referencers_for_asset 返回引用该资产的所有包路径。
    #   这在清理资产、理解依赖关系时非常有用。
    # 【注意】返回的是包路径（.uasset），不是资产对象。
    references = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
        asset_path
    )
    unreal.log(f"被 {len(references)} 个资产引用:")
    for ref in references[:5]:
        unreal.log(f"  ← {ref}")


# 测试（替换为你项目中的实际资产路径）
# 先判断列表非空再取下标 —— 空目录时 all_assets[0] 会 IndexError。
if all_assets:
    # 演示：检查列表里的第一个资产
    inspect_asset(all_assets[0])
else:
    unreal.log_warning("没有找到任何资产，跳过演示")

# ─────────────────────────────────────────────────────────
# 5. 查找未使用的资产
# ─────────────────────────────────────────────────────────


def find_unused_assets(search_path="/Game"):
    """查找没有被任何其他资产引用的资产（可能是废弃资产）"""
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)
    unused = []

    # 【UE 概念】ScopedSlowTask 是 UE 提供的进度条工具。
    #   当你需要遍历大量资产时（可能几千个），没有进度条用户会以为程序卡死了。
    #   构造参数：总工作量（数字）、描述文字。
    task = unreal.ScopedSlowTask(len(all_assets), "正在查找未使用的资产...")
    # make_dialog(True) 显示一个带"取消"按钮的进度对话框
    # 【注意】如果不调用 make_dialog，进度条不会显示，但任务仍会执行。
    task.make_dialog(True)

    for asset_path in all_assets:
        # should_cancel() 检查用户是否点击了取消按钮
        # 这是长时间操作中必须有的"退出机制"，否则用户无法中断
        if task.should_cancel():
            break

        # enter_progress_frame 推进一个单位的进度
        # 第一个参数是工作量（和构造时的总数对应），第二个参数是当前描述
        task.enter_progress_frame(1.0, f"检查: {asset_path.split('/')[-1]}")

        # 【为什么这里不用判断文件夹？】list_assets 默认 include_folder=False，
        #   返回的全是资产路径，不会包含文件夹 —— 只有显式传 include_folder=True
        #   时才需要再用 does_directory_exist 过滤。

        referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path,
            load_assets_to_confirm=True,  # 删除/判定前把需要加载才能确认的引用也算进来
        )

        # 【初学者易错点】find_package_referencers_for_asset 的结果可能包含
        #   资产自身（自引用）。比如一个蓝图的默认值引用了自身。
        #   所以要过滤掉自身，只看"外部引用"。
        external_refs = [r for r in referencers if r != asset_path]

        if len(external_refs) == 0:
            unused.append(asset_path)

    return unused


# 取消注释以运行（可能需要较长时间）
# unused = find_unused_assets("/Game")
# unreal.log(f"\n找到 {len(unused)} 个未使用的资产:")
# for path in unused[:20]:
#     unreal.log(f"  {path}")
