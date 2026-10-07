# AGENTS.md

## What this is

A Chinese-language tutorial course for UE5 **Python editor scripting**. Each `*.py`
lesson uses the `unreal` module and must be executed **inside a running UE editor** —
the `unreal` module does not exist outside the editor.

**Consequences:**
- Do NOT try to run or import these scripts with a local `python` interpreter
  (`python script.py` always fails at `import unreal`). There is no test/lint/
  CI setup in this repo — do not invent one. Script verification happens in-editor only.
- Scripts print/return results via `unreal.log()`, not stdout.

## Project layout

This folder (`PythonLearning/`) sits **inside** the `LyraStarterGame` UE project
(parent dir, `Lyra.uproject`, UE 5.8). Scripts operate on that project's `/Game`
assets, so cross-check asset paths against `<project>\Content\` before writing code.

- `NN_Topic/` lesson folders, files named `NN_topic.py`. All comments/annotations
  are in Chinese — preserve that style when editing.
- `my*.py` files (e.g. `01_Basics/my01.py`) are the learner's personal practice
  scripts with dense tutorial commentary — not course material; don't treat them
  as canonical examples.
- `utils/helpers.py` contains reusable helpers (`log_*`, asset/actor queries,
  `TransactionContext`, `Timer`). To import it from a lesson, prepend this repo root
  to `sys.path`: `sys.path.append(r"...\PythonLearning")` then `from utils.helpers import *`.
- `README.md` is the course index (Chinese).
- `AGENTS.zh-CN.md` is the Chinese translation of this file.

## Running scripts

Prefer the UE Python Console: `exec(open("absolute/path/to/script.py").read())`
(Console is at **Window → Developer Tools → Python Console**, `Alt+Shift+P`).
The editor's CWD is not this folder, so use absolute paths (or relative to the
project root like `PythonLearning/01_Basics/01_hello_unreal.py`).

If an `unreal-mcp` MCP server is configured (see `../.mcp.json`, endpoint
`http://127.0.0.1:8000/mcp`) and reachable, you can execute scripts in the running
editor through it instead of asking the user. The editor must already be running.

## UE Python API — verification rule (mandatory)

**Before answering any UE5 Python API question, always check `..\Intermediate\PythonStub\unreal.py` first.**
That file is the engine's auto-generated Python stub and holds the **real signatures** of every class, method, and property.
Do not rely on memory, documentation, or guesses — trust only the stub file.

Verification method:
```
# Search for a class name
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData"

# Search for a method name
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "disk_size"

# List a class's properties
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData" -Context 0,50
```

If an API cannot be found in the stub file, **do not answer "it should be XXX"** — say plainly "that API is not in the stub file".

## UE Python API gotchas (verified)

- **`unreal.Transactions` does not exist.** Transaction APIs are on `unreal.SystemLibrary`:
  `begin_transaction(context: str, description, primary_object) -> int`, `end_transaction()`,
  and `cancel_transaction(index: int)` (must pass the index returned by `begin_transaction`).
  See the corrected wrappers in `utils/helpers.py`.
- For asset queries (listing/statistics) use `EditorAssetLibrary.list_assets` /
  `find_asset_data` — do not `load_asset` to enumerate; loading every asset is slow
  and can return `None` for broken assets. In UE5 the asset class name is
  `asset_data.asset_class_path.asset_name` (UE4's `asset_class` is gone).
- `AssetData` has no `disk_size` property. Getting the file size requires converting to a disk path:
  `content_dir = unreal.Paths.project_content_dir()`, then
  `disk_path = content_dir + asset_path.replace("/Game/", "") + ".uasset"`,
  then `os.path.getsize(disk_path)`.

## Global instructions

- Always answer the user in Simplified Chinese (including code comments, explanations, and summaries).
- Do not reply in English unless the user explicitly asks for it.
- After every code snippet, append a concise API function signature with a brief description at the end.
- For Unreal-related code, also give the exact path of the API in the official docs https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/index ; other code needs no doc link. Example: ScopedSlowTask: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedSlowTask

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Do not enumerate, preload, or search wikis at task start. Use retrieval when the user asks for it, when unfamiliar architecture or dependency behavior materially affects the task, or when source inspection leaves an important uncertainty. Stop once the question is grounded.
- When those conditions apply and OpenWiki retrieval tools are available, use `openwiki_search` for just-in-time context and `openwiki_read` for the relevant complete sections. If search returns `workspace_required`, ask which listed workspace to use and retry with its ID.
- Use `openwiki_list_workspaces` or `openwiki_list_wikis` when workspace membership itself needs to be discovered.
- If the retrieval tools are unavailable, read `openwiki/quickstart.md` and follow its links to the relevant pages.
- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->
