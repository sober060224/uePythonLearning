---
type: architecture
title: Repository Layout & Course Structure
description: PythonLearning is a standalone git repository nested inside the UE 5.8 project LyraStarterGame. It organizes 34 editor scripts under a three-tier structure:Official Lessons / Personal Practice Drafts / Shared Utility Library, maintaining consistency via Chinese docstring templates and unreal.log conventions.
tags: [layout, repository, course-structure, conventions]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---
# Repository Layout & Course Structure
## What This Repository Is and Its Boundaries
`PythonLearning/` itself **is not** an Unreal project. Instead, it is a tutorial set for Chinese UE5 Python editor scripting, with the git repository root located here. Physically, it is nested within the host project `LyraStarterGame/` (the parent directory contains `Lyra.uproject`, UE 5.8). As a result, `/Game/...` paths inside scripts refer to assets in the host project rather than content within this repository. Before writing code, asset paths should be cross-checked under `<project>\Content\`.

This placement imposes the repository's strictest constraint: the `unreal` module **only exists within a running Editor process**. Three rules derive from this constraint and apply across the entire repository:
- Do not run or import these scripts using a local `python` interpreter — `python script.py` will always fail at `import unreal`.
- This repository **has no** test, lint, or CI validation setup. The sole GitHub Actions workflow only updates documentation (see below). Script correctness can only be verified inside the Editor.
- Scripts output through `unreal.log()` instead of stdout.

## Directory Structure & Scale
8 lesson directories + 1 utility library directory, totaling 34 git-tracked `.py` files and 11749 lines:

| Directory | Official Lessons | `my*.py` Practice Drafts | Total Lines |
|------|--------|-----------------|----------|
| `01_Basics/` | 3 | 3 | 1044 |
| `02_AssetManagement/` | 3 | 3 | 2286 |
| `03_BlueprintAutomation/` | 3 | 3 | 1804 |
| `04_EditorScripting/` | 3 | 0 | 1275 |
| `05_LevelAndActors/` | 3 | 0 | 1227 |
| `06_MaterialAndTexture/` | 3 | 0 | 1230 |
| `07_SequenceAndCinematic/` | 2 | 0 | 747 |
| `08_AdvancedTopics/` | 3 | 0 | 1541 |
| `utils/` | — | — | 595 (2 files) |

There are 23 official lesson scripts in total. `07_SequenceAndCinematic/` is the only chapter with just 2 lessons (`01_level_sequence.py`, `02_camera_animation.py`), and the chapter table in `README.md` lists only two entries for it. `README.md` is the only index that enumerates all 23 official lessons with their respective topics.

## Three-Tier Responsibilities
### 1. Official Lessons `NN_Topic/NN_topic.py`
Each lesson is a sequentially executed module-level script: a three-part docstring at the top (`Learning Objectives` / `Prerequisites` / `How to Run` / list of API signatures for APIs likely used in this lesson), numbered sections progressing through the content, and a `🎯 Exercises` comment block at the end. All 23 official lessons include `Learning Objectives` in their docstrings.

```python
"""
Lesson 1: Hello Unreal - Your first UE Python script
Learning Objectives: ...
APIs likely used in this lesson:
  unreal.EditorAssetLibrary.list_assets(directory_path: str, recursive: bool = True,
      include_folder: bool = False) -> Array[str]  — Lists assets under the specified directory path
"""
import unreal
...
# 🎯 Exercises
# 1. Modify the code to list only assets under the /Game/Characters path
```

The API list inside the docstring is not merely decorative: it serves as a self-check entry point for learners and explains the prevalence of comments across the repository advising to "consult `Intermediate/PythonStub/unreal.py` before writing code".

### 2. Personal Practice Drafts `my01.py`–`my03.py`

These only appear in chapters `01_Basics/`, `02_AssetManagement/`, and `03_BlueprintAutomation/`. They start directly with `import ...`, without the official lesson docstring template, and contain more conversational, dense comments (for example, `01_Basics/my01.py:2-3` uses "OS toolbox" and "time toolbox" to explain `os`/`time`).

`AGENTS.md` explicitly states they **are not lesson material and should not be treated as normative examples**. They are not indexed in `README.md` at all. The only files across the repository with `main()` and `if __name__ == "__main__"` guards are `03_BlueprintAutomation/my03.py:530` and `:541` — official lessons never use entry guards.

### 3. `utils/` Shared Utility Library

`utils/helpers.py` (313 lines) and `utils/ui_helpers.py` (282 lines) provide helper functions for logging, asset/Actor queries, math, paths, transactions, progress bars, and table printing. The "Utility Library" section in `README.md` registers them as general-purpose helpers and UI helpers.

## Tension Between `utils/` and the "Each Script Must Run Independently" Requirement

The import method specified in `AGENTS.md` prepends `sys.path` to lesson scripts then runs `from utils.helpers import *`. However, actual dependency relationships contradict the documentation:

- **No lesson script in the repository actually imports `utils`**. `grep` only finds two relevant mentions: usage examples within the docstring of `utils/helpers.py`, and a "common pitfall" comment block in `06_MaterialAndTexture/02_material_instances.py:325-328`. It notes that the original `from utils.helpers import get_actors_by_label` fails with `ModuleNotFoundError` when run standalone, because the PythonLearning folder is not added to `sys.path` for this lesson. The logic was therefore inlined directly within the lesson, justified by the requirement that "every script must run independently". There is no `__init__.py` inside the `utils/` directory.

Visible consequences of this constraint include duplicated logic across the repository:

- `log_section(title)` is defined separately in both `utils/helpers.py` and `utils/ui_helpers.py`, with identical names across modules. After `from utils.helpers import *` followed by `from utils.ui_helpers import *`, the latter silently overwrites the former.
- Queries such as `get_actors_by_label` are inlined on demand inside lesson scripts (see `06_MaterialAndTexture/02_material_instances.py:329-330`, which directly expands the list comprehension wrapping `EditorActorSubsystem.get_all_level_actors()`).

For this reason, treat `utils/` as **an optional toolbox and reference implementation of validated patterns**, not a shared base for all lessons. To determine a lesson's real behavior, inspect its internal code.

## Repository Hygiene & Generated Artifacts

- **No `.gitignore`**: `__pycache__/*.pyc` files were accidentally committed and remain tracked (17 tracked `.pyc` files), the only source-irrelevant noise in the repository.
- `openwiki/` is an evidence index directory generated by OpenWiki, owned by the toolchain. Do not edit manually.
- `.github/workflows/openwiki-update.yml` is a **documentation pipeline**: scheduled daily at UTC 08:00 (and manually via `workflow_dispatch`). It runs `openwiki code --update --print`, then uses `create-pull-request` to submit a PR on the `openwiki/update` branch. Its change scope covers `openwiki/`, `AGENTS.md`, the workflow itself, and `CLAUDE.md` if present. It **does not compile, execute, or validate any scripts**. The accurate phrasing for "this repository has no CI" is "there is no code validation pipeline", while the documentation update pipeline does exist.
- The block at the end of `AGENTS.md` (lines L85–L100) is an OpenWiki managed block (`<!-- OPENWIKI:START -->` … `<!-- OPENWIKI:END -->`), written by the tool. Do not modify it by hand.
- `ideas.md` is a scratchpad for pending ideas, currently containing only one entry: build an iterable asset import plugin (input a source folder path and export path, one-click import all assets and configure import settings per asset). There is no corresponding implementation directory or skeleton in the repository.

## Extension Points

- **Add a lesson**: Create `NN_Topic/NN_topic.py`, copy the official lesson docstring template (Learning Objectives / Prerequisites / How to Run / list of APIs likely used in this lesson) + numbered sectioning + trailing `🎯 Exercises`, and register it in the chapter table within `README.md`.
- **Add shared utilities**: Per existing conventions, prefer inlining logic within individual scripts first to preserve standalone script execution. If opting to `import utils/`, prepend `sys.path` setup code to that lesson and watch for silent name overrides across modules.
- **Add a practice draft**: Use the `myNN.py` naming convention, start directly with `import` statements, no official lesson template required.