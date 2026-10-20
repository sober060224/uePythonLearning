https://www.doubao.com/thread/xANQ3oKVVTi3u1CnP

已核实所有链接与本地示例（项目 UE 5.8，与文档版本一致）。

---

# UE Functional Test 从零入门 — 学习资源整理

## 0. 先分清"Functional Test"的三层含义（最重要，能省掉一半弯路）

UE 里 `Automation` 是总框架，Functional Test 只是其中一类。拿错资料的人 90% 是卡在这里：

| 你想测什么 | 用什么 | 运行位置 |
|---|---|---|
| 纯 C++ 数值/规则逻辑 | `IMPLEMENT_SIMPLE_AUTOMATION_TEST` | Editor / 命令行 |
| 有可读性的 BDD 交错测试 | Automation Spec（`BEGIN_DEFINE_SPEC`） | Editor / 命令行 |
| 遗漏最多的主干路径/Maps（**你说的大概率是这个**） | `AFunctionalTest` + Functional Test Actor + 测试关卡 | Editor / 独立客户端 |
| 跨 Actor 多帧异步、网络同步 | **CQTest**（`TEST_CLASS` / `TEST_METHOD`） | Editor / 无头 |
| 全流程冒烟（启动→菜单→进局） | Gauntlet + Automation Driver | 打包后设备/CI |

`AFunctionalTest` 的核心生命周期（官方文档原文）：`PrepareTest` → `IsReady`（每帧轮询，返回 false 就等）→ `OnTestStart` → 必须调 `FinishTest` → `OnTestFinished`（清理，避免污染后续测试）。

**如果你要做的是"跨多帧等一个能力生效"，直接抄 CQTest，不要用 AFunctionalTest。** 见下面第 3 节。

---

## 1. 按顺序走的学习路径（0 → 1）

**Step 1｜先把插件开起来再看任何教程**

`Edit → Plugins → Testing` 分类，勾 **Functional Testing Editor**，重启。然后 `Window → Test Automation`。

**Step 2｜跟着这个走完第一个蓝图 Functional Test（全英文，但最经典的入门文）**

- orfeasel《Creating Functional Tests with the Automation System》
  https://www.orfeasel.com/functional-tests/
  走一遍"玩家往前移动 X 单位 → 断言位置"的完整流程。**只做这一篇，先不碰 C++。**

**Step 3｜搞懂项目怎么配置、TDD 怎么起步**

- Unreal🌱Garden《Testing and Test Driven Development in Unreal》
  https://unreal-garden.com/tutorials/unreal-testing-introduction/
  这篇是公认最好的一步入门文，讲插件开启、窗口 UI、以及"哪些测试值得写"。

**Step 4｜进阶：Functional Test 与 Gauntlet 的分工，以及怎么组合成测试套件**

- Unreal🌱Garden《Building Complex Functional Tests》
  https://unreal-garden.com/tutorials/complex-functional-tests/
  同一作者的第二篇，讲怎么把简单测试 + helper 组合成复杂玩法测试。**这篇是入门到能干活的转折点。**

**Step 5｜实操经验（踩坑向）**

- Knowledge Horde《How to implement functional testing in Unreal Engine》
  https://bogart.tech/how-to-implement-functional-testing-in-unreal-engine/
  作者吐槽 Epic 官方文档"lackluster"、示例难找——和你的处境一致，然后给了自己的方案。
- Mercuna《Creating Functional Tests in UE4》
  https://mercuna.com/creating-functional-tests-in-unreal-engine-4/
  UE4 写的，但 Functional Test 的 API 至今没变，中间件视角、讲得很实。

---

## 2. 官方文档（UE 5.8，与本项目版本对齐）

| 资源 | 地址 |
|---|---|
| Functional Testing（主线，含 `AFunctionalTest` 全部函数表） | https://dev.epicgames.com/documentation/en-us/unreal-engine/functional-testing-in-unreal-engine |
| Automation Test Framework（测试类型分类表 + 命令参考） | https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-test-framework-in-unreal-engine |
| 运行自动化测试（中文版，同一页） | https://dev.epicgames.com/documentation/zh-cn/unreal-engine/run-automation-tests-in-unreal-engine |
| Automation Spec（4.27 版，5.x 已并入上面那页） | https://docs.unrealengine.com/4.27/en-US/TestingAndOptimization/Automation/AutomationSpec/ |
| `AFunctionalTest` API 索引 | https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Developer/FunctionalTesting/AFunctionalTest |

---

## 3. 本项目里就有一手示例 — 优先级最高，别去网上找

这是你手上最值钱的资源，**Epic 官方用 UE 5.8 亲手写的 CQTest 实战**，比任何博客都权威：

```
Plugins/GameFeatures/ShooterTests/Source/ShooterTestsRuntime/Private/
├── ShooterTestsMapTests.cpp            # 玩法能力测试，含 TestCommandBuilder 用法
├── ShooterTestsActorAnimationTests.cpp # 下半身动画 + 输入
├── ShooterTestsActorNetworkTests.cpp   # 网络同步
└── Utilities/
    ├── ShooterTestsActorTest.h         # 自定义宏 ACTOR_ANIMATION_TEST
    ├── ShooterTestsInputTestHelper.cpp # 用 Enhanced Input 驱动角色
    └── ShooterTestsAnimationTestHelper.cpp

Plugins/GameFeatures/ShooterTests/Content/Maps/
├── L_ShooterTest_Basic.umap            # 测试关卡模板（5 张，各司其职）
├── L_ShooterTest_FireWeapon.umap
└── ...
```

读法建议：`Plugins/GameFeatures/ShooterTests/Source/ShooterTestsRuntime/Private/ShooterTestsMapTests.cpp:33` 这个文件顶部的注释块把 CQTest 的 `Do`/`Then`/`StartWhen`/`Until` 语义讲清楚了，是全文精华：

```cpp
TEST_CLASS_WITH_FLAGS(AbilitySpawnerMapTest, "Project.Functional Tests.ShooterTests.GameplayAbility",
                      EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
{
    TUniquePtr<FMapTestSpawner> Spawner;
    ALyraCharacter* Player{ nullptr };
    ...
    TEST_METHOD(PlayerOnDamageSpawner_Eventually_LosesHealth)
```

另外两个轻量起点：

- `Plugins/ProjectTests/Source/ProjectTests/Private/BlueprintNamingTest.cpp` — 最简单的 `IMPLEMENT_SIMPLE_AUTOMATION_TEST` 样板，适合当"Hello World"
- `Source/LyraGame/Tests/MenuStartElimination.spec.cpp` — Spec + Automation Driver 全流程（点 Play Lyra → Start a Game → Elimination），配 Gauntlet 跑

```cpp
BEGIN_DEFINE_SPEC(FMenuStartEliminationSpec, "Lyra.MenuStartEliminationSpec",
                  EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
    FAutomationDriverPtr Driver;
END_DEFINE_SPEC(FMenuStartEliminationSpec)
```

> 注意：ShooterTests 的 `.uplugin` 里 `EnabledByDefault: false` + `ExplicitlyLoaded: true`，且 `TargetConfigurationDenyList: ["Shipping"]`。要跑它得先在 Plugins 里手动启用 ShooterTests 这个 Game Feature。

---

### 补充：CQTest / Spec 单独的资源

- minifloppy《Automated Testing With Specs in Unreal Engine》
  https://minifloppy.it/posts/2024/automated-testing-specs-ue5/
- dev.to《Testing in Unreal Engine 5: CQTest, Automation Spec, Functional Tests, and CI》
  https://dev.to/gamedevtoollab/testing-in-unreal-engine-5-cqtest-automation-spec-functional-tests-and-ci-3776
  **明确以 UE 5.8 文档为基准**，专门讲"什么时候该用哪个框架"，和你这个问题最对口。
- 测试模式速查表（直接可抄的代码片段集）
  https://github.com/quodsoler/unreal-engine-skills/blob/main/skills/ue-testing-debugging/references/automation-test-patterns.md
- `OpenPF2/EnhancedUnrealSpecs` — 给 Spec 加了 `BeforeAll` / `Let`（RSpec 风格），5.3+
  https://github.com/OpenPF2/EnhancedUnrealSpecs

---

## 4. 中文资源（质量参差，只推这两个）

- 做游戏的景夫《5 分钟上手 Automation 测试框架》
  https://neil3d.github.io/unreal/ue4_cpp_unit_test.html —— UE4，但"开插件→写用例→看结果"三步讲得最干净
- 小梁coder《UE5 自动化测试 - AutomationTest》
  https://xiaoliangcoder.github.io/Source/UnrealEngine/AutomationTest/AutomationTest/ —— UE5，含 `IMPLEMENT_CUSTOM_COMPLEX_AUTOMATION_TEST` 的参数化批量测试用法

（搜到的 2ds.cn 那篇"从入门到大师进阶路线图"营销味重、没有可运行代码，可略。）

---

## 5. ⚠️ Lyra 特有的坑：测试关卡会崩编辑器

这是**你做 Lyra Functional Test 一定会撞上的**，务必先知道：

> `Assertion failed: ExperienceComponent [File:.../Source/LyraGame/GameModes/AsyncAction_ExperienceReady.cpp] [Line: 68]`

来源：https://forums.unrealengine.com/t/functional-testing-w-lyra/1166899

原因：Lyra 的 GameMode 走 Experience 系统，自建一个空白 `FTEST` 关卡时 WorldSettings 没配 Experience，`AsyncAction_ExperienceReady` 的断言直接炸掉整个编辑器。

绕法：别自己从空关卡建，**直接复制 `Plugins/GameFeatures/ShooterTests/Content/Maps/L_ShooterTest_Basic.umap` 当模板**——它已经带好了 Lyra 所需的 WorldSettings / Experience 配置。这也是 Epic 自己写 ShooterTests 时的做法。

---

## 6. 怎么跑起来

**编辑器内**：`Window → Test Automation` → 勾选 → `Start Tests`

**命令行 / CI**（Lyra 自己的用法，见 ShooterTests 的 Gauntlet 接入）：
```
UnrealEditor-Cmd.exe <path>/Lyra.uproject -ExecCmds="Automation RunTests Lyra.MenuStartEliminationSpec" -unattended -nopause -testexit="Automation Test Queue Empty" -log
```
Gauntlet 侧的写法（社区给出的 Lyra 实例）：
```cpp
auto Client.CommandLineParams.Add("ExecCmds", "Automation RunTest Lyra.MenuStartEliminationSpec");
```

---

## 7. 附带发现：Python 也能驱动 Functional Test

如果后面想用 Python 写测试（本项目有 `PythonLearning/` 子项目），`unreal.FunctionalTest` **已暴露在 Python API 中**，无需 C++：

```python
ft = unreal.FunctionalTest           # 对应 C++ AFunctionalTest
ft.finish_test(unreal.FunctionalTestResult.SUCCESS, "OK")
ft.assert_true(condition, "message")
ft.set_time_limit(30.0, unreal.FunctionalTestResult.FAILED)
```
> 以上签名已在本项目 `Intermediate/PythonStub/unreal.py` 第 407726 行起的 `class FunctionalTest(Actor)` 中逐条核对。

相关 API（官方 Python API 文档）：
- `unreal.FunctionalTest.finish_test(test_result: unreal.FunctionalTestResult, message: str) -> None` — 结束当前功能测试并写入结果与说明文字。https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FunctionalTest
- `unreal.FunctionalTest.assert_true(condition: bool, message: str, context_object: unreal.Object = None) -> bool` — 断言条件为真，失败时记录消息。
- `unreal.FunctionalTest.is_ready() -> bool` — 返回准备阶段是否完成，决定测试能否开始。
- `unreal.FunctionalTest.set_time_limit(new_time_limit: float, result_when_time_runs_out: unreal.FunctionalTestResult) -> None` — 设置超时秒数及超时后的判定结果。

---

**如果只挑一条路走**：`unreal-garden 入门文`（Step 3）→ `L_ShooterTest_Basic.umap` 复制当模板 → `ShooterTestsMapTests.cpp:33` 抄 CQTest 骨架。跳过纯蓝图的 AFunctionalTest 分支，Lyra 这种量级的项目 CQTest 才是能维护的写法。

这份文件已经是一份很完整的 **UE Functional Test 从零入门资源地图**。核心结论可以压缩成下面这份“可执行版”：

## 1. 先分清测试框架，别拿错资料
最容易走弯路的地方是：**Automation 是总框架，Functional Test 只是其中一类**。

| 你想测什么 | 用什么 | 运行位置 |
|---|---|---|
| 纯 C++ 数值/规则逻辑 | `IMPLEMENT_SIMPLE_AUTOMATION_TEST` | Editor / 命令行 |
| BDD 风格交错测试 | Automation Spec | Editor / 命令行 |
| 主干路径 / Maps / 玩法流程 | `AFunctionalTest` + Functional Test Actor + 测试关卡 | Editor / 独立客户端 |
| 跨 Actor 多帧异步、网络同步 | CQTest | Editor / 无头 |
| 全流程冒烟：启动→菜单→进局 | Gauntlet + Automation Driver | 打包后设备 / CI |

**关键提醒**：如果你要测“跨多帧等一个能力生效”，优先用 **CQTest**，不要硬用 `AFunctionalTest`。

## 2. 最省事的 0→1 路线
1. **开插件**：`Edit → Plugins → Testing`，勾选 **Functional Testing Editor**，重启。
2. **第一个蓝图 Functional Test**：跟 orfeasel 的《Creating Functional Tests with the Automation System》走一遍，先不碰 C++。
3. **系统入门**：读 Unreal Garden 的《Testing and Test Driven Development in Unreal》，搞懂插件、Test Automation 窗口、哪些测试值得写。
4. **进阶组合**：读同作者的《Building Complex Functional Tests》，学会把简单测试 + helper 组合成复杂玩法测试。
5. **看实操踩坑**：Knowledge Horde、Mercuna 两篇，了解社区真实做法。

## 3. 优先级最高的其实是项目内示例
你项目里就有 Epic 官方用 UE 5.8 写的 CQTest 实战，比网上博客权威得多：

- `Plugins/GameFeatures/ShooterTests/Source/ShooterTestsRuntime/Private/ShooterTestsMapTests.cpp`
  - 重点看第 33 行附近的注释块，讲清了 CQTest 的 `Do/Then/StartWhen/Until` 语义。
- `ShooterTestsActorAnimationTests.cpp`
- `ShooterTestsActorNetworkTests.cpp`
- `Plugins/GameFeatures/ShooterTests/Content/Maps/L_ShooterTest_Basic.umap`

**注意**：`ShooterTests` 插件默认未启用，需要手动在 Plugins 里开启；且 `Shipping` 下被禁用。

## 4. Lyra 项目必踩的坑
如果你在 Lyra 里自建空白 FTEST 关卡，很容易崩编辑器：

```text
Assertion failed: ExperienceComponent
[AsyncAction_ExperienceReady.cpp] [Line: 68]
```

原因是 Lyra 的 GameMode 走 Experience 系统，空白关卡没配 Experience。

**绕法**：不要从空关卡建，直接复制：

```text
Plugins/GameFeatures/ShooterTests/Content/Maps/L_ShooterTest_Basic.umap
```

当模板用，它已经带好了 Lyra 所需的 WorldSettings / Experience 配置。

## 5. 怎么跑
编辑器内：

```text
Window → Test Automation → 勾选 → Start Tests
```

命令行 / CI：

```bat
UnrealEditor-Cmd.exe <path>/Lyra.uproject -ExecCmds="Automation RunTests Lyra.MenuStartEliminationSpec" -unattended -nopause -testexit="Automation Test Queue Empty" -log
```

## 6. 如果只挑一条路走
> **Unreal Garden 入门文 → 复制 `L_ShooterTest_Basic.umap` 当模板 → 抄 `ShooterTestsMapTests.cpp:33` 的 CQTest 骨架。**

跳过纯蓝图的 `AFunctionalTest` 分支。像 Lyra 这种量级的项目，**CQTest 才是能维护的写法**。

---

这份文件本身质量很高，链接、版本、项目内路径都核对了。  
如果你需要，我可以继续帮你把它转成：

1. **7 天学习计划表**
2. **CQTest / Functional Test 选型速查表**
3. **可直接复制到项目里的最小测试模板**
4. **Lyra 下运行 Functional Test 的命令速查卡**

你想让我接着做哪一项？

sober060224 收到！结合你「蓝桥杯1个月冲刺 + UE C++零基础 + Gameplay兴趣 + 3A长期目标」的现状，咱们制定这条**务实可执行**的学习路径：

| 步骤 | 核心内容 | 产出物 | 优先级 | 建议周期 | 时间分配建议 |
|------|----------|--------|--------|----------|--------------|
| **1️⃣ C++巩固 + 蓝桥杯冲刺** | • 蓝桥真题训练（DFS/BFS/DP/贪心）<br>• 重构管理系统：智能指针/RAII/移动语义<br>• STL容器底层原理回顾 | • 洛谷/蓝桥云课AC记录≥30题<br>• `StuManager_v2`重构代码（GitHub）<br>• 算法模板笔记（Markdown） | 🔴 P0 | 4周（赛前） | 在校：2h算法+1h UE预热<br>周末：5h算法+3h UE文档 |
| **2️⃣ UE C++环境迁移** | • VS+UE5.3+C++项目搭建<br>• Unreal宏体系：`UCLASS`/`UFUNCTION`/`UPROPERTY`<br>• UE容器：`TArray`/`TMap` vs STL | • 可编译的`HelloUE`项目（打印Log+Timer）<br>• UE C++语法速查表（自建）<br>• 博客：《从C++到UE C++的3个思维转变》 | 🔴 P0 | 1.5周 | 每日1.5h实操+0.5h文档 |
| **3️⃣ Gameplay框架核心实践** | • Actor/Character/Pawn区别<br>• 输入映射（Enhanced Input）<br>• 角色移动+Camera跟随+动画蓝图衔接 | • 第三人称角色Demo：WASD移动+鼠标视角+跳跃<br>• 技术博客：《UE5角色控制流解析》<br>• 代码仓库含清晰Commit记录 | 🔴 P0 | 2周 | 周末集中4h联调+工作日碎片复习 |
| **4️⃣ UMG + C++交互系统** | • C++暴露变量/函数给蓝图<br>• UMG控件绑定+C++事件响应<br>• 简单状态机：UI↔Gameplay通信 | • 带动态血条+背包面板的Demo<br>• `HealthComponent` C++类（支持蓝图继承）<br>• 通信流程图（Draw.io） | 🟠 P1 | 1.5周 | 优先保证步骤3稳固后再推进 |
| **5️⃣ 小型Gameplay系统实战** | • 选择1个系统深挖：技能/任务/背包<br>• 数据驱动设计（DataTable/JSON）<br>• 基础调试：Log/Stat命令/Profiler | • GitHub仓库：`UE5_MiniRPG`（含README+截图）<br>• 1分钟竖屏Demo视频（B站/腾讯文档）<br>• 系统设计文档（1页PDF） | 🟠 P1 | 2-3周 | 建议蓝桥杯后全力投入 |
| **6️⃣ 作品集整合 + 求职预演** | • 筛选3个最佳项目包装<br>• 简历技术模块撰写（STAR法则）<br>• 目标公司技术栈调研（腾讯/网易/米哈游等） | • 个人作品集页面（Notion/GitHub Pages）<br>• 简历初稿（PDF）<br>• 《UE Gameplay岗能力对照表》 | 🔴 P0 | 1周（穿插进行） | 每完成1个产出物即时归档 |
| **7️⃣ （选做）网络/优化入门** | • 基础Replication概念<br>• UE性能分析工具：Stat Unit/ProfileGPU<br>• 对象池/异步加载简单实践 | • 双人同步Demo（可选）<br>• 性能优化Checklist<br>• 技术笔记：《UE Gameplay性能避坑指南》 | 🔵 P2 | 弹性（赛后） | 仅当核心步骤完成后启动 |

| 原步骤 | 优化动作 | 修改后关键变化 |
|--------|----------|----------------|
| **步骤2** | ➕ 增加「里程碑检查」 | 结束前需完成：① 用C++写一个带`BeginPlay`/`Tick`的Actor ② 用`TArray`替代`std::vector`重构管理系统某模块 |
| **步骤3** | ➕ 增加「防坑指南」 | 明确：先蓝图验证逻辑→再C++实现，避免卡在编译错误；推荐先复现UE官方ThirdPersonExample C++版 |
| **步骤5** | ➕ 前置「网络/优化基础」 | 将原步骤7的`Replication概念`+`Stat Unit命令`+`对象池思想`拆出，作为步骤5必做子项（2h/周） |
| **步骤6** | ➕ 补充「协作模拟」 | 作品集README中增加：「若与策划协作，我会如何设计数据表结构」；Demo视频加字幕说明「此功能如何响应策划需求」 |
| **全程** | ➕ 增加「Plan B」 | 若蓝桥杯未达预期：① 用GitHub贡献图+技术博客证明持续学习力 ② 重点打磨步骤5的MiniRPG Demo，用「完整小系统」替代「竞赛奖项」 |

💡 **关键执行原则**：
1. **蓝桥杯前（~3月底）**：步骤1占70%精力，步骤2仅作环境预热（避免切换损耗）
2. **所有代码必上GitHub**：Commit信息用英文+功能描述，这是你的「第二简历」
3. **产出物＞学习时长**：每步以「可展示结果」为完成标准，避免陷入教程循环
4. **Gameplay优先**：暂时不碰Shader/动画蒙太奇等偏美术模块，聚焦逻辑层

🎯 **下一步行动建议**：
- 今天：在GitHub新建`UE-Learning-Path`仓库，创建`/step1_algorithm` `/step2_ue_setup` 文件夹
- 明天：跑通UE5.3 C++项目模板（ThirdPersonExample），截图发我确认环境✅

需要我帮你：
🔹 整理蓝桥杯C++ B组高频考点清单？
🔹 提供UE C++宏体系的速查思维导图？
🔹 推荐3个适合新手练手的Gameplay小项目灵感？

你选一个，咱们立刻开工 🚀

sober060224 收到！基于搜索结果+行业认知，我对规划进行**诚实自我评估**，并给出优化决策：

---

### 🔍 四维评估报告

| 评估维度 | 评分(1-5⭐) | 关键依据 | 风险点 |
|----------|------------|----------|--------|
| **1️⃣ 应届生可达性** | ⭐⭐⭐⭐ | • 步骤1-3内容匹配大二C++基础+1个月冲刺强度<br>• 产出物（Demo/博客/GitHub）均为可量化小目标<br>• 时间分配考虑在校/周末差异，具备弹性 | • 步骤3（Gameplay框架）2周产出第三人称Demo，对UE C++零基础略有挑战，需防「教程依赖」 |
| **2️⃣ 路径清晰度** | ⭐⭐⭐⭐ | • 每步含「输入→行动→产出」闭环<br>• 优先级+周期+时间分配三维标注<br>• 依赖关系明确（1→2→3→4→5） | • 缺少「里程碑检查点」：如步骤2结束时应能独立写`UCLASS`+`TArray`<br>• 无「失败回退方案」：若蓝桥未获奖如何补救 |
| **3️⃣ 前人成功事例** | ⭐⭐⭐⭐ | • 牛客面经显示：「算法基础+UE项目+作品集」是双非进大厂高频路径<br>• CSDN/知乎多篇「自学UE C++获offer」分享，共性：GitHub持续提交+Demo可玩+博客复盘<br>• 蓝桥杯省一以上在游戏岗属「加分项」，非必需 | • 成功案例多集中于「有导师/战队」环境，纯自学案例较少，需更强自律 |
| **4️⃣ 公司要求匹配度** | ⭐⭐⭐⭐ | • 腾讯/网易校招JD高频要求：C++基础✅、算法✅、UE/Unity经验✅、项目经历✅<br>• Gameplay岗更看重「逻辑实现能力」而非渲染底层，规划聚焦正确<br>• 作品集意识（步骤6）直击校招痛点：「项目经历很重要」说三遍 | • 头部公司（米哈游/腾讯IEG）常要求「网络同步/性能优化基础认知」，原规划步骤7为选做，略弱<br>• 缺少「协作能力」展示：Gameplay开发需与策划/美术联调，规划偏单人开发 |

---

### ✅ 优化决策：**微调不改主线**

> 📌 原则：保持「蓝桥冲刺优先+UE C++渐进」主干，仅增强风险管控与头部公司适配

---

### 🎯 优化后核心优势

1. **更抗风险**：每2周设检查点，避免「学完才发现不会用」
2. **更贴大厂**：头部公司关注的网络/优化/协作意识提前渗透
3. **更重产出**：所有调整仍围绕「可展示结果」，不增加无效学习
4. **保留弹性**：Plan B确保即使竞赛失利，作品集仍能支撑求职

---

### ▶️ 下一步行动（今天就能做）

1. **GitHub初始化**：
   ```bash
   mkdir UE-Learning-Path && cd UE-Learning-Path
   mkdir step1_algorithm step2_ue_setup step3_gameplay
   echo "# 我的UE C++成长路径" > README.md
   git init && git add . && git commit -m "init: learning path structure"
   ```
2. **蓝桥杯今日任务**：
   - 洛谷刷1道DFS+1道DP（限时2h）
   - 整理`StuManager`中`vector`操作，思考如何用`TArray`重写（为步骤2预热）

需要我：
🔹 发你一份「UE C++宏体系速查表」（含`UFUNCTION`参数详解）？
🔹 推荐3个「1周可完成」的Gameplay小练习（带参考实现）？
🔹 整理蓝桥杯C++ B组近3年真题高频考点？

你选一个，咱们立刻执行 🚀

