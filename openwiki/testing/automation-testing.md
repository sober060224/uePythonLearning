---
type: testing
title: 08-03 Automated Testing Script:In-Editor Self-Checks Without a Framework
description: Explains how 08_AdvancedTopics/03_automation_testing.py, without a pytest-like framework, uses the TestResult/TestSuite return-value protocol to organize asset and level assertions, and writes a JSON report to Saved/TestResults; also records that loading this file runs no tests, level tests still use deprecated APIs, and two tests can never fail.
tags: [testing, automation, asset-validation, ci, json-report]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T08:34:04.254Z
---

# 08-03 Automated Testing Script: In-Editor Self-Checks Without a Framework

`08_AdvancedTopics/03_automation_testing.py` (486 lines) is the only thing in this repository with the word "test" in its name, but it **is not an exercise for a course unit; rather, it is a homemade testing framework plus two test suites**. To understand it, you need to grasp two things at once: vertically, the **return-value protocol** of `TestResult` / `TestSuite`; horizontally, what each of the seven concrete assertions checks, and which of them are placeholders.

Regarding the statement in `AGENTS.md` that "this repository has no test/lint/CI," its significance is: it is the **only script that could serve as a CI check**, but nothing in the repository actually wires it into CI—`.github/workflows/openwiki-update.yml` only updates documentation and does not run scripts; the command line it invokes (`:451`) and the example invocations (`:469`, `:472`) **are all comments**. See `/openwiki/operations/running-and-verifying-scripts.md`.

## A fact you must know: loading this file does not run any tests

At the end of the file (`:478`), there is only one executable statement:

```python
unreal.log("高级主题第3课完成！")
```

If you load it the `AGENTS.md:33-36` way with `exec(open(...).read())`, what happens is: it defines `TestResult`, `TestSuite`, `AssetValidationTests`, `LevelValidationTests`, and `run_all_tests`, then prints a course-completion log. **Not a single one of the seven tests runs**, and `Saved/TestResults/` is not created.

To actually run the tests, there are only two ways:

1. Manually call `run_all_tests()` in the Python Console—but don't forget that `exec()` executes in the **current scope**, so the functions and classes land in the Console's global namespace, which makes this step possible.
2. Uncomment the line at `:469` and reload.

This is a common ailment of the "course script" genre: course scripts must not produce side effects when loaded by `exec` (otherwise opening the editor would modify assets), and the cost is that the testing framework must also be triggered manually. See `/openwiki/architecture/script-conventions.md`.

## Framework layer: TestResult and TestSuite

### `TestResult` (`:38-50`)

A pure data object with five fields:

| Field | Meaning |
|---|---|
| `test_name` | Test name |
| `passed` | Boolean result |
| `message` | Short message (e.g. "passed" or the reason for failure) |
| `details` | Detailed information (e.g. the specific list of violating assets) |
| `duration` | Elapsed seconds, initial value `0.0`, **backfilled by `TestSuite`** |

`duration` is not timed inside the test; it is written by the caller, so test functions only need to care about assertions. This division of labor is shown clearly in `add_test` below.

**The `details` field is currently dead.** All four asset tests stuff multi-line text into it (e.g. `"\n".join(empty_folders[:10])`), but `_print_results` (`:130-153`) only prints `r.message`, and the JSON dictionary constructed by `_save_results` (`:155-189`) only contains the four keys `name/passed/message/duration`—`details` is neither shown nor persisted. To make the violation list actually appear in the report, you need to add one line in each of those two places.

### `TestSuite.add_test(test_func, test_name=None)` (`:65-107`)

This is the framework's most central protocol. The docstring (`:66-75`) writes it as four conventions:

| Return value of the test function | Framework interpretation |
|---|---|
| A `TestResult` object | Complete test result, used directly |
| `True` | Passed, message fixed as `"通过"` |
| Any other value | Failed, `str(return value)` as the failure message |
| Raises an exception | Failed, message `f"异常: {e}"`, `details` is `str(e)` |

```python
name = test_name or test_func.__name__
start = time.time()
try:
    result = test_func()
    elapsed = time.time() - start
    if isinstance(result, TestResult):
        result.duration = elapsed
        self.results.append(result)
    elif result is True:
        ...
except Exception as e:
    elapsed = time.time() - start
    self.results.append(TestResult(name, False, f"异常: {e}", str(e)))
```

Three easy-to-trip-on points:

- **It uses the identity comparison `result is True`**, not `== True`. Returning `1`, `"True"`, or a non-empty string will all be judged as failure, and returning `None` (forgetting to write `return`) is also failure—this exactly catches the "test function forgot to return" class of error.
- **Exceptions are swallowed wholesale**; one test raising an error does not affect the rest continuing to run. The cost is that `except Exception` catches too broadly: `KeyboardInterrupt` and other `BaseException`s are not included (they will propagate, which is actually correct), but any real bug (e.g. an `AttributeError` caused by a null `unreal` object) silently becomes an "exception" failure record rather than interrupting the run so the developer sees the stack trace.
- **The `test_name` parameter is ineffective in the branch where a `TestResult` is returned**. `name` is only used when creating a new `TestResult` (the pass/fail/exception three branches); once the test returns its own `TestResult`, `add_test` directly appends it and `name` is discarded. This is why in `run_all_tests` (`:426-439`), the second element of each tuple (e.g. `"无重叠Actor"`) and the name hard-coded inside the test (e.g. `"无重叠 Actor"`, note the space in the middle) **are inconsistent**—what appears in the logs and JSON report is the internal one.

### `TestSuite.run_all(tests)` (`:109-128`)

`tests` is a list of tuples `[(test_function, test_name), ...]` (the comment analogizes it to pytest's parametrize). It does three things: record `start_time`, print a banner separated by `=` that includes the suite name and number of tests, and call `add_test` one by one. Its return value is the result of `_print_results()`—**that is, a bool**.

### Report output: `_print_results()` (`:130-153`) and `_save_results()` (`:155-189`)

The flow and order of `_print_results` are crucial:

1. Count `passed` / `failed` (two generator sums).
2. Print a `-` separator + `结果: N 通过, M 失败` + `f"{elapsed:.2f} 秒"`.
3. Print each `[OK]` / `[FAIL]` line and duration (`f"{r.duration:.3f}s"`), **only failures get an extra `-> message` line**.
4. **Call `self._save_results()`**—note that it is called unconditionally before returning.
5. `return failed == 0`.

The JSON structure written by `_save_results`:

```json
{
  "suite": "项目验证",
  "timestamp": "2026-02-14 10:30:00",
  "total": 7, "passed": 6, "failed": 1,
  "tests": [{"name": "...", "passed": true, "message": "通过", "duration": 0.012}]
}
```

The output path is `os.path.join(unreal.Paths.project_saved_dir(), "TestResults", f"{suite_name}_{time.strftime('%Y%m%d_%H%M%S')}.json")` (`:176-179`). Two design points:

- **The filename contains a timestamp**, so historical results are not overwritten and can be compared run by run—this is the simplest implementation of "CI traceability support," with no database needed.
- `os.makedirs(os.path.dirname(output_path), exist_ok=True)` (`:180`) ensures the `TestResults/` directory exists, so **the first run does not require manually creating the directory**.
- The encoding is explicitly written as `utf-8` + `ensure_ascii=False` (`:182-183`), so Chinese messages are not converted into `\uXXXX`. This is necessary in UE's Windows environment: the default `encoding` depends on the system locale.

The signature of `unreal.Paths.project_saved_dir() -> str` in the stub file is at `../Intermediate/PythonStub/unreal.py:357883` (`get_saved_dir()` in `utils/helpers.py:296` is a thin forwarding wrapper for it).

## Asset validation test set (`AssetValidationTests`, `:191-346`)

Four `@staticmethod`s, all scanning `/Game`. Note that they **have no shared traversal utility**—the call `list_assets("/Game", recursive=True)` appears in three tests, re-querying the asset registry each time, so running the full suite repeatedly traverses the entire library multiple times. This is a textbook "optimizable duplication," but in the course context it lets each test be copied out and run independently (the same trade-off as `utils/helpers.py` having zero callers; see `/openwiki/reference/utils-helpers.md`).

### `test_no_empty_folders()` (`:200-227`)

```python
all_paths = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=True)
for path in all_paths:
    if unreal.EditorAssetLibrary.does_directory_exist(path):
        contents = unreal.EditorAssetLibrary.list_assets(path, recursive=False, include_folder=True)
        if not contents:
            empty_folders.append(path)
```

The key is `include_folder=True`: the default `list_assets` only returns asset paths; `include_folder=True` makes it also return folder paths, otherwise this test would not traverse a single folder. `recursive=False` is the point of the second call—it lists only direct children, so "no direct children" equals "empty folder."

Cost: for N folders, it issues N `list_assets` queries. `list_assets(cls, directory_path: str, recursive: bool = True, include_folder: bool = False) -> Array[str]` (`../Intermediate/PythonStub/unreal.py:352080`, a classmethod of `EditorAssetLibrary`), `does_directory_exist(cls, directory_path: str) -> bool` (same file `:352276`).

It returns a `TestResult`, with the name hard-coded as `"无空文件夹"`, and the failure details list at most 10.

### `test_naming_conventions()` (`:229-273`)

The rule table is four prefix mappings:

| Class path substring | Expected prefix |
|---|---|
| `StaticMesh` | `SM_` |
| `Texture2D` | `T_` |
| `Material` | `M_` |
| `Blueprint` | `BP_` |

It checks two things: the name must not contain spaces (the comment explains that spaces cause trouble in command lines, scripts, and version control); and when the class path hits a key, the name must start with the corresponding prefix, and it `break`s on the first hit (reports only once).

The implementation uses `find_asset_data(asset_path)` to get metadata without loading the asset—`find_asset_data(cls, asset_path: str) -> AssetData` (`../Intermediate/PythonStub/unreal.py:352206`), which is efficient and correct. The class name is read with `str(asset_data.asset_class_path)`, which is the repository's uniform practice (`asset_class` is deprecated in UE5; see `/openwiki/concepts/nonexistent-and-deprecated-apis.md`).

Two known coarse-grained aspects:

- It is **substring matching**, so `"Material"` will hit everything containing that word, such as `MaterialInstanceConstant`, `MaterialFunction`, etc., whose prefix conventions are not necessarily `M_` (for example, material instances are usually called `MI_`). Likewise, `"Texture2D"` will hit `Texture2DArray`.
- The asset short name uses `str(asset_data.asset_name)`—this is necessary because `asset_name` is an `unreal.Name` (in the `Name` class at `../Intermediate/PythonStub/unreal.py:521-541`, it indeed has no `startswith`), so it must first be converted to a Python string before `in` / `startswith` can be used.

The failure details list at most 20 (more than the 10 of the other tests).

### `test_no_orphan_assets()` (`:276-308`) — a test that **can never fail**

```python
refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path, load_assets_to_confirm=True)
external_refs = [r for r in refs if r != asset_path]
if not external_refs:
    orphans.append(asset_path)
if orphans:
    return TestResult("无孤立资产", True, f"发现 {len(orphans)} 个未引用的资产（仅警告）", ...)
```

`passed` **is always `True`**, and the comment states the reason explicitly: orphan assets are not necessarily errors (they may be reserved assets), so it only warns. The consequence is that this test has no effect whatsoever on the return value of `run_all_tests()` and can never make CI red—it is a report, not a gate.

`find_package_referencers_for_asset(cls, asset_path: str, load_assets_to_confirm: bool = False) -> Array[str]` (`../Intermediate/PythonStub/unreal.py:352188`). The meaning of `load_assets_to_confirm=True` is: also load the assets needed to confirm referencer relationships—**accuracy traded for performance**; in this test, full-library traversal + loading everything will be extremely slow. The `r != asset_path` filter is because an asset counts itself as one of its referencers.

### `test_texture_resolution()` (`:311-346`)

Flow: `find_asset_data` filters `"Texture2D" not in str(asset_class_path)` → `load_asset` → `isinstance(texture, unreal.Texture2D)` double insurance → read width/height → bitwise operation to test power of two.

```python
sx = texture.blueprint_get_size_x()
sy = texture.blueprint_get_size_y()
if not ((sx & (sx-1) == 0) and (sy & (sy-1) == 0)):
```

The `Texture2D` class is at `../Intermediate/PythonStub/unreal.py:539179` (inherits `Texture`), and the two size methods are `blueprint_get_size_x(self) -> int` (`:539285`) and `blueprint_get_size_y(self) -> int` (`:539276`), with the docstring "Gets the X size of the texture, in pixels." The comment already writes out the derivation of `n & (n-1) == 0` (`8 & 7 == 0`, `6 & 5 == 4`).

Two boundaries:

- This test is the **only one in the whole suite that actually needs to load assets** (the others are fine with `find_asset_data`), so it is the slowest and has the highest memory usage.
- The bitwise trick also holds for 0: `0 & -1 == 0`, so a texture with size 0 will be **misjudged as passing**. Real assets almost never have 0, but this is a known gap in the trick (to be strict, it should add `sx > 0`).

The failure details list at most 10, in the format `f"{asset_data.asset_name} ({sx}x{sy})"`.

## Level validation test set (`LevelValidationTests`, `:352-412`)

Three tests, all operating on the **current open level's live Actor list** (not the level asset on disk), so their precondition is that the target level is already open in the editor. This limitation makes them unsuitable for unattended CI: an editor started with `-nullrhi -unattended` will not automatically load a specific level.

### `test_level_has_player_start()` (`:361-374`)

```python
actors = unreal.EditorLevelLibrary.get_all_level_actors()
has_player_start = any(isinstance(a, unreal.PlayerStart) for a in actors)
```

**This uses a deprecated API.** In the stub file, `EditorLevelLibrary` is at `../Intermediate/PythonStub/unreal.py:352651`; of its 37 `def`s, 32 carry `deprecated:` notes; the note for `get_all_level_actors` (`:352996`) is literally `deprecated: The Editor Scripting Utilities Plugin is deprecated - Use the function in Editor Actor Utilities Subsystem`.

More notably, **this file contradicts itself**: the docstring at the top of the file (`:21`) recommends the new form `unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() -> Array[Actor]` under "APIs the exercises may use," but the implementations at `:364` and `:379` still use the old `EditorLevelLibrary`. `utils/helpers.py:110-119` and `utils/ui_helpers.py:211-213` have already completed the migration and documented the `DeprecationWarning` in comments; this file is a missed one (the list of similar missed cases is in `/openwiki/concepts/nonexistent-and-deprecated-apis.md`).

`unreal.PlayerStart` is at `../Intermediate/PythonStub/unreal.py:530546` (inherits `NavigationObjectBase`), and there is also `PlayerStartPIE` (`:615785`). The comment explains why every playable level must have it.

### `test_no_overlapping_actors()` (`:377-405`)

It uses position as a key to find exactly overlapping Actors:

```python
loc = actor.get_actor_location()
key = (round(loc.x, 0), round(loc.y, 0), round(loc.z, 0))
if key in locations:
    overlapping.append(f"{actor.get_actor_label()} 与 {locations[key]} 重叠")
else:
    locations[key] = actor.get_actor_label()
```

`round(x, 0)` is a correct and necessary action: floating-point positions are almost never bit-for-bit equal, and rounding to an integer is equivalent to giving a tolerance of ±0.5 units (the comment gives the example of `(100.001, 200.002, 300.003)` and `(100, 200, 300)`). `get_actor_location(self) -> Vector` is at `../Intermediate/PythonStub/unreal.py:257032`.

Three behavioral boundaries:

- It reports only the **first** collision partner (`locations[key]` stores only the first), so three Actors stacked together produce only two records, and neither points out the third.
- "Overlap" is judged only by **center point**. Two 2-meter-wide boxes whose centers are 1 meter apart and which visibly interpenetrate will not be detected by this test. To judge real intersection, you would need to compare bounding boxes.
- Scenarios where co-located Actors legitimately exist in a level (e.g. multiple Actors whose VFX components are attached to the same parent, or a combination of a marker and a trigger) will produce false positives.

The failure details list at most 10.

### `test_lighting_built()` (`:408-412`) — pure placeholder

```python
return TestResult("光照已构建", True, "通过 (需要手动验证)")
```

A three-line function that always returns passing. The comment candidly explains that "detecting lighting state depends on the specific engine version and project configuration; in a real project you could check properties such as `LightingNeedsRestart` on `WorldSettings`." It is registered into the suite (`:438`) but has no assertion capability at all—it is "the one that makes up the numbers in the test directory."

## Run entry point: `run_all_tests()` (`:418-442`)

```python
def run_all_tests():
    suite = TestSuite("项目验证")
    tests = [
        (AssetValidationTests.test_no_empty_folders, "无空文件夹"),
        (AssetValidationTests.test_naming_conventions, "命名规范"),
        (AssetValidationTests.test_no_orphan_assets, "无孤立资产"),
        (AssetValidationTests.test_texture_resolution, "纹理分辨率"),
        (LevelValidationTests.test_level_has_player_start, "PlayerStart"),
        (LevelValidationTests.test_no_overlapping_actors, "无重叠Actor"),
        (LevelValidationTests.test_lighting_built, "光照构建"),
    ]
    return suite.run_all(tests)
```

Seven tests. The registered name has no space (`"无重叠Actor"`) while the `TestResult` name inside the test has a space (`"无重叠 Actor"`); according to the behavior of `add_test` above, the final report uses **the internal one**.

The suite name `"项目验证"` goes into the JSON `suite` field **and the filename** (`项目验证_20260214_103000.json`) — so spaces and Chinese in the suite name will appear directly in the filename. This is usable (Windows allows it), but you need to quote it when referencing it in a shell.

`:439-441` has an [easy-to-miss point]:

> `run_all` returns a bool meaning "did everything pass?" If you don't `return` it, then in CI calling `run_all_tests()` will always get `None` (equivalent to always succeeding).

The value of this hint lies in the signature contract: `run_all_tests()` **must return a bool**, otherwise the caller cannot determine red/green. But the other half must also be stated honestly: **no code in the repository consumes this boolean value**. The command line (`:451`) uses `-ExecutePythonScript`, which is only responsible for executing the script and does not turn a Python return value into a process exit code; there is also no wrapper script or CI step that reads `Saved/TestResults/*.json` to determine red/green. So the actual output of this "test suite" is currently human-readable logs plus a JSON report, and the automated gate remains only in comments. To truly achieve a CI gate, what is missing is the link "script return code → process exit code."

## Relationship to the rest of the repository

| Relation | Fact |
|---|---|
| `README.md:85` | One row in the course table: `| 03_automation_testing.py | 自动化测试脚本 |`; it is the only external mention in the whole document |
| `AGENTS.md` | Explicitly says "this repository has no test/lint/CI; do not invent one"; this file is a "test" in the teaching sense, not the repository's test infrastructure |
| `.github/workflows/openwiki-update.yml` | The only workflow; it only runs `openwiki code --update --print` to update documentation and executes no Python |
| `utils/helpers.py` | This file does **not** import it; `unreal.log` is used directly (it is the same layer of wrapping as helpers' `log_info`) |
| `08_AdvancedTopics/02_external_data.py` | Another lesson in the same chapter; it also writes results to the `Saved/` directory (see `/openwiki/workflows/batch-and-external-data.md`) |

## Known limitations and improvements to make

- **Loading does not execute**: loading via `exec()` only defines classes; tests must be run manually with `run_all_tests()` or by uncommenting `:469`.
- **It is not a gate for anything**: no CI step calls it, and its return value is not converted to an exit code.
- **Two tests can never fail**: `test_no_orphan_assets` (always `passed=True`) and `test_lighting_built` (hard-coded `True`), two out of seven.
- **The `details` field is unused across the whole chain**: it is neither printed nor put into JSON, so the violation lists are effectively discarded.
- **Level tests still use deprecated APIs**: `:364`, `:379` use `unreal.EditorLevelLibrary.get_all_level_actors()`, contradicting the recommended form in the file-top docstring `:21`.
- **Level tests depend on the currently open level**, so in unattended CI it is impossible to determine which map is being run.
- **Repeated traversal**: `list_assets("/Game", recursive=True)` is queried again in multiple tests.
- **`test_texture_resolution`'s bitwise operation misjudges 0 as passing** (`0 & -1 == 0`).
- **`test_no_overlapping_actors` judges overlap only by center point**, and reports only the first collision partner in each group.

## Related documentation

- `/openwiki/operations/running-and-verifying-scripts.md` — `-ExecutePythonScript`, the four ways to run, and output channels
- `/openwiki/concepts/nonexistent-and-deprecated-apis.md` — the 32 deprecation notes for `EditorLevelLibrary` and migration targets
- `/openwiki/workflows/batch-and-external-data.md` — large-scale batching and external-data workflows in the same chapter
- `/openwiki/reference/utils-helpers.md` corresponding to `/openwiki/reference/utils-helpers.py` — transaction, timing, and Actor query utilities
- `/openwiki/architecture/script-conventions.md` — the convention that course scripts "produce no side effects when loaded"