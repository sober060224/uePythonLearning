---
type: architecture
title: Script Writing Conventions and Validation Rules
description: This repository uses a unified script skeleton, docstring-embedded API signature lists, Chinese comments with tagging notation, and mandatory verification rules referencing PythonStub/unreal.py. These replace absent tests and CI to guarantee editor script correctness and instructional readability.
tags: [conventions, annotations, verification, style]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# Script Writing Conventions and Validation Rules

## Why these "conventions" exist

Within this repository, conventions take on roles handled by tooling elsewhere. Since the `unreal` module only exists inside the editor process, scripts cannot be imported by local interpreters and cannot pass through any automated validation. There are no tests, linters, or code CI in the repository. Correctness is therefore enforced by two practices: **consulting engine stub files before writing code**, and documenting verification findings alongside erroneous patterns in comments. This workflow is formalized into the reusable rules below.

## Script Skeleton

### Three-part structure for official lessons

Each official lesson is a sequentially executed module-level script with this form: top-level docstring → `import` statements → numbered sections separated by `# ─────` divider lines → a trailing `🎯 Exercises` comment block.

The docstring is a template framed by `=` separator lines. Fields vary slightly between lessons, but `Learning Objectives` appears across all 23 official lessons, and `APIs Available for Exercises` (written as `APIs Available for This Lesson` in the first 3 lessons) appears in all 23 lessons. These two serve as stable anchors for the skeleton. Other optional fields include `Prerequisites` (only 2 lessons), `Execution Method` (only 3 lessons), `Core Classes` (9 lessons), and `Application Scenarios` (e.g. `08_AdvancedTopics/02_external_data.py:14-17`).

### API signature lists inside docstrings

The most substantial section of the template is the API list: each line contains **a verbatim signature copied from the stub file**, followed by `——` or `--` and a one-sentence rationale for its use:

```python
APIs Available for Exercises:
  unreal.BlueprintEditorLibrary.reparent_blueprint(blueprint, new_parent_class) -> None
      —— Reassign blueprint parent class; core API for batch parent modification in exercise 3
  unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).get_tag_values(asset_path: str) -> Map[Name, str]
      —— Retrieve all tag-value pairs for an asset
    (Note: get_tag_values belongs only to EditorAssetSubsystem; EditorAssetLibrary does not have this method)
```

This is not a documentation excerpt. It acts as a self-check checklist for learners: it locks down required call signatures, argument names, default values and return types, so mistakes from "writing APIs from memory" are caught before coding begins. The list may even include counterexample warnings (the note above stating `EditorAssetLibrary` lacks this method).

### Trailing exercise block

Scripts end with a `🎯 Exercises` comment block listing roughly 3 small tasks built around the lesson APIs. Some tasks carry a `【Skip】` marker explaining why they are omitted (for example, `01_Basics/my03.py:15-18` notes that `ScopedSlowTask.make_dialog` almost always freezes the UI in Python because the Python main thread shares execution with the editor).

## Output: Use only `unreal.log`, never `print`

The repository contains **657** `unreal.log*` calls and **0** genuine `print(` statements. This is an explicit convention: `print` inside the editor Python Console does not route to UE logs. Commented-out `print` statements are retained as comparison references, with the reasoning written immediately adjacent:

```python
# 【Before modification】print() used for output — print does not route to UE logs in the editor Python Console.
# Per repository convention, replaced with unreal.log(); output appears in the Output Log.
unreal.log("Hello, Unreal Engine!")
```

Commented-out `print` remnants exist in 8 files (`01_Basics/`, `02_AssetManagement/my01.py`, `03_BlueprintAutomation/01_blueprint_basics.py`, etc.) as intentional instructional artifacts, not oversights. Section headers are consistently rendered with string literals such as `unreal.log("=" * 50)` instead of importing printing utilities.

## Comments as teaching material: Tagging Notation

Chinese comments are first-class citizens in the repository, using standardized square-bracket tags to denote comment intent. The most frequent tags:

| Tag | Files containing tag | Purpose |
|------|-----------|------|
| `【Common Pitfall】` / `【Beginner Common Pitfall】` | 20+ | Contrast incorrect and correct implementations |
| `【Before modification】` | 14 | Paste the original erroneous implementation of this code segment |
| `【Issue Analysis】` | 10 | Explain why the bug occurs, typically citing stub file evidence |
| `【UE Concept】` | 4 | Explain engine-level concepts (component trees, transactions, Slate, etc.) |
| `【In-depth Simplification】` | 3 | Analogical explanations for beginners |
| Others | — | `【Note】【Important】【Key】【Performance】【Python Syntax】【Use Case】【User Cancellation Detection】`, etc. |

### "Evidence-based Bug Fix" Pattern

The most reusable pattern pairs `【Before modification】` with `【Issue Analysis】`: preserving faulty code alongside its root cause, and documenting **how the bug was verified**. Two representative examples:

- `utils/helpers.py:213-227`: Documents that three functions originally called `unreal.Transactions.xxx`, but this class does not exist. Inspection of `Intermediate/PythonStub/unreal.py` revealed transaction methods reside on `SystemLibrary`. The true signatures were transcribed line by line (`begin_transaction(context: str, description: Text, primary_object: Object) -> int`, etc.), concluding the original code had both an incorrect class name and mismatched argument count.
- `01_Basics/03_editor_basics.py:219-233`: Records that `unreal.EditorUtilityLibrary.show_notification` raises `AttributeError`. Verification found the `unreal` module exports neither `NotificationInfo` nor `NotificationManager`, because blueprint notifications use pure C++ Slate `FNotificationInfo`, and Python bindings only expose `UFUNCTION`s within the `UObject` hierarchy.

This approach turns faulty code itself into primary teaching material, and the verification workflow ("inspect unreal.py") can be reproduced by learners. It partially replaces automated testing: every resolved bug retains a traceable evidence chain.

## Mandatory Validation Rules

For all UE5 Python API questions (whether writing scripts or answering queries), the engine auto-generated stub file `Intermediate/PythonStub/unreal.py` **must** be consulted first. It is the single authoritative source for all class, method, and property signatures. Do not rely on memory, official documentation, or guesswork. If an API cannot be found in the stub file, the correct response is "This API is not present in the stub file", rather than inventing a name.

Script comments repeatedly reference this file as evidence: "Search `Intermediate/PythonStub/unreal.py` to verify" (`01_Basics/03_editor_basics.py:226`), "Searching for `SimpleConstructionScript` in PythonStub/unreal.py returns no results" (`03_BlueprintAutomation/02_blueprint_components.py:19`), "Self-check: search `class TextureCompressionSettings` in PythonStub/unreal.py to view all members" (`06_MaterialAndTexture/03_texture_management.py:154`), "Searching for add_row in PythonStub/unreal.py finds nothing" (`08_AdvancedTopics/02_external_data.py:305`), and `utils/helpers.py:216`. The stub file resides within the host project, with relative path `..\Intermediate\PythonStub\unreal.py` from the repository root.

## Language and Citation Rules for Contributors (including AI Assistants)

The repository root and `AGENTS.md` specify output language and citation format: always reply in Simplified Chinese (including code comments, explanations, summaries). After every code snippet, attach a concise API function signature and description. For Unreal-related code, also provide the exact link to the official Unreal Engine Python API documentation (example: `[https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedSlowTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedSlowTask)`).

Important distinction: **No official documentation URLs appear inside script bodies**. A full search of `.py` files in the repository returns zero matches for `docs.unrealengine.com` or `dev.epicgames.com`. Documentation links are reserved for answers and explanations; the authoritative API source inside scripts remains the stub file. The three `docs.unrealengine.com/5.0` links in `README.md:104-106` are reference entries in the lesson index and are outdated versions.

## Boundaries and Known Breaches of Conventions

These are conventions, not enforced mechanisms, so inconsistencies exist. Expect these when reading code:

- **Non-rigid skeleton**: `Prerequisites`, `Execution Method`, and `Core Classes` only appear in a small subset of lessons. `03_BlueprintAutomation/my02.py`, `my03.py`, both scripts under `07_SequenceAndCinematic/`, and `08_AdvancedTopics/03_automation_testing.py` — five scripts total — omit `# ─────` section dividers entirely. `08_AdvancedTopics/03_automation_testing.py` uses classes plus a test suite structure and diverges from the lesson skeleton.
- **`my*.py` as counterexamples**: `01_Basics/my03.py:1-10` places `import unreal` on the first line while the docstring is treated as a multi-line block comment to disable an entire code block. This violates the official lesson skeleton and strips the docstring of semantic meaning. `AGENTS.md` explicitly states `my*.py` are not normative examples and their patterns must not be copied.
- **File hygiene**: `03_BlueprintAutomation/02_blueprint_components.py` is the only script with a UTF-8 BOM (harmless but redundant). Tracked `__pycache__` `.pyc` files are repository noise and unrelated to in-script conventions.