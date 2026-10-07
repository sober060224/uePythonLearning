---
type: reference
title: utils/helpers.py API Reference
description: A group-by-group explanation of the signatures and semantics of the logging, asset, Actor, math, path, transaction, and timing utilities in utils/helpers.py, with emphasis on the world_context pitfall in show_screen, the two context managers TransactionContext and Timer, and the copy relationship with the course scripts.
tags: [reference, utils, python-api]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# utils/helpers.py API Reference

`utils/helpers.py` is a 313-line general-purpose utility library and is the **only "fixed version" of shared code** in the repository: it turns the erroneous patterns that appear repeatedly in the course text (`print_string` passed `None`, `unreal.Name.lower()`, `unreal.Transactions`) into correct code and leaves forensic comments behind. To understand its value, you must also understand its relationship with the course scripts.

## Role and Import Style

The module docstring gives the usage directly (`utils/helpers.py:1-13`): add the repository root to `sys.path` and then star-import——

```python
import sys
sys.path.append("/path/to/PythonLearning")
from utils.helpers import *
```

The only import dependencies are four standard-library modules plus `unreal` (`utils/helpers.py:15-18`): `unreal`, `math`, `time`, `os`. There are no third-party dependencies. There is no `__init__.py` under the `utils/` directory, so it works as an implicit namespace package via `sys.path` (`AGENTS.md:26-28`).

One important but easily overlooked consequence: **a star import will also bring out the four names `unreal`, `math`, `time`, and `os`** (the module has no `__all__`). The caller's own `import os` will be overwritten by the same object (harmless), but if the caller layers another `from utils.ui_helpers import *` on top, `log_section` will be silently overwritten by the latter—see "Name Collisions" below.

## Key Structural Fact: Currently No Script Imports It

There are only three references to `utils.helpers` in the entire repository, two of which are comments: `utils/helpers.py:11` in its own docstring, `02_AssetManagement/my02.py:211` (mentioning "working with the `Timer` in `utils/helpers.py`"), and `06_MaterialAndTexture/02_material_instances.py:325` (explaining why it is not imported). **There is no `import` statement at all.**

Instead, the course scripts each contain an equivalent copied implementation:

| Definition in helpers.py | Independent copy in the course | Difference |
|---|---|---|
| `log_section`/`log_info`/`log_warn`/`log_err` (`:27-47`) | `01_Basics/02_logging.py:111-127` | Word-for-word identical |
| `show_screen` (`:50-62`) | `01_Basics/02_logging.py:130-135` | The course version passes `None` as world_context, which is the [before modification] pattern named in the helpers comment |
| `get_all_actors`/`get_actors_by_class`/`get_actors_by_label` (`:104,132,120`) | `05_LevelAndActors/02_modify_actors.py:59-87` | The course version uses the deprecated `EditorLevelLibrary` and directly calls `a.get_actor_label().lower()` |
| `find_actor` (`:137`) | `05_LevelAndActors/02_modify_actors.py:86` (named `find_actor_by_label`) | Different function name |
| `get_selected_actors` (`:113`) | `04_EditorScripting/01_editor_utility.py:193-198` | The course version uses `EditorLevelLibrary` |
| `TransactionContext` (`:251-270`) | The `editor_transaction` decorator generator, with **5 separate copies**: `04_EditorScripting/01_editor_utility.py:34-50`, `04_EditorScripting/03_custom_tools.py:33-49`, `05_LevelAndActors/01_spawn_actors.py:32-48`, `05_LevelAndActors/02_modify_actors.py:36-52`, `08_AdvancedTopics/02_external_data.py:35-51` | Different style (generator vs class), equivalent behavior |

This is not an oversight, but a direct consequence of the repository's implicit contract that "every script can run independently" (`06_MaterialAndTexture/02_material_instances.py:325-337` spells out the reason). The cost is that the same transaction code is copied six times, and **changing one place will not affect the other five**.

## Logging Utilities (`:22-62`)

| Function | Implementation | Notes |
|---|---|---|
| `log_section(title)` `:27-32` | Three `unreal.log` lines, with the first two containing 50 `=` characters | Leaves a blank line before and after the output to make it easier to locate in the Output Log |
| `log_info(message)` `:35-37` | `unreal.log(f"[INFO] {message}")` | |
| `log_warn(message)` `:40-42` | `unreal.log_warning(f"[WARN] {message}")` | Uses warning level, and the UI changes color |
| `log_err(message)` `:45-47` | `unreal.log_error(f"[ERROR] {message}")` | |

The prefix is a uniform bracketed severity tag, which is also the logging style of the entire repository (657 `unreal.log*` calls across the repo).

### `show_screen(message, color=None, duration=3.0)` `:50-62`

This is the most heavily commented function in this module, because it fixes a **silent failure**:

```python
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world:
    unreal.SystemLibrary.print_string(world, message, True, True, color, duration)
else:
    unreal.log(message)
```

When `color=None`, it is filled in with white `[1.0, 1.0, 1.0, 1.0]` (`:52-53`). Lines 54-58 record two things in [before modification]/[problem analysis]: the first parameter of `print_string` is `world_context_object`, and passing `None` in the editor **does not error and produces no output**; therefore this first obtains the editor World from `UnrealEditorSubsystem`, and if that fails it falls back to `unreal.log`—ensuring that the helper itself will never crash due to environment issues.

The stub file signature is `print_string(cls, world_context_object: Object, string: str = "Hello", print_to_screen: bool = True, print_to_log: bool = True, text_color: LinearColor = [...], duration: float = 2.0, key: Name = "None") -> None` (all stub-file references below are one level outside the repository: `../Intermediate/PythonStub/unreal.py:382116`, i.e. the verification target specified by `AGENTS.md:43-61`). There are two signature details worth comparing here: `print_to_screen`/`print_to_log` **both default to `True`**, and `text_color` is a `LinearColor` rather than a list—so the fact that helpers passes a list works because the UE side performs an implicit conversion; explicitly constructing `unreal.LinearColor(*color)` is merely the safer approach.

One easily missed point: the return type of `get_editor_subsystem` in the stub is **`Optional`** (`unreal.py:750362`), meaning it may return `None`. `show_screen` only performs a null check on world and does not check the subsystem itself—if the subsystem is unavailable, this will first raise `AttributeError`, and the fallback path will never be reached.

## Asset Queries (`:65-95`)

| Function | Signature | Semantics |
|---|---|---|
| `get_all_assets(search_path="/Game", recursive=True)` `:70-72` | `-> Array[str]` | Directly forwards to `EditorAssetLibrary.list_assets`, returning a list of **path strings** |
| `get_assets_by_type(class_name, search_path="/Game")` `:75-83` | `-> list[AssetData]` | First obtains all paths, then calls `find_asset_data` on each, matching by class-name substring |
| `load_asset_safe(asset_path)` `:86-91` | `-> Object \| None` | First checks `does_asset_exist`; if it does not exist, logs a warning and returns `None` |
| `asset_exists(asset_path)` `:94-95` | `-> bool` | Forwards to `does_asset_exist` |

The corresponding stub signatures are: `list_assets(cls, directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]` (`unreal.py:352080`, with the instance version on `EditorAssetSubsystem` at `:674144`), `find_asset_data(cls, asset_path: str) -> AssetData` (`:352206`), `does_asset_exist(cls, asset_path: str) -> bool` (`:352289`), and `load_asset(cls, asset_path: str) -> Object` (`:352067`).

Three noteworthy points:

- `recursive=True` is the default, and `get_assets_by_type` does not expose `recursive`, so it **can only search recursively**.
- `include_folder=False` is the default (helpers does not expose it either), so the path list does not include folder entries—this is exactly why `08_AdvancedTopics/03_automation_testing.py` still has to additionally call `does_directory_exist` for filtering.
- The matching condition in `get_assets_by_type` is `class_name.lower() in str(asset_data.asset_class_path).lower()`. **Substring matching** means `"mesh"` will match both `StaticMesh` and `SkeletalMesh`, while `"actor"` will match a large swath of things. It is also the only implementation in this module that performs an O(n) full scan plus one `find_asset_data` call per asset, making it the main source of overhead when `/Game` is large. It returns `AssetData` rather than asset objects, so the caller must call `load_asset` themselves.

## Actor Queries (`:99-142`)

All four queries internally call `get_all_actors()`, so each one is **a complete level traversal**—`get_actors_by_class` and `get_actors_by_label` each query the list once, and using them together results in repeated traversals.

| Function | Implementation Notes |
|---|---|
| `get_all_actors()` `:104-110` | `get_editor_subsystem(EditorActorSubsystem).get_all_level_actors()`; the [UE5] comment on lines 106-107 explains using the subsystem instead of the deprecated `EditorLevelLibrary` |
| `get_selected_actors()` `:113-116` | `get_selected_level_actors()`, which retrieves the **editor's global selection** |
| `get_actors_by_label(label_contains)` `:120-129` | Case-insensitive **substring** matching |
| `get_actors_by_class(actor_class)` `:132-134` | `isinstance` filtering; passing a base class (such as `unreal.Actor`) will match subclasses |
| `find_actor(label)` `:137-142` | Exact label matching; returns `None` if not found; **note that the comparison with `get_actor_label()` does not cast the type** |

Stub signatures: `EditorActorSubsystem.get_all_level_actors(self) -> Array[Actor]` (`unreal.py:673806`), `get_selected_level_actors(self) -> Array[Actor]` (`:673788`). The classmethods with the same names on the old class are at `:352996` / `:352924`.

### About the `str(a.get_actor_label())` wrapper

`get_actors_by_label` says, "`get_actor_label()` returns `unreal.Name`, not `str`—there is no `.lower()`, so convert with `str()` before comparing" (`:124-125`). **This assertion does not match the UE 5.8 stub file**:

```
unreal.py:257730  def get_actor_label(self, create_if_none: bool = True) -> str:
```

The return type is written as `str`. Meanwhile, `unreal.Name` exposes only four members in the stub: `__init__` / `cast` / `is_valid` / `is_none` (`unreal.py:521-541`), and indeed has no `lower()`—so the half of the statement that says "Name has no lower" holds up, but "`get_actor_label()` returns Name" is outdated (or was never true) memory. The extra `str()` is **harmless redundancy**, not a necessary fix.

There is another more noteworthy side effect of this comment that was omitted: `get_actor_label(create_if_none=True)` has `create_if_none` **defaulting to `True`**, meaning that calling it on an Actor that does not yet have a label produces a side effect (generating a label) rather than being a pure read operation.

## Math Utilities (`:145-181`)

| Function | Implementation |
|---|---|
| `vector_from_dict(d)` `:150-152` | `unreal.Vector(d.get("x",0), d.get("y",0), d.get("z",0))`, missing keys default to 0 |
| `rotator_from_dict(d)` `:155-161` | Constructs `Rotator` using **keyword arguments** |
| `distance_between(actor1, actor2)` `:164-168` | `(loc2 - loc1).length()`, calculated from Actor world locations |
| `lerp_vector(v1, v2, t)` `:171-173` | `v1 * (1-t) + v2 * t` |
| `direction_to_rotation(direction)` `:176-181` | Uses `atan2` for yaw, uses `atan2` for pitch and then **negates it**, with roll fixed at 0 |

The comment in `rotator_from_dict` explains why keyword arguments are required: the constructor in the stub is `Rotator.__init__(self, roll: float = 0, pitch: float = 0, yaw: float = 0)` (near `unreal.py:73322`, with the class definition at `:73306`). **The positional argument order is roll → pitch → yaw**, while people are accustomed to writing pitch/yaw/roll. Writing positional arguments will shift all three angles out of place, and it will not error—a typical silent bug.

The `pitch=-pitch` handling in `direction_to_rotation` likewise reflects a convention: in UE, a positive Rotator pitch means looking **downward** (right-hand rule around the Y axis), while the mathematical orientation computed by `atan2(dz, horizontal distance)` is positive when facing upward, so it must be negated.

The use of dictionaries as an intermediate format in `vector_from_dict` / `rotator_from_dict` via `d.get(...)` is intended for reading external data such as CSV/JSON in scenarios like `08_AdvancedTopics/02_external_data.py`.

## Path Utilities (`:184-205`)

All four are thin forwards, and **none of them is a custom path-joining implementation**; this itself is the repository's path convention: get the project directory first, then `os.path.join`.

| Function | Forwarding Target (stub line number) |
|---|---|
| `get_project_dir()` `:189-191` | `unreal.Paths.project_dir() -> str` (`unreal.py:357945`) |
| `get_saved_dir()` `:194-196` | `unreal.Paths.project_saved_dir() -> str` (`:357883`) |
| `get_content_dir()` `:199-201` | `unreal.Paths.project_content_dir() -> str` (`:357958`) |
| `make_project_path(relative_path)` `:204-205` | `os.path.join(get_project_dir(), relative_path)` |

These three `Paths` methods are all `@classmethod`, and their return values all end with `os.sep` (the docstring for `project_dir()` explains that it is based on `FApp::GetProjectName()` and can be overridden by the command line). Because they end with a separator, `make_project_path("Saved/report.json")` joins correctly, but `make_project_path` does not perform existence checks, nor does it handle the case where `relative_path` is already an absolute path.

## Transaction Utilities (`:209-276`)

This section contains the longest comment in the entire file (`:213-224`), recording an original implementation in which **both the class name and the number of parameters were wrong**:

```python
# [before modification] All three functions in this section call unreal.Transactions.xxx — this class does not exist at all.
#   begin_transaction(context: str, description: Text, primary_object: Object) -> int
#   end_transaction() -> int
#   cancel_transaction(index: int) -> None
```

The stub file confirms these three points: `SystemLibrary.begin_transaction(cls, context: str, description: Text, primary_object: Object) -> int` (`unreal.py:385411`), `end_transaction(cls) -> int` (`:384227`), `cancel_transaction(cls, index: int) -> None` (`:385138`); a full-text search shows that the class `unreal.Transactions` **does not exist**.

| Function | Signature | Semantics |
|---|---|---|
| `begin_transaction(name, primary_object=None)` `:227-238` | `-> int` | When `primary_object` is omitted, takes the editor World at the top; `context` is hard-coded as `"Python脚本"` |
| `end_transaction()` `:241-243` | `-> None` (discards the return value) | Commits the transaction |
| `cancel_transaction(token)` `:246-248` | `-> None` | The parameter name was changed to `token`, but what must be passed is the **index** returned by `begin_transaction` |

Defaulting `primary_object` to the editor world (`:236-238`) is the most practical correction in this code: the original implementation required the caller to always be able to provide an object, while in batch operations there may not be a single Actor in the code. It reaches the same conclusion as the [problem analysis] in `05_LevelAndActors/02_modify_actors.py:222-232`.

### `TransactionContext` `:251-270`

A class-form context manager with three members: `name`, `primary_object`, `token` (`:254-257`).

- `__enter__` (`:259-261`): calls `begin_transaction`, stores the index in `self.token`, and **returns `self`**.
- `__exit__` (`:263-270`): if there is an exception → `cancel_transaction(self.token)` and `log_err(f"事务 '{self.name}' 失败: {exc_val}")`; if there is no exception → `end_transaction()` and `log_info(f"事务 '{self.name}' 完成")`; finally `return False`—**does not suppress the exception**, and the exception continues to propagate upward.

Two interface differences are worth remembering:

1. `__enter__` returns the `TransactionContext` instance itself, so `with TransactionContext("Batch Move") as tx:` gives you the object rather than the index; to use the index, you read `tx.token`. The generator version in the course, `editor_transaction` (`04_EditorScripting/01_editor_utility.py:35-50`), does `yield token`, **handing the index directly to the `as` variable**.
2. The course version uses `raise` to re-raise in the exception branch (`:46-48`), relying on `try/except BaseException` + `else` to ensure commit; the helpers version relies on the `exc_type` check in `__exit__` + `return False` to achieve the same effect. The behavior is the same; only the style differs—if the caller does `return` inside the `with`, both can finish correctly (the comment at `04_EditorScripting/01_editor_utility.py:41` specifically explains this).

The usage example is written directly in the comment (`:273-276`):

```python
with TransactionContext("Batch Move"):
    for actor in actors:
        actor.set_actor_location(new_loc)
```

## Timing Utility: `Timer` `:284-308`

A minimal wall-clock timer that uses `time.time()` rather than `time.perf_counter()`:

| Member | Behavior |
|---|---|
| `__init__(label="")` `:287-290` | `start_time = None`, `elapsed = 0.0` |
| `start()` `:292-293` | Records `time.time()` |
| `stop()` `:295-300` | Computes `elapsed`, logs `log_info(f"{label}: {self.elapsed:.3f} 秒")`, and returns it; **if `start()` was never called, returns `0.0` and does not log** |
| `__enter__` `:302-304` | Calls `start()`, returns `self` |
| `__exit__(*args)` `:306-307` | Calls `stop()`, **capturing all arguments** |

Usage example (`:310-313`):

```python
with Timer("Process Assets"):
    for asset in assets:
        process(asset)
```

Note that the loose signature `__exit__(*args)` means it **swallows exception information but does not suppress exceptions** (there is no `return True`); it merely stops the timer and logs as usual—so when an exception is thrown inside the `with` block, you will first see the elapsed-time log and then the exception. `Timer` is not safe for reuse: there is no reset protection in `start()`, and a second `stop()` will still calculate from the original `start_time` (because `stop()` does not reset it).

## Relationship with utils/ui_helpers.py

The two modules **do not import each other**, but both explicitly provide the ability to "display messages," and their responsibilities overlap:

- `helpers.show_screen` (`:50`) and `ui_helpers.show_message` (`utils/ui_helpers.py:35`) both wrap `print_string`; the former is the **raw version**, while the latter adds a layer of color-name mapping and `print_to_log` composition.
- `helpers.log_section` (`:27`) and `ui_helpers.log_section` (`utils/ui_helpers.py:277`) are **same-named and same-meaning**. Because neither module has `__all__`, doing `from utils.helpers import *` and then `from utils.ui_helpers import *` will cause the latter's definition to **silently overwrite** the former. Currently no script imports both, so this conflict is still only a hidden risk rather than an incident.

For a more detailed function-by-function explanation, see `/openwiki/reference/utils-ui-helpers.md`.

## Three Places That Do Not Match the Stub File (Recheck Before Acting)

The comments in this module are generally reliable, but three assertions need to be rechecked against the stub file (`../Intermediate/PythonStub/unreal.py`) according to the rules in `AGENTS.md:43-61`:

| Location | Comment Assertion | Actual Stub File |
|---|---|---|
| `:124-125` | `get_actor_label()` returns `unreal.Name` | Returns `str` (`unreal.py:257730`); the extra `str()` is redundant |
| `:124-125` | (omitted) Reading the label is a pure operation | `get_actor_label(create_if_none=True)` **creates** the label by default |
| Entire file | —— | The return type of `get_editor_subsystem` is `Optional` (`unreal.py:750362`); this module only checks world and does not check subsystem |

For other examples of the same pattern (`EditorAssetLibrary.get_tag_values`, `AssetData.asset_class`), see `/openwiki/concepts/nonexistent-and-deprecated-apis.md`. The common lesson is: the "verified" in comments is only valid for the engine version in which it was written, and **the stub file should be checked again before acting each time** (`AGENTS.md:43-61`).

## Related Documentation

- `/openwiki/reference/utils-ui-helpers.md` —— The companion UI prompt library
- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` —— Three falsified "nonexistent" assertions
- `/openwiki/workflows/level-and-actors.md` —— Practical usage scenarios for Actor queries and transactions
- `/openwiki/architecture/script-conventions.md` —— Comment style and the "each script runs independently" contract