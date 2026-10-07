---
type: workflow
title: 资产管理流：枚举、导入导出与批量操作
description: 说明第 02 章六份脚本如何用 list_assets/find_asset_data 做零加载枚举、用 AssetImportTask/AssetExportTask 走任务式导入导出、用 rename_asset 同时完成重命名与移动，以及删除、整合、磁盘大小计算各自的约束与已知缺陷。
tags: [asset-management, editor-asset-library, import-export, batch-operations, safety]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# 资产管理流：枚举、导入导出与批量操作

第 02 章是仓库里最大的一章（六份脚本共 2288 行），也是唯一通篇围绕 `unreal.EditorAssetLibrary` 展开的章节。它的主线可以概括成一句话：**先用「不加载资产」的手段把范围缩小，只对真正命中的资产付出 `load_asset` 的代价，然后对这批资产做批量改名/移动/删除，并在删除前强制检查引用。**

## 六份文件的角色

| 文件 | 行数 | 内容 |
|---|---|---|
| `02_AssetManagement/01_list_assets.py` | 256 | 枚举与查询：`list_assets`、目录树、按类名筛选、`AssetData` 元数据、标签、引用关系、未使用资产 |
| `02_AssetManagement/02_import_export.py` | 465 | 导入导出：`AssetImportTask`、`FbxImportUI` 选项、批量导入、纹理导入后配置、`AssetExportTask` + `Exporter`、`create_asset` 造材质实例 |
| `02_AssetManagement/03_asset_actions.py` | 456 | 增删改：重命名、批量改名、标准前缀、移动、安全删除、清理未使用、整合、保存 |
| `02_AssetManagement/my01.py` | 311 | 练习稿：目录树、按类查询、`generate_asset_report`、**资产体积 Top10**、材质反查网格体、组合搜索、Markdown 报告 |
| `02_AssetManagement/my02.py` | 521 | 练习稿：导入管线四练习（含 `scan_watch_folder` 状态集合、按分辨率分类导出、导入后建 MI 并分配、选中资产连同依赖导出） |
| `02_AssetManagement/my03.py` | 277 | 练习稿：资产清理向导（未用/重复/命名不规范）、按规范改名、按日期归档、跨项目迁移 |

官方三课共用同一体裁（见 `/openwiki/architecture/script-conventions.md`）：顶部 docstring 列「习题可能用到的 API」及签名，正文用编号分节，**所有示例调用都注释掉，文件末尾只留一行 `unreal.log("…完成！")`**，最后是 `🎯 练习题`。`my*.py` 是把练习题真的写出来的个人稿，因此更接近可用工具，但也带着调试碎片（`my03.py:266-278` 留着一段 BFS 草稿）。

## 一、查询铁律：能查元数据就不要加载资产

### `/Game` 是虚拟路径

`/Game` 对应磁盘上的 `Content/`，但脚本里**只写 `/Game/...`**。`01_list_assets.py:35-45` 的注释点明：写磁盘路径（`Content/Characters`）不会报错，只会得到空结果，这是最难查的一类失败。

### 三条查询原语

| 调用 | 返回 | 是否加载 |
|---|---|---|
| `list_assets(directory_path, recursive=True, include_folder=False)` | `Array[str]` 路径 | 否 |
| `find_asset_data(asset_path)` | `AssetData` 元数据 | 否 |
| `does_asset_exist` / `does_directory_exist` | `bool` | 否 |

`01_list_assets.py:106-133` 的 `find_assets_by_class` 是这个模式的范例，三步固定：

1. `list_assets(search_path, recursive=True)` 只拿到路径字符串；
2. 对每个路径 `find_asset_data(asset_path)` 读 `asset_class_path` 做**预筛**；
3. 命中的才在后续步骤 `load_asset`。

`02_AssetManagement/my02.py:283-292` 把这条写得最清楚，并给出了反例的代价：如果第 2、3 步写反（先 `load` 再判类型），等于把整库读进内存，「脚本会慢到像卡死」。

### `AssetData` 的字段

`AssetData` 是 `StructBase` 子类，用到的三个字段：

| 字段 | 内容 |
|---|---|
| `asset_name` | 资产短名（`unreal.Name`，**没有** `startswith`/`lower`，要先 `str()`） |
| `package_name` | 包路径，如 `/Game/Characters/Hero` |
| `asset_class_path` | 类型，`TopLevelAssetPath` 对象 |

读类名有**两种写法在仓库里并存**，都有效：

| 写法 | 出处 | 结果 |
|---|---|---|
| `str(asset_data.asset_class_path.asset_name)` | `01_list_assets.py:125`、`my03.py:74` | `"Texture2D"` |
| `str(asset_data.asset_class_path).split(".")[-1]` | `03_asset_actions.py:170-172` | `"Texture2D"`（先得到 `"Engine.Texture2D"` 再切） |

`01_list_assets.py:122-124` 的注释把 `asset_class` 当成了「UE5 里已经改掉」的旧属性；按 `AGENTS.md` 的强制核验规则查桩文件后可知它**仍然存在但已废弃**（详见 `/openwiki/concepts/nonexistent-and-deprecated-apis.md`），推荐写法没错，理由描述偏了。

### 模糊匹配的两个后果

`find_assets_by_class` 用 `class_name.lower() in asset_class.lower()`（`01_list_assets.py:127-128`）。好处是 `"Mesh"` 能一次拿到 `StaticMesh` 与 `SkeletalMesh`；代价是**无法精确匹配**，`"Material"` 会连带命中 `MaterialInstanceConstant`、`MaterialFunction`。这个取舍在 `03_asset_actions.py:170`（用 `split(".")[-1]` 精确取类名再查 `PREFIX_MAP` 字典）里被避免了——同一章里两种策略并存。

### 目录树的三个坑（`01_list_assets.py:65-97`）

```python
sub_dirs = list_assets(path, recursive=False, include_folder=True)
for item in sub_dirs:
    clean_path = item.rstrip("/")          # ①
    item_name = clean_path.split("/")[-1]  # ②
    is_folder = does_directory_exist(item) # ③
```

- ① `include_folder=True` 时**文件夹路径带尾斜杠**（`/Game/Characters/`），直接 `split("/")[-1]` 会返回空串，必须先 `rstrip("/")`。
- ③ 判断「这一项是文件夹还是资产」不能靠尾斜杠，要靠 `does_directory_exist(item)`（传带斜杠的原始值）。
- `max_depth=3` 是必需的防御：大型项目的 `/Game` 有几十层嵌套，不限制会爆输出。

另外 `01_list_assets.py:50-52` 用 `does_directory_exist` 包住 `list_assets` 是有意义的：路径不存在时 `list_assets` 只返回空数组，不区分「空目录」与「目录不存在」。

## 二、磁盘大小：`AssetData` 里没有这个信息

`AssetData` 没有 `disk_size` 属性（桩文件里 `def disk_size` 零命中），要算体积必须**离开引擎 API 回到 `os.path`**。官方五课都没写这个需求，两份练习稿各自实现了一遍，路径不同：

| | `my01.py:151-170` | `my03.py:41-66` |
|---|---|---|
| 基准目录 | `unreal.Paths.project_dir()` + `"Content"` | `os.path.abspath(unreal.Paths.project_content_dir())` 再 `os.path.normpath` |
| 相对路径 | `str(asset_path).removeprefix("/Game").replace("/", os.sep)` | `asset_path.removeprefix("/Game/")` 再 `os.path.normpath` |
| 扩展名 | 硬编码 `.uasset` + `os.path.isfile` 过滤 | `next((a for a in [path + ".uasset", path + ".umap"] if os.path.exists(a)), None)` |
| 用途 | 按体积 `sorted(..., key=lambda item: item[2], reverse=True)[:10]` | 按体积分桶，作「重复资产」的第一道过滤 |

`my03.py` 的 `next(...)` 写法更完整：关卡资产存成 `.umap` 而不是 `.uasset`，硬编码 `.uasset` 会漏掉所有关卡（`my03.py:181-215` 的归档功能也复用了这个判断，用 `asset_class_path.asset_name == "World"` 决定扩展名）。

**反向换算**（磁盘路径 → 引擎路径）在 `my03.py:88-95`：

```python
dir = dir.removeprefix(f"{content_dir}\\")
dir = unreal.Paths.normalize_filename(dir)     # 全部斜杠转成 /
dir = unreal.Paths.combine(["/Game", dir])
dir = dir.removesuffix(".umap").removesuffix(".uasset")
```

`unreal.Paths.combine(cls, paths: Array[str]) -> str` 与 `unreal.Paths.normalize_filename(cls, path: str) -> str` 都是 `Paths` 上的 classmethod。`my03.py:109-127` 留了一段试验这个换算的草稿，注释里记录了 `removeprefix(content_dir)`（不加尾分隔符）会剩一个前导反斜杠的失败经验。

## 三、引用关系：两个方向、一个开关

### 向上查引用

`find_package_referencers_for_asset(asset_path, load_assets_to_confirm=False) -> Array[str]` 返回**引用该资产的包路径**。三处实现都做了同一件必要动作——**过滤自引用**：

```python
external_refs = [r for r in referencers if r != asset_path]
```

`01_list_assets.py:241-246` 的注释解释了原因：资产可能引用自身（例如蓝图的默认值），这不算「被外部使用」。

一个细节差异：`01_list_assets.py:244` 与 `03_asset_actions.py:259` 直接比较 `asset_path`，而 `my03.py:48` 写的是 `asset_path.split(".")[0]`。后者更稳——`find_package_referencers_for_asset` 返回的是**包名**（`/Game/A/B`），而调用方传入的路径可能带 `.AssetName` 后缀，不切掉就过滤不掉自引用。

### `load_assets_to_confirm` 是准确度开关

默认 `False` 会漏掉「必须加载资产才能确认」的那类引用，因此在**判定未使用**与**删除前检查**的场景必须显式传 `True`。这个参数出现在 `01_list_assets.py:236-239`、`03_asset_actions.py:254-257`、`03_asset_actions.py:325-328` 三处，注释措辞一致：「删除/判定前把需要加载才能确认的引用也算进来」。代价是它会真的加载资产，让本来零加载的遍历变得昂贵。

### 向下查依赖

`AssetRegistry.get_dependencies(package_name: Name, dependency_options) -> Optional[Array[Name]]` 是相反方向（本资产引用了谁），入口是 `unreal.AssetRegistryHelpers.get_asset_registry()`。返回值是 `Optional`，**必须 `or []` 兜底**，否则 `None` 上 for 遍历会 `TypeError`（`my02.py:505-506` 的【易错点】）。

`AssetRegistryDependencyOptions` 是开关集合，两份练习稿的选法不同：

| 文件 | 开启的引用类型 |
|---|---|
| `my03.py:243-245` | `include_hard_package_references`、`include_soft_package_references` |
| `my02.py:481-486` | 再加 `include_game_package_references`、`include_editor_only_package_references`（「迁移才完整」） |

依赖遍历必须处理**环**。`my02.py:436-455` 的注释把做法拆成两个容器：`stack`（待查询清单）+ `pkgs`（成果袋，同时充当已访问标记），并入栈前查 `dep not in pkgs`、出栈后再查 `pkg in pkgs`。`my03.py:249-262` 的版本用 `queue.Queue` + `selected_package` 列表，同样防环（`if t in selected_package: continue`），但列表的 `in` 是 O(n)，在包数量大时会退化成 O(n²)。

### 未使用资产遍历的成本

`01_list_assets.py:209-249` 的 `find_unused_assets` 结构是：`list_assets` 全库 → 对**每个**资产调一次 `find_package_referencers_for_asset(..., load_assets_to_confirm=True)` → 过滤自引用 → 空则为未使用。这是 O(N) 次资源注册表查询加全量加载，所以外面套了 `ScopedSlowTask`：

```python
task = unreal.ScopedSlowTask(len(all_assets), "正在查找未使用的资产...")
task.make_dialog(True)   # 不调用则不显示进度条，但任务照常执行
for asset_path in all_assets:
    if task.should_cancel():
        break
    task.enter_progress_frame(1.0, f"检查: {asset_path.split('/')[-1]}")
```

`should_cancel()` 是长时间操作**必须**留的中断点，否则用户只能等。写法的另一种形态见 `03_asset_actions.py:312-320` 与 `03_asset_actions.py:220-233`：`with unreal.ScopedSlowTask(...) as task:` 直写法（`ScopedSlowTask` 本身就是上下文管理器），以及与 `/openwiki/reference/utils-ui-helpers.md` 里 `ProgressBar` 包装类的差别。

## 四、导入：任务模式的两段式

导入走的是**先描述、后执行**的任务模式，这样同一个接口天然支持批量。

```python
task = unreal.AssetImportTask()
task.filename = file_path                                   # 磁盘上的源文件
task.destination_path = destination_path                    # /Game/ 下的目录
task.destination_name = os.path.splitext(os.path.basename(file_path))[0]
task.replace_existing = True
task.automated = True
task.save = True
task.options = options                                      # 可选，挂导入 UI 类
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
imported_paths = task.imported_object_paths
```

（`02_import_export.py:39-77` 是单文件版，`:84-148` 是 FBX 版，`:156-208` 是批量版）

六个属性的作用与坑：

| 属性 | 作用 | 坑 |
|---|---|---|
| `filename` | 磁盘源文件路径 | 必须真实存在，否则导入静默失败 |
| `destination_path` | `/Game/` 下的目标目录 | 不能写磁盘路径 |
| `destination_name` | 资产名，**不含路径也不含扩展名** | 直接写文件名会把扩展名带进资产名 |
| `replace_existing` | 覆盖同名资产 | 不开则重复导入会冲突 |
| `automated` | 跳过所有弹窗确认 | **批量脚本必备**，否则每个文件弹一次对话框 |
| `save` | 导入后自动落盘 | 不开的话资产只在内存里，关编辑器就丢 |

结果读取有两组：`task.imported_object_paths`（`Array[str]`，失败时为空列表——`02_import_export.py:70-73` 明确提示）与 `task.result` / `task.get_objects()`（`Array[Object]`）。

### `options` 是多态的

`task.options` 的类型是通用的 `Object`，按资产类型挂不同的导入配置类：

| 资产 | 选项类 | 关键开关 |
|---|---|---|
| FBX 网格体/动画 | `unreal.FbxImportUI()` | `import_as_skeletal`（False=静态网格体，True=骨骼网格体）、`import_mesh`、`import_animations` |
| 静态网格体细化 | `options.static_mesh_import_data` | `import_uniform_scale`、`combine_meshes`、`generate_lightmap_u_vs` |
| 骨骼网格体细化 | `options.skeletal_mesh_import_data` | `import_uniform_scale`、`import_morph_targets`、`update_skeleton_reference_pose` |
| 动画 | `options` + `options.skeleton` | **必须指定已有骨骼资产**，否则引擎不知道动画绑在哪套骨架上（`02_import_export.py:139-141` 留了注释版） |

### 批量导入只有一个重点

```python
tasks = []
for file_path in files_to_import:
    task = unreal.AssetImportTask()
    ...
    tasks.append(task)
asset_tools.import_asset_tasks(tasks)   # 一次性提交
```

`02_import_export.py:180-199` 的注释说明理由：先建全部任务再一次性交给引擎，引擎内部会优化内存与 I/O，比逐个导入快。结果按 task 分别汇总（`all_imported.extend(task.imported_object_paths)`），因为**每个 task 只记录自己的结果**。

`batch_import` 还示范了两个 Python 侧的细节：可变默认参数用 `file_extensions=None` 再在函数内建列表（`:165-168` 解释了共享可变默认值的陷阱）；扩展名匹配前先 `.lower()` 统一大小写（`:174`）。

### 导入后改配置：纹理是最典型的场景

`02_import_export.py:215-294` 的 `import_texture` 展示了「引擎用默认设置导入，脚本再改属性」的模式。三个必须记住的点：

- `set_editor_property` 的属性名必须与桩文件里**完全一致**：sRGB 的属性名是 `"srgb"`（全小写，不是 `s_rgb`），纹理组是 `"lod_group"`。
- `compression_settings` 等枚举属性**不能直接赋字符串**（`TypeError`），要先做字符串到枚举成员的映射表：

```python
compression_map = {
    "default": unreal.TextureCompressionSettings.TC_DEFAULT,
    "normalmap": unreal.TextureCompressionSettings.TC_NORMALMAP,
    "ui": unreal.TextureCompressionSettings.TC_EDITOR_ICON,
    "skybox": unreal.TextureCompressionSettings.TC_HDR,
}
```

- 枚举成员名必须全大写（`TEXTUREGROUP_WORLD`），不确定时用 `dir(unreal.TextureGroup)` 自查——这是 `06_MaterialAndTexture/03_texture_management.py:154` 推荐的核验方法。
- **改完必须 `save_asset`**，否则修改只在内存里。
- 映射表都配了 `.get(key, 默认成员)` 兜底，所以传入未知的字符串不会崩，只会静默退化为默认值——便于脚本化，但拼错参数名时不会报错。

### 不用外部文件造资产

`02_import_export.py:399-431` 的 `create_material_instance` 走 `asset_tools.create_asset(asset_name, package_path, unreal.MaterialInstanceConstant, factory)`。这里有个 UE API 的「分步」设计：**Factory 不负责设置父材质**，`MaterialInstanceConstantFactoryNew` 没有 `initial_parent` 属性，创建后必须再调 `unreal.MaterialEditingLibrary.set_material_instance_parent(new_asset, base_material)`。同类用法见 `/openwiki/workflows/editor-scripting-tools.md` 里用 `EditorUtilityWidgetBlueprintFactory` 造 EUW 资产。

`create_asset` 的完整签名（含 `calling_context: Name = "None"`、`overwrite_existing: bool = False`）写在 `02_import_export.py:23` 的 docstring 里。

## 五、导出：两条路，用途不同

| | 路径 A：`asset_tools.export_assets` | 路径 B：`AssetExportTask` + `Exporter` |
|---|---|---|
| 签名 | `export_assets(assets_to_export: Array[str], export_path: str) -> None` | `run_asset_export_task(task: AssetExportTask) -> bool` |
| 入参 | 路径字符串数组 + 目录 | 任务对象（含 `object`/`filename`/`options`） |
| 自定义选项 | **不支持** | 支持（如 `FbxExportOption`） |
| 导出器选择 | 按资产类型自动 | 自动或由 `task.exporter` 指定 |
| 批量 | 一次调用即批量 | 用 `run_asset_export_tasks(Array[...])` |
| 仓库用例 | `02_import_export.py:389`、`my02.py:517`、`my03.py:179` | `02_import_export.py:365` |

`02_import_export.py:363-365` 的注释把选择依据写死了：「**关键点：AssetTools.export_assets 不接受自定义选项，想用 FbxExportOption 必须走 Exporter.run_asset_export_task**」。

`AssetExportTask` 用到的属性（`02_import_export.py:340-358`）：

```python
task.object = asset                 # 要导出的是对象，不是路径字符串
task.filename = filename            # 「目录 + 资产名」，不带扩展名，导出器自己补 .fbx/.obj/.png
task.automated = True               # 不弹任何对话框
task.prompt = False                 # 不询问用户确认（无人值守必备）
task.replace_identical = True       # 目标文件已存在则覆盖
```

配套的三个准备动作：`load_asset` 拿到对象（拿不到就是路径写错，早退避免拿 `None` 继续跑）；`os.makedirs(export_directory, exist_ok=True)` 让脚本可反复运行（否则第二次会 `FileExistsError`）；`asset.get_name()` 取不带路径的资产名。

类的完整属性集还包括 `exporter`、`selected`、`use_file_archive`、`write_empty_files`、`ignore_object_list`、`errors`（`errors` 是失败原因数组，仓库里没用，是排查导出失败的第一手资料）。

## 六、重命名与移动是同一个操作

UE 的资产路径就是它的地址，所以**移动 = 重命名**：

```python
dest_dir = "/".join(current_path.split("/")[:-1])
success = unreal.EditorAssetLibrary.rename_asset(current_path, dest_dir + "/" + new_name)
```

`03_asset_actions.py:50-56` 记录了最容易踩的一条：`rename_asset` 的**第二个参数是完整目标路径**，不是新名字。写成 `"NewName"` 会失败。

移动版（`03_asset_actions.py:181-213`）在此基础上加了三步：`make_directory(destination_directory)` 递归建目录（已存在不报错）；拼 `dest_path`；**先 `does_asset_exist(dest_path)` 检查**——目标已有同名资产时 `rename_asset` 会失败，不检查就是静默失败（`:203-206` 的【初学者易错点】）。

`rename_asset` 还会自动更新所有引用（`03_asset_actions.py:58-62` 的「自动引用维护」），但**会在原位置留下 redirector**，见下文。

### 批量改名的顺序与安全边界

`03_asset_actions.py:74-119` 的 `batch_rename(search_path, prefix, suffix, find_text, replace_text)` 有两个刻意的选择：

- **顺序是先查找替换、再加前后缀**（`:107-113` 注释「顺序很重要」）。反过来会把新加的前缀也纳入替换范围。
- `recursive=False`（`:85-88`）：批量改名**不递归**，理由是跨目录改名容易出问题，建议「逐层操作，先处理一层确认无误再处理下一层」。
- 只有 `new_name != current_name` 才真的调 `rename_asset`，避免无意义的 I/O（`:115-116`）。

### 标准前缀表与它的两种实现

`03_asset_actions.py:129-145` 的 `PREFIX_MAP` 是全仓第二份前缀表，比 `08_AdvancedTopics/03_automation_testing.py:229-273` 里那份完整得多：

| 类名 | 前缀 | | 类名 | 前缀 |
|---|---|---|---|---|
| Blueprint | `BP_` | | AnimBlueprint | `ABP_` |
| Material | `M_` | | AnimSequence | `AS_` |
| MaterialInstanceConstant | `MI_` | | SoundWave | `S_` |
| Texture2D | `T_` | | WidgetBlueprint | `WBP_` |
| StaticMesh | `SM_` | | ParticleSystem | `PS_` |
| SkeletalMesh | `SK_` | | NiagaraSystem | `NS_` |
| DataTable | `DT_` | | DataAsset | `DA_` |

`add_standard_prefixes`（`:147-176`）用 `PREFIX_MAP.get(class_name, "")` 查表，**表里没有的类直接跳过**——这正是它不会像 `03_automation_testing` 那样产生子串误报的原因：它匹配的是切出来的裸类名，不是子串。

`my03.py:130-151` 的 `second()` 是同一需求的另一种实现，思路不同：**丢掉原名的第一个下划线之前的部分**再拼上标准前缀：

```python
prefix = str(asset_data.asset_name).split("_", 1)
if len(prefix) < 2:
    continue                      # 没有下划线会越界，必须挡
name = standard_prefix + prefix[1]
```

它用 `asset_data.package_name` 作 `rename_asset` 的源路径（注释：「路径名最好就是用包名」），目标路径用 `"/".join(asset_path.split("/")[:-1]) + f"/{name}"`。两种实现的差别在于：官方版是「没有前缀就加上」，练习版是「把非标准前缀替换成标准前缀」。

## 七、删除：三重防线与一处真实缺陷

删除是全章唯一有**强制门禁**的操作，防线叠了三层：

```python
def safe_delete_asset(asset_path):        # 03_asset_actions.py:240-268
    ...
    return True, []                        # (是否可安全删除, 引用列表)
```

1. **引用检查**（`:254-268`）：`find_package_referencers_for_asset(..., load_assets_to_confirm=True)`，过滤自引用后非空即判定「不可删」，并把前 5 个引用者打出来供人工判断。
2. **双重确认**（`:272-286`）：

```python
if force and not confirm_force:
    unreal.log_error("force=True 会跳过引用检查、可能造成引用断裂。...")
    return False
```

   注释解释了为什么需要第二个开关：**删除不可撤销，光一个 `force=True` 太容易误删**。这个设计值得作为仓库里「危险性 API 的包装惯例」记录。
3. **dry_run 预演**（`:304-350`）：`cleanup_unused_assets(search_path, dry_run=True)` 默认只报告不删除，注释明确说这是「先用 `dry_run=True` 看看会删什么，确认没问题再用 `dry_run=False`」的习惯。

### 已知缺陷：dry_run=False 时一个都删不掉

`cleanup_unused_assets` 的删除分支（`:342-346`）是：

```python
if not dry_run and unused:
    unreal.log("\n正在删除...")
    for path in unused:
        delete_asset(path, force=True)
```

`delete_asset` 的签名要求 `force=True` 时**必须同时给 `confirm_force=True`**（`:272-286`）。这里只给了 `force=True`，于是每一次调用都在第一道守卫处 `log_error` 并 `return False`——即 `cleanup_unused_assets("/Game", dry_run=False)` **一个资产也删不掉，只会在日志里刷满错误**。这是把「双重确认」这个正确设计用在内部调用上产生的结果：同一个文件里写了两套互相矛盾的契约，需要把内部调用改成 `delete_asset(path, force=True, confirm_force=True)`（或让 `cleanup_unused_assets` 自己接收确认参数）才自洽。

同章存在的其它删除相关 API 均未被课程使用：`delete_directory(directory_path)`、`delete_loaded_asset` / `delete_loaded_assets`（针对已加载对象的版本）。

## 八、整合（Consolidate）：清理重复资产

`03_asset_actions.py:356-393` 的 `consolidate_assets(asset_to_keep, asset_to_replace)` 语义是「把所有引用 `replace` 的地方改成引用 `keep`，然后删掉 `replace`」，用于清理重复导入的资产（同一张纹理导进来两次）。

唯一的坑写在 `:370-377`：**`consolidate_assets` 要求传对象，不是路径字符串**，必须先用 `load_asset` 转成对象再传入，传字符串会 `TypeError`。签名是 `consolidate_assets(asset_to_consolidate_to: Object, assets_to_consolidate: Array[Object]) -> bool`——第一个参数是单个对象，第二个是**数组**，所以调用写成 `consolidate_assets(keep_obj, [replace_obj])`。

## 九、保存：资产与关卡走不同 API

| 场景 | 调用 |
|---|---|
| 单个资产 | `save_asset(asset_path, only_if_is_dirty=True)` |
| 目录下全部脏资产 | `save_directory("/Game", only_if_is_dirty=True)`（`recursive=True` 是默认值） |
| 已加载对象 | `save_loaded_asset` / `save_loaded_assets` |
| 当前关卡 | `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()` |

`03_asset_actions.py:410-413` 解释了「脏资产」（dirty asset）概念与 `only_if_is_dirty` 的作用：只保存改过的，没改过的不重复写盘。

关卡的保存**不能**用 `save_asset`，`03_asset_actions.py:417-424` 特意写明了迁移理由：`EditorLevelLibrary` 属于已废弃的 Editor Scripting Utilities 插件，调用会打 `DeprecationWarning`，应改用 `LevelEditorSubsystem`。这一课是全仓少数**已经完成迁移**的地方（同章 `:19` 的 docstring 里仍推荐 `EditorLevelLibrary` 的旧路径，见 `/openwiki/concepts/nonexistent-and-deprecated-apis.md`）。

## 十、Python 侧做不到的事：修复 redirector

`03_asset_actions.py:11-13` 的学习目标里写了「修复引用关系」，但文件里没有任何对应实现。查桩文件可以确认原因：**Python API 完全没有暴露 redirector 的修复能力**——全文件大小写不敏感搜索 `redirector`，没有 `fix_up_redirectors`、没有 `Redirector` 类、也没有 `AssetTools.fix_up_referencers_*`。

能做的只有两半：

| 能力 | 入口 |
|---|---|
| **检测**是不是 redirector | `AssetData.is_redirector() -> bool`；或 `unreal.AssetRegistryHelpers.is_redirector(asset_data: AssetData) -> bool` |
| **修复** | 无 Python API，只能在内容浏览器里选中并右键「Fix Up Redirectors」 |

所以「重命名/移动后会出现 redirector」这件事必须作为**流程约束**记住：`rename_asset` 会自动把引用指到新路径（引用不会断），但旧路径会留下一个 redirector 存根；批量移动之后要专门跑一次内容浏览器的修复动作，否则 redirector 会不断累积。`ContentBrowserItemCategoryFilter.INCLUDE_REDIRECTORS` 是内容浏览器侧的过滤开关，也说明它是被当作独立类别管理的。

## 十一、安全约束汇总

| 约束 | 出处 | 原因 |
|---|---|---|
| 先 `find_asset_data` 预筛，命中的才 `load_asset` | `01_list_assets.py:106-133`、`my02.py:283-292` | 全量加载会让脚本卡死 |
| 路径必须写 `/Game/...` | `01_list_assets.py:35-45` | 磁盘路径静默返回空 |
| 判「未使用」/ 删除前必须 `load_assets_to_confirm=True` | `01_list_assets.py:236-239`、`03_asset_actions.py:254-257` | 默认 `False` 会漏引用，导致误删 |
| 过滤自引用 | 三处 | 资产会引用自身 |
| `rename_asset` 第二参数是完整路径 | `03_asset_actions.py:50-56` | 只给新名字会失败 |
| 移动前检查目标是否已存在 | `03_asset_actions.py:203-206` | 同名冲突是静默失败 |
| 批量改名不递归 | `03_asset_actions.py:85-88` | 跨目录改名风险高 |
| 删除必须 `force=True` + `confirm_force=True` | `03_asset_actions.py:272-286` | 删除不可撤销 |
| 先 `dry_run=True` 预演 | `03_asset_actions.py:333-348` | 防止误删 |
| 改完属性必须 `save_asset` | `02_import_export.py:292` | 否则改动只在内存 |
| 导出前 `os.makedirs(..., exist_ok=True)` | `02_import_export.py:326` | 保证脚本可重复运行 |
| `automated=True` + `prompt=False` | `02_import_export.py:52`、`:349-350` | 无人值守脚本不能被弹窗卡住 |
| 整批操作外套 `ScopedSlowTask` + `should_cancel()` | `01_list_assets.py:217-230`、`03_asset_actions.py:220-233` | 长任务要给用户中断点 |

## 相关文档

- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` —— `asset_class` 的废弃状态、`EditorLevelLibrary` 的迁移目标
- `/openwiki/reference/utils-helpers.md` —— 事务上下文与计时器；本章脚本**没有**使用这些工具，都是直写
- `/openwiki/reference/utils-ui-helpers.md` —— `ProgressBar` 包装类与 `ScopedSlowTask` 直写法的差别
- `/openwiki/workflows/batch-and-external-data.md` —— 第 08 章的大规模批处理与外部数据版本
- `/openwiki/testing/automation-testing.md` —— 同样扫描 `/Game` 但只读的验证脚本，其前缀表与本页的 `PREFIX_MAP` 是两份不同实现