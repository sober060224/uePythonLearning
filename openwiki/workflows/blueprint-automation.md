---
type: workflow
title: 蓝图自动化：创建、组件树与变量
description: 说明第 03 章如何用 BlueprintFactory 三步曲创建蓝图、用 BlueprintEditorLibrary 读写变量与父类、用 SubobjectDataSubsystem 的句柄三步曲遍历组件树，以及 my03 蓝图对比工具为何用层级路径当键。
tags: [blueprint, subobject-subsystem, blueprint-editor-library, comparison-tool, scoped-slow-task]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# 蓝图自动化：创建、组件树与变量

第 03 章是仓库里唯一以「蓝图」为操作对象的章节，也是唯一需要引擎内部组件树 API 的地方。它的技术主线有两条：官方三课示范**能被 Python 直接改的蓝图层面**（创建、编译、父类、变量、依赖），两份练习稿则分别试探**边界之外的部分**——组件树的增删（`SubobjectDataSubsystem`）与蓝图之间的语义对比（`my03.py`）。

## 六份文件的角色

| 文件 | 行数 | 内容 |
|---|---|---|
| `03_BlueprintAutomation/01_blueprint_basics.py` | 349 | 查找/检查/创建/批量创建/编译蓝图，外加一套「游戏框架蓝图集」 |
| `03_BlueprintAutomation/02_blueprint_components.py` | 239 | **同一课的第二版**：同样四件事，多了 `reparent_blueprint`，并在 docstring 里宣布「Python 无法操作组件树」 |
| `03_BlueprintAutomation/03_blueprint_variables.py` | 399 | 变量清单、CDO 默认值修改、属性反射、依赖两个方向、描述与分类、蓝图审计 |
| `03_BlueprintAutomation/my01.py` | 172 | 四道练习题：加组件、批量创建、父类关系图、编译错误清单 |
| `03_BlueprintAutomation/my02.py` | 87 | 第 3、4 题：批量改父类 + 组件树增删 |
| `03_BlueprintAutomation/my03.py` | 557 | 第 2 题「蓝图对比工具」——本页的重点，也是全仓注释最密的一份 |

## 一、01 与 02 是同一课的两版，而 01 会自己跑起来

两份官方课的函数几乎是同一批：

| 功能 | `01_blueprint_basics.py` | `02_blueprint_components.py` |
|---|---|---|
| 创建蓝图 | `:131` | `:51` |
| 检查蓝图 | `:84` | `:97` |
| 批量创建 | `:220` | `:158` |
| 编译蓝图 | `:266` | `:197` |
| 改父类 | 无 | `:126` |

`02` 不是 `01` 的进阶，而是 `01` 的改写（少了 `create_game_framework` 与额外的父类快捷函数，补上 `reparent_blueprint`），命名上却叫「组件」——而它对组件的结论是「做不到」：

> UE Python 并没有暴露 `SimpleConstructionScript` / `SCS_Node` 相关接口（在 `Intermediate/PythonStub/unreal.py` 中搜索 `SimpleConstructionScript` 无结果），因此「往蓝图中添加组件」无法用纯 Python 完成。（`02_blueprint_components.py:19-25`）

这句话在 `my02.py:35-41` 被明确推翻：UE 5.8 的 `SubobjectDataSubsystem`（桩文件 `666504` 行）已经把组件树的增删改查全部暴露给 Python，不需要写 C++ 编辑器扩展。**同一章里第三节否定、练习稿肯定**，是本章最值得注意的一处教材滞后。

### `01_blueprint_basics.py` 是唯一会在载入时自己执行的官方课

其余官方课都遵循「示例调用全注释、末尾只留一行完成日志」的体例（见 `/openwiki/architecture/script-conventions.md`），但 `01` 有三行模块级代码：

```python
bps = find_all_blueprints()                  # :72  ← 递归扫描 /Game
unreal.log(f"项目中共有 {len(bps)} 个蓝图:")   # :73
for bp in bps[:20]:
    unreal.log(f"  {bp.package_name} - {bp.asset_name}")
...
if bps:                                       # :123-124
    inspect_blueprint(bps[0].package_name)    # ← 还会真的 load_asset 第一个蓝图
```

所以用 `exec(open(...).read())` 载入这个文件，会立刻触发一次全库资产扫描加一次蓝图加载——在资产量大的项目里这是可感知的卡顿，而且这是唯一一个「载入即执行」的官方课脚本。

## 二、创建蓝图：工厂三步曲

四份文件用的是同一套流程（`01:131-178`、`02:51-88`、`my01.py:37-48`、`my02.py:44-50`）：

```python
unreal.EditorAssetLibrary.make_directory(destination)          # ① 目录要先存在
factory = unreal.BlueprintFactory()                            # ② 工厂
factory.set_editor_property("parent_class", parent_class)       #    父类挂在工厂上
new_bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    name, destination, unreal.Blueprint, factory)               # ③ 造出来
```

`my01.py:28-32` 把这个模式讲得最直白：「工厂 = 流水线，告诉引擎『我要生产什么类型的东西』」。

三个必须记住的点：

- **属性名是全小写的 `parent_class`**。`01:145-149` 的 `【修改前】/【问题分析】` 记录了写成 `ParentClass` 的失败，并给出核验方法：去桩里看 `class BlueprintFactory` 的属性列表。`set_editor_property` 的属性名与 UE 反射系统里注册的名称必须**完全一致（大小写敏感）**。
- **创建后必须编译再保存**（`02:82-88`）：`compile_blueprint` 生成 `BlueprintGeneratedClass`，没有它就没有 CDO，后面所有读默认值的代码都会空手而归。
- **失败处理不一致**：`02:57-59` 在 `create_asset` 返回非蓝图时打 `log_error`，而 `01:163-165` 是**裸 `return`**——同一个失败在 `01` 里完全静默。

`create_asset` 返回的一定要 `isinstance(new_bp, unreal.Blueprint)` 再判：`create_asset` 的返回类型是通用 `Object`，名字已存在等情况下会返回 `None`（`my01.py:56-58` 注明「最常见原因是名字已存在」）。

## 三、编译：返回值被丢掉的三份实现

桩文件里的签名是 `unreal.BlueprintEditorLibrary.compile_blueprint(cls, blueprint: Blueprint) -> bool`，**它会告诉你编译成功还是失败**。但：

```python
# 01:266-279
unreal.BlueprintEditorLibrary.compile_blueprint(bp)   # 返回值丢弃
unreal.log(f"已编译蓝图: {blueprint_path}")
return True                                            # ← 永远 True

# 02:203-207
# 编译将蓝图的可视化脚本转换为可执行字节码
# 编译成功返回 True，有错误返回 False
unreal.BlueprintEditorLibrary.compile_blueprint(bp)   # 返回值丢弃
unreal.log(f"已编译蓝图: {blueprint_path}")
return True                                            # ← 永远 True
```

`02` 的注释把 API 的行为**描述对了**，代码却没接住它。后果是 `01:282-303` 的 `compile_all_blueprints` 里 `if compile_blueprint(bp_data.package_name): compiled += 1` 恒成立，最终日志「已编译 N/N 个蓝图」永远是满分——即使一半蓝图编译报错。

要真正实现 `01` 的练习题 4「查找所有编译有错误的蓝图」，答案是**读状态而不是去编译**（`my01.py:141-160`）：

```python
if obj.status == unreal.BlueprintStatus.BS_ERROR:
    ...   # BS_UP_TO_DATE / BS_UP_TO_DATE_WITH_WARNINGS / BS_DIRTY / BS_ERROR
```

`my01.py:143-145` 还给出了理由：编译是有副作用的操作，用「编译一下看返回什么」去探测状态会真的改动蓝图。`Blueprint.status` 是只读属性，这条路干净得多。

顺带一提，`compile_blueprint` 这个函数名在 `01:266` 和 `02:197` 各定义了一次、**签名不同**（前者收路径、后者也收路径），而 `03_blueprint_variables.py` 完全没有它——三课之间没有可共享的公共层。

## 四、父类：三个等价入口与一个不可检查的操作

读父类在仓库里出现了三种写法，效果相同：

| 写法 | 性质 | 出处 |
|---|---|---|
| `bp.get_blueprint_parent_class()` | `Blueprint` 的实例方法 | `01:112`、`my01.py:105` |
| `unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)` | `BlueprintEditorLibrary` 的 classmethod | `02:113`、`my03.py:83` |
| `unreal.BlueprintEditorLibrary.reparent_blueprint(bp, cls)` | 写操作 | `02:145`、`my02.py:29` |

前两个是同一功能的两套绑定（`Blueprint` 自己也有 `list_member_variable_names`、`get_member_variable_type`、`generated_class`），教材里两种混用，`01` 用实例方法、`02` 用 classmethod，同一个仓库两个风格并存。

改父类（`02:126-156`）是一个**不可回滚的破坏性操作**，`02:134-141` 的注释列了三条后果：移除旧父类带来的默认组件与函数、继承新父类的、与新父类不兼容的节点会产生编译错误。所以顺序是固定的——先 `reparent_blueprint`，再 `compile_blueprint`，最后 `save_asset`。

但 `reparent_blueprint` 的桩签名是 `-> None`：**它不返回成功与否**。`02:152` 因此只能无条件打一行「已修改父类: …」并 `return True`；调用方无法知道这次改父类是不是真成功了。

`my02.py:17-39` 的 `third()` 是这个操作的批量版：遍历内容浏览器里选中的资产、按类名过滤、逐个 `reparent_blueprint(object, unreal.Character)`。它有两个可查的差异：

- 过滤条件写的是 `asset_data.asset_class_path.asset_name != "Blueprint"`（`my02.py:21`），**没有包 `str()`**，而 `my01.py:84` 与 `my03.py:10` 在同一位置都写了 `str(...)`（理由见 `/openwiki/reference/utils-helpers.md`：`asset_name` 是 `unreal.Name`）。
- 批量改父类没有任何 `dry_run` 或确认步骤，也不需要保存——`reparent_blueprint` 内部已经改了资产。

## 五、组件树：`SimpleConstructionScript` 不存在，改用「句柄三步曲」

这是本章技术含量最高的一段。Python 侧读蓝图组件树要经过三层：

```python
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)   # 引擎子系统
handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)            # ① 句柄
data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)      # ② 句柄 → 数据
is_comp = unreal.SubobjectDataBlueprintFunctionLibrary.is_component(data) # ③ 读内容
```

**为什么必须绕这一圈**：`SubobjectDataHandle` 与 `SubobjectData` 在 Python 里都是只有 `__init__` 的 `StructBase`，**类体里一个字段都没有**——句柄是一张「找得到它」的凭证，不是组件对象本身。内容只能靠 `SubobjectDataBlueprintFunctionLibrary` 的 `get_xxx` 系列读出来。`my01.py:18-27` 用「图书馆的索书号 / 快递单号」解释这件事，并指出底层路径永远是「要改谁 → 通过句柄定位 → 再操作」。

### 可用的读接口（全部为 classmethod）

| 分组 | 方法 |
|---|---|
| 判断类型 | `is_valid`、`is_component`、`is_scene_component`、`is_root_component`、`is_root_actor`、`is_child_actor`、`is_actor`、`is_default_scene_root`、`is_attached_to` |
| 判断来源 | `is_native_component`、`is_inherited_component`、`is_instanced_component`、`is_instanced_actor` |
| 取内容 | `get_data`、`get_handle`、`get_variable_name`、`get_display_name`、`get_parent_handle`、`get_blueprint` |
| 取对象 | `get_object`、`get_associated_object`、`get_object_for_blueprint` |
| 能力查询 | `can_rename`、`can_reparent`、`can_edit`、`can_duplicate`、`can_delete`、`can_copy` |

注意 `get_instanced_component` 这个来源标志是**多余的**：同一个 SCS 组件节点会被 `k2_gather_subobject_data_for_blueprint` 输出两条（SCS 节点视图 + 实例化视图），`my03.py:417-455` 的 `test03` 实测证明这两条在所有可观测标志上完全一致，说明 Python API 层根本区分不了它们——引擎保留两份是给编辑器「组件面板」与「CDO 实例」两套 C++ 逻辑用的。

### 可用的写接口（`SubobjectDataSubsystem` 实例方法）

| 操作 | 签名要点 |
|---|---|
| 增 | `AddNewSubobjectParams(parent_handle, new_class, blueprint_context, skip_mark_blueprint_modified=False, conform_transform_to_parent=False)` → `add_new_subobject(params) -> Tuple[SubobjectDataHandle, Text]`（**返回元组**：新句柄 + 错误说明） |
| 删 | `delete_subobject(context_handle, subobject_to_delete, bp_context=None) -> int`、`delete_subobjects(context_handle, subobjects_to_delete, bp_context) -> int`（返回删除个数） |
| 复制 | `duplicate_subobjects(context, subobjects_to_dup, bp_context) -> Array[SubobjectDataHandle]` |
| 换父 | `reparent_subobject(params, to_reparent_handle) -> bool`、`reparent_subobjects(params, handles_to_move) -> bool` |
| 改名 | `rename_subobject_member_variable(bp_context, handle, new_name) -> None` |
| 找句柄 | `find_handle_for_object(context, object_to_find, bp_context=None) -> SubobjectDataHandle` |
| 遍历 | `k2_gather_subobject_data_for_blueprint(context: Blueprint) -> Array[SubobjectDataHandle]`、`k2_gather_subobject_data_for_instance(context: Actor)`（后者的存在说明同一套句柄机制也适用于关卡里的实例） |

写操作的完整范例在 `my01.py:50-76`（只增）与 `my02.py:58-77`（增了再删）：

```python
handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
root_handle = handles[0] if handles else None        # :53 索引 0 一般是根节点
params = unreal.AddNewSubobjectParams(root_handle, unreal.StaticMeshComponent, bp)
new_handle, text = subsystem.add_new_subobject(params)   # 元组解包
...
deleted = subsystem.delete_subobject(root_handle, handle)
```

三个细节值得记录：`handles[0]` 被两个练习稿都当成根节点（`my01.py:53` 的注释用「一般」两字标出了不确定性，两处都没有验证取到的确实是根）；`add_new_subobject` 返回的是元组，`my02.py:71` 与 `my01.py:69` 都用二元解包接住，`err_text` 只在失败时才有意义；`delete_subobject` 的第三个参数 `bp_context` 在蓝图场景下其实是要给的（签名里有，默认 `None`），两个练习稿都只传了两个参数——`my02.py:74` 的注释写的是删掉「刚才加的那个组件」，而在同一个蓝图上下文里按句柄删除是否需要显式 `bp_context` 值得在编辑器里实测。

顺手一个便利接口：`my03.py:458-514` 的 `test04` 演示了同一个组件节点的**三种取对象口径**（`get_object` / `get_associated_object` / `get_object_for_blueprint`）在继承组件上的差别，结论是「`get_associated_object` 等价于用树根蓝图调 `get_object_for_blueprint`，而 `get_object` 会拿到父蓝图的模板」。

## 六、变量：名字与默认值来自两个不同的层

这是第一次看蓝图变量时最容易卡住的地方，`my03.py:220-256` 的注释把它写得很清楚：

| 信息 | 住在哪 | API |
|---|---|---|
| 变量名清单 | 蓝图资产 | `BlueprintEditorLibrary.list_member_variable_names(bp, include_inherited_members=True) -> Array[str]` |
| 变量类型 | 蓝图资产 | `BlueprintEditorLibrary.get_member_variable_type(bp, name) -> Optional[EdGraphPinType]` |
| 默认值 | 编译后的类的 CDO | `unreal.get_default_object(bp.generated_class())` |

```python
cls = bp.generated_class()                       # ← 是方法，必须加括号
cdo = unreal.get_default_object(cls)             # ← 模块级函数，类对象上没有这个方法
value = cdo.get_editor_property(name)            # 变量名就是 UPROPERTY 的名字
```

`03_blueprint_variables.py:147-152` 的 `【易错点】` 专门记了 `generated_class`：

> `generated_class` 是方法不是属性，必须加括号：写 `bp.generated_class`（不加括号）拿到的是「绑定方法对象」，它永远为真，下面的空值判断会形同虚设，也不能当类使用。

同文件 `:169` 还指出 `get_default_object` 是**模块级函数**，不能写成 `cls.get_default_object()`。

`include_inherited_members` 是两份实现的分水岭：

| 文件 | 取值 | 理由 |
|---|---|---|
| `03_blueprint_variables.py:68` | 默认 `True`（把继承来的也算进「所有用户定义的变量」） | 注释说明：继承来的变量名会带声明类的完整路径前缀，只想要本蓝图自己声明的就传 `False` |
| `my03.py:236` | `False` | 「父类已经单独比过一次，否则父类一改，两张蓝图会满屏属性差异噪音」 |

### 写默认值的两种实现，差一个 `save_asset`

`03_blueprint_variables.py:114-178` 的 `modify_blueprint_defaults`：

```python
for prop_name, prop_value in property_updates.items():
    try:
        cdo.set_editor_property(prop_name, prop_value)
    except Exception as e:
        unreal.log_warning(f"  设置 {prop_name} 失败: {e}")
...
unreal.EditorAssetLibrary.save_asset(blueprint_path)   # ← 关键
```

逐属性 `try/except` 是必要的：属性名拼错、类型不匹配都会抛异常（注释列了这三类常见原因），单条失败不应该中断整批修改。

`my03.py:6-33` 的 `first()` 是同一需求的另一版，**没有 `try/except`、也没有 `save_asset`**：

```python
cdo.set_editor_property(property, value)     # :32 函数到此结束
```

也就是说 `first()` 跑完，改动只活在内存里，关掉编辑器就没了；属性名写错则会以异常中断整个遍历，前面改好的资产也不会保存。这是练习稿与官方课之间一次明确的退步——但因为 `my03.py:34-36` 的调用点被注释掉了，它一直没被暴露。

### 用 `dir()` 反射的两种态度

`03_blueprint_variables.py:180-220` 的 `inspect_blueprint_properties` 走的是 `dir(cdo)` 取前 30 个、`getattr` 加 `callable` 过滤的老路，遇到抛异常的属性就 `log_error` 后 `pass`。

`my03.py:38-44` 的注释给出了为什么对比工具**不能**用这条路：

> 【为什么不用 `dir(cdo)`】`dir()` 里混着方法和内部属性，还得靠 `try/except` 筛，而且拿不到变量类型。`list_member_variable_names` 返回的就是真正的变量名(str)。

同一个仓库里，探索性工具用 `dir()`、生产性工具用反射 API——这个分界是合理的。

## 七、依赖与引用：两个方向，只有一个方向被包装

| 方向 | API | 出处 |
|---|---|---|
| 我引用了谁（依赖） | `AssetRegistryHelpers.get_asset_registry().get_dependencies(package_name, options)` | `03:222-253` |
| 谁引用了我（被引用） | `EditorAssetLibrary.find_package_referencers_for_asset(asset_path)` | `03:265-283` |

`03:223-235` 的 `【修改前】/【问题分析】` 记录了源头：这一课原本调用了 `unreal.EditorAssetLibrary.find_package_references()`——**桩里根本没有这个方法**。`EditorAssetLibrary` 上「引用/被引用」两个方向只暴露了一个，依赖方向必须绕到 `AssetRegistry`：

```python
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions()
options.include_hard_package_references = True   # 硬引用：不用就跑不起来的
options.include_soft_package_references = True   # 软引用：SoftObjectPath 那种
result = registry.get_dependencies(asset_path, options)
return list(result) if result else []            # 查不到返回 None，不是空列表
```

两个达标写法上的细节：

- 第二参数 `AssetRegistryDependencyOptions` **是必传的**（桩里没有默认值），想数出「所有」依赖就把软硬引用都勾上。
- `03:252` 传的第一个参数是 `asset_path`（`str`），而桩里的形参类型是 `Name`；同样的调用在 `02_AssetManagement/my02.py` 里写的是 `unreal.Name(pkg)`。Python 绑定通常能自动转换，但两种写法并存本身说明这里没有定论。
- 返回值是 `Optional`，`None` 上直接 for 遍历会 `TypeError`，所以那行 `list(result) if result else []` 是必需的。

`03:265-283` 的 `find_what_references_blueprint` 则没有传 `load_assets_to_confirm=True`——与 `/openwiki/workflows/asset-management.md` 里三处显式传 `True` 的做法不一致，用它做删除前检查会漏引用。

### 审计工具的功能缺口

`03:317-...` 的 `audit_blueprints` 的 docstring 承诺四项检查：

```
- 检查命名规范      ← 实现了（name.startswith("BP_")）
- 检查是否有描述    ← 没有实现
- 检查依赖数量      ← 实现了（len(refs) > 20）
- 检查父类          ← 没有实现
```

`results` 字典里也只有 `no_prefix` 与 `high_dependency` 两个计数器，没有 `no_description` 之类的字段。文档与实现之间少了两项，是这一章里最容易被读者当成「已经做了」的假象。

## 八、描述与分类：两个属性名都被记录成易错点

| 用途 | 属性名 | 桩文件说明 |
|---|---|---|
| 内容浏览器悬停提示 | `blueprint_description` | `[Read-Write] Shows up in the content browser tooltip when the blueprint is hovered` |
| 调色板窗口分组 | `blueprint_category` | `[Read-Write] The category of the Blueprint, used to organize this Blueprint class when displayed in palette windows` |

`03:285-297` 与 `03:299-315` 分别用 `try/except` 包住 `set_editor_property`，注释说明属性名**不叫** `description` / `category_name`，写错会抛异常。两处都采纳了「先改再保存」的顺序，保存失败不检查返回值。

## 九、`my03.py`：蓝图对比工具的设计

这是全仓注释密度最高的一份文件（557 行里注释约占一半），目标是实现 `03_blueprint_variables.py` 的练习题 2：**比较两个蓝图的组件和属性差异**。它的核心设计可以拆成四件事。

### 1. 为什么不能直接比较两个蓝图

`my03.py:39-45` 用三行讲清了这个问题：

> UObject 的 `==` 比的是「是不是同一个对象」，不是「内容像不像」。两张不同蓝图永远是两个对象，直接比必然「不同」，但也说不出哪儿不同。所以必须自己拆成可比的小项（字符串、数字、bool）再逐个比。

### 2. 三条链路，每条都用现成 API

| 链路 | API | 比的是什么 |
|---|---|---|
| ① 父类 | `BlueprintEditorLibrary.get_blueprint_parent_class` | 父类不同是后面一切差异的根源，先单独报一句 |
| ② 组件（结构） | `SubobjectDataSubsystem` + `SubobjectDataBlueprintFunctionLibrary` | 挂了哪些组件、类型/来源/配置是否一致 |
| ③ 变量（数据） | `BlueprintEditorLibrary.list_member_variable_names` + CDO | 有没有、类型、默认值 |
| ④ 图表 | `BlueprintEditorLibrary.list_graph_names` | 「同一个库里就有，顺手一行」 |

执行顺序把父类放在最前，理由写在 `my03.py:266-271`：「父类不同意味着后面所有的『继承来的东西』都可能不同，先给用户一个总因，再看细节，不然满屏差异找不到原因」。

### 3. 键用层级路径，不用变量名

`my03.py:110-137` 的 `subobject_path` 从当前节点一路回溯父级，拼成 `父/子/孙` 形式的路径当字典键。为什么不能拿 `variable_name` 当键，注释给了三条实测证据：

1. 根 Actor 那条的 `variable_name` 是 `None`（不是空串）；
2. 同一个 SCS 组件节点会被 `k2_gather_subobject_data_for_blueprint` 输出两条（SCS 节点视图 + 实例化视图），两条的 `variable_name` 和关联对象完全相同；
3. 跨蓝图时，同一个变量名可能出现在不同的树层级上。

变量名既不唯一也对不准「哪个组件」，当键必然丢数据或误配对。路径键天然唯一：同一节点重复输出 → 路径相同，覆盖即去重；同名但位置不同 → 路径不同，正确区分。

实现里有一个顺序陷阱（`my03.py:132-134`）：根 Actor 的 `variable_name` 是 `None`，`str(None)` 会得到 `"None"` 这个**真字符串**，先 `str()` 再判空会永远成立——必须先判 `None` 再 `str`。

### 4. 值拆成三列，差异用三段式集合公式

`my03.py:139-178` 的 `get_components` 把每个组件拍平成三列，对应人看图时会问的三个问题：

| 列 | 内容 | 来源 |
|---|---|---|
| `class` | 这是什么东西？ | `component.get_class()` → `class_name()` |
| `origin` | 哪来的？ | `is_native_component` → 「原生」/ `is_inherited_component` → 「继承」/ 否则「本蓝图」 |
| `config` | 配成什么样了？ | `read_component_config`：`static_mesh` / `skeletal_mesh` / `mobility` / `relative_transform` |

`config` 只挑了几个属性，理由写在 `my03.py:180-185`：**桩里没有枚举 UPROPERTY 的 API**，所以按组件的真实类型用 `isinstance` 判断，只读它一定有的属性——这样不需要 `try/except` 兜底。资产引用（`static_mesh`）显示成 `get_path_name()` 路径而不是对象 repr，因为信息量更大。

对比的动作统一写成三行公式（`my03.py:277-283`）：

```python
set(comp_1) - set(comp_2)   # 只有 A 有（新增/删除）
set(comp_2) - set(comp_1)   # 只有 B 有
set(comp_1) & set(comp_2)   # 两边都有 → 才需要逐项比内容
```

注释给的实用理由很中肯：**先用集合把「要不要比内容」筛出来，再对交集逐个比**。三组分开遍历还有一个副作用——每组取出来的字典一定不是 `None`，就不用再写一堆判空分支。

值比较交给 `my03.py:93-107` 的 `same_value`：

```python
if type(value_1) is not type(value_2):
    return False                       # int 0 与 bool False 在 Python 里 == 为 True
return str(value_1) == str(value_2)    # 结构体/数组/枚举的 == 行为不一致
```

先卡类型是因为 `0` 与 `False` 在蓝图里的含义完全不同（一个数字开关 vs 一个真假开关），报「无差异」会误导用户；退化成比字符串则是因为结构体、数组、枚举的 `==` 行为不一致，统一比字符串最省心。

### 输出风格：给人看，不是给程序解析

`my03.py:262-265` 明说：全程用 `unreal.log` 打印成人话，而不是 `return` 一个大字典——「这是给人在 Output Log 里看的工具，屏幕上的可读性 > 程序里的可解析性」。代价是**这个工具无法被自动化测试或 CI 消费**（对比 `/openwiki/testing/automation-testing.md` 里那套返回 `TestResult` 的协议）。

### 已知缺陷清单

| 位置 | 问题 |
|---|---|
| `my03.py:6-33` `first()` | 改完 CDO 不 `save_asset`；无 `try/except`，属性名写错会中断整批 |
| `my03.py:363-366` | `second(...)` 在**模块级**被调用，参数是写死的 `/Game/BluePrintClass/BallAdventure/BP_Cannon` 与 `BP_Cannon1`——载入文件即执行对比，与 `01_blueprint_basics.py:72` 是同一类副作用 |
| `my03.py:519-526` `test02()` | `unreal.log(object.get_name)` / `get_package` / `get_full_name` **没加括号**，打印的是绑定方法对象而不是值 |
| `my03.py:528-536` `main()` | 当前调用的是 `test04(selected_asset)`（第 4 题的演示），不是 `test03`；`my03.py:539` 的 `if __name__ == "__main__"` 被注释掉，所以整份文件唯一的入口只能靠模块级的 `second(...)` |
| `my03.py:544-553` `third()` | 第 3 题（自动文档生成器）只写到「开文件 + 写一行表头」；`box = "|"` 声明后从未使用；输出路径 `os.path.join(unreal.Paths.engine_saved_dir(), "md")` 落在**引擎安装目录**下的一个名为 `md`、没有扩展名的文件——在 `Program Files` 下可能因权限直接失败，且不该污染引擎目录 |
| `my03.py:557` | 第 4 题（蓝图版本管理）没有任何代码 |

## 十、安全约束与工效约束汇总

| 约束 | 出处 | 原因 |
|---|---|---|
| `set_editor_property` 的属性名必须与桩文件完全一致（大小写敏感） | `01:145-149`、`03:290-297` | `parent_class` 不是 `ParentClass`；`blueprint_description` 不是 `description` |
| 创建资产前 `make_directory` | 四份实现都有 | 目录不存在时创建资产会失败 |
| `create_asset` 返回 `Object`，必须 `isinstance` 判类型再判空 | `my01.py:55-58` | 名字已存在会返回 `None` |
| 改完必须 `save_asset` | `02:86`、`03:176` | 否则只活在内存里 |
| 读默认值前先确认 `bp.generated_class()` 非空 | `03:154-160`、`my03.py:230-232` | 未编译的蓝图没有 CDO |
| `generated_class` 是方法要加括号 | `03:147-152` | 不加括号拿到的是永远为真的绑定方法 |
| 遍历组件树用 `is_component` 过滤非组件项 | `my03.py:158-160` | 树里混着蓝图自身、根 Actor |
| 长循环套 `ScopedSlowTask` + `should_cancel()` | `01:236-256`、`02:170-184`、`03:334-348` | 批量操作要给用户中断点 |
| 依赖查询返回值是 `Optional`，要 `or []` 兜底 | `03:250-253` | `None` 上 for 遍历会 `TypeError` |
| 探测编译状态读 `bp.status`，不要靠重新编译 | `my01.py:143-145` | 编译有副作用，会真的改动蓝图 |

## 相关文档

- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` —— `SimpleConstructionScript`、`get_blueprint_variables`、`find_package_references` 三个不存在的 API
- `/openwiki/workflows/asset-management.md` —— `find_package_referencers_for_asset` 的 `load_assets_to_confirm` 惯例与本页 `03:265-283` 的落差
- `/openwiki/reference/utils-helpers.md` —— `unreal.Name` 为什么要先 `str()`
- `/openwiki/reference/utils-ui-helpers.md` —— `ProgressBar` 与 `ScopedSlowTask` 直写法的差别
- `/openwiki/testing/automation-testing.md` —— 返回结构化结果的工具与 `my03.py` 只打日志的工具，两种输出哲学