---
type: workflow
title: 大规模批处理与外部数据驱动
description: 说明第 08 章两课如何用 BatchProcessor 框架批量操作资产与 Actor、如何把 CSV/JSON 外部数据映射成 DataTable 与关卡内容，以及这套框架的统计缺陷、DataTable 读写的能力边界与往返损失。
tags: [batch-operations, external-data, datatable, json, csv, transactions]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# 大规模批处理与外部数据驱动

第 08 章两课是仓库里最接近「生产工具」的两份脚本（`01_batch_operations.py` 505 行、`02_external_data.py` 550 行），它们回答的是同一类问题的两个方向：

- 第 1 课：**同一批操作摊在大量对象上**——写一个框架把「进度、统计、错误隔离、取消、耗时」一次解决，然后用它实现三个工具。
- 第 2 课：**数据在编辑器之外**——CSV/JSON 进出 UE，以及用外部 JSON 驱动关卡生成。

两者都在 `08_AdvancedTopics/`，都遵守 `/openwiki/architecture/script-conventions.md` 的体裁：顶部 docstring 列「习题可能用到的 API」及签名，示例调用全部注释掉，末尾只留一行 `unreal.log("高级主题第N课完成！")`，然后是 `🎯 练习题`。**载入这两个文件都不会执行任何实际操作。**

## 一、`BatchProcessor`：通用批量框架

`BatchProcessor`（`01_batch_operations.py:33-138`）是全仓唯一被设计成复用的类，只有三个成员：

| 成员 | 位置 | 作用 |
|---|---|---|
| `__init__(operation_name)` | `:39` | 记录操作名；初始化 `self.results = {"success": 0, "failed": 0, "skipped": 0, "errors": []}` 与 `start_time` |
| `process(items, process_func, description="处理中...")` | `:52` | 主循环 |
| `_print_summary()` | `:117` | 打摘要 |

### 处理函数的返回值协议

```python
result = process_func(item)
if result is True:
    self.results["success"] += 1
elif result is False:
    self.results["failed"] += 1
else:
    self.results["skipped"] += 1
```

`:97-100` 用的判据是三态协议：**`True` = 成功、`False` = 失败、其它任何值（含 `None`）= 跳过**。注释把它写清了：「返回 True 表示成功，False 表示失败，None 表示跳过」。

注意判等用的是**身份比较**（`is True` / `is False`）而不是 `== True`。这与 `08_AdvancedTopics/03_automation_testing.py:96-107` 的写法一致（见 `/openwiki/testing/automation-testing.md`），是仓库里第二处同样的选择。后果是返回 `1` 或非空字符串会被判成**跳过**而不是成功——对内部工具来说这是「宁可漏计也不误判」的取舍，但它没有写在注释里，是本框架的隐含契约。

`skipped` 这个分支被用得最轻：三个工具里只有 `AssetOrganizer.organize_asset`（`:315-325`）真的返回 `None`（跳过文件夹、跳过已在 `_Organized` 里的资产）。

### 错误隔离

```python
except Exception as e:
    self.results["failed"] += 1
    self.results["errors"].append({"item": str(item), "error": str(e)})
    unreal.log_warning(f"处理失败: {item} - {e}")
```

`:101-111` 的注释解释了设计意图：「批量处理中单个项目失败不应影响其他项目」。用 `log_warning` 而不是 `log_error` 也是刻意的——注释写着「因为这是预期中的错误」。这是本章与 `automation_testing` 最不同的一点：那里用 `log_error` 报失败，这里把「个别项目失败」当作正常路径。

### 三个缺陷

| 缺陷 | 位置 | 后果 |
|---|---|---|
| `process` **不返回**统计 | `:115` | `_print_summary()` 的 `return self.results`（`:138`）被直接丢弃，`process` 隐式返回 `None`；调用方拿不到任何数据，统计只能靠读日志 |
| `results` 不在 `process` 开头重置 | `:52-59` | 同一实例连续调两次 `process`，计数会**累加**；`start_time` 会重置但 `success/failed/skipped/errors` 不会。当前三个工具都只调一次，所以没暴露 |
| 取消不计入任何一栏 | `:82-85` | 用户点取消时直接 `break`，剩余项目既不算 `skipped` 也不算 `failed`，摘要仍打「处理完成！」，看不出这次是**被中断**的，只多一行「用户取消了操作」 |

### 进度反馈

```python
task = unreal.ScopedSlowTask(len(items), description)
task.make_dialog(True)          # 带取消按钮的对话框
for i, item in enumerate(items):
    if task.should_cancel():
        unreal.log("用户取消了操作")
        break
    item_name = str(item).split("/")[-1] if isinstance(item, str) else str(item)
    task.enter_progress_frame(1.0, f"[{i+1}/{len(items)}] {item_name}")
```

`:70-91`。三件事各自都有注释支撑：`make_dialog(True)` 才会显示可取消的对话框；`should_cancel()` 是「长时间操作必须支持取消」的用户体验要求；描述文本里带 `[i+1/len(items)]` 与项目名，是为了让用户知道**卡在哪一项**。

`item_name` 的 `isinstance(item, str)` 分支说明 `process` 其实接受任意类型的 items（资产路径字符串或 Actor 对象），只有字符串才按 `/` 取尾段。

## 二、工具 1：项目清理器（`ProjectCleaner`）

### `remove_unused_assets(search_path="/Game", dry_run=True)`

`:148-191`。骨架是「`list_assets` 全库 → `BatchProcessor.process` 逐项检查」，检查函数里：

```python
if unreal.EditorAssetLibrary.does_directory_exist(asset_path):
    return None                                    # 跳过文件夹
refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
    asset_path,
    load_assets_to_confirm=True,                   # :172
)
external_refs = [r for r in refs if r != asset_path]   # :175
if not external_refs:
    if not dry_run:
        unreal.EditorAssetLibrary.delete_asset(asset_path)   # :181
    unreal.log(f"  未使用: {asset_path}")
    return True
return False
```

三处值得记录：

- **`does_directory_exist` 是死分支**。`list_assets(search_path, recursive=True)` 没有传 `include_folder=True`，返回的全是资产路径，这个 `if` 永远不会成立。同一个文件在 `fix_naming_conventions` 里明确点出了这一点（`:219-221`：「list_assets 默认 include_folder=False，返回的都是资产路径，不需要再判断"是不是文件夹"（原判断永远不会成立）」），却**没有回头修 `remove_unused_assets`**——同一份脚本里两种写法并存。
- **这里用的是引擎原生 `EditorAssetLibrary.delete_asset`**，签名 `delete_asset(asset_path_to_delete: str) -> bool` **没有 `force`/`confirm_force` 参数**（那套双重确认是 `02_AssetManagement/03_asset_actions.py:272-286` 自己包的包装函数）。所以这条删除路径**没有任何引用二次确认**，只靠前面的 `external_refs` 检查兜底。
- **`delete_asset` 的返回值被丢弃**，删除失败时仍然打「未使用」并按成功计数。`dry_run=True` 时同一个 `return True` 表示「会被删除」，摘要里那一栏的标题却固定写作「成功」——在预览模式下它统计的是**候选数**而不是成功数。

### `fix_naming_conventions(search_path="/Game")`

`:194-252`。这是全章唯一**已经修好了**子串匹配问题的函数：

```python
prefix_map = {                                  # :205-212，6 条
    "StaticMesh": "SM_", "Texture2D": "T_", "Material": "M_",
    "MaterialInstanceConstant": "MI_", "Blueprint": "BP_", "SoundWave": "S_",
}
...
class_name = class_str.split(".")[-1]           # :234 取真正的类名
for class_key, prefix in prefix_map.items():
    if class_name == class_key and not name.startswith(prefix):
```

`:223-231` 的【易错点】注释把原因写透：`class_str` 形如 `/Script/Engine.MaterialInstanceConstant`，若用子串匹配，字典里排在前面的 `"Material"` 会抢先命中，于是 `MI_Foo` 被改成 `M_MI_Foo`。修法是先切出 `.` 之后的类名再做**精确比较**。

前缀表只有 6 条，是 `02_AssetManagement/03_asset_actions.py:129-145`（14 条）与 `08_AdvancedTopics/03_automation_testing.py:229-273`（4 条）之外的**第三份前缀表**，三份内容各不相等——这是仓库里「没有共享工具」这一取舍最直接的证据（见 `/openwiki/reference/utils-helpers.md`）。

改名动作用的是 `rename_asset(asset_path, new_path)`，`new_path` 由 `f"{os.path.dirname(asset_path)}/{new_name}"` 拼出（`:236-238`），保持了原目录。

### `empty_folders_cleanup(search_path="/Game")`

`:254-285`。这是本章唯一**逆序处理**的地方：

```python
folders = sorted(
    [p for p in all_paths
     if unreal.EditorAssetLibrary.does_directory_exist(p)],
    key=lambda x: -len(x.split("/")),          # 深→浅
)
for folder in folders:
    contents = unreal.EditorAssetLibrary.list_assets(
        folder, recursive=False, include_folder=True
    )
    if not contents:
        unreal.EditorAssetLibrary.delete_directory(folder)
```

`:259-266` 的注释解释了排序的必要性：删除必须**先子后父**，`/Game/A/B/C` 要先删 `C`，`B` 才会在本轮后续的检查里变成空的。用 `-len(x.split("/"))` 做降序，等价于按路径深度从深到浅。这里 `include_folder=True` 是必需的，否则 `all_paths` 里不会有任何文件夹。

`delete_directory(folder)` 是 `EditorAssetLibrary` 上的原生方法（同章的 `delete_asset` 一样，无确认参数）。摘要只打 `已删除 N 个空文件夹`，**没有走 `BatchProcessor`**——所以这次操作没有进度条，也不受取消控制。三个工具里只有两个用框架，这点不一致。

## 三、工具 2：资产重组（`AssetOrganizer`）

### `organize_by_type`：字典顺序埋了一个真实缺陷

`:293-365` 把资产按 15 条 `type_dirs` 映射搬到 `/Game/_Organized/<子目录>`：

```python
type_dirs = {                                   # :300-316
    "StaticMesh": "Meshes",
    "SkeletalMesh": "Characters",
    "Texture2D": "Textures",
    "Material": "Materials",
    "MaterialInstanceConstant": "Materials/Instances",   # 不可达
    "Blueprint": "Blueprints",
    ...
    "WidgetBlueprint": "UI",                             # 不可达
    ...
    "AnimBlueprint": "Animation",                        # 不可达
    ...
}
...
for class_key, subdir in type_dirs.items():
    if class_key in class_str:                   # :336 子串匹配
        target_subdir = subdir
        break
```

**这里用的是子串匹配加 `break`**，也就是 `fix_naming_conventions` 刚刚修掉的那个错误。三个条目的目标因此永远走不到（都是 "Materials" / "Blueprints" / "Animation" 被更短的名字抢走）：

| 资产类型 | 期望目录 | 实际目录 | 被谁抢走 |
|---|---|---|---|
| `MaterialInstanceConstant` | `Materials/Instances` | `Materials` | `"Material"`（字典里在前） |
| `WidgetBlueprint` | `UI` | `Blueprints` | `"Blueprint"` |
| `AnimBlueprint` | `Animation` | `Blueprints` | `"Blueprint"` |

`AnimSequence` → `Animation` 仍然可用（`"AnimSequence"` 不被 `Blueprint` 命中），所以「Animation 目录」不是空的，只是 `AnimBlueprint` 不会被放进去——这种「一半对一半错」的症状最难排查。

### 两个安全动作，一个有一个没有

`organize_asset`（`:317-362`）在移动前做了两件事：跳过路径中含 `_Organized` 的资产（避免重复处理，返回 `None` → 计入 skipped），以及 `does_asset_exist(dest_path)` 预检（目标已存在就跳过，避免覆盖）。`make_directory(target_dir)` 负责建多级目录。

`batch_redirect_assets(old_base, new_base)`（`:367-395`）做同样性质的批量移动，却**只建目录、没有 `does_asset_exist` 预检**：

```python
relative = asset_path.replace(old_base, "", 1)
new_path = new_base + relative
unreal.EditorAssetLibrary.make_directory(os.path.dirname(new_path))
return unreal.EditorAssetLibrary.rename_asset(asset_path, new_path)
```

`:374-378` 用注释给出了推导示例（`/Game/Old/Assets/SM_Cube` → `/Game/New/Assets/SM_Cube`）。因为没有预检，目标位置已有同名资产时 `rename_asset` 会失败，但失败会被 `BatchProcessor` 记成一条 `failed` 而不是抛异常，所以**不会中断、也不会提示冲突原因**。另外 `asset_path.replace(old_base, "", 1)` 是纯字符串替换，如果 `old_base` 不是 `asset_path` 的严格前缀，得到的相对路径会出错，调用方需要自己保证这一点。

## 四、工具 3：项目健康报告（`ProjectHealthReport`）

`generate_full_report(search_path="/Game")`（`:401-495`）是这三个工具里唯一**不修改任何东西**的，产出是三段文本 + 一个落盘文件：

| 段落 | 检查内容 | 实现 |
|---|---|---|
| 资产统计 | 总数 + 按类名计数，按数量降序取前 15 | `find_asset_data` 读 `asset_class_path` 再 `split(".")[-1]` |
| 命名规范 | 名称含空格的数量（只检查空格） | `name = asset_path.split("/")[-1]`；`if " " in name` |
| 顶级目录 | `/Game/<目录>` 下的资产数 | `set(parts[2] for parts len>=3)`，再逐个统计 |

三处实现细节值得记录：

- **落盘文件名是硬编码的**：`os.path.join(unreal.Paths.project_saved_dir(), "ProjectHealthReport.txt")`（`:468-471`），每次运行**覆盖上一次**。对比 `08_AdvancedTopics/03_automation_testing.py:155-189` 的报告用 `f"{suite_name}_{时间戳}.json"` 保留历史，两者对「报告是否需要留档对比」的假设不同。注释给了写 `Saved/` 的理由：「Saved 目录不会被版本控制，适合存放生成的文件」。
- **顶级目录统计是 O(目录数 × 资产数) 的嵌套扫描**：`count = len([p for p in all_assets if f"/{d}/" in p])`（`:455-458`）在遍历每个顶级目录时都重新扫一遍全表。单次遍历累加计数即可降到 O(资产数)。
- **`f"/{d}/" in p` 是子串匹配，会重复计数**：如果任意子目录与某个顶级目录同名（例如 `/Game/A/B/A/x`），这个资产会同时算进 `/Game/A`，多计一次。加上前面统计段落里 `does_directory_exist` 同样是死分支（`:517-519`、`:457-459` 用了 `include_folder=False` 的结果）。

报告格式是 `.txt`（分隔线 + 缩进），不是 JSON——与 `automation_testing` 的结构化报告形成对照，两者都落在 `Saved/` 下但互不相干。

## 五、外部数据读写：JSON 与 CSV 四函数

`02_external_data.py` 的前半段是四个薄封装（`:60-166`），全部用标准库，没有引入任何依赖。

| 函数 | 位置 | 关键点 |
|---|---|---|
| `read_json(file_path)` | `:60-80` | 先 `os.path.exists` 再 `open`（否则 `FileNotFoundError`）；`encoding='utf-8'`；日志打 `type(data).__name__` 让人一眼看出读到的是 `dict` 还是 `list` |
| `write_json(data, file_path)` | `:83-95` | `indent=2` 便于阅读；**`ensure_ascii=False`** 让中文直接写入而不是转成 `\uXXXX` |
| `read_csv(file_path, has_header=True)` | `:98-125` | `has_header` 决定用 `csv.DictReader`（每行变字典，按列名访问）还是 `csv.reader`（每行是列表） |
| `write_csv(data, file_path, fieldnames=None)` | `:128-166` | 按 `data[0]` 的类型分两条路；`newline=''` 避免 Windows 上多出空行 |

### `write_json` 与 `write_csv` 的一处不一致

```python
# write_json :87
os.makedirs(os.path.dirname(file_path), exist_ok=True)

# write_csv :137-139
parent = os.path.dirname(file_path)
if parent:
    os.makedirs(parent, exist_ok=True)
```

`write_csv` 有 `if parent:` 保护，`write_json` 没有。当 `file_path` 不带目录部分（例如 `"data.json"`）时，`os.path.dirname` 返回空串，`os.makedirs("")` 会抛 `FileNotFoundError`。当前所有调用方传的都是 `os.path.join(..., project_saved_dir(), ...)` 拼出的绝对路径，所以没踩到——但两个同族函数的写法不一致本身就是缺陷。

### `write_csv` 的双形态分支与它的历史

`:146-165` 的注释把「原来只处理了 dict 列表，传 list of list 时会用 `DictWriter` 去写列表，直接抛异常」这段历史留在了代码里，并给出两种形态的对应写法（`list of dict` → 列名从第一个字典的键提取 + `writeheader()`；`list of list` → 列名由调用方通过 `fieldnames` 给出）。`if not data:` 提前返回则挡住了 `data[0]` 越界。

## 六、DataTable 的三条路与一条走不通的路

### 建表：JSON → CSV → DataTable

`create_datatable_from_json(json_path, table_name, destination="/Game/Data")`（`:169-199`）说明 UE Python 直接创建 DataTable 比较麻烦，所以采用**先转 CSV 再导入**的两步法：

```python
csv_path = json_path.replace('.json', '.csv')
write_csv(data, csv_path)
return import_csv_as_datatable(csv_path, table_name, destination)
```

它要求 JSON 必须是数组格式（`if not data or not isinstance(data, list)`），每行是一个扁平字典（示例里是 `{"Name": "Sword", "Damage": 10, "Weight": 3.0}`）。注意 `write_csv` 的列名直接来自第一个字典的键，因此**JSON 的键必须与 Row Structure 的属性名完全一致**，否则导入后列对不上。副作用是会在 JSON 旁边留下一个同名 CSV 中间文件。

### 导入：`CSVImportSettings` + `AssetImportTask`

`import_csv_as_datatable(csv_path, table_name, destination)`（`:201-247`）复用第 02 章的导入套路：

```python
task = unreal.AssetImportTask()
task.filename = csv_path
task.destination_path = destination
task.destination_name = table_name
task.replace_existing = True
task.automated = True
task.save = True

import_data = unreal.CSVImportSettings()                        # :227
import_data.set_editor_property("import_row_struct", None)
task.options = import_data
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
```

`CSVImportSettings` 是 DataTable/CurveTable 专用的导入选项，构造签名是 `CSVImportSettings(import_row_struct: ScriptStruct = None, import_type: CSVImportType = CSVImportType.ECSV_DATA_TABLE, import_curve_interp_mode: ...)`——`import_type` 默认就是 `ECSV_DATA_TABLE`，`import_row_struct` 默认就是 `None`，所以 `:229-231` 那次 `set_editor_property` 其实是**重复默认值**。注释说「设为 None 表示自动创建行结构」，这也是 CSV 导入能免去手写 `ScriptStruct` 的原因。

返回值是 `task.imported_object_paths`（失败时是空列表而非 `None`），与同文件其它函数「失败返回 None」的约定不同。

### 读表：只能按列取再转置，而且值全变字符串

`read_datatable(table_path)`（`:249-287`）的 docstring 把 API 现状写得很准：

> 没有"按行名取整行数据"的函数，只能按列取再按行拼。

实现是「取行名 → 取列名 → 逐列 `get_data_table_column_as_string` → `zip(row_names, values)` 转置」：

```python
data = {row_name: {} for row_name in row_names}
for column in column_names:
    values = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(table, column)
    for row_name, value in zip(row_names, values):
        data[row_name][str(column)] = value
```

它能工作的前提是「每列的值顺序与 `row_names` 一一对应」。代价是**所有值都被字符串化**（`get_data_table_column_as_string` 的返回类型就是 `Array[str]`），读出来是 `"10"` 而不是 `10`，再写回去就要靠 CSV 导入时重新推断类型。

**这条限制其实有更好的替代路线，仓库里都没用**：

| 未被使用的 API | 位置 | 好处 |
|---|---|---|
| `DataTable.fill_from_csv_string(json_string)` | 实例方法 | 不用落中间文件 |
| `DataTable.fill_from_json_string(json_string, import_row_struct=None)` | 实例方法 | **直接从 JSON 字符串写表**，跳过 CSV 中转 |
| `DataTable.fill_from_json_file(json_file_path, import_row_struct=None)` | 实例方法 | 同上，文件版 |
| `DataTableFunctionLibrary.fill_data_table_from_json_string/json_file` | 静态方法 | 同上的静态版本 |
| `DataTableFunctionLibrary.export_data_table_to_json_string(data_table) -> Optional[str]` | 静态方法 | **一次拿到整行、且保留 JSON 原生类型** |
| `DataTableFunctionLibrary.export_data_table_to_json_file(data_table, json_file_path) -> bool` | 静态方法 | 直接落盘 |

也就是说：读表可以用 `export_data_table_to_json_string` + `json.loads` 拿到带正确类型的整行数据；写表可以用 `fill_from_json_file` / `fill_from_csv_string` 免去临时文件。仓库用的是最原始的一条路。

### 加行：能力真的不存在，但删行可以

`add_row_to_datatable(table_path, row_name, row_data)`（`:289-322`）是一个**刻意失败**的函数：

```python
row_struct = table.get_row_struct()
unreal.log_error(
    f"无法直接新增行: UE Python 没有 DataTable.add_row。"
    f"该表的行结构是 {row_struct.get_name() if row_struct else '未知'}；"
    f"请改用 CSV + fill_data_table_from_csv_file 导入。"
)
return False
```

`:299-305` 的注释写明取舍：「与其 save_asset 一下就 return True 让调用方以为写成功了，不如如实返回 False」。核验桩文件后这个判断成立——搜 `def add_row` 零命中，`DataTable` 上只有 `get_row_struct` / `get_row_names` / `get_column_names` / `get_column_as_string` 与 `fill_from_*` 系列。

但有一处**不对称**没被注意到：`DataTableFunctionLibrary.remove_data_table_row(cls, data_table: DataTable, row_name: Name) -> None` **存在**。所以 Python 侧「不能加行、能删行」。`row_data` 参数在函数体里也完全没用上——只有 `row_name` 出现在错误消息的上下文里。

## 七、导出到外部格式

### `export_asset_list_to_csv`：引用计数含自引用

`:324-368` 默认输出 `Saved/AssetList.csv`，逐资产写四列：

```python
refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path)
rows.append({
    "Path": asset_path,
    "Name": str(asset_data.asset_name),
    "Type": str(asset_data.asset_class_path).split(".")[-1],
    "ReferenceCount": len(refs),
})
```

两处与第 02 章不一致：

- **没有传 `load_assets_to_confirm=True`**，所以「需要加载才能确认」的那一类引用不计入，引用数会**偏小**；第 02 章在判定未使用与删除前检查时都显式传了这个参数。
- **`len(refs)` 没有过滤自引用**，而第 02 章三处实现都写了 `[r for r in refs if r != asset_path]`。因此这里每行的 `ReferenceCount` 至少多 1，用它判「有没有被引用」会全部判成「有引用」。

`str(asset_data.asset_name)` 的注释点明原因（「Name -> str，CSV 才写得出来」）——`asset_name` 是 `unreal.Name`，`csv` 模块写不了它。

### `export_actor_data_to_json`：为往返导出，但往返是单向的

`:371-428` 默认输出 `Saved/ActorData.json`，每个 Actor 导出七个字段：

| 字段 | 来源 | 备注 |
|---|---|---|
| `label` | `actor.get_actor_label()` | 签名 `get_actor_label(create_if_none: bool = True) -> str` |
| `class` | `type(actor).__name__` | Python 包装类名，见下文 |
| `location` | `get_actor_location()` | `{x, y, z}` |
| `rotation` | `get_actor_rotation()` | `{pitch, yaw, roll}` |
| `scale` | `get_actor_scale3d()` | `{x, y, z}` |
| `folder` | `str(actor.get_folder_path())` | 返回 `Name`，必须 `str()` |
| `mesh` | 可选 | `get_component_by_class(unreal.StaticMeshComponent)` → `get_editor_property("static_mesh")` → `mesh.get_path_name()` |

两处细节：

- **`type(actor).__name__` 拿到的是 Python 包装类名，不是资产类名**。对蓝图子类（例如 `BP_Barrel`，父类是 `StaticMeshActor`），Python 侧暴露的类仍然是父类的原生类，因此导出成 `"StaticMeshActor"`——**用这个 JSON 无法还原出原来用的是哪个蓝图**，只能还原成原生类。
- **`get_all_level_actors()` 只返回当前打开的关卡**，不是整个项目（注释也这么写）。签名是 `EditorActorSubsystem.get_all_level_actors(self) -> Array[Actor]`，这个脚本已经迁移到子系统（`:385-387` 的注释「【UE5】EditorLevelLibrary 已废弃，统一用 EditorActorSubsystem」），是仓库里**已彻底迁移**的少数文件之一（见 `/openwiki/concepts/nonexistent-and-deprecated-apis.md`）。
- `get_component_by_class` 的桩返回类型写的是 `ActorComponent` 而非 `Optional[ActorComponent]`，但实际找不到时返回 `None`，所以 `if mesh_comp:` 这层判空是必需的。同类还有 `mesh_comp.get_editor_property("static_mesh")` 的判空——`StaticMeshComponent` 其实有 `static_mesh` 属性和 `set_static_mesh(new_mesh) -> bool` 方法，直接用属性访问更短，但 `get_editor_property` 的写法更通用。

### `spawn_actors_from_json`：反向那一半，以及它的静默回退

`:430-540` 是本课的核心——**策划在 Excel 里排关卡，导出 JSON，脚本在编辑器里把 Actor 生成出来**。

```python
class_map = {                                   # :457-462，4 条
    "StaticMeshActor": unreal.StaticMeshActor,
    "PointLight": unreal.PointLight,
    "SpotLight": unreal.SpotLight,
    "CineCameraActor": unreal.CineCameraActor,
}
...
actor_class = class_map.get(class_name, unreal.StaticMeshActor)   # 静默回退
```

**`class_map.get(..., unreal.StaticMeshActor)` 的兜底是静默的**：JSON 里写着 `"class": "TriggerBox"` 或任何不在表里的类型，都会变成**一个没有网格体的 StaticMeshActor**，既不报错也不警告。这一点与同章 `add_row_to_datatable` 刻意 `log_error` 的姿态正好相反（见下文对比）。

其余步骤：

- 事务包裹整个生成循环（见下节）。
- `unreal.Vector(x, y, z)` 用**位置参数**构造，顺序正确；而 `unreal.Rotator` 用**关键字参数**（`:487-489`）并配了【易错点】注释——因为 `Rotator` 的位置参数顺序是 `(roll, pitch, yaw)`，而 JSON 里习惯按 `pitch/yaw/roll` 写，串位不会报错只会转错方向。
- 生成用 `unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(actor_class, location, rotation) -> Actor`（`:493-497`），返回 `None` 时跳过后续配置（`if actor:`）。
- `actor.set_actor_label(item.get("label", "FromJSON"))`——签名 `set_actor_label(new_actor_label: str, mark_dirty: bool = True)` **没有返回值**，默认就会标脏。
- 缩放用 `set_actor_scale3d(unreal.Vector(x, y, z))`，只在 JSON 里有 `scale` 时才设。
- 网格体走 `load_asset(mesh_path)` → `get_component_by_class(unreal.StaticMeshComponent)` → `comp.set_static_mesh(mesh) -> bool`，两处都判空（`:513-524`）。

### 往返的丢失清单

把 `export_actor_data_to_json` 与 `spawn_actors_from_json` 成对看，能明确哪些字段是有去无回的：

| 字段 | 导出 | 导入 | 结果 |
|---|---|---|---|
| `label` | ✅ | ✅ `set_actor_label` | 往返完整 |
| `location` / `rotation` / `scale` | ✅ | ✅ | 往返完整 |
| `mesh` | ✅ | ✅ `set_static_mesh` | 往返完整（仅 `StaticMeshActor`） |
| `class` | ✅ | ⚠️ 只在 4 条映射内 | 其它类型静默变 `StaticMeshActor` |
| `folder` | ✅ | ❌ 没有 `set_folder_path` 调用 | **导出后丢弃** |

因此「导出关卡 → 导入关卡」目前只能当作静态网格体布局的搬运，不能当作关卡备份：蓝图子类会退化、大纲文件夹结构会丢。

## 八、事务：仓库里的第六份副本

`02_external_data.py:35-51` 定义了这一章的事务上下文：

```python
@contextlib.contextmanager
def editor_transaction(description, context):
    token = unreal.SystemLibrary.begin_transaction("Python脚本", description, context)
    try:
        yield token
    except BaseException:
        unreal.SystemLibrary.cancel_transaction(token)
        raise
    else:
        unreal.SystemLibrary.end_transaction()
```

结构与 `utils/helpers.py:251-270` 的 `TransactionContext` 类等价，但写法更紧凑，并且用 `try/except/else` 把「正常结束」与「异常回滚」分成两条明确的路径。**唯一值得一提的命名问题是参数名 `context` 实际被当作 `primary_object` 传给 `begin_transaction`**——`begin_transaction(context: str, description: Text, primary_object: Object)` 的第一个参数才是「上下文」（这里是硬编码的 `"Python脚本"`），所以调用方传进来的 `context` 是撤销历史里的**锚点对象**。这个错位在 `:464-467` 的调用处最明显：`world = ...get_editor_world()` 然后 `editor_transaction("从JSON生成Actor", world)`。

这是仓库里 `editor_transaction` 的**第 6 份实现**（另 5 份逐字重复在 `04_EditorScripting/01_editor_utility.py:34-50`、`04_EditorScripting/03_custom_tools.py:33-49`、`05_LevelAndActors/01_spawn_actors.py:32-48`、`05_LevelAndActors/02_modify_actors.py:36-52` 与 `utils/helpers.py`），根源是 /openwiki/architecture/script-conventions.md 记录的「每个脚本都能独立运行」这条隐性契约。

值得肯定的是事务的**位置**：`with editor_transaction(...):` 只包住生成循环，`unreal.log(f"从 JSON 生成了 {len(spawned)} 个 Actor")` 写在 `with` 之外（`:536`），因此日志不会被算进撤销栈。`world` 取自 `UnrealEditorSubsystem.get_editor_world()`，注释也说明了为什么用它当锚点：「生成 Actor 的操作作用于关卡」。

## 九、两课的对照

| | `01_batch_operations.py` | `02_external_data.py` |
|---|---|---|
| 主线 | 对内：把操作摊在多对象上 | 对外：数据进出 UE |
| 复用 | 有 `BatchProcessor` 框架（但 3 个工具里只有 2 个用它） | 无框架，函数平铺 |
| 事务 | 未使用（改资产的工具都不包事务） | 唯一使用事务的地方 |
| 进度条 | `ScopedSlowTask` + 取消 | 无（生成循环没有进度反馈） |
| 输出 | `Saved/ProjectHealthReport.txt`（硬编码名，覆盖） | `Saved/AssetList.csv`、`Saved/ActorData.json` |
| 失败姿态 | 个别失败记 `log_warning` 继续 | 能力缺失时 `log_error` + 如实 `return False` |
| 已知缺陷 | `organize_by_type` 的字典顺序、`process` 不返回统计、删除无确认 | `write_json` 的 `makedirs("")`、`class_map` 静默回退、引用计数含自引用 |

两课都不导入 `utils/helpers.py` / `utils/ui_helpers.py`，各自实现了需要的日志、进度、事务——与第 02 章、`automation_testing` 是同一个取舍的第四次重复（见 `/openwiki/reference/utils-helpers.md` 的「零调用方」结论）。

## 相关文档

- `/openwiki/workflows/asset-management.md` —— 第 02 章的同类工具，本页多处缺陷都是与那份实现对比出来的
- `/openwiki/testing/automation-testing.md` —— 另一份「扫描 `/Game` + 落盘报告」的脚本，报告格式与留档策略都不同
- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` —— `DataTable.add_row`、`unreal.Transactions` 两项缺失的取证
- `/openwiki/reference/utils-helpers.md` —— `TransactionContext` 与本章 `editor_transaction` 的关系
- `/openwiki/workflows/level-and-actors.md` —— 生成与修改 Actor 的基础用法
- `/openwiki/architecture/script-conventions.md` —— 「每个脚本都能独立运行」这条契约的来源