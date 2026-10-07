---
type: "参考"
title: "Editor Tooling: Tool Backends, Transactions, and the Menu Myth"
openwiki_generated: true
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---


# Editor Tooling: Tool Backends, Transactions, and the Menu Myth

Chapter 04 is where the repository stops writing "scripts that do something" and starts writing "tools a user drives from the editor". Three lessons build up to it: the first supplies the shared primitives (undoable transactions, on-screen notifications, selection helpers, four transform tools), the second wraps them in an Editor Utility Widget backend, and the third assembles two complete tools — an asset health checker and a level layout tool.

It is also the chapter with the most consequential factual error in the whole repository, and unlike the Chapter 03 one, this error makes the chapter's own title impossible: `02_menu_extension.py` is named "custom menus and toolbars", yet it opens by asserting that Python cannot register them.

## The three files

| File | Lines | Role |
|---|---|---|
| `04_EditorScripting/01_editor_utility.py` | 444 | Shared utilities: `editor_transaction`, `transactional_operation`, `notify_user`, selection helpers, four transform tools, a generated-script template |
| `04_EditorScripting/02_menu_extension.py` | 347 | `create_editor_utility_widget`, the `EditorToolBackend` MVC-style backend, a script registry driven by `exec`, a JSON `ToolConfig`, a shortcut wish-list |
| `04_EditorScripting/03_custom_tools.py` | 484 | Two complete tools: `AssetHealthChecker` (naming / orphan-refs / path depth) and `LevelLayoutTool` (circle, line, scatter, mirror) |

The two ends of the chapter are visibly combined: `03_custom_tools.py:33-49` is a byte-for-byte copy of `01_editor_utility.py:34-50`. That makes six copies of the same transaction wrapper in the repository (the class version in `utils/helpers.py:251-270` plus five `@contextlib.contextmanager` generators), all traced to the same implicit contract: **every script must be runnable on its own**, so no lesson file imports another (see `/openwiki/reference/utils-helpers.md`).

## 1. Transactions: the technical core of the chapter

`01_editor_utility.py:66-99` is the best piece of teaching prose in the repository. It answers the question a newcomer does not know to ask: why does Ctrl+Z not undo my script's changes?

> `begin_transaction()` is like "taking a photo" of the current state. `end_transaction()` is like "confirm and save" — the operation enters the undo history stack. `cancel_transaction()` is like "roll back to the snapshot" — all changes are reverted. (`01:82-85`, translated)

The same block documents the three failure modes (`01:94-98`):

1. Not passing `primary_object`, or passing `None` — the editor crashes or silently fails.
2. Forgetting `end_transaction` — the transaction stays "in progress" forever and **subsequent operations are all blocked**.
3. Unpaired begin/end — editor state becomes abnormal.

### The `【修改前】` record (`01:99-110`)

```
# unreal.Transactions.begin_transaction(operation_name)   # Transactions 类不存在
# unreal.Transactions.end_transaction()
# unreal.Transactions.cancel_transaction()
```

The problem analysis that follows is accurate on both counts: there is no `unreal.Transactions` class, and the real signatures live on `SystemLibrary` with a completely different shape — `begin_transaction(cls, context: str, description: Text, primary_object: Object) -> int` returns a **transaction index** that `cancel_transaction(index: int) -> None` requires, while `end_transaction() -> int` takes nothing. The same `【修改前】` comment is carried into four other chapters as a deliberate counter-example (see `/openwiki/concepts/nonexistent-and-deprecated-apis.md`).

### The shared wrapper

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

Four properties are worth naming:

- It catches `BaseException`, not `Exception`, so that a `KeyboardInterrupt` (Ctrl+C in the Python Console) also rolls back rather than leaving the transaction half-open.
- It **re-raises**. The wrapper never swallows the failure — the caller still sees the traceback.
- The `try/except/else` shape puts `end_transaction()` in `else`, so a mid-block `return` still commits. The docstring spells this out as three bullets.
- `"Python脚本"` is hard-coded as the `context` argument, so every transaction in the repository shows up in the undo history under the same script name.

**A parameter-name trap**: the wrapper's own second parameter is called `context`, but it is passed to `begin_transaction` as the **third** argument — `primary_object`. The API's `context` (the script label) is the hard-coded literal. So `editor_transaction("排列为圆形", actors[0])` reads as "description, context" but means "description, primary_object". The same misnomer appears in the five sibling copies and in `08_AdvancedTopics/02_external_data.py:36-44`.

### Two styles, two choices of `primary_object`

| Style | Where | Primary object |
|---|---|---|
| `transactional_operation(operation_name, func, *args, **kwargs)` — a helper that wraps an arbitrary callable | `01:88-131` | the **editor world**, because "the operation may touch many Actors and there is no single main object" (`01:119-121`) |
| `with editor_transaction("…", actors[0]):` — inline | `03:292-474` (all four layout tools) | the **first selected Actor** |

Both are defensible; the repository never explains why they diverge. Note also that `01`'s four transform tools call `notify_user(...)` *inside* the `do_*` callback that runs within the transaction (`01:269`, `01:307`, `01:350`, `01:392`), so a viewport message is emitted while the transaction is still open. Harmless in practice, but it mixes UI feedback into the undo scope.

## 2. Notifications: the `world_context_object` trap

`01:138-181` implements `notify_user(message, notification_type="info", duration=5.0)` as two maps plus one call:

```python
color = color_map.get(notification_type, [1.0, 1.0, 1.0, 1.0])   # 4 RGBA channels
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.print_string(
    world, message, True, True,
    unreal.LinearColor(color[0], color[1], color[2], color[3]),
    duration)
log_funcs.get(notification_type, unreal.log)(f"[{notification_type.upper()}] {message}")
```

The header comment (`01:150-157`) explains why the world argument exists and names it as "one of the easiest traps in UE4/5":

- passing `None` → the message is **silently dropped** in the editor;
- passing the wrong object type → the editor crashes;
- the correct route is `UnrealEditorSubsystem.get_editor_world()`, because there is no Game World while editing.

The same lesson is learned twice more in the repository: `utils/helpers.py:62-70` degrades to `unreal.log` when the world is unavailable, and `utils/ui_helpers.py:35-53` simply omits the fallback (see `/openwiki/reference/utils-ui-helpers.md`).

Note that all six arguments here are positional, including the two booleans. Compare `utils/ui_helpers.py`, which uses the keyword form `print_to_screen=True, print_to_log=True, text_color=unreal.LinearColor(...)`. Both work; the named version is what survives an engine signature change.

## 3. Selection: a snapshot of references, and two very different treatments of a deprecated API

`01:183-192` documents the migration:

> In UE5, selecting Actors moved from `EditorLevelLibrary` to `EditorActorSubsystem`. Old code calling `get_selected_level_actors()` still runs, but produces a `DeprecationWarning`. (`01:184-187`, translated)

It also answers a question the code alone does not: **the returned list holds references to the Actors, not copies**, so mutating a returned Actor changes the level; and the list is a snapshot — if the selection changes, an earlier list does not update.

Then the chapter does something no other chapter does:

```python
def get_selected_actors():
    """获取关卡中选中的 Actor 列表"""
    # 注意：UE5 推荐用 EditorActorSubsystem，这里保留旧写法做对比
    return unreal.EditorLevelLibrary.get_selected_level_actors()
```

`01:195` is explicit that this is **deliberate**: "UE5 recommends `EditorActorSubsystem`; the old form is kept here for comparison". Everywhere else in the repository the deprecated call is an oversight (see `/openwiki/concepts/nonexistent-and-deprecated-apis.md`), but here it is pedagogy — the surrounding comment names the replacement, and `03_custom_tools.py:270-272` and `:304-305` show the migrated form for real:

```python
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
```

The trade-off is that `02_menu_extension.py:166` also calls the deprecated version without any such note, and the generated-script template at `01:412` bakes `unreal.EditorLevelLibrary.get_selected_level_actors()` into a template that the author intends to hand out to students. So the "deliberate counter-example" leaks into two places where it is not labelled.

Stub-level shape difference worth knowing: `EditorLevelLibrary.get_selected_level_actors` is a **classmethod**, while `EditorActorSubsystem.get_selected_level_actors` is an **instance method** (you must call it on the subsystem object you got back). That is why the migration is not a mechanical rename.

`require_selection(min_count=1, selection_type="actor")` (`01:208-238`) is the chapter's defensive-programming pattern: check the precondition, `notify_user(..., "warning")`, and return `None` so the caller can `if not actors: return`. It is a near-duplicate of `utils/ui_helpers.py`'s `require_selected_actors` / `require_selected_assets`, but instead of two functions it takes a `selection_type` string and branches internally — and when the type is `"asset"` in `"actor"` mode it returns a list of **strings** (package paths) rather than objects, so callers must know which type they asked for.

## 4. The four transform tools (`01:241-393`)

| Tool | Lines | Algorithm |
|---|---|---|
| `snap_selected_to_grid(grid_size=100.0)` | `241-272` | `round(location.x / grid) * grid` on X and Y; **Z is left untouched** so objects are not snapped to a height grid |
| `align_selected_to_first(axis="z")` | `274-309` | `actors[0]` is the reference and is skipped; only the chosen axis component is overwritten |
| `distribute_actors_evenly(axis="x", spacing=200.0)` | `311-355` | sort by the chosen axis, then `start_val + i * spacing` |
| `randomize_rotation(selected_actors=None, max_yaw=360.0, max_pitch=0.0, max_roll=0.0)` | `357-393` | Yaw-only by default |

Small things that repay attention:

- **Default Yaw-only** is a design decision with a stated reason (`01:365-368`): most props (trees, rocks, buildings) only need horizontal variety, while random pitch/roll makes them topple.
- `distribute_actors_evenly` **hard-codes `idx`'s fallback to `0`** (`axis_map.get(axis.lower(), 0)`) whereas `align_selected_to_first` falls back to `2`. Passing an unrecognised axis therefore snaps to X in one tool and Z in the other, silently.
- `import random` sits **inside the function body** (`01:372`), unlike `03_custom_tools.py:27` which imports it at module scope. Both are legal; the inconsistency is a sign the files were written independently.
- Every tool guards with `require_selection(...)` first, so none of them crash on an empty selection.

### A comment that contradicts the stub — and contradicts its own chapter

`align_selected_to_first` reads the location into a list before overwriting one component (`01:295-303`):

```python
# 注意：这里用 list() 转换是因为
# Unreal Vector 的 x/y/z 是只读属性，不能直接修改
loc = list([actor.get_actor_location().x,
            actor.get_actor_location().y,
            actor.get_actor_location().z])
```

**This claim is false.** The auto-generated stub lists `Vector.x`, `Vector.y`, and `Vector.z` as `[Read-Write]` and generates real setters for each, so a `Vector` returned by `get_actor_location()` can be mutated in place. Confirming this inside the same chapter: `03_custom_tools.py:440` and `:450` do exactly what `01` says is impossible —

```python
loc.x = -loc.x          # 03:440
rot.yaw = -rot.yaw      # 03:450
```

Since all three components are read from a fresh `get_actor_location()` call three times in a row (rather than once into a variable), the `list()` dance also costs three extra engine calls per Actor for no benefit. The correct write-up of the underlying UE concept is different from what the comment says: the *getter returns a copy*, which is why mutating it does not move the Actor until you call `set_actor_location` — not that the fields are read-only.

## 5. `02`: creating an Editor Utility Widget

`create_editor_utility_widget(name, destination="/Game/EditorUtilities")` (`02:74-107`) is the chapter's bridge from "functions" to "a UI a designer can click":

```python
unreal.EditorAssetLibrary.make_directory(destination)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
factory = unreal.EditorUtilityWidgetBlueprintFactory()
widget = asset_tools.create_asset(name, destination, unreal.EditorUtilityWidgetBlueprint, factory)
```

Three things the lesson gets right and states plainly:

- **The Factory pattern** (`02:53-64`): "UE's asset system is factory-based: every asset type has a factory class. A Blueprint uses `BlueprintFactory`, a texture uses `TextureFactory`. The factory initialises the new asset's default properties." This is the same三步曲 as Chapter 03's `BlueprintFactory` (see `/openwiki/workflows/blueprint-automation.md`).
- **`make_directory` is idempotent** (`02:80-81`): "directory already exists → returns `True` rather than erroring", so it doubles as an existence guard.
- **The result is an empty frame.** `02:100-102` warns that only the asset shell is created; the actual UMG layout must be built by hand in the Widget Designer. This is the honest boundary of the tool: Python can create the asset, design the layout, and delete it, but it cannot author the widget tree in a way a human would want to review.

Stub confirmation of the three types used: `EditorUtilityWidgetBlueprintFactory` (a `Factory` subclass from the `Blutility` module, exposing `parent_class` and `blueprint_type` as `[Read-Write]` properties), `EditorUtilityWidget` (a `UserWidget` subclass), and `EditorUtilityWidgetBlueprint` (a `WidgetBlueprint` subclass).

## 6. `EditorToolBackend`: state plus dictionary routing

`02:112-188` is the chapter's model-view separation argument:

> The Editor Utility Widget's UI layer (UMG) only displays; the Python class only holds logic — a simplified MVC. A UI button click calls a Python method such as `on_button_click("batch_rename")`. After the Python method finishes, it updates state variables, and the UI reads those variables when it refreshes. (`02:113-118`, translated)

The mechanism is two state fields (`status_message`, `progress`) and one routing dictionary (`02:127-149`):

```python
handlers = {
    "batch_rename": self._batch_rename,
    "align_actors": self._align_actors,
    "export_selected": self._export_selected,
    "cleanup_assets": self._cleanup_assets,
}
handler = handlers.get(button_id)
if handler:
    handler()
else:
    unreal.log_warning(f"未知的按钮: {button_id}")
```

The stated rationale for a dict over `if/elif` is standard and correct: all buttons are visible in one place, adding a button is one line, and there is no growing conditional chain. Unknown ids fall through to a warning instead of an `AttributeError`, which is the right default for a UI that can be wired up incorrectly.

Two facts about this backend that no comment mentions:

- **All four handlers are stubs.** Each one fetches a selection, sets `status_message`, and logs — none of them renames, aligns, exports, or cleans anything (`02:151-184`). `_cleanup_assets` does not even look at the project: it sets `"正在扫描未使用资产..."` and returns. The backend demonstrates the *shape* of a tool, not a tool.
- **`_align_actors` uses the deprecated API** (`02:166`) even though `01`'s comment three files over names the replacement. The migration awareness stayed in the file where it was taught.

The dict is also rebuilt on every click, which is irrelevant at this scale; the same pattern appears in a different form in the chapter's registry below.

## 7. `SCRIPT_REGISTRY` and `exec`-based dispatch

`02:196-259` builds a small script launcher: a three-entry registry keyed by id, each entry holding `path` / `description` / `category`, and a `run_script(script_id)` that resolves the path and executes the file.

```python
SCRIPT_REGISTRY = {
    "project_report": {"path": "PythonLearning/02_AssetManagement/01_list_assets.py", ...},
    "batch_rename":   {"path": "PythonLearning/02_AssetManagement/03_asset_actions.py", ...},
    "cleanup":        {"path": "PythonLearning/08_AdvancedTopics/01_batch_operations.py", ...},
}
...
project_dir = unreal.Paths.project_dir()
script_path = os.path.join(project_dir, info["path"])
if os.path.exists(script_path):
    exec(open(script_path).read())
```

Points that matter for anyone extending it:

- The registered paths are relative to the **Unreal project root** (`LyraStarterGame/`), not to `PythonLearning/`, because `unreal.Paths.project_dir()` returns the directory containing the `.uproject`. So the `PythonLearning/` prefix is load-bearing and the registry silently depends on the repository being nested inside a UE project at that exact depth.
- `os.path.exists` is checked before `exec`, which turns a wrong path into a clear `log_error` instead of an exception.
- `02:224-234` documents `exec(open(path).read())` honestly: read the file as a string, execute the string as code, **and run it in the current scope** so it can see the caller's variables — with the explicit security caveat that `exec` runs arbitrary code and should only be pointed at trusted scripts. That is the same mechanism `AGENTS.md` specifies as this repository's way of running scripts, and the same one documented in `/openwiki/operations/running-and-verifying-scripts.md`.
- Because `exec` runs the file at module scope, **any module-level side effect in a registered script becomes a side effect of clicking a button.** Two files in this repository execute at import time (`03_BlueprintAutomation/01_blueprint_basics.py:72-124`, `03_BlueprintAutomation/my03.py:363`); neither is registered today, but nothing in `run_script` prevents it.

## 8. `ToolConfig`: JSON files instead of Editor Preferences

`02:265-313` stores per-tool settings in `Saved/PythonToolConfigs/{tool_name}.json`, with `load` / `save` / `get` / `set`. The rationale is listed as four bullets (`02:261-265`), and the third is the interesting one: **`Saved/` is in `.gitignore`**, so generated config never pollutes version control. That is the same reasoning behind writing reports to `project_saved_dir()` elsewhere in the repository.

Implementation notes:

- `os.makedirs(config_dir, exist_ok=True)` happens in `__init__`, so construction has a filesystem side effect.
- `set()` writes to disk on every call (`02:309-313`), justified as "ensure config is not lost if we crash". For a settings panel driven by UI events this is fine; for a loop it would be one write per key.
- Both `open()` calls omit `encoding=` (`02:294`, `02:301`), so they use the platform default encoding — on Windows that is typically the ANSI code page, not UTF-8.
- `json.dump(self.config, f, indent=2)` also omits `ensure_ascii=False`, so any non-ASCII string (a Chinese tool name, for instance) is written as `\uXXXX` escapes. `08_AdvancedTopics/03_automation_testing.py` does pass `ensure_ascii=False` and `encoding='utf-8'` for its report, so the repository knows the right incantation and simply did not use it here.

## 9. `SHORTCUT_SUGGESTIONS`: a dictionary nothing reads

`02:329-335` declares five recommended shortcuts (`Ctrl+Shift+R` for batch rename, and so on). **No code in the repository consumes this dictionary**, and the surrounding comment concedes the limitation: "shortcuts are mainly managed through Editor Preferences; Python scripts cannot directly register shortcuts — but you can bind shortcuts via an Editor Utility Widget button" (`02:325-328`, translated).

This is the point where the chapter's premise needs correcting, because the same claim appears in two other places as if it were a language limitation:

> Toolbar Extension: add a button to the editor toolbar. Menu Extension: add an item to the editor menu. These are usually implemented through C++ or Editor Utility. Python scripts can act as backend logic. (`02:11-16`, translated)

## 10. Correction: Python **can** register editor menus in this engine version

The check this repository mandates (`AGENTS.md:43-61`) — search the engine's auto-generated Python stub before making any claim about what the Python API exposes — contradicts the chapter. The relevant classes in `Intermediate/PythonStub/unreal.py` (which sits one directory **above** the repository root and therefore can never be cited as `repo://` evidence; the line numbers below are for your own re-verification):

| Symbol | Stub line | Signature / note |
|---|---|---|
| `class ToolMenus(Object)` | 314408 | the menu-registration singleton |
| `ToolMenus.get(cls) -> ToolMenus` | 314544 | **classmethod accessor** — this is the entry point |
| `register_menu(self, name: Name, parent: Name = "None", type: MultiBoxType = MultiBoxType.MENU, warn_if_already_registered: bool = True) -> ToolMenu` | 314498 | register a new menu |
| `extend_menu(self, name: Name) -> ToolMenu` | 314579 | extend an existing one (Level Editor main menu, Content Browser context menu, …) |
| `find_menu(self, name: Name) -> ToolMenu` | 314553 | look up a registered menu |
| `is_menu_registered(self, name: Name) -> bool` | 314531 | |
| `add_menu_entry_object(cls, menu_entry_object: ToolMenuEntryScript) -> bool` | 314592 | **classmethod** — attach a Python-defined entry |
| `remove_menu_entry_object(cls, menu_entry_object: ToolMenuEntryScript) -> bool` | 314466 | |
| `find_context(cls, context: ToolMenuContext, class_: Class) -> Object` | 314566 | resolve a context object inside an entry's callback |
| `class ToolMenuEntryScript(Object)` | 314255 | the Python/Blueprint-side entry definition |
| `ToolMenuEntryScript.data` (`ToolMenuEntryScriptData`) | 314269 / 314275 | `owner_name` / `menu` / `section` / `name` / `label` / `tool_tip` / `icon` / `insert_position` / `advanced` |
| `register_menu_entry(self) -> None` | 314295 | |
| `unregister_menu_entry(self) -> None` | 314277 | the documented way to clean up |
| `init_entry(self, owner_name, menu, section, name, label="", tool_tip="") -> None` | 314313 | override to fill `data` |
| `execute(self, context: ToolMenuContext) -> None` | 314375 | override — this is the button's action |
| `get_label` / `get_tool_tip` / `get_icon` / `get_check_state` / `is_visible` / `can_execute` | 314339 / 314327 / 314351 / 314363 / 314301 / 314395 | all take `context` and are meant to be overridden |
| `construct_menu_entry(self, menu: ToolMenu, section_name: Name, context: ToolMenuContext) -> None` | 314384 | |
| `show_in_toolbar_top_level(self, context) -> bool` | 314283 | toolbar placement |
| `class ToolMenu(ToolMenuBase)` | 488507 | |
| `ToolMenu.init_menu(self, owner, name, parent="None", type=MultiBoxType.MENU)` | 488670 | |
| `ToolMenu.add_section(self, section_name, label="", insert_name="None", insert_type=ToolMenuInsertType.DEFAULT, alignment=ToolMenuSectionAlign.DEFAULT)` | 488698 | |
| `ToolMenu.add_sub_menu(self, owner, section_name, name, label, tool_tip="") -> ToolMenu` | 488682 | |
| `class ToolMenuContext(StructBase)` | 163013 | passed to every callback |

So a functioning Python menu extension is: subclass `ToolMenuEntryScript`, override `init_entry` to set `data.menu` / `data.section` / `data.name` / `data.label`, override `execute` to do the work, instantiate it, and call `ToolMenus.get().add_menu_entry_object(entry)` (or, for a brand-new menu, `ToolMenus.get().register_menu(...)` then `extend_menu(...)` and add a section). The supporting types — `MultiBoxType`, `ToolMenuInsertType`, `ToolMenuSectionAlign`, `ToolMenuOwner`, `ToolMenuInsert`, `ToolMenuProfile`, `ToolMenuStringCommand`, `ScriptSlateIcon` — are all present as well.

Three caveats that keep this honest:

- The class existing does not by itself prove the entry appears in the editor; the callback objects must survive garbage collection, which is why the stub exposes `owner_name` ("Optional identifier used for unregistering a group of menu items") and explicit `unregister_*` methods. The right next step is a live test in a running editor, not a stronger claim here.
- **Keyboard shortcuts** are a separate mechanism and the chapter's weaker statement about them may well hold: the stub shows menu entries and commands, but nothing equivalent to "bind a chord to this Python function" was found.
- `02`'s headline claim about **toolbars** is partly recoverable too: `register_menu(..., type=MultiBoxType.TOOLBAR)` and `ToolMenu.add_section` plus `show_in_toolbar_top_level` are the same machinery the Level Editor toolbar uses.

This is the second chapter in a row where the Python API is more capable than the lesson says. Chapter 03's `02_blueprint_components.py:19-25` declares SCS component editing impossible while `SubobjectDataSubsystem` exposes it; Chapter 04's `02_menu_extension.py:11-16` declares menu registration impossible while `ToolMenus` exposes it. In both cases the lesson compensates by being useful anyway (a backend class is still the right design), but the stated reason is wrong, and a reader who trusts it will reach for C++ when Python would have sufficed.

## 11. `03`: `AssetHealthChecker`

`class AssetHealthChecker` (`03:60-283`) scans a content path and reports three classes of problem. The skeleton is the standard three-step: `list_assets(search_path, recursive=True)`, wrap the loop in a `ScopedSlowTask` with `make_dialog(True)` and a `should_cancel()` break, then `_check_single_asset` each entry, which uses `find_asset_data` (metadata only — `03:126-133` re-states the "never `load_asset` for cheap checks" rule) and dispatches to three checks.

| Check | Rule | Severity |
|---|---|---|
| `_check_naming` (`03:150-183`) | an 8-entry `prefix_map`, substring-matched against the class path | `warning` |
| `_check_references` (`03:185-208`) | no external referencers after filtering self-references | `warning` |
| `_check_path_depth` (`03:210-228`) | `len(asset_path.split("/")) > 6` | `info` |

The comments on `_check_references` are the best part: it explains *why* an orphan is only a warning, listing three possibilities — a genuinely unused asset, something hard-referenced but not soft-referenced, or something loaded dynamically from a path string that no tool can detect. That distinction is exactly what `/openwiki/testing/automation-testing.md` records as a test that can never fail, and this chapter's version is the more honest treatment.

### Defects in this tool

- **The dictionary-order substring bug returns.** `_check_naming` matches with `if class_key in class_str` (`03:175-183`), and the `prefix_map` lists `"Material"` before `"MaterialInstanceConstant"`, so `MI_` assets are told they should start with `M_`. The comment even walks up to the problem and accepts it — "`class_str` may contain several class names, so use `in` for fuzzy matching; for example `MaterialInstanceConstant`'s `class_str` also contains `Material`" (`03:170-174`) — which is a description of the bug rather than a defence of it: it never wanted a `MaterialInstanceConstant` to match the `"Material"` entry at all. `01_batch_operations.py:234` gets the same job right by extracting `class_str.split(".")[-1]` first.
- **`name.startswith(...)` is called on a `Name`.** `_check_single_asset` does `name = asset_data.asset_name` with no `str()` (`03:118-120`), and `_check_naming` then calls `name.startswith(expected_prefix)` (`03:176`). The stub annotates `AssetData.asset_name` as `Name`, and `unreal.Name` is a `_WrapperBase` whose only members are `__init__`, `cast`, `is_valid`, and `is_none` — there is **no** `startswith`. Every other read of `asset_name` in the repository wraps it (`02_AssetManagement/03_asset_actions.py`, `08_AdvancedTopics/03_automation_testing.py`, `03_BlueprintAutomation/my03.py`). As written, the first asset whose class matches one of the eight map keys should raise `AttributeError` and abort the whole scan, since nothing in `check_project` catches it. Treat this as a defect to reproduce in a live editor rather than a settled fact — but it is the kind of claim this repository's own rules exist to catch.
- **`_add_issue` counts `info` issues as `passed`.** `03:230-244` increments `stats["errors"]` for `"error"`, `stats["warnings"]` for `"warning"`, and otherwise `stats["passed"]`. Since `_check_path_depth` emits `"info"`, a deep path increments the "passed" counter — so `stats["passed"]` means "issues that were not errors or warnings", not "assets that passed". It is also **never printed**: `_print_report` (`03:246-283`) shows only `total_assets`, `errors`, and `warnings`.
- **`stats` is not reset between runs.** `check_project` clears `self.issues = []` (`03:83`) but leaves `self.stats` intact, so calling `check_project` twice accumulates counts across both scans. This is the same defect as `BatchProcessor.results` in `08_AdvancedTopics/01_batch_operations.py` — a recurring pattern of resetting the list but not the counters.
- **`find_package_referencers_for_asset` is called without `load_assets_to_confirm=True`** (`03:199-202`), the third place in the repository that omits it. Here the consequence is milder than in the delete paths — the tool only warns — but reusing `_check_references` as a deletion gate would under-report. Note also that the report truncates to 50 issues and never says how many were dropped (`03:275`).
- The `does_directory_exist` guard (`03:105-107`) is unreachable, because `list_assets` is called without `include_folder=True`, so folder paths never appear in the results. Identical to `08_AdvancedTopics/01_batch_operations.py`.

## 12. `03`: `LevelLayoutTool`

Four static methods, all of them using the **migrated** subsystem API and all four wrapped in a transaction keyed on `actors[0]`:

| Method | Lines | Placement |
|---|---|---|
| `arrange_in_circle(radius=500.0, z_height=0.0)` | `292-342` | `x = radius·cos θ`, `y = radius·sin θ`, θ = `i·(360/count)`, then `yaw = atan2(direction.y, direction.x)` so each Actor faces the centre |
| `arrange_in_line(start_pos=None, direction="x", spacing=200.0)` | `345-377` | `start_pos + axis_vector · spacing · i`; `start_pos` defaults to `actors[0]`'s current location |
| `scatter_randomly(bounds_min, bounds_max, random_rotation=True)` | `380-413` | `random.uniform` per axis inside an AABB, plus random yaw |
| `mirror_actors(axis="x")` | `416-473` | negate one location component and apply an axis-specific yaw rule |

Design notes:

- `arrange_in_circle` places Actors on a circle **centred on the world origin**, not on the selection's centroid. That is why the math does not need `actors[0]`'s location — and why using this tool on a selection somewhere in a large level teleports everything to the origin-relative ring. The docstring does not mention this.
- The facing calculation reuses `z_height` for the look-at point, so `direction.z` is always `0` and only yaw is computed. Deliberate and correct for a horizontal ring.
- `mirror_actors` contains the chapter's rotation math: X mirror → `yaw = -yaw`, Y mirror → `yaw = 180 - yaw`, Z mirror → rotation unchanged (`03:445-453`). The comment explains the Y case as "back-to-front reversal, which also reverses left-right".
- Both Rotator constructions carry an `【易错点】` note about keyword arguments (`03:339-341`, `03:406-408`) — the third and fourth repetitions of that warning in the repository, after `01:381-383`. Keyword form is used consistently.
- `03:304-305` shows the migrated selection call with a comment naming `EditorLevelLibrary` as the old home — proving the chapter knows the difference, which makes `02_menu_extension.py:166` and the template at `01:412` look like pure oversights.

## 13. APIs named in docstrings but not present under that receiver

Both `01:20` and `03:20` list, under "APIs you may need for the exercises":

```
actor.duplicate_actor(offset_location: Vector) -> Actor
```

No such method exists on `Actor` or on `EditorLevelLibrary`. The stub exposes duplication only on `EditorActorSubsystem`:

```
duplicate_actor(self, actor_to_duplicate: Actor, to_world: World = None, offset: Vector = [0,0,0]) -> Actor   # 673850
duplicate_actors(self, actors_to_duplicate: Array[Actor], to_world: World = None, offset: Vector = [0,0,0]) -> Array[Actor]   # 673836
```

So the receiver is wrong (a subsystem, not the Actor), the parameter list is wrong (three parameters, not one), and the batch form `duplicate_actors` is more useful for a tool. Neither function is ever called in the chapter — the entries sit in the exercise crib sheet, which is the same place Chapter 03's wrong `SCS` claim and Chapter 02's wrong "`asset_class` is gone" claim live. Exercise 2 of `01` ("duplicate the selected Actors and paste them on a grid") is precisely the task this broken signature would mislead a student on.

## 14. Constraints, verified and practical

| Constraint | Source | Why |
|---|---|---|
| Wrap every state-changing editor operation in `begin/end_transaction` | `01:66-99` | otherwise Ctrl+Z does not undo script changes |
| Always pass a real `primary_object` (the edited Actor, or the editor world) | `01:94-96` | `None` crashes or silently fails |
| `begin`/`end` must be paired; a missing `end` blocks later operations | `01:97-98` | the transaction stays open |
| Never swallow the exception inside the wrapper | `01:44-49` | an exception must roll back *and* propagate |
| `print_string` needs the **editor world**, not `None` | `01:150-167` | `None` drops the message silently |
| `Rotator` must be built with keyword arguments | `01:381-383`, `03:339-341`, `03:406-408` | positional order is `(roll, pitch, yaw)` |
| Guard on the selection before doing anything | `01:208-238` | every tool starts with `require_selection` |
| Long loops need `ScopedSlowTask` + `should_cancel()` | `03:96-116` | the Python main thread shares the editor's UI thread |
| `find_asset_data` for checks, `load_asset` only when content is required | `03:126-133` | loading for cheap checks is what makes scripts appear to hang |
| `Saved/` is the correct home for generated config and reports | `02:261-265` | it is git-ignored |
| The old `EditorLevelLibrary` selection calls still run but warn | `01:183-192` | use `EditorActorSubsystem` for new code |

## Related pages

- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` — the `unreal.Transactions` counter-example and the full `EditorLevelLibrary` deprecation map
- `/openwiki/reference/utils-ui-helpers.md` — `show_message`, `ProgressBar`, and the `ScopedSlowTask` wrapper that this chapter calls directly
- `/openwiki/reference/utils-helpers.md` — the sixth transaction wrapper (`TransactionContext`) and why the course files never import it
- `/openwiki/operations/running-and-verifying-scripts.md` — `exec(open(...).read())` semantics, which `run_script` builds on
- `/openwiki/workflows/blueprint-automation.md` — the other chapter whose stated Python limitation is out of date
- `/openwiki/workflows/level-and-actors.md` — the Actor manipulation subset of these tools, applied to level management