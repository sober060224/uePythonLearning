---
type: concept
title: Non-existent APIs and Deprecated API Migration
description: This repository documents all API pitfalls encountered in comments:fictional classes like unreal.Transactions, non-existent functions (DataTable.add_row, blueprint variable reading, dependency queries, notifications), the deprecated Editor Scripting Utilities plugin and its migration mapping to three editor subsystems, plus inconsistencies between stub files and actual comments.
tags: [api-gotchas, deprecated, stub-verification, migration]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---
# Non-existent APIs and Deprecated API Migration
## The sole source of truth: stub files
There is no second authority within this repository for determining whether an API exists. The only reference is the auto-generated engine `Intermediate/PythonStub/unreal.py` file (located in the host project, relative to this repository at `..\Intermediate\PythonStub\unreal.py`). Evidence notes in the comments repeatedly point to the same action: inspecting the stub file.

To judge whether an API is deprecated, check for the `deprecated:` tag within the stub file docstring:
```
deprecated: The Editor Scripting Utilities Plugin is deprecated - Use the function in Editor Actor Utilities Subsystem
```
If the name cannot be found, the API does not exist. If the name exists without a `deprecated:` tag, the API remains usable (even if its parent plugin is in overall decline). The repository also documents a trick for reverse-lookup of names: instead of guessing API names, use `dir()` for self-inspection. The recommendation in `01_Basics/03_editor_basics.py:114-125` is `print([m for m in dir(unreal.Paths) if 'norm' in m])`.

## Fictional Class: `unreal.Transactions`
This is the most prominent pitfall across the repository. `unreal.Transactions` does not appear anywhere in the stub file; transaction interfaces reside on `unreal.SystemLibrary`, with signatures completely different from intuitive assumptions:
```
SystemLibrary.begin_transaction(context: str, description: Text, primary_object: Object) -> int
SystemLibrary.end_transaction() -> int
SystemLibrary.cancel_transaction(index: int) -> None
```
Three key points: `primary_object` is the main object being modified (the anchor in undo history; when bulk-modifying Actors, pass the first item in the list. If no specific object is available, pass the editor world since `World` is also a `UObject`). `cancel_transaction` must receive the index returned by `begin_transaction`. Description and context are two separate parameters. Supporting evidence comments are preserved in three locations: `utils/helpers.py:213-227` (which implements wrapper functions `begin_transaction` / `end_transaction` / `cancel_transaction` and the `TransactionContext` context manager), `04_EditorScripting/01_editor_utility.py:101-112`, `05_LevelAndActors/02_modify_actors.py:222-232` and line `:244` of the same file. `08_AdvancedTopics/02_external_data.py:464-469` concludes with a note: "Warning: unreal.Transactions does not exist; transaction methods are located on SystemLibrary".

## List of Non-existent Methods and Classes
| Misused Name | Truth from Stub File | Alternative Route in Repository |
|---|---|---|
| `unreal.Transactions.*` | Class does not exist | `SystemLibrary.begin/end/cancel_transaction` |
| `EditorUtilityLibrary.show_notification` | No such method; only a property of the same name exists on `TakeRecorderParameters.show_notifications` | See next section "Two Routes for Notifications" |
| `unreal.NotificationType` | Class does not exist | Remove branches pretending availability, use `print_string` instead |
| `DataTable.add_row` | No such method | CSV + `DataTableFunctionLibrary.fill_data_table_from_csv_file` |
| `BlueprintEditorLibrary.get_blueprint_variables` | No such method | `BlueprintEditorLibrary.list_member_variable_names(blueprint, include_inherited_members=True) -> Array[str]` |
| `EditorAssetLibrary.find_package_references` | No such method (only the reverse `find_package_referencers_for_asset` exists) | `unreal.AssetRegistryHelpers.get_asset_registry().get_dependencies(package_name, dependency_options)` |
| `EditorLevelLibrary.duplicate_actor` | This library contains no such method | `EditorActorSubsystem.duplicate_actors(actors, to_world, offset) -> Array[Actor]` |
| `EditorLevelLibrary.add_level_to_world` | This library contains no such method | `EditorLevelUtils.add_level_to_world(world, level_package_name, level_streaming_class)` |
| `unreal.Paths.normalize_path_name` | No such method (C++ equivalent is `FPaths::NormalizeFilename`) | `unreal.Paths.normalize_filename(path) -> str` |
| `CineCameraComponent.set_current_focal_length` | No such method | Directly assign properties `current_focal_length` / `current_aperture` |

Several notable details to remember:
- **Asymmetrical dependency query direction** (`03_BlueprintAutomation/03_blueprint_variables.py:222-235`): `EditorAssetLibrary` only exposes queries for "what references this asset". To query "what assets this asset references", you must go through the AssetRegistry. The second argument of `get_dependencies` must pass `AssetRegistryDependencyOptions`, with both soft and hard references enabled for full counting.
- **`add_level_to_world` missing a parameter** (`05_LevelAndActors/03_level_management.py:260-278`): Misplacing the class name is only the first error. The original call also omits the third parameter `level_streaming_class`, which determines the streaming behavior of the sub-level (`LevelStreamingAlwaysLoaded` for permanent loading, `LevelStreamingKismet` for blueprint or code-controlled loading).
- **Changed Actor duplication signature** (`05_LevelAndActors/02_modify_actors.py:318-330`): The replacement API accepts and returns lists. The `offset` parameter represents the position offset of duplicated actors relative to originals; manual `set_actor_location` is unnecessary.
- **Correct handling when `DataTable.add_row` is missing** (`08_AdvancedTopics/02_external_data.py:302-315`): Do not fake successful function execution. Instead, call `log_error` to state "UE Python has no DataTable.add_row" and honestly `return False`. The rationale in comments: "Rather than calling save_asset and returning True to mislead the caller into believing writes succeeded, return False truthfully".
- **Only valid approach when factory properties are missing** (`06_MaterialAndTexture/02_material_instances.py:69-76`): `MaterialInstanceConstantFactoryNew` has no parent material property. Parent materials must be bound after creation via `set_material_instance_parent`.

## Notifications: an entire capability is unavailable
The failure of `EditorUtilityLibrary.show_notification` is not merely a naming error. This capability is completely unavailable on the Python layer. The entire `unreal` module does not contain `NotificationInfo` / `NotificationManager`. The bottom-right pop-up notifications in Blueprints are implemented in pure C++ Slate `FNotificationInfo`, while Python bindings only export `UFUNCTION`s within the `UObject` system. Evidence and analysis are documented in `01_Basics/03_editor_basics.py:218-235`.

Therefore, there remain only two ways to notify users within UE5 Python:
1. `EditorDialog.show_message(...)` — Modal pop-up that blocks script execution until the user clicks OK.
2. `unreal.SystemLibrary.print_string(world, text, ...)` — Non-blocking. Text renders in the viewport and automatically fades after several seconds. You must obtain the editor world first; passing `None` results in silent no output.

`utils/ui_helpers.py:88-101` documents another variant of this same issue: original code constructed a `type_map` with entries written as `unreal.NotificationType.INFO if hasattr(unreal, "NotificationType") else None`. The `hasattr` guard prevents runtime crashes (all values resolve to `None`), but this constructed map is never used, making it dead code while creating false impressions that `NotificationType` exists. The conclusion is to delete this code and explicitly fall back to `print_string`. This follows a general design principle of the repository: **Admit missing capabilities explicitly instead of retaining code that pretends to work.**

## Deprecated Plugin: Editor Scripting Utilities → Three Editor Subsystems
`EditorLevelLibrary` still exists in the UE 5.8 stub file (`unreal.py:352651`, with 37 methods), yet **32** of these methods carry the `deprecated:` tag with uniform wording: "The Editor Scripting Utilities Plugin is deprecated - Use the function in …", pointing to three subsystems grouped by responsibility:

| Migration Target | Typical Members | Replacement Usage |
|---|---|---|
| Editor Actor Utilities Subsystem (`EditorActorSubsystem`) | `get_all_level_actors`, `get_selected_level_actors`, `set_selected_level_actors`, `set_actor_selection_state`, `select_nothing`, `destroy_actor`, `get_actor_reference`, `get_all_level_actors_components` | `unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()` |
| Unreal Editor Subsystem | `get_editor_world`, `get_game_world`, `set_level_viewport_camera_info`, `get_level_viewport_camera_info` | `unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()` |
| Level Editor Subsystem | `save_current_level`, `save_all_dirty_levels`, `load_level`, `new_level`, `new_level_from_template`, `set_current_level_by_name`, `pilot_level_actor`, `eject_pilot_level_actor`, `editor_play_simulate`, `editor_set_game_view`, `editor_invalidate_viewports` | `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()` |

A mnemonic is written in `01_Basics/03_editor_basics.py:70-77`: old APIs formed a monolithic static library. New APIs are split into multiple responsibility-separated subsystems, all retrieved via `get_editor_subsystem()`. Subsystems should be reused: the `actor_subsystem` obtained in section 2 can be reused in section 6 without repeated calls.

`utils/ui_helpers.py:213-217`, `02_AssetManagement/03_asset_actions.py:419-423`, `05_LevelAndActors/03_level_management.py:71-73`, `06_MaterialAndTexture/02_material_instances.py:335-338`, `07_SequenceAndCinematic/02_camera_animation.py:346-349`, `08_AdvancedTopics/02_external_data.py:385-387` all restate the same conclusion with minor wording variations: calling old APIs "still runs, but emits DeprecationWarning".

## Incomplete Migrations
Deprecated APIs appear in three forms within the repository. You must distinguish them when reading code:
1. **Fully migrated**: Files such as `04_EditorScripting/03_custom_tools.py:303-306`, `07_SequenceAndCinematic/02_camera_animation.py:346-349`, `08_AdvancedTopics/02_external_data.py:386` directly use subsystems.
2. **Old implementations retained intentionally for comparison**: `04_EditorScripting/01_editor_utility.py:183-197` explicitly states "old implementation kept here for comparison". Its `get_selected_actors()` still returns `unreal.EditorLevelLibrary.get_selected_level_actors()`. `01_Basics/03_editor_basics.py:266-272` comments out the old invocation and marks the corrected version. These are teaching assets, not legacy bugs.
3. **Still in use, pending migration**: Script bodies including `05_LevelAndActors/01_spawn_actors.py:75`, `05_LevelAndActors/02_modify_actors.py:63`, `05_LevelAndActors/03_level_management.py:38`, plus `04_EditorScripting/02_menu_extension.py:166`, `07_SequenceAndCinematic/01_level_sequence.py:264`, `08_AdvancedTopics/03_automation_testing.py:364` and `:379`. Matching docstrings still recommend these APIs (`01_Basics/01_hello_unreal.py:75`, `05_LevelAndActors/01_spawn_actors.py:12-21`, `05_LevelAndActors/03_level_management.py:12-21`). The API lists in docstrings were not updated alongside script bodies, representing the most consistent "desync between teaching materials and implementation" in this repository.

Additionally, `EditorLevelLibrary.spawn_actor_from_class` / `spawn_actor_from_object` **do not** carry the `deprecated:` tag (among the minority exceptions of those 37 methods). Per stub-file rules, they are not deprecated. However, their parent plugin is deprecated, and `EditorActorSubsystem.spawn_actor_from_class` is their new home. Such grey areas where methods lack deprecation tags while their host plugin is deprecated must be judged by plugin affiliation, not only by the single tag line.

## Two Discrepancies Between Stub Files and Repository Comments
When validated against the repository rule of "stub files are authoritative", two comment claims are overly absolute:
- **`AssetData.asset_class` has not been removed.** It still exists in the stub file (`unreal.py:67751`, returns `Name`), but its docstring marks it `deprecated: Short asset class name must be converted to full asset pathname. Use AssetClassPath instead.`. Therefore, the statement in `AGENTS.md:69-72` that "UE4's `asset_class` is gone" should be interpreted as "deprecated; use `asset_class_path` instead". The recommendation in `02_AssetManagement/01_list_assets.py:122-126` to use `asset_class_path.asset_name` is correct, but the trigger condition is not "property missing" but "property deprecated".
- **`EditorAssetLibrary.get_tag_values` exists.** In the stub file it is a `@classmethod get_tag_values(cls, asset_path: str) -> Map[Name, str]` (`unreal.py:352109`) with **no** `deprecated:` tag. An instance version of the same method also exists on `EditorAssetSubsystem`. However, `02_AssetManagement/01_list_assets.py:20-21`, lines `:175-177` of the same file, and `02_AssetManagement/my01.py:76-77` all assert as fact that "`EditorAssetLibrary` does not have this method; invocation raises AttributeError". The recommended approach (using the subsystem) remains valid, but this claim of non-existence does not hold under UE 5.8.

These inconsistencies are exactly why the repository mandates "inspect stub files before answering". Comments are human conclusions captured at a point in time and drift with engine versions, while stub files regenerate alongside the engine.