---
type: reference
title: utils/ui_helpers.py API Reference
description: This document describes screen messages, editor notifications, dialog boxes, progress bars, selection validation and table printing utilities in utils/ui_helpers.py. It focuses on dead code removed from notify, the stub implementation of input_dialog, the relationship between ProgressBar and ScopedSlowTask, and name collision/overlap with helpers.py.
tags: [reference, utils, ui, python-api]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---
# utils/ui_helpers.py API Reference
`utils/ui_helpers.py` is a 282-line module importing only `unreal` (`:15`). It is the repository’s sole module dedicated to **user-facing feedback**: on-screen messages, editor notifications, dialog windows, progress bars, selection validation and table printing. Like `utils/helpers.py`, **no scripts currently import it**; its only mention appears in the tool library table in `README.md:91`. Its purpose is to consolidate scattered UE editor UI calls under a unified naming convention, while documenting three pieces of "apparently usable but non-functional" API as code comments.

## On‑Screen Messages (`:18-70`)
### `COLORS` `:23-32`
Mapping of eight color names to 4-element RGBA lists: `white`, `red`, `green`, `blue`, `yellow`, `cyan`, `orange`, `purple`. Values take the form `[r, g, b, a]`, with `a` always fixed at `1.0`.

### `show_message(text, color="white", duration=5.0)` `:35-53`
This is the core function of the module; all other display utilities route through it:
```python
c = COLORS.get(color, COLORS["white"])
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.print_string(
    world, text,
    print_to_screen=True, print_to_log=True,
    text_color=unreal.LinearColor(*c), duration=duration,
)
```
Lines 37–41 contain a [Before Modification] / [Issue Analysis] block recording two fixes, with more precise wording than `helpers.show_screen`:
1. **Passing `None` as world context** — The engine receives no target world to render on-screen output, resulting in silent failure inside the editor (no visible message and no error). The editor World must be supplied.
2. **Passing raw Python lists for colors** — Automatic conversion works in some engine builds, but explicitly constructing an `unreal.LinearColor` struct is robust and avoids version-dependent breakage. `LinearColor.__init__(r=0, g=0, b=0, a=0)` accepts four positional arguments, so unpacking `*c` matches exactly.

The `color` parameter accepts **color names**, not raw numeric values. Unknown color names silently fall back to white via `COLORS.get(color, COLORS["white"])` with no thrown error — this is an intentional lenient design, yet it means typos such as `"grey"` produce no warning.

Differences from `helpers.show_screen`: `ui_helpers.show_message` omits the fallback branch for empty world context (`helpers.py:61-62` has an `unreal.log` fallback) and assumes the editor World can always be retrieved. It explicitly sets both `print_to_screen` and `print_to_log` to `True` — messages render in the viewport **and** write to the Output Log. Its default `duration=5.0` is longer than `helpers.show_screen`’s 3.0 seconds.

### Four Semantic Shortcut Functions (`:57-70`)
| Function | Prefix | Color | Default Duration |
|---|---|---|---|
| `show_success(text, duration=3.0)` `:57-58` | `✅` | green | 3.0 |
| `show_warning(text, duration=5.0)` `:61-62` | `⚠️` | yellow | 5.0 |
| `show_error(text, duration=5.0)` `:65-66` | `❌` | red | 5.0 |
| `show_info(text, duration=3.0)` `:69-70` | `ℹ️` | blue | 3.0 |

None of these four shortcut functions carry docstrings; they only contain a single forwarding line. The module’s docstring strategy — only documenting functions prone to misunderstanding — matches `helpers.py`.

## Editor Notifications: `notify(text, notification_type="info")` `:78-110`
This function carries the heaviest comments in the file because a block of **dead code** was removed from it. Its docstring first reproduces the original implementation:
```python
type_map = {
    "info": unreal.NotificationType.INFO if hasattr(unreal, "NotificationType") else None,
    ...
}
```
Then two points of [Issue Analysis] (`:94-103`):
1. **`unreal.NotificationType` does not exist in Python stubs.** The bottom-right pop-up notifications in the editor are backed by the Slate UI framework (`FNotificationInfo`), pure C++ code not exposed to Python. Python bindings only export `UFUNCTION`s within the UObject system (the same analysis appears in `01_Basics/03_editor_basics.py:227-233`).
2. **`hasattr` guards prevent crashes but achieve nothing**: all mapped values resolve to `None`, are constructed and immediately discarded with never a read. Retaining such code creates false impression that `NotificationType` is available.

The honest fallback implementation maps `notification_type` values to color names (`:100-105`: `info/success/warning/error` → `blue/green/yellow/red`), calls `show_message(text, color, 5.0)` and runs `unreal.log(text)` (`:107-108`) to preserve copies in both viewport overlay and log. A comment summary serves as a repository guideline: **"On-screen messages are the closest equivalent to native notifications in UE5 Python: colored and auto-expiring."**

One interface detail: misspelled `notification_type` values also silently fall back to `"white"` without warnings.

## Dialog Boxes (`:112-154`)
### `show_message_dialog(title, message, msg_type="ok")` `:117-135`
`msg_type` accepts three values mapped to three `AppMsgType` members (`:125-129`):
| `msg_type` | `AppMsgType` |
|---|---|
| `"ok"` | `OK` |
| `"yes_no"` | `YES_NO` |
| `"yes_no_cancel"` | `YES_NO_CANCEL` |

Unknown values fall back to `OK`. The function invokes `unreal.EditorDialog.show_message(title, message, app_msg_type)` and **returns the raw `AppReturnType` unchanged** (not a boolean). The full stub signature is `show_message(cls, title: Text, message: Text, message_type: AppMsgType, default_value: AppReturnType = AppReturnType.NO, message_category: AppMsgCategory = AppMsgCategory.WARNING) -> AppReturnType` (`../Intermediate/PythonStub/unreal.py:352513`). `AppMsgType` and `AppReturnType` are both `EnumBase` types (stub locations `:6543` and `:6563`), and the latter has eight members: `NO/YES/YES_ALL/NO_ALL/CANCEL/OK/RETRY/CONTINUE`.

This module does **not** expose the last two parameters, so callers receive default behavior with two notable consequences:
- `message_category` defaults to `AppMsgCategory.WARNING`, so popups always display a warning icon even for plain informational prompts. `AppMsgCategory` is defined at stub line `:6526`.
- `default_value=AppReturnType.NO`, meaning pressing Esc or closing the window directly returns `NO`.

Additionally, `AppMsgType` contains other members not covered by the module’s `msg_type` whitelist: `OK_CANCEL`, `CANCEL_RETRY_CONTINUE`, `YES_NO_YES_ALL_NO_ALL`.

### `confirm_action(title, message)` `:138-141`
Wraps `show_message_dialog(..., "yes_no")`, compares the result against `unreal.AppReturnType.YES`, and returns a native boolean. Since `default_value` is `NO`, **closing the popup is treated as a negative confirmation**, a safe default.

### `input_dialog(title, message, default_value="")` `:144-154`
**This is a stub implementation, not a real input dialog.** It merely logs the title, message and default value via `unreal.log`, then **returns `default_value` verbatim**. The docstring and inline comments state the reason: UE Python has limited support for native input dialogs. The recommended real-world alternative is custom UI via Editor Utility Widgets (the EUW approach shown in `04_EditorScripting/02_menu_extension.py`, documented in `/openwiki/workflows/editor-scripting-tools.md`).

Callers **must** be aware: `input_dialog` always returns the default value, and any logic expecting user text input will not function. Similar stubs requiring careful handling of return values exist elsewhere in the repository, e.g. near `03_BlueprintAutomation/my03.py:262`.

## Progress Bar: `ProgressBar` (`:157-199`)
```python
with ProgressBar(100, "Processing...") as pb:
    for i in range(100):
        if pb.should_cancel():
            break
        pb.update(1, f"Processing item {i}")
```
| Member | Behavior |
|---|---|
| `__init__(total, description="Processing...")` `:175-179` | Stores `total`/`description`; initializes `task = None`, `current = 0` |
| `__enter__()` `:181-184` | Creates `unreal.ScopedSlowTask(self.total, self.description)`, calls `task.make_dialog(True)` (argument enables cancel button), returns `self` |
| `__exit__(*args)` `:186-187` | **Only sets `self.task` to `None`** |
| `update(amount=1.0, text="")` `:189-193` | If task exists, calls `enter_progress_frame(amount, text)` and accumulates `amount` into `current` |
| `should_cancel()` `:195-199` | Forwards to `task.should_cancel()` if task exists; otherwise returns `False` |

Key fact: **`unreal.ScopedSlowTask` is already a context manager natively**. Its stub defines `__enter__(self) -> ScopedSlowTask` (comment: begin this slow task) and `__exit__(...) -> bool` (comment: end this slow task), plus `make_dialog(can_cancel=False, allow_in_pie=False)`, `make_dialog_delayed(delay, can_cancel=False, allow_in_pie=False)`, `enter_progress_frame(work=1.0, desc="")`, `should_cancel() -> bool`, `tick_progress()` and `__init__(work: float, desc: Union[Text, str] = "", enabled: bool = True)` (in `../Intermediate/PythonStub/unreal.py`, class `ScopedSlowTask`).

Therefore, the shorter native pattern from course examples covers all functionality, with more intuitive placement of `make_dialog` (`02_AssetManagement/03_asset_actions.py:220-233`):
```python
with unreal.ScopedSlowTask(len(asset_paths), "Moving assets...") as task:
    task.make_dialog(True)
    for asset_path in asset_paths:
        if task.should_cancel():
            break
        task.enter_progress_frame(1.0, f"Moving: {asset_path}")
        ...
```

Compared to this direct usage, `ProgressBar` only adds a manual `current` counter, at the cost of a real bug: **`__exit__` merely discards the reference and never invokes the wrapped `task.__exit__`**. `ScopedSlowTask.__exit__` is responsible for ending the slow task. Inside `with ProgressBar(...)`, it never runs explicitly; cleanup only happens indirectly via object destruction during Python garbage collection. This breaks the semantic guarantee that the task terminates at scope exit. No such defect exists when using raw `with unreal.ScopedSlowTask(...)`.

Additionally, calling `make_dialog` after task construction inside `ProgressBar.__enter__` is mandatory: the [Common Pitfall] note at `01_Basics/03_editor_basics.py:191-192` states that instantiating `ScopedSlowTask` alone does not display the progress window — `make_dialog()` must be called or the UI appears unresponsive.

One runtime limitation (outside this file but critical for usability): `01_Basics/my03.py:13-20` documents that `ScopedSlowTask.make_dialog` **almost always freezes the editor UI in Python**, since Python executes on the same main thread as the editor. Truly asynchronous progress requires C++ or Editor Utility Widgets.

## Selection Validation (`:202-237`)
| Function | Selection Source | Behavior on Insufficient Selection |
|---|---|---|
| `require_selected_actors(min_count=1, message=None)` `:207-223` | `get_editor_subsystem(EditorActorSubsystem).get_selected_level_actors()` | `show_warning` + returns `None` |
| `require_selected_assets(min_count=1, message=None)` `:226-237` | `unreal.EditorUtilityLibrary.get_selected_asset_data()` | `show_warning` + returns `None` |

Both return **either a list or `None`** (they do not throw exceptions), so callers must perform null checks. Default messages read `"Please select at least {min_count} Actor(s)"` and `"Please select at least {min_count} asset(s)"` respectively; the `message` parameter overrides these strings.

`require_selected_actors` carries a [Before Modification] comment (`:211-213`): the old implementation using `EditorLevelLibrary.get_selected_level_actors()` emitted `DeprecationWarning`, as Actor selection APIs have moved to `EditorActorSubsystem`. `require_selected_assets` has no migration note; it uses `EditorUtilityLibrary.get_selected_asset_data(cls) -> Array[AssetData]` (stub `../Intermediate/PythonStub/unreal.py:338546`), a `BlueprintFunctionLibrary` under module `Blutility` (stub `:338435`) with **no `deprecated:` tags on the class**. This is not an oversight — this path remains valid today. It returns `AssetData` rather than loaded asset objects; callers must call `load_asset` manually.

## Table Printing: `print_table(headers, rows, title="")` `:240-274`
Formats tabular data into fixed-width aligned tables written to logs instead of JSON. This is an explicit repository design choice (documented near `03_BlueprintAutomation/my03.py:262`: "readability on screen > parseability in code").

Workflow:
1. If `title` is non-empty, call `log_section(title)` (`:254-255`).
2. Calculate column widths: initial values are `[len(h) for h in headers]`. Iterate rows to take the maximum `len(str(cell))` for each column (`:258-262`). **This assumes every header item is already a string**: `len(h)` is used directly without wrapping in `str()`, while cell values are converted with `str()`.
3. Render header row and separator line: `" | ".join(h.ljust(w) ...)` and `"-+-".join("-" * w ...)` (`:265-266`).
4. Print each data row prefixed with two spaces (`:269-271`).

Two edge behaviors to note:
- **Column count mismatch is silently truncated.** `zip(headers, widths)` and `zip(row, widths)` terminate at the shorter sequence. Cells beyond the header count are discarded without error; rows shorter than the header only render partial columns.
- **No newline handling:** `\n` characters inside cells break column alignment.

`print_table` invokes `log_section` at line 254, while `log_section` is defined at the end of the file (`:277-281`). Runtime execution works (name resolution occurs at call time), but code readers may mistakenly assume it is imported elsewhere.

## Relationship with utils/helpers.py
The two modules do not import each other but overlap in three capabilities:
| ui_helpers | helpers | Relationship |
|---|---|---|
| `show_message` `:35` | `show_screen` `:50` | Wrappers around the same underlying `print_string` call; ui version adds named color mapping, `print_to_log`, 5-second default duration and removes world fallback logic |
| `log_section` `:277` | `log_section` `helpers.py:27` | **Two separate definitions with identical purpose and name** |
| `show_warning` `:61` etc. | `log_warn` `helpers.py:40` | Different output channels: the former renders viewport messages, the latter writes log-level warnings |

Neither module defines `__all__`. Executing `from utils.helpers import *` followed by `from utils.ui_helpers import *` causes the latter to **silently overwrite** the former’s `log_section` (and imported names such as `unreal`). No scripts currently import both modules, so this remains a latent hazard. However, the wildcard import style recommended in `AGENTS.md:26-28` can easily trigger this collision. The safe practice is to import only required names or import just one of the two modules.

## Points for Review
- `input_dialog` always returns `default_value` (`:144-154`); do not treat it as a real input channel.
- `ProgressBar.__exit__` does not delegate to `ScopedSlowTask.__exit__` (`:186-187`). Use raw `with unreal.ScopedSlowTask(...) as task:` when deterministic task cleanup is required.
- The last two parameters of `EditorDialog.show_message` are not configurable (`:131`); popups always show warning icons and treat Esc as `NO`.
- The fallback implementation of `notify` means native bottom-right editor notifications are unavailable in UE5 Python; supporting evidence is documented at `/openwiki/concepts/nonexistent-and-deprecated-apis.md`.

## Related Documentation
- `/openwiki/reference/utils-helpers.md` — Companion reference for the general utility library (the other half of the name collision issue)
- `/openwiki/operations/running-and-verifying-scripts.md` — Full comparison of output channels (viewport / log / popup)
- `/openwiki/workflows/editor-scripting-tools.md` — Workflow for replacing `input_dialog` with Editor Utility Widgets
- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` — Documentation for non-existent APIs such as `NotificationType` and `show_notification`