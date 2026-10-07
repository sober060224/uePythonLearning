---
type: operations
title: Running and self-check scripts inside the editor
description: Repository scripts can only execute within a live Unreal Editor instance. Four execution methods (Python Console, command-line -ExecutePythonScript, editor UI, exec(open())), applicable scenarios for each, output routing rules, plus validation via stub files and in-editor testing in the absence of unit tests or CI pipelines.
tags: [operations, running, verification, editor]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---
# Running and self-check scripts inside the editor
## Prerequisites
Before running any script, enable two plugins inside the editor: **Python Editor Script Plugin** and **Editor Scripting Utilities**, then restart the editor (`README.md:7-14`). The console is accessible via **Window → Developer Tools → Python Console**, shortcut `Alt+Shift+P` (`README.md:15-18`).

A notable caveat: the second required plugin, **Editor Scripting Utilities, is deprecated**. All methods exposed by its `EditorLevelLibrary` carry `deprecated:` annotations; see `/openwiki/concepts/nonexistent-and-deprecated-apis.md`. Modern scripting workflows do not actually require it, but the repository prerequisites and parts of course material still reference it.

## Four execution methods
`README.md:21-26` documents these four approaches, while `04_EditorScripting/01_editor_utility.py:55-61` provides a three-way classification by use case; the two sources complement each other:

| Method | Command / Entrypoint | Use Cases | Limitations |
|---|---|---|---|
| Python Console | Open with `Alt+Shift+P`, execute segment by segment | Debugging, interactive exploration | Only suitable for short snippets and line-by-line validation |
| `exec(open(...).read())` | Run inside Console: `exec(open("absolute/path/to/script.py").read())` | **Preferred for this repository** (`AGENTS.md:33-36`) | Requires absolute path; executes within the console’s current scope |
| Command line | `UnrealEditor.exe Project.uproject -ExecutePythonScript="path/to/script.py"` | Batch jobs, CI/CD | Requires companion headless arguments (below) |
| Editor UI | Invoked via Editor Utility Widget / Blueprint | Tool panels for non-programmers | Requires pre-built UI assets; not pure Python |

### Why `exec(open(...).read())` is the preferred option
`04_EditorScripting/02_menu_extension.py:223-241` explains its semantics: read file content as a string and evaluate it as code. **Executed code runs in the current scope**, so it can access variables already present in the Console. The embedded safety note also points out the tradeoff: `exec()` runs arbitrary code, so only use it for trusted, self-authored scripts — all scripts here are project-local, so usage is valid.

One direct implication: entry guards are meaningless under this execution model. In `03_BlueprintAutomation/my03.py:541-542`, the repository’s only `if __name__ == "__main__": main()` block is fully commented out. Instead, the caller (Console or parent script) must explicitly invoke `main()`.

Another consequence: **the Console’s working directory is NOT the repository root**. Use absolute paths, or paths relative to the project root, e.g. `PythonLearning/01_Basics/01_hello_unreal.py`. This rule appears both in `AGENTS.md:34-36` and course docstrings (`01_Basics/01_hello_unreal.py:15-17`, `01_Basics/02_logging.py:11-12`, `01_Basics/03_editor_basics.py:11-12`). The robust pattern given in `04_EditorScripting/02_menu_extension.py:244-251` avoids hardcoded paths: combine `unreal.Paths.project_dir()` with relative path via `os.path.join()`, then validate existence with `os.path.exists()`.

### Enabling `import utils.helpers`
`utils/` contains no `__init__.py`. Imports for helpers rely on runtime modification of `sys.path`: append `r"...\PythonLearning"` to `sys.path`, then `from utils.helpers import *` (`AGENTS.md:26-28`, also documented in the module docstring of `utils/helpers.py:1-13`).

This requirement is inconsistently applied across course material. `06_MaterialAndTexture/02_material_instances.py:325-330` documents `from utils.helpers import get_actors_by_label` directly raises `ModuleNotFoundError` when the repo root is not added to `sys.path`. The prescribed fix is **not** patching `sys.path`, but inlining the logic as a list comprehension using `EditorActorSubsystem.get_all_level_actors()`. The comment states an implicit repository contract: **every course script must run independently**.

### Command-line / CI execution
`08_AdvancedTopics/03_automation_testing.py:443-460` provides a ready-to-copy headless invocation:
```
UnrealEditor.exe Project.uproject \
  -ExecutePythonScript="PythonLearning/08_AdvancedTopics/03_automation_testing.py" \
  -nullrhi -nosplash -unattended \
  -stdout -fullstdoutlogoutput
```
Purpose of each flag:
- `-nullrhi`: skip renderer initialization (headless mode, no GPU required)
- `-nosplash`: disable startup splash screen
- `-unattended`: unattended run, suppress pop-up dialogs
- `-stdout` / `-fullstdoutlogoutput`: stream full logs to standard output

Test outputs land under `Saved/TestResults/` (`08_AdvancedTopics/03_automation_testing.py:462`).

Matching code convention: **`run_all_tests()` must return the boolean result from `suite.run_all(tests)`** (`08_AdvancedTopics/03_automation_testing.py:439-441`). Without returning this value, CI will always receive `None`, treated as unconditional success.

### Editor UI trigger: essentially Editor Utility Widget
Chapter 4 Lesson 2 is titled "Custom Menus and Toolbar Extensions", yet the repository **contains no menu or toolbar registration code**. Its docstring acknowledges this route usually requires C++ or Editor Utility assets; the actual implemented workflow is:
1. `EditorAssetLibrary.make_directory(destination)` creates directories (idempotent; returns `True` without error if already exists, `04_EditorScripting/02_menu_extension.py:81-83`);
2. Instantiate factory with `unreal.EditorUtilityWidgetBlueprintFactory()`, then `asset_tools.create_asset(name, destination, unreal.EditorUtilityWidgetBlueprint, factory)` to generate EUW asset (`04_EditorScripting/02_menu_extension.py:85-100`);
3. Register scripts as repeatable commands via `SCRIPT_REGISTRY` (`04_EditorScripting/02_menu_extension.py:196-211`), entries like `{"path": "PythonLearning/02_AssetManagement/01_list_assets.py", "description": ..., "category": "Tools"}`;
4. `run_script(script_id)` performs lookup → resolves project-relative path → `exec(open(script_path).read())` for execution (`04_EditorScripting/02_menu_extension.py:221-255`).

In short: **UI is a UMG panel hosted inside EUW; Python acts merely as backend invoked by button clicks**. `EditorToolBackend` maintains state variables `status_message` / `progress` plus a dictionary route table via `on_button_click(button_id)` to handle this layer (`04_EditorScripting/02_menu_extension.py:119-127`).

## Output routing rules
This is one of the most common pitfalls: scripts run but output is invisible. Four channels behave completely differently:

| Call | Destination | Critical Limitations |
|---|---|---|
| `unreal.log` / `log_warning` / `log_error` | Output Log panel (searchable, savable) | Repository default channel; used in 657 locations |
| `print()` | Only visible inside the console shell | Does not enter UE logs or viewport — repository convention forbids this |
| `unreal.SystemLibrary.print_string(...)` | Top-left viewport overlay, auto-expires after several seconds | **First argument `world_context_object` must point to valid World. Passing `None` silently fails with no visible message** |
| `unreal.EditorDialog.show_message(...)` | Modal pop-up dialog | Blocks script execution; waits for user confirmation |

The distinction between `print()` and `print_string` is explicitly documented in `01_Basics/my02.py:49-60`: `print()` is native Python output, while `print_string` is Python binding for Blueprint’s Print String node; use it for on-screen rendering. The world context trap is restated in three locations (`01_Basics/02_logging.py:50-52`, `01_Basics/my02.py:57-58`, `utils/helpers.py:64-68`). The `show_screen()` helper in `utils/helpers.py:62-70` implements fallback logic: fetch editor World from `UnrealEditorSubsystem`; fall back to `unreal.log` on failure to prevent helper crashes. `utils/ui_helpers.py:35-55` wraps this logic more completely in `show_message()` (defaults `duration=5.0`, uses `COLORS` dictionary for colors).

One type detail for colors: UE expects `LinearColor` (r/g/b/a as floats 0~1). Explicit construction `unreal.LinearColor(*color)` from Python lists is the safe pattern (`01_Basics/my02.py:66-67`).

## Self-checking without unit tests and CI
This repository contains no linters, unit tests or CI for Python scripts. The `unreal` module only exists within the Unreal Editor process; scripts cannot be imported or validated by standalone local Python interpreters (`AGENTS.md:5-13`).

The single workflow at `.github/workflows/openwiki-update.yml` is documentation-only: scheduled cron `0 8 * * *` triggers `openwiki code --update --print`, then creates a PR targeting branch `openwiki/update` (`.github/workflows/openwiki-update.yml:1-36`, `:64-70`). It never executes or validates any Python script.

Validation relies on three reproducible practices:
1. **Stub file inspection (mandatory)**: For API verification, always consult `Intermediate/PythonStub/unreal.py`. Runtime equivalent: introspect with `dir()`, e.g. `print([m for m in dir(unreal.Paths) if 'norm' in m])` (`01_Basics/03_editor_basics.py:114-121`).
2. **In-editor live testing**: Scripts only have meaning inside a running editor. Verify against Output Log and viewport rendering, not theoretical print expectations.
3. **Preserve findings as comments**: Retain failed patterns together with root analysis using `[Before Change] + [Problem Analysis]` comments. Do not delete old buggy code; convention defined in `/openwiki/architecture/script-conventions.md`.

Important note: "Verified" labels in comments are valid only for a specific engine version. As an example: `02_AssetManagement/01_list_assets.py:20-21` states `get_tag_values` is absent on `EditorAssetLibrary` and triggers `AttributeError`, yet UE 5.8 stub files define it without deprecation markers. **Re-run step #1 before every modification; do not rely solely on historical comments.**

## Optional automation channel: unreal-mcp
`.mcp.json` at project root defines an `unreal-mcp` server of type `http`, endpoint `[http://127.0.0.1:8000/mcp](http://127.0.0.1:8000/mcp)`. `AGENTS.md:38-40` notes that when this server is reachable, AI agents can run scripts remotely inside the live editor without manual copy-paste. This is an agent helper transport, not a separate execution mode — code still runs under the same in-editor Python environment described above.

## Known friction points
- **Hardcoded sample paths**: `02_AssetManagement/my02.py:188-196` documents original code hardcoded absolute texture paths from another machine, executing immediately on load. The fix: comment out sample invocation, add `os.path.exists()` guard and emit hints instead of crashing. `02_AssetManagement/my01.py:152` restates the same principle: resolve project directory via `unreal.Paths.project_dir()`, avoid hardcoded absolute paths.
- **Output readability priority**: For human-readable Output Log tools, comments explicitly state **on-screen readability > machine parseability** (`03_BlueprintAutomation/my03.py:262`). These scripts use monospaced alignment and separators instead of JSON.
- **Progress dialog deadlocks**: `ScopedSlowTask.make_dialog` almost always freezes UI in Python, since Python shares the main thread with the editor (`01_Basics/my03.py:15-20`). True asynchronous progress UI requires C++ or Editor Utility Widget.