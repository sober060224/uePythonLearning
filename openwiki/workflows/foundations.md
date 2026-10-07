---
type: "workflow"
title: "01_Basics: Your First Editor Script"
description: "How the three introductory lessons move from module orientation to log/screen output to editor subsystems, and what the my01–my03 exercise files correct."
tags: ["foundations", "logging", "print-string", "editor-subsystem", "slow-task", "paths", "exercise-files"]
---

# 01_Basics: Your First Editor Script

`01_Basics/` is the only chapter of `PythonLearning` that teaches the *environment* rather than an asset family. Its three lessons (`01_hello_unreal.py` 138 lines, `02_logging.py` 207 lines, `03_editor_basics.py` 289 lines) and three exercise files (`my01.py` 169, `my02.py` 137, `my03.py` 104) exist to answer three questions in order: *what is the `unreal` module*, *how do I see anything I did*, and *how do I reach the editor state*. Everything else in the repository assumes those three answers.

## The three lessons form a deliberate ladder

| Lesson | Question | Primary API surface | Ends by |
| --- | --- | --- | --- |
| `01_hello_unreal.py` | What is available? | `SystemLibrary`, `Paths`, `EditorAssetLibrary`, `dir(unreal)` | logging a module-wide class count and loading one arbitrary asset |
| `02_logging.py` | How do I observe it? | `log`/`log_warning`/`log_error`, `SystemLibrary.print_string`, `LinearColor` | defining five reusable debug helpers and calling them |
| `03_editor_basics.py` | How do I touch the editor? | `get_editor_subsystem`, `UnrealEditorSubsystem`, `EditorActorSubsystem`, `Paths`, `EditorUtilityLibrary`, `ScopedSlowTask`, `EditorDialog` | reading content-browser selection and a summary of engine/project identity |

The ladder is load-bearing for the rest of the repository. `01_Basics/02_logging.py:111-135` defines the four log helpers (`log_section`, `log_info`, `log_warn`, `log_err`, `show_screen`) that `utils/helpers.py:27-62` later vendors essentially verbatim, and `03_editor_basics.py:60-77` writes the `EditorLevelLibrary` → subsystem migration that `05_LevelAndActors/` depends on.

## The execution model: a script, not a module

All six files are written to be executed top-to-bottom in the editor's Python Console, not imported. The repository-wide evidence:

- **No `if __name__ == "__main__"` guard exists anywhere in the tree.** The only textual occurrence is inside a comment at `03_BlueprintAutomation/my03.py:539`, where it was commented out. Every module-level statement in every lesson runs the moment the file is loaded.
- **There is not a single executable `print()` call in the tree.** All 11 occurrences of the token `print(` are inside comments (`01_Basics/01_hello_unreal.py:39`, `01_Basics/03_editor_basics.py:120`, `01_Basics/my01.py:7-11`, `01_Basics/my02.py:45`, `01_Basics/my02.py:50`, `02_AssetManagement/my01.py:36`, `02_AssetManagement/my01.py:306-308`). Output goes through `unreal.log` / `log_warning` / `log_error` or `SystemLibrary.print_string`.
- Lesson docstrings carry a 运行方式 field prescribing `exec(open("path/to/01_hello_unreal.py").read())` (`01_Basics/01_hello_unreal.py:15-17`, `02_logging.py:11-12`, `03_editor_basics.py:11-12`) rather than an import.

Consequences that matter when reusing this code:

- A lesson cannot be partially reused. Running `01_hello_unreal.py` to read its helper definitions also lists `/Game` and loads an asset.
- `02_logging.py` changes character halfway down. Lines 36-100 are a linear script; from line 111 the file becomes a library of five helpers, and lines 138-144 immediately call them. The same file is simultaneously the demonstration and the reusable module.
- `my03.py:104-105` calls `print_static_mesh_positions()` and `print_selected_actor_info()` at module scope, so loading the exercise file triggers a full level-actor scan.

## Lesson 1 — module orientation, and a catalogue that already contradicts lesson 3

`01_hello_unreal.py` establishes three facts and then surveys the API:

- `unreal` imports only inside the editor (`:32-43`); the file's 【修改前】 note records that the original used `print()` and was changed to `unreal.log()` per repository convention.
- Identity comes from `SystemLibrary.get_engine_version()` (`:49`), `Paths.project_dir()` (`:57`) and `Paths.project_content_dir()` (`:62`).
- Scale comes from a comprehension over `dir(unreal)`, `all_classes = [name for name in dir(unreal) if not name.startswith('_')]`, logged as a count (`:85-86`).

The module-structure comment block at `:66-83` is the part that has aged badly. It presents `unreal.EditorLevelLibrary` under "编辑器类" as a first-class API alongside `unreal.LevelEditor` and `unreal.Subsystem`. Two files later, `03_editor_basics.py:64-77` explains that `EditorLevelLibrary` belongs to the whole deprecated "Editor Scripting Utilities" plugin and that its duties were split into subsystems. A reader who only reads lesson 1 will reach for the API the rest of the chapter is teaching them to leave.

`01_hello_unreal.py:105-112` also has a side effect it does not advertise. The "type system" section loads `all_assets[0]` — whichever asset happens to sort first under `/Game` — to print `type(first_asset).__name__` and `first_asset.get_class().get_name()`. The engine stub's `EditorAssetLibrary.load_asset` docstring is explicit that it "will verify if the object is already loaded and only load it if it's necessary", so the call is idempotent per asset but still pulls an arbitrary asset into memory on every run of an otherwise read-only orientation script. `while my01.py:147-170` later argues at length that cheap inspection should use `find_asset_data` instead.

## Lesson 2 — output, and the four helpers the whole repository reuses

`02_logging.py` is the origin of the repository's observability layer.

**The three log functions** (`:36-46`) are module-level shims: `unreal.log(arg)` is `def log(arg: Any) -> None`, and `log_warning`/`log_error` have the same one-argument shape. There is no level-prefix API — the `[INFO]`/`[WARN]`/`[ERROR]` tags are invented by the lesson's own helpers at `:118-127` and copied into `utils/helpers.py`.

**Screen messages.** `SystemLibrary.print_string` is the Python form of the Blueprint Print String node. The lesson's own 【易错点】 at `:53-56` writes the rule and then follows it: `editor_world` is obtained once from `UnrealEditorSubsystem.get_editor_world()` and passed as `world_context_object`. Sections `:69-81` then show three coloured messages using the positional form:

```python
unreal.SystemLibrary.print_string(
    editor_world, "红色警告消息", True, True,
    [1.0, 0.0, 0.0, 1.0], 5.0   # 红色
)
```

Two things are worth correcting about that positional form. First, the lesson's own docstring API list at `:18` stops after `duration`, but the real signature carries a seventh parameter:

```python
def print_string(cls, world_context_object: Object, string: str = "Hello",
                 print_to_screen: bool = True, print_to_log: bool = True,
                 text_color: LinearColor = [0.0, 0.66, 1.0, 1.0],
                 duration: float = 2.0, key: Name = "None") -> None
```

`key` is documented as "If a non-empty key is provided, the message will replace any existing on-screen messages with the same key" — i.e. the API has a built-in way to prevent stacking, which no file in the repository uses. Second, `duration` accepts a negative number, meaning "load the duration from config", which the lesson does not mention.

**The helpers, and the one that kept the bug.** `:130-135` defines `show_screen(message, color=None, duration=3.0)` and then passes `None` as the world context:

```python
def show_screen(message, color=None, duration=3.0) -> None:
    if color is None:
        color = [1.0, 1.0, 1.0, 1.0]  # 默认白色
    unreal.SystemLibrary.print_string(
        None, message, True, True, color, duration
    )
```

This is the exact anti-pattern the same file warned about 77 lines earlier, and `utils/helpers.py:62-70` is the corrected descendant (it falls back to `unreal.log` when the editor world is unavailable). `utils-ui-helpers.md` and `operations/running-and-verifying-scripts.md` track that lineage.

**`inspect_object` and its bare `except`.** `:150-175` splits `dir(obj)` into callables and non-callables and prints up to `max_attrs=20` of each. The property read is wrapped in a bare `except:` (`:166`):

```python
        try:
            value = getattr(obj, prop)
            log_info(f"  .{prop} = {value}")
        except:
            log_info(f"  .{prop} = <无法读取>")
```

A bare `except:` also catches `KeyboardInterrupt` and `SystemExit`, and it discards the exception entirely — the output cannot distinguish "this property raises" from "this property does not exist". Combined with `max_attrs=20` against an object whose `dir()` is hundreds of entries long, the tool prints a truncated, unlabelled sample. The repository's own convention elsewhere is `except Exception as e` with `e` in the message, as in `safe_load_asset` twenty lines below.

**`safe_load_asset` is the chapter's reference guard sequence** (`:183-202`): `does_asset_exist` → early `log_warn` + `None`; `load_asset` → `if asset is None` → `log_err` + `None`; success → `log_info` with `type(asset).__name__`; and an outer `except Exception as e` returning `None`. The type annotation `-> None | unreal.Object` is the file's declaration that failure is a value, not an exception. Its test calls at `:204-205` include `/Game/Characters/Character_Default.Character_Default`, which is a Lyra content path and will not exist in a project whose `Content/` was never downloaded — that call is *supposed* to exercise the `does_asset_exist` branch, which is a reasonable use of a missing asset but reads like a stale reference.

## Lesson 3 — editor state, and the `修改前` / `问题分析` / `修改后` pattern

`03_editor_basics.py` is the canonical example of the teaching device used throughout the repository: a comment block marking what the naive code was (【修改前】), why it failed (【问题分析】), and what replaced it. In this file the device appears four times, and each one is a different kind of failure.

### Migration (`:64-77`)

The 【修改前】 block preserves the two deprecated calls (`EditorLevelLibrary.get_editor_world()`, `.get_all_level_actors()`) and the analysis names the plugin-level cause: "Editor Scripting Utilities" was deprecated in UE5 and its functions were dispersed into subsystems. The memory aid — *the old API is one all-in-one static library, the new API is split by responsibility and reached with `get_editor_subsystem()`* — is the sentence the rest of the repository relies on. The file then demonstrates the intended reuse pattern: `editor_subsystem` created in section 1 is reused in section 2 for `get_editor_world()`, and `actor_subsystem` created in section 2 is reused in section 7 for `get_selected_level_actors()` instead of calling `get_editor_subsystem` again.

### A guessed API name (`:114-127`)

The 【修改前】 shows `unreal.Paths.normalize_path_name(messy_path)` with the note that the script "died here" with `AttributeError`. The analysis is correct about the cause — C++ `FPaths::NormalizeFilename()` becomes Python `normalize_filename`, and guessing names is what fails — and it recommends `dir()` self-service.

**But the correction's own description of the replacement is wrong twice over.** The file states at `:121-123` that `normalize_filename` does two things: unify slashes *and* collapse redundant parts (`"//"` → `"/"`, `"a/../b"` → `"b"`). The engine stub documents `Paths.normalize_filename(cls, path: str) -> str` as exactly one thing — "Convert all / and \ to TEXT(\"/\")". Slash de-duplication lives in a separate function, `Paths.remove_duplicate_slashes(cls, path: str) -> str`, whose docstring shows the `BaseDirectory/SomeDirectory//SomeOtherDirectory////Filename.ext` → `BaseDirectory/SomeDirectory/SomeOtherDirectory/Filename.ext` example; and relative-directory collapsing lives in a third, `Paths.collapse_relative_directories(cls, path: str) -> Optional[str]`. Neither is called by this file.

So the demonstration output at `:124-127` on the input `"/Game//Characters/../Materials/MyMaterial"` is not what the comment implies: after `normalize_filename` the `//` and the `..` survive, and the honest sequence is three calls whose last two are not `NormalizeFilename` at all. The lesson's docstring at `:27` repeats the same two-in-one claim ("标准化路径（统一斜杠、折叠冗余）"). `collapse_relative_directories` returning `Optional[str]` also means it can fail on a path that escapes its root, which the lesson's flat description hides.

One further wrinkle worth knowing before trusting a guess: the stub contains **two** identical `normalize_filename` classmethods, `Paths.normalize_filename` and `SystemLibrary.normalize_filename`, both documented as "Convert all / and \ to TEXT(\"/\")". `dir(unreal.Paths)` will find the one the lesson wants, but the duplication means a prefix-less `normalize_filename` reference in the docs is ambiguous.

### The database of a hang (`:153-176`)

This is the most valuable block in the chapter. The 【修改前】 preserves the original progress-bar demo — `ScopedSlowTask(5.0, "正在执行操作...")`, `make_dialog(True)`, `should_cancel()`, `enter_progress_frame(1.0, ...)` and `time.sleep(0.5)` — and the analysis identifies the culprit as the `time.sleep`, not the progress dialog: the editor UI and the Python script share one main thread, so sleeping blocks the Windows message loop and the bar never repaints while the whole editor appears frozen.

`my03.py:15-20` records the opposite conclusion — that "`ScopedSlowTask.make_dialog` 在 Python 里几乎必定卡死 UI" — and that version is also carried by `architecture/script-conventions.md` and `operations/running-and-verifying-scripts.md`. The lesson file in the same directory refutes it: `03_editor_basics.py:180-212` actually calls `make_dialog(True)` and runs a cancellable progress dialog successfully. The real invariant is not "`make_dialog` is broken" but "no call inside the loop may block, and the per-frame work must stay small". That is why the corrected demo (a) drives the bar with real work — one `find_asset_data` per frame — and (b) caps the scan with `SCAN_SCOPE = "/Game/EditorWidgetUtilities"` while warning at `:184-185` that switching the scope to `/Game` will stall the UI again even without any `time.sleep`. The stub also exposes two tools this file never uses that belong to exactly this problem: `ScopedSlowTask.tick_progress()` ("Let the UI refresh but doesn't advance progress") and `make_dialog_delayed(delay, can_cancel, allow_in_pie)` (only show the dialog if the task is still running after `delay` seconds).

Two smaller points of contract are correct and worth keeping: `make_dialog()` must be called explicitly — the stub calls it "creates a new dialog for this slow task, if there is currently not one open", and the lesson's 【易错点】 at `:191-192` warns that merely constructing the task shows nothing; and `should_cancel()` must be re-checked on every iteration (`:198`), with the loop breaking rather than unwinding.

### A capability that does not exist (`:218-243`)

The fourth block removes `EditorUtilityLibrary.show_notification(...)` after an `AttributeError`, and the analysis is a small piece of real research: `EditorUtilityLibrary` has no such method, the `unreal` module has no `NotificationInfo` or `NotificationManager` type at all, because Blueprint-side notifications are Slate `FNotificationInfo` — pure C++ — while the Python bindings only export `UFUNCTION`s from the `UObject` hierarchy. Both parts check out against the engine stub.

The file then states that UE5 Python offers exactly two ways to notify a user, and the stub agrees on the shape but adds a caveat the lesson omits:

| Route | Behaviour | Stub evidence |
| --- | --- | --- |
| `SystemLibrary.print_string` | non-blocking, drawn in the viewport, disappears after `duration` | used at `:243-251` with `unreal.LinearColor(0.2, 1.0, 0.2, 1.0)` |
| `EditorDialog.show_message` | modal, blocks until the user decides | docstring: "it will block execution until the user makes a decision" |

`show_message`'s docstring continues: "If running in `-unattended` mode it will immediately return the value specified by `default_value`". So a script that gates a destructive action on `show_message` behaves differently under commandlet or unattended runs — it returns `AppReturnType.NO` by default and proceeds down whatever branch that implies. The lesson's commented-out examples at `:135-149` and `:246-251` are both `show_message` calls and neither mentions it. This is the one place in `01_Basics` where a fact about CI or automation behaviour is load-bearing and absent.

## The exercise files: what the student code gets corrected into

The three `my*.py` files in this chapter answer the 🎯 exercise blocks of the three lessons. They are the only files in the repository that preserve the *wrong* code alongside the fix, and `AGENTS.md` declares them non-normative.

| File | Answers | Preserves | Net effect |
| --- | --- | --- | --- |
| `my01.py` | lesson 1's three exercises | all four student errors inline as comments | a working asset-type census and an mtime-based "5 newest assets" report |
| `my02.py` | lesson 2's three exercises | three 【修改前】 blocks | a colour-correct `log_level`, a hardened `inspect_all_assets`, a working `log_screen` |
| `my03.py` | lesson 3, exercises 1 and 3 (2 skipped) | docstring-fenced copy of lesson-3 code, plus two 【修改前】 blocks | two level-inspection functions |

### `my01.py` — four student errors, one of them silent

The module-level banner `unreal.log('-' * 50)` at `:5` and `:170` brackets the file. Exercise 1 (`:29-32`) lists `/Game/Characters` non-recursively and logs `asset_class_path.asset_name` — marked correct.

Exercise 2 (`:41-97`) is the annotated teardown of the student's census, and the errors are named individually:

- **The `'list' object has no attribute 'get_name'` crash.** The student wrote `type(all_assets.get_name()).__name__`. `list_assets` returns `Array[str]`, so the loop variable is a *path string*, and neither the list nor the string has `get_name()`. The comment separates these into two distinct mistakes rather than one.
- **Python type vs engine class.** `type(x).__name__` answers "what is `x` in Python" (`str`, `list`), not "what class is this asset in the engine". The accepted replacement is `str(asset_data.asset_class_path.asset_name)` via `find_asset_data`.
- **The missing `else`.** The student wrote `key = cnt.keys()` / `if type_name in key: cnt[type_name] += 1`, so a class seen for the first time is never entered and the dictionary stays empty forever. The file supplies both the explicit `if/else` and the one-line equivalent `cnt[type_name] = cnt.get(type_name, 0) + 1`, plus the note that `key = cnt.keys()` is redundant because `in cnt` works directly.

The file also answers the natural follow-up — *can I just `load_asset` and use `type(obj).__name__`?* — with a section at `:147-166` that concedes the type name *would* be correct (the Python plugin generates a Python class per engine class, so a loaded `Texture2D` really does report `"Texture2D"`) and then gives the three reasons to prefer `find_asset_data` anyway: metadata-only access keeps assets off the heap, `load_asset` returns `None` on broken assets so `type(None).__name__ == "NoneType"` silently pollutes the census, and for Blueprints the loaded object's type is `Blueprint` — the asset — not the class it generates.

**Structural wart:** `all_assets` is rebound at `:35`, so the list exercise 1 iterated is discarded and replaced by a `/Game` recursive listing for exercise 2. The variable name does triple duty across the file. The comment at `:98-100` admits the scope mismatch with the exercise text ("项目中" vs `/Game/Characters`) and says the only change needed is the `list_assets` argument.

**Exercise 3 — the "5 newest assets" and why it goes to the filesystem.** The exercise's own hint says to look at `find_asset_data`'s return value. The file's investigation at `:104-113` reports the finding that makes the task interesting: `AssetData` has no creation-time field. The stub's field list for `AssetData` is `package_name`, `package_path`, `asset_name`, `asset_class` (deprecated), `asset_class_path`, plus `to_soft_object_path` and the `is_*` predicates — no timestamps. So the solution walks out of the asset registry and onto disk: `find_asset_data(path).package_name` → strip the `/Game/` prefix → `os.path.join(project_content_dir(), rel + ".uasset")` → `os.path.getmtime` → `sorted(..., key=..., reverse=True)[:5]`. The `return 0` fallback for a missing file is deliberate so the sort does not raise.

Two details this leaves on the table. The `key=` callback is invoked once per element during `sorted`, and then the print loop at `:141-144` calls `get_asset_file_time(asset_path)` *again* for each of the top five — two `find_asset_data` calls and two stat calls per displayed row. And the `package_name` → filename mapping is a text transform, not a registry lookup, so it is only valid for assets under `/Game`; anything in a plugin content root or an engine content root silently falls into the `getmtime`-absent branch and sorts as oldest.

### `my02.py` — three corrections, one unimplemented exercise

`my02.py` opens with `UnrealLog(text)`, a three-line banner helper (`:4-7`), called at `:13` with the project name — a second, incompatible banner style next to `02_logging.py`'s `log_section`. `get_editor_world()` at `:25-31` is the file's factored-out fix and documents why subsystems must be fetched rather than constructed directly.

The three 【修改前】 blocks each cover a different failure class:

1. **`log_level(color)` — a parameter received and never used** (`:57-88`). The original called `print(world.get_name())`. Three separate faults are named: `color` was dead, so all three "different colour" calls rendered identically; `print()` never reaches the viewport; and the world context was missing. The fix converts the Python list to `unreal.LinearColor(*color)` and passes keyword arguments, with `duration=10.0`. This is the file's best demonstration that a silently ignored argument is harder to notice than an exception.
2. **`inspect_all_assets(path)` — correct but fragile** (`:95-118`). The original passed `recursive` positionally and dereferenced `find_asset_data` unconditionally. The fix restores the keyword and adds an `is_valid()` guard with a `log_warning` + `continue`. `find_asset_data` returns an `AssetData`, not an optional, so an invalid entry is a struct full of empty values rather than `None` — which is exactly why the guard is needed instead of a `None` check.
3. **`log_screen(text)` — `None` as world context** (`:124-129`). `print_string(None, text)` fails silently in the editor; the fix reuses `get_editor_world()`.

**Exercise 3 of lesson 2 — "a logging system that writes to both the screen and a log file" — is not implemented.** `my02.py` contains no `open()` call and no file output; `log_level`'s `print_to_log=True` writes to the Output Log, not to a file. The closest working implementations of that exercise live elsewhere in the repository: `08_AdvancedTopics/01_batch_operations.py` (report writing) and `04_EditorScripting/02_menu_extension.py`'s `ToolConfig` (JSON persistence). The gap is not marked in the file, unlike `my03.py`'s explicit 【跳过】.

Both remaining tests at `:136-137` hard-code `/Game/EditorWidgetUtilities` — the same Lyra-specific scope as `03_editor_basics.py:180` — and the screen-message text is the literal `"abcdomg"`.

### `my03.py` — a fenced-off copy and a wrong reason to skip

`my03.py` is the chapter's worst-shaped file, and `architecture/script-conventions.md` already records the top-level problem: `import unreal` on line 1, then lines 3-9 are a multi-line string used as a block comment to fence off a copy of `03_editor_basics.py`'s content-browser selection section. Because it is the first statement after the import, that fence *is* the module docstring — the file has no documentation and the platform-copy code exists twice in the repository.

Exercise 2 is marked 【跳过】 at `:15-20` with the reason that `make_dialog` "几乎必定卡死 UI" and that real async progress needs C++ or an Editor Utility Widget. Per the analysis above, the mechanism named is wrong — `03_editor_basics.py` runs the same call successfully and names `time.sleep` as the culprit — and the recommended escape hatch is unnecessary for a bounded scan. The conclusion (don't run an unbounded loop on the main thread) is right; the stated cause would mislead a reader into avoiding `ScopedSlowTask` entirely.

The two implemented functions are correct and worth reusing:

- `print_static_mesh_positions()` (`:40-73`) filters with `isinstance(actor, unreal.StaticMeshActor)`, logs `get_actor_label()` and a formatted `get_actor_location()`, and counts. `isinstance` is the right predicate because it matches native subclasses too, unlike a name comparison.
- `print_selected_actor_info()` (`:78-100`) guards the empty selection first with a `unreal.log` hint and an early `return` — the defensive shape that `04_EditorScripting/01_editor_utility.py:208-238` turns into `require_selection` — then prints label, type, location, rotation and scale with `:.1f`/`:.2f` formatting. Note the rotation line labels the components `P=`, `Y=`, `R=` in `pitch, yaw, roll` order while `unreal.Rotator`'s positional constructor order is `(roll, pitch, yaw)`; reading each component by name as this file does is what keeps that trap out of the code.

Both functions are invoked at module scope (`:104-105`), so the file cannot be loaded without scanning the level.

## Corrections to the lesson text

| Location | Stated | Actually |
| --- | --- | --- |
| `01_Basics/01_hello_unreal.py:66-83` | `EditorLevelLibrary` is the editor-class API to learn | deprecated plugin; `03_editor_basics.py:64-77` teaches the subsystem replacement |
| `01_Basics/02_logging.py:18` | `print_string` signature ends at `duration` | real signature has a 7th `key: Name = "None"` parameter |
| `01_Basics/02_logging.py:130-135` | `show_screen` passes `None` as world context | the same file's `:53-56` warns against exactly this; `utils/helpers.py:62-70` is the fixed version |
| `01_Basics/02_logging.py:166` | bare `except:` on property read | swallows `KeyboardInterrupt` and discards the cause |
| `01_Basics/03_editor_basics.py:27`, `:121-123` | `normalize_filename` unifies slashes *and* collapses `//` and `../` | stub: it only converts slashes; `remove_duplicate_slashes` and `collapse_relative_directories` are separate functions, neither called |
| `01_Basics/03_editor_basics.py:232-234` | two notification routes, `show_message` blocks | true, plus: under `-unattended` it returns `default_value` (`AppReturnType.NO`) instead of blocking |
| `01_Basics/my03.py:15-20` | `make_dialog` in Python will stall the UI | `time.sleep` / blocking work stalls it; `03_editor_basics.py:180-212` runs `make_dialog(True)` fine |
| `01_Basics/my02.py` exercise 3 | implied implemented | no file output anywhere in the file |

## Safe defaults this chapter establishes

| Rule | Where it is taught | Why |
| --- | --- | --- |
| `unreal.log*` for text, `print_string` for the screen | `02_logging.py:36-86` | no executable `print()` exists in the tree |
| Always pass a real editor world to `print_string` | `02_logging.py:53-56`, `my02.py:57-58`, `my02.py:124-129` | `None` fails silently |
| `find_asset_data` to inspect, `load_asset` only to use | `my01.py:147-166`, `03_editor_basics.py:126-133` | keeps assets off the heap; `None` and `NoneType` cannot pollute counts |
| Check `is_valid()` on `AssetData` | `my02.py:95-118` | an invalid struct is empty, not `None` |
| Never `time.sleep()` on the editor's main thread | `03_editor_basics.py:164-171` | the UI thread is shared; the editor appears hung |
| `make_dialog()` must be called explicitly, `should_cancel()` every frame | `03_editor_basics.py:190-198` | constructing the task shows nothing; cancellation must be re-read |
| Reach editor state through `get_editor_subsystem()` and reuse the handle | `03_editor_basics.py:60-77`, `my02.py:25-31` | `EditorLevelLibrary` is deprecated; constructing subsystems directly is the old form |
| Wire `get_editor_world()` through one helper | `my02.py:25-31` | every screen-message call in the chapter needs the same context |

## Representative checks

- `02_logging.py:130-135` versus `utils/helpers.py:62-70` — the only pair in the repository where the same helper exists in a buggy and a fixed form, making it the best unit test target for the world-context rule.
- `my01.py:41-97` — the four-error census is the chapter's worked example of the two most common UE Python mistakes: treating an `Array[str]` element as an object, and reading the engine class from a Python type.
- `03_editor_basics.py:180-212` — the progress-dialog demo, and the counter-example to `my03.py`'s claim about `make_dialog`.
- `01_Basics/03_editor_basics.py:114-127` — the `normalize_filename` block, which is simultaneously a correct lesson about guessing API names and an incorrect description of what the API does.

## Related pages

- `/openwiki/architecture/script-conventions.md` — the docstring skeleton, the 🎯 exercise blocks, and the commented-out `print` remnants
- `/openwiki/architecture/repository-layout.md` — where `01_Basics/` sits among the chapters and how `my*.py` differs from the lesson files
- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` — the full `EditorLevelLibrary` deprecation map and the `show_notification` case
- `/openwiki/operations/running-and-verifying-scripts.md` — `exec(open(...).read())`, `print()` vs `print_string`, and the world-context trap
- `/openwiki/reference/utils-helpers.md` — the vendored descendants of `02_logging.py`'s helpers
- `/openwiki/reference/utils-ui-helpers.md` — `show_message`, `ProgressBar`, and the `ScopedSlowTask` wrapper
- `/openwiki/workflows/level-and-actors.md` — where the `EditorActorSubsystem` migration taught here is applied