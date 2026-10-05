# AGENTS.md（中文版）

> 英文原文见 `AGENTS.md`，以英文版为准；本文为对应中文翻译，供中文会话参考。

## 这是什么

一份中文撰写的 UE5 **Python 编辑器脚本**教程。每个 `*.py` 课程脚本都使用 `unreal`
模块，**必须在正在运行的 UE 编辑器内部执行** —— 编辑器之外不存在 `unreal` 模块。

**因此：**
- **不要**用本机 `python` 解释器去运行或导入这些脚本（`python script.py` 必定在
  `import unreal` 处失败）。本仓库没有 test/lint/CI 体系——不要自作主张去新建。脚本的
  验证只能在编辑器内完成。
- 脚本通过 `unreal.log()` 输出/返回结果，而不是 stdout。

## 项目结构

本文件夹（`PythonLearning/`）位于 **`LyraStarterGame`** UE 项目内部（父目录
`Lyra.uproject`，UE 5.8）。脚本操作的是该项目 `/Game` 下的资产，所以写代码前要把资产
路径跟 `<项目>\Content\` 里的实际情况核对一遍。

- `NN_Topic/` 为课程章节目录，文件名形如 `NN_topic.py`。所有注释/讲解都是中文——
  编辑时保持这一风格。
- `my*.py`（如 `01_Basics/my01.py`）是学习者自己的练习脚本，注释密集，属于过程记录，
  **不是课程范例**，不要拿它当标准写法参考。
- `utils/helpers.py` 是可复用的辅助函数（`log_*`、资产/Actor 查询、`TransactionContext`、
  `Timer`）。要在课程脚本里 import 它，先把本仓库根目录加进 `sys.path`：
  `sys.path.append(r"...\PythonLearning")`，然后 `from utils.helpers import *`。
- `README.md` 是课程目录索引（中文）。

## 运行脚本

首选 UE Python 控制台：`exec(open("绝对/路径/脚本.py").read())`
（控制台位置：**Window → Developer Tools → Python Console**，快捷键 `Alt+Shift+P`）。
编辑器的 CWD 不是本文件夹，所以要写绝对路径（或相对项目根，如
`PythonLearning/01_Basics/01_hello_unreal.py`）。

如果配置了 `unreal-mcp` MCP 服务（见 `../.mcp.json`，端点
`http://127.0.0.1:8000/mcp`）且可访问，也可以直接通过它让脚本在已运行的编辑器里执行，
不必每次麻烦用户。前提：编辑器必须先开着。

## UE Python API — 查证规则（强制）

**回答任何 UE5 Python API 问题前，必须先查 `..\Intermediate\PythonStub\unreal.py`。**
这个文件是引擎自动生成的 Python 桩文件，包含所有类、方法、属性的**真实签名**。
不要凭记忆、不要凭文档、不要编造——只信桩文件。

验证方法：
```powershell
# 搜索类名
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData"

# 搜索方法名
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "disk_size"

# 查看类的属性
Select-String -Path "..\Intermediate\PythonStub\unreal.py" -Pattern "class AssetData" -Context 0,50
```

如果桩文件里找不到某个 API，**不要回答"应该是 XXX"**，直接说"桩文件里没有这个 API"。

## UE Python API 注意事项（已验证）

- **`unreal.Transactions` 不存在。** 事务接口在 `unreal.SystemLibrary` 上：
  `begin_transaction(context: str, description, primary_object) -> int`、
  `end_transaction()`、以及 `cancel_transaction(index: int)`（必须传回 `begin_transaction`
  返回的那个索引）。修正后的封装见 `utils/helpers.py`。
- 资产查询（列目录/统计）用 `EditorAssetLibrary.list_assets` / `find_asset_data`，
  **不要**用 `load_asset` 去枚举——逐个加载很慢，遇到坏资产还会返回 `None`。UE5 里
  资产类别名是 `asset_data.asset_class_path.asset_name`（UE4 的 `asset_class` 已移除）。
- `AssetData` 没有 `disk_size` 属性。获取文件大小需要转磁盘路径：
  `content_dir = unreal.Paths.project_content_dir()`，然后
  `disk_path = content_dir + asset_path.replace("/Game/", "") + ".uasset"`，
  再用 `os.path.getsize(disk_path)`。

## 全局指令

- 始终使用简体中文回答用户（包括代码注释、解释和总结）。
- 除非用户明确要求，否则不要用英文回复。
- 每次给出代码之后，还要在最后给出简洁的 API 函数签名和相应的简要介绍。
- 如果是 Unreal 相关代码，还要简洁地说明在官方文档 https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/index 里 API 的具体路径，别的代码不需要官方文档链接。例：ScopedSlowTask: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedSlowTask