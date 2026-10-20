# 第 2 篇：UE 的四层测试，和项目里现成的两个例子

> 目标：分清 UE 五个测试框架各自管什么，然后读懂项目里两个真实样例——一个是 207 行的资产命名检查，一个是点菜单进对局的 UI 驱动流程。

---

## 2.1 先认清：不是"一种测试"，是五种

新手最大的困惑是搜到五个词却不知道用哪个。它们的分工是这样的：

| 框架 | 写法入口 | 能干什么 | 代价 | 项目里有没有 |
|---|---|---|---|---|
| Simple Automation Test | `IMPLEMENT_SIMPLE_AUTOMATION_TEST` | 无 World 的纯逻辑、资产扫描 | 极低 | ✅ `BlueprintNamingTest.cpp` |
| Complex Automation Test | `IMPLEMENT_COMPLEX_AUTOMATION_TEST` | 同一逻辑跑多组参数 | 低 | ❌ |
| Automation Spec | `BEGIN_DEFINE_SPEC` + `It(...)` | BDD 风格、可异步、线程池 | 中 | ✅ `MenuStartElimination.spec.cpp` |
| CQTest | `TEST_CLASS` + `TEST_METHOD` | 有 World、有 Player、命令队列 | 高（要建测试关卡） | ✅ `ShooterTestsMapTests.cpp` |
| Functional Test Actor | 关卡里放 `AFunctionalTest` | 蓝图层面的验收测试 | 低但要摆关卡 | ⚠️ 只有关卡资产，无 C++ |
| Gauntlet | `UnrealTestNode` (C#) | 打包后跑整局、多机、性能 | 最高（要 cook） | ❌ |

**判据只有一句话**：需要真实 World / Player 吗？

- 不需要 → Simple Test 或 Spec
- 需要 → CQTest（首选）或 Functional Test Actor
- 需要打包产物 → Gauntlet

本篇讲前两层（不需要 World），第 3 篇讲 CQTest。

---

## 2.2 第一层：`IMPLEMENT_SIMPLE_AUTOMATION_TEST`

这是整个框架的"Hello World"，也是 `BlueprintNamingTest.cpp` 用的形式。

### 骨架

```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FBlueprintNamingTest,                          // 1. 类名（你自己定）
    "Project.BlueprintNaming",                     // 2. 路径（决定 UI 里的树形位置）
    EAutomationTestFlags::EditorContext            // 3. 在哪种上下文跑
    | EAutomationTestFlags::ProductFilter)         // 4. 什么构建里出现

bool FBlueprintNamingTest::RunTest(const FString& Parameters)
{
    // ... 检查 ...
    return bAllGood;    // true = 通过
}
```

四个参数各自的含义：

**1. 类名** —— 宏会在内部 `IMPLEMENT_CUSTOM_SIMPLE_AUTOMATION_TEST` 展开出一个 `FAutomationTestBase` 子类。名字必须唯一。

**2. 路径字符串** —— 点分分隔，UI 里就是一棵树：

```
Project
└── BlueprintNaming
```

跑的时候可以用前缀批量跑：`Automation RunTests Project` 会跑所有 `Project.` 开头的。

**3. 上下文 Flag** —— 决定这个测试能在哪儿出现：

| Flag | 含义 |
|---|---|
| `EditorContext` | 只在编辑器里 |
| `ClientContext` | 只在客户端（-game）里 |
| `ServerContext` | 只在专用服务器里 |
| `ApplicationContextMask` | 上面三个的并集，哪都能跑 |

`BlueprintNamingTest` 选的是 `EditorContext`，因为 `AssetRegistry` 在客户端里拿不到未 cook 的资产。

**4. 过滤器 Flag** —— 决定什么构建里编进去：

| Flag | 含义 |
|---|---|
| `ProductFilter` | Shipping/Test 等正式构建里**也保留** |
| `EngineFilter` | 只在引擎开发构建里 |
| `SmokeFilter` | 冒烟测试，CI 每次必跑 |

绝大多数项目测试写 `ProductFilter`。

> **API**
> `IMPLEMENT_SIMPLE_AUTOMATION_TEST(TClass, PrettyName, TestFlags)` —— 注册一个无参测试类，需自行实现 `bool TClass::RunTest(const FString&)`。

### 断言与上报

`RunTest` 里能用的核心方法（都来自 `FAutomationTestBase`）：

```cpp
TestTrue(TEXT("条件"), bCondition);                  // 失败时记错误
TestEqual(TEXT("说明"), Actual, Expected);
TestNotNull(TEXT("说明"), Ptr);
AddError(FString::Printf(TEXT("细节: %s"), *Str));   // 手动记错误
AddWarning(TEXT("..."));
AddInfo(TEXT("..."));                                // 只记录，不影响结果
```

注意最后两行：`AddError` / `AddWarning` / `AddInfo` 是**三种不同颜色**的输出。`AddError` 会让测试失败，另两个不会。

返回值是另一个通道：`return false` 也会让测试失败。**但它不带信息**。所以真实测试里通常两种都做——`AddError` 说明原因，`return Violations.Num() == 0` 给出结论。

### 逐段拆 `BlueprintNamingTest.cpp`

路径：`Plugins/ProjectTests/Source/ProjectTests/Private/BlueprintNamingTest.cpp`

#### 第 1 段：拿资产列表

```cpp
FAssetRegistryModule& AR =
    FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
AR.WaitForCompletion();          // ← 关键：等索引建完

FARFilter Filter;
Filter.bRecursivePaths = true;
Filter.bRecursiveClasses = true;
Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
TArray<FAssetData> AllBlueprints;
AR.GetAssets(Filter, AllBlueprints);
```

`WaitForCompletion()` 这行是新手最容易漏的。编辑器刚启动时 AssetRegistry 还在后台扫盘，不等待就会拿到空列表，测试"通过"了但什么都没检查。这就是**假阳性** —— 比失败更危险。

#### 第 2 段：过滤 + 取 Blueprint 对象

```cpp
for (const FAssetData& AssetData : AllBlueprints)
{
    if (AssetData.PackagePath.ToString().StartsWith(TEXT("/Engine/")))
        continue;    // 引擎自带资产不符合项目规范，跳过

    const UBlueprint* BP = Cast<UBlueprint>(AssetData.GetAsset());
    if (!BP) continue;
    ...
}
```

`AssetData.GetAsset()` 会**同步加载**资产。在大项目上这一步很慢——207 行的测试可能跑几分钟。这是简单测试的固有成本：它没有 World，但也因此没法用流式加载。

#### 第 3 段：规则匹配

```cpp
const FBlueprintNamingRule* R = BlueprintNamingRules::FindRule(BP->ParentClass, Rules);
```

`FindRule` 内部是一个**顺序敏感**的循环：

```cpp
for (const auto& R : Rules)
    if (ParentClass->IsChildOf(R.BaseClass))
        return &R;
```

所以规则表必须"子类在前、父类在后"。`Character` 规则必须在 `Actor` 规则之前，否则所有 Character 都会落到 `Actor` 的默认前缀上。

规则表长这样：

| 父类 | 允许前缀 |
|---|---|
| `EditorUtilityWidget` | `EUW_` |
| `EditorUtilityObject` | `EUO_` |
| `AnimInstance` | `ABP_` |
| `UserWidget` | `WBP_`, `UMG_` |
| `BlueprintFunctionLibrary` | `BFL_`, `BP_` |
| `Character` | `BP_`, `B_` |
| `Actor` | `BP_`, `B_` |
| （兜底） | `BP_` |

#### 第 4 段：上报

```cpp
if (!bOK)
{
    AddError(FString::Printf(
        TEXT("[%s] %s (%s) - expected one of: %s"),
        *AssetData.PackageName.ToString(),
        *BP->GetName(),
        *BP->ParentClass->GetName(),
        *FString::Join(AllowedPrefixes, TEXT(", "))));
    Violations.Add(...);
}
```

`AddError` 的格式值得学：**资产路径 + 资产名 + 父类 + 期望值**。一条错误消息里包含修复所需的全部信息，不用去翻代码。

#### 第 5 段：落盘 + 返回

```cpp
const FString OutputPath = FPaths::ProjectSavedDir()
    / TEXT("ProjectTests") / TEXT("BlueprintNamingReport.json");
// FJsonObject → FJsonSerializer::Serialize → FFileHelper::SaveStringToFile

return Violations.Num() == 0;
```

和第 1 篇的 `Saved/TestResults/*.json` 完全对应。JSON 报告的意义是：CI 挂了以后你可以直接 `jq` 出失败清单，不用扒日志。

### 这个测试的三个可改进点

读到这儿你已经能看出问题了：

1. **同步加载全部蓝图** —— 几千个资产会跑到超时。改进：用 `AssetData.TagsAndValues` 读 `ParentClass` 标签，不 `GetAsset()`。
2. **没检查命名冲突** —— 两个 `BP_Foo` 在不同路径下都合法，但重命名时会撞车。
3. **`/Engine/` 是硬编码** —— 项目里自己的插件路径（`/ProjectTests/`）反而没被覆盖。

这就是"读懂并小改"的入口：随便挑一条改，改完加个能失败的用例验证。

---

## 2.3 第二层：`DEFINE_SPEC`（BDD 风格）

路径：`Source/LyraGame/Tests/MenuStartElimination.spec.cpp`

这个文件短，但它演示了三件简单测试做不到的事：**清理钩子、异步执行、UI 驱动**。

### 骨架

```cpp
#if WITH_DEV_AUTOMATION_TESTS && WITH_AUTOMATION_DRIVER

BEGIN_DEFINE_SPEC(FMenuStartEliminationSpec,
                  "Lyra.MenuStartEliminationSpec",
                  EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
    FAutomationDriverPtr Driver;
    void ClickButton(const FString& Text) const;
END_DEFINE_SPEC(FMenuStartEliminationSpec)
```

三层宏夹住成员声明：`BEGIN_DEFINE_SPEC` 开始类体，中间写成员，`END_DEFINE_SPEC` 收尾。这和写普通 class 一样，只是外面包了宏。

两个 `#if` 条件不能省：
- `WITH_DEV_AUTOMATION_TESTS` —— Shipping 里整个测试框架不编译
- `WITH_AUTOMATION_DRIVER` —— 没启用 AutomationDriver 插件时不编译

### `Define()` 就是测试清单

```cpp
void FMenuStartEliminationSpec::Define()
{
    BeforeEach([this]() { /* 开 Driver */ });
    AfterEach ([this]() { /* 关 Driver */ });

    Describe("Menu Start Elimination", [this]()
    {
        It("Should click buttons to Start Elimination",
           EAsyncExecution::ThreadPool,
           [this]() { ... });
    });
}
```

层级对应关系：

```
Describe  = 一组相关测试（"菜单启动流程"）
It        = 一条用例（"应该能点按钮进对局"）
BeforeEach= 每条 It 前都跑
AfterEach = 每条 It 后都跑
```

这就是 BDD 的三段式。`Define()` 本身**不执行测试**，它只登记。真正执行由 Automation 框架驱动。

### `BeforeEach` / `AfterEach` 为什么必须写

```cpp
BeforeEach([this]()
{
    if (IAutomationDriverModule::Get().IsEnabled())
        IAutomationDriverModule::Get().Disable();   // ← 强制复位

    IAutomationDriverModule::Get().Enable();
    Driver = IAutomationDriverModule::Get().CreateDriver();
});

AfterEach([this]()
{
    Driver.Reset();
    IAutomationDriverModule::Get().Disable();
});
```

注释里那句 "Check if the Driver was left enabled by a previous test" 说明了问题：AutomationDriver 是**全局单例**。上一个测试没关干净，下一个测试就会拿到脏状态。这类"全局状态泄漏"是集成测试最常见的 flaky 来源。

`AfterEach` 里的 `Driver.Reset()` 是"先放掉引用，才能允许销毁"。少了这行，`Disable()` 会因为还有人持有 driver 而卡住。

### `EAsyncExecution::ThreadPool` 是什么

```cpp
It("...", EAsyncExecution::ThreadPool, [this]() { ... });
```

第二个参数把测试体丢到线程池。这样 `It` 的 lambda 里可以写**阻塞代码**（等 UI 出现、等 60 秒），而不卡住游戏线程。

代价：线程池里的代码**不能碰 UObject**。这个测试全靠 `Driver->FindElement()` 这种间接接口，正是为了满足这个约束。

对比第 3 篇 CQTest 的做法：CQTest 不用线程池，它把等待拆成 `Until(条件)` 命令，每帧 tick 检查一次。两种思路都成立：

| | Spec + 线程池 | CQTest + 命令队列 |
|---|---|---|
| 等待写法 | 阻塞 `Wait()` | `Until(条件, 超时)` |
| 能碰 UObject | ❌ | ✅ |
| 能测 Player | ❌ | ✅ |

### `ClickButton` 里的等待三件套

```cpp
void FMenuStartEliminationSpec::ClickButton(const FString& Text) const
{
    const auto Button = Driver->FindElement(
        By::TextFilter::Contains(By::Path("<SCommonButton>"), Text));

    Driver->Wait(Until::ElementIsInteractable(Button, FWaitTimeout::InSeconds(60)));

    Button->Click();
}
```

三步：**定位 → 等可交互 → 点击**。少任何一步都会 flaky：

- 只点击不等待 → 菜单还没动画完就点，点空
- 等待但不定位 → 元素指针为空
- 定位后立刻点 → 元素在但不一定能交互（遮罩/动画）

`By::Path("<SCommonButton>")` 里的 `< >` 是 UMG 控件类型标记。`TextFilter::Contains(Text)` 匹配按钮文字——所以测试里写 `"Play Lyra"`、`"Start a Game"`、`"Elimination"` 正好是 UI 上实际显示的字。

**这条测试的价值**：它把"点三次按钮进对局"这个每次改 UI 都要手测 2 分钟的流程自动化了。改按钮文字会立刻红灯——这正是你想要的。

---

## 2.4 怎么跑

### 编辑器里

1. `Edit → Plugins` 启用 `Functional Testing Editor`（在 `Testing` 分类下）
2. 重启编辑器
3. `Window → Test Automation`
4. 在树里找 `Project.BlueprintNaming` 或 `Lyra.MenuStartEliminationSpec`
5. 勾选 → `Start Tests`

### 命令行

```
UnrealEditor.exe Lyra.uproject ^
  -ExecCmds="Automation RunTests Project.BlueprintNaming; Quit" ^
  -unattended -nopause -nullrhi -stdout -fullstdoutlogoutput
```

关键参数：

| 参数 | 作用 |
|---|---|
| `Automation RunTests <前缀>` | 跑名字以该前缀开头的所有测试 |
| `;Quit` | 跑完退出，否则进程挂着 |
| `-nullrhi` | 无 GPU，CI 必需 |
| `-unattended` | 不弹对话框 |
| `-nopause` | 出错也不停 |

跑整个项目：`Automation RunTests Project`。
只跑冒烟：`Automation RunTests Project` + 测试自己的 `SmokeFilter`（或用 `Automation SetFilter Smoke`）。

> **API 参考**
> 官方文档「在虚幻引擎中运行自动化测试」：https://dev.epicgames.com/documentation/zh-cn/unreal-engine/run-automation-tests-in-unreal-engine

---

## 2.5 动手练习

**练习 A（读）**：打开 `BlueprintNamingTest.cpp`，回答：
- 如果一个 `WBP_` 前缀的控件继承了 `AnimInstance`，会用哪个前缀？（提示：规则顺序）
- `AddError` 的格式串里有几个 `%s`？分别是什么？

**练习 B（小改）**：把 `/Engine/` 硬编码改成也跳过 `/Script/`：

```cpp
const FString Path = AssetData.PackagePath.ToString();
if (Path.StartsWith(TEXT("/Engine/")) || Path.StartsWith(TEXT("/Script/")))
    continue;
```

**练习 C（新写）**：在 `ProjectTests` 里加第二个测试，检查所有 `Content/` 下的 `Texture2D` 尺寸不超过 2048：

```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTextureSizeTest,
    "Project.TextureSize",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FTextureSizeTest::RunTest(const FString& Parameters)
{
    // 1. FARFilter 过滤 UTexture2D
    // 2. 遍历，GetAsset → Cast<UTexture2D>
    // 3. Blueprint_GetSizeX/Y 或 GetSizeX()/GetSizeY()
    // 4. 超限就 AddError
    return true;
}
```

写完**必须验证它能失败**：临时把阈值改成 `1`，确认红灯亮起来。

> **API**
> `UTexture2D::GetSizeX() / GetSizeY() -> int32` —— 返回纹理宽高（像素）。
> `FAutomationTestBase::AddError(const FString& InError) -> void` —— 记一条失败信息，测试整体判负。

---

## 2.6 本篇小结

- 五层框架按"需不需要 World"分工，不是按"哪个更高级"
- `IMPLEMENT_SIMPLE_AUTOMATION_TEST` 的两个坑：忘 `WaitForCompletion()`、只 `return false` 不给原因
- `DEFINE_SPEC` 的价值是 `BeforeEach`/`AfterEach` 和线程池，适合 UI 驱动流程
- 全局单例（AutomationDriver）必须自己复位，否则测试互相污染
- **跑起来之前，先想清楚它怎么才会失败**

下一篇专攻 CQTest：它同时有 World、有 Player、有异步，是 Lyra 测试的主力形态。

---

*跳过的：`IMPLEMENT_COMPLEX_AUTOMATION_TEST`（项目里没有实例，用不到）；`AFunctionalTest` Actor 的蓝图用法（官方文档已写得很全，且你的项目只有关卡资产没有 C++ 子类）。风险：`MenuStartElimination.spec.cpp` 依赖 AutomationDriver 插件，若你的 `Lyra.uproject` 未启用该插件，这个文件根本不会编译——先 grep 一下 `uproject` 确认。*
