# 第 1 篇：先用 Python 造一个测试框架

> 目标：理解"一个测试框架到底在做什么"。做完这篇，你再看 UE 的 `FAutomationTestBase` 会立刻觉得眼熟——它们是同一个东西的两种写法。

本篇只讲一个文件：`08_AdvancedTopics/03_automation_testing.py`。前面 7 章不用管。

---

## 1.1 为什么从这个文件开始

大多数人学测试是先学"怎么用框架"，结果永远只会抄模板。真正管用的是先知道框架内部只有三件事：

1. **收集**：把一堆测试函数排进一张表
2. **执行**：一个个调，捕获返回值或异常
3. **汇报**：数通过/失败，落一份报告

UE 的 `FAutomationTestBase` 干的也是这三件事。`03_automation_testing.py` 用 460 行 Python 把它从头实现了一遍，你能看懂全部细节——这在 C++ 侧是看不到的（都藏在引擎里）。

---

## 1.2 三个类的关系

```
TestResult        一条结果：名字 / 通没通过 / 消息 / 耗时
   ▲
   │ 收集
TestSuite         一次运行：results 列表 + 计时 + 汇总输出
   │
run_all_tests()   入口：把 7 个测试函数塞进 TestSuite
```

打开文件，从 `class TestResult`（第 64 行）往下看。

### TestResult：一条结果

```python
class TestResult:
    def __init__(self, test_name, passed, message="", details=""):
        self.test_name = test_name
        self.passed = passed        # True / False
        self.message = message      # 简短原因
        self.details = details      # 详细内容（如失败资产清单）
        self.duration = 0.0         # 由 TestSuite 事后填
```

`duration` 故意不在构造时填——因为只有 `TestSuite` 知道开始/结束时间。这就是"数据类只管数据，计时归调度方"。

> **API**
> `TestResult.__init__(test_name, passed, message="", details="")` —— 封装单条测试的结论；`duration` 由外部赋值。

### TestSuite：调度 + 汇报

关键在 `add_test()`（第 93 行），它定义了**测试函数的返回值协议**：

| 返回值 | 含义 |
|---|---|
| `True` | 通过 |
| `False` | 失败，无原因 |
| `"字符串"` | 失败，字符串就是原因 |
| `TestResult` 对象 | 完整结果（自带名称/消息/详情） |
| 抛异常 | 失败，异常文本转成原因 |

```python
def add_test(self, test_func, test_name=None):
    name = test_name or test_func.__name__
    start = time.time()
    try:
        result = test_func()
        elapsed = time.time() - start

        if isinstance(result, TestResult):
            result.duration = elapsed
            self.results.append(result)
        elif result is True:
            self.results.append(TestResult(name, True, "通过"))
            self.results[-1].duration = elapsed
        else:
            self.results.append(TestResult(name, False, str(result)))
            self.results[-1].duration = elapsed

    except Exception as e:   # noqa: BLE001
        elapsed = time.time() - start
        self.results.append(TestResult(name, False, f"异常: {e}", str(e)))
        self.results[-1].duration = elapsed
```

注意 `except Exception` 外面那个 `# noqa: BLE001`。它压的是 lint 的"不要捕获裸 Exception"警告。这里**故意要捕**——一个测试炸了不该带崩整轮。这个取舍在 C++ 侧也一样：`FAutomationTestBase` 会让单个测试 `AddError` 后继续跑下一个。

> **API**
> `TestSuite.add_test(test_func, test_name=None) -> None` —— 执行单个测试并按上述协议记结果；异常也转成失败项。

### run_all：把表跑完并返回总账

```python
def run_all(self, tests):
    self.start_time = time.time()
    for test_func, test_name in tests:
        self.add_test(test_func, test_name)
    return self._print_results()     # 返回 bool
```

`tests` 是 `[(函数, 名字), ...]` 形式。为什么要显式传名字？因为 7 个测试函数都是 `@staticmethod`，`__name__` 只能是 `test_no_empty_folders` 这种英文标识符，而你要的是"无空文件夹"这种中文可读名。

`_print_results()` 返回 `failed == 0`，即"是否全过"。

> **API**
> `TestSuite.run_all(tests) -> bool` —— 顺序执行全部测试、打印摘要、落盘 JSON、返回是否全部通过。

---

## 1.3 已经埋好的三个坑

`openwiki/testing/automation-testing.md` 里已经核实过，这三个坑是真实存在的：

### 坑 1：加载文件不跑任何测试

文件末尾只有一行可执行语句：

```python
unreal.log("高级主题第3课完成！")
```

在 Python Console 里 `exec(open(...).read())` 只会打印这一行并定义类。**必须手动调**：

```python
run_all_tests()
```

### 坑 2：两个测试永远不可能失败

```python
@staticmethod
def test_no_overlapping_actors(): ...   # 依赖已废弃 API，实际拿不到重叠信息
@staticmethod
def test_lighting_built():
    return TestResult("光照已构建", True, "通过 (需要手动验证)")
```

`test_lighting_built` 硬编码 `True`。它是一个**占位符**，不是测试。这是最常见的自我欺骗形式：绿灯很好看，但它什么都没验。

### 坑 3：不 return 就等于永远成功

```python
def run_all_tests():
    suite = TestSuite("项目验证")
    tests = [...]
    return suite.run_all(tests)      # ← 少了 return，CI 永远拿到 None
```

`None` 在 CI 里通常被当假值，但也有大量脚本把"非 False"当成功。**必须显式 `return`**。

---

## 1.4 这个框架和 UE 的对应关系

对照着看，后面第 2、3 篇会一路复用这张表：

| 这个 Python 框架 | UE C++ | 作用 |
|---|---|---|
| `class TestResult` | `FAutomationExecutionEntry` | 一条结果记录 |
| `class TestSuite` | `FAutomationTestBase` 的派生类 | 一组测试的容器 |
| `TestSuite.add_test(f, name)` | `FAutomationTestBase::RunTest()` | 执行一个测试体 |
| `TestResult(passed=False, message=...)` | `AddError(Message)` | 记一条失败 |
| `unreal.log("OK ...")` | `AddInfo(Message)` | 记一条信息 |
| `return failed == 0` | `return true;` / `return false;` | 告诉框架这轮通不通 |
| `Saved/TestResults/*.json` | `Saved/TestResults/*.json`（同目录） | 落盘报告 |

**你已经会写 UE 测试了**——只是换了个语言和宏。

---

## 1.5 动手练习

在 `03_automation_testing.py` 末尾加一个**真能失败**的测试，让 `run_all_tests()` 返回 `False`：

```python
class LevelValidationTests:
    @staticmethod
    def test_actor_count_under_threshold():
        """关卡 Actor 数量必须小于 5000（大关卡会拖慢自动化）"""
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        count = len(actors)
        if count >= 5000:
            return f"Actor 数量 {count} 超过阈值 5000"
        return True
```

然后在 `tests` 列表里注册它：

```python
(LevelValidationTests.test_actor_count_under_threshold, "Actor 数量阈值"),
```

跑一遍：

```python
run_all_tests()
```

然后故意把阈值改成 `1`，再跑一遍，观察：
- 日志里出现 `[FAIL] Actor 数量阈值`
- `Saved/TestResults/` 里多一个带时间戳的 JSON，`failed: 1`
- `run_all_tests()` 返回 `False`

这个"改一个数字，看红灯亮起来"的动作，是**验证你的测试真的能失败**的唯一办法。第 2、3 篇每加一个测试都要做一次。

> **API**
> `unreal.EditorLevelLibrary.get_all_level_actors() -> Array[Actor]` —— 返回当前关卡所有 Actor。
> https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLevelLibrary#unreal.EditorLevelLibrary.get_all_level_actors

---

## 1.6 本篇小结

- 测试框架 = 收集 + 执行 + 汇报，三件事而已
- 返回值协议（True / False / 字符串 / TestResult / 异常）就是"测试怎么表达失败"
- 单个测试失败必须被隔离，不能带崩整轮
- **验证测试能失败，比验证测试能通过更重要**

下一篇：把这个心智模型映射到 UE C++，先看最小的 `IMPLEMENT_SIMPLE_AUTOMATION_TEST`，再看带 UI 驱动的 `DEFINE_SPEC`。

---

*跳过的：01~07 章内容（你已学过）；`_save_results()` 的 JSON 写法细节（第 2 篇会用 C++ 版对照）。风险：`test_no_overlapping_actors` 依赖的废弃 API 在 5.8 可能已完全移除，届时该测试会抛异常而不是返回失败——这本身也符合"异常即失败"的协议。*
