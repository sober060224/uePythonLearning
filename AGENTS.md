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

## UE Python API — 查证规则（强制）

**回答任何 UE5 Python API 问题前，必须先查 `..\Intermediate\PythonStub\unreal.py`。**
这个文件是引擎自动生成的 Python 桩文件，包含所有类、方法、属性的**真实签名**。
不要凭记忆、不要凭文档、不要编造——只信桩文件。

验证方法：
```
# 搜索类名
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData"

# 搜索方法名
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "disk_size"

# 查看类的属性
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData" -Context 0,50
```

如果桩文件里找不到某个 API，**不要回答"应该是 XXX"**，直接说"桩文件里没有这个 API"。

## UE Python API gotchas (verified)

- **`unreal.Transactions` does not exist.** Transaction APIs are on `unreal.SystemLibrary`:
  `begin_transaction(context: str, description, primary_object) -> int`, `end_transaction()`,
  and `cancel_transaction(index: int)` (must pass the index returned by `begin_transaction`).
  See the corrected wrappers in `utils/helpers.py`.
- For asset queries (listing/statistics) use `EditorAssetLibrary.list_assets` /
  `find_asset_data` — do not `load_asset` to enumerate; loading every asset is slow
  and can return `None` for broken assets. In UE5 the asset class name is
  `asset_data.asset_class_path.asset_name` (UE4's `asset_class` is gone).
- `AssetData` 没有 `disk_size` 属性。获取文件大小需要转磁盘路径：
  `content_dir = unreal.Paths.project_content_dir()`，然后
  `disk_path = content_dir + asset_path.replace("/Game/", "") + ".uasset"`，
  再用 `os.path.getsize(disk_path)`。

## 全局指令

- 始终使用简体中文回答用户（包括代码注释、解释和总结）。
- 除非用户明确要求，否则不要用英文回复。
- 每次给出代码之后，还要在最后给出简洁的 API 函数签名和相应的简要介绍。
- 如果是 Unreal 相关代码，还要简洁地说明在官方文档 https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/index 里 API 的具体路径，别的代码不需要官方文档链接。例：ScopedSlowTask: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedSlowTask