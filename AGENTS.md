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

## UE Python API gotchas (verified)

- **Check signatures in the generated stubs**, not docs: `..\Intermediate\PythonStub\unreal.py`
  is generated from the engine and is the authoritative reference.
- **`unreal.Transactions` does not exist.** Transaction APIs are on `unreal.SystemLibrary`:
  `begin_transaction(context: str, description, primary_object) -> int`, `end_transaction()`,
  and `cancel_transaction(index: int)` (must pass the index returned by `begin_transaction`).
  See the corrected wrappers in `utils/helpers.py`.
- For asset queries (listing/statistics) use `EditorAssetLibrary.list_assets` /
  `find_asset_data` — do not `load_asset` to enumerate; loading every asset is slow
  and can return `None` for broken assets. In UE5 the asset class name is
  `asset_data.asset_class_path.asset_name` (UE4's `asset_class` is gone).