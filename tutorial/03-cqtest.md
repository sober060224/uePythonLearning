# 第 3 篇：CQTest 逐行拆解

> 目标：读懂 Lyra 里唯一一个"真的在测 Gameplay"的测试文件，并能照着骨架加自己的用例。
>
> 主教材：`Plugins/GameFeatures/ShooterTests/Source/ShooterTestsRuntime/Private/ShooterTestsMapTests.cpp`（130 行）

---

## 3.1 为什么是 CQTest

前三层（Simple / Complex / Spec）的共同短板是：**没有 World**。

你要测"玩家踩到伤害垫会掉血"，就需要真实的 Level、真实的 Player、真实的 AbilitySystem。手工搭这一套要几百行，还容易搭错。

CQTest 把这套东西包成了三块：

| 组件 | 位置 | 解决什么 |
|---|---|---|
| `FMapTestSpawner` | `Engine/Source/Developer/CQTest/Public/Components/MapTestSpawner.h` | 加载测试关卡、等流式加载完、找 Player Pawn |
| `TObjectBuilder<T>` | `Public/ObjectBuilder.h` | 在测试里 spawn Actor 并设参数，自动清理 |
| `TestCommandBuilder` | `Public/Commands/TestCommandBuilder.h` | 把"等 X 出现"变成一帧一帧检查的命令队列 |

三者组合起来，你就有了一个**可重复、可回收的迷你游戏世界**。

---

## 3.2 骨架第一行：`TEST_CLASS_WITH_FLAGS`

```cpp
#if WITH_AUTOMATION_TESTS

#include "CQTest.h"

TEST_CLASS_WITH_FLAGS(AbilitySpawnerMapTest,
                      "Project.Functional Tests.ShooterTests.GameplayAbility",
                      EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
{
    // ... 成员 ...
};
```

这个宏展开后是一个 `struct AbilitySpawnerMapTest : public TTest<AbilitySpawnerMapTest, FNoDiscardAsserter>`，外加一个静态注册器 `FAbilitySpawnerMapTest_Runner`。

看引擎里的定义（`CQTest.h:263-311`），它带了两个 `static_assert`：

```cpp
static_assert(!!((_TestFlags) & EAutomationTestFlags_ApplicationContextMask),
              "CQTest has no application flag and will not run.");

static_assert(!!(((_TestFlags) & EAutomationTestFlags_FilterMask) == EAutomationTestFlags::SmokeFilter) || ...,
              "All CQTests must have exactly 1 filter type specified.");
```

意思是：**必须给且只给一个上下文 Flag，一个过滤 Flag**。写错编译期就报，不会静默失效。这比 Spec 友好。

为什么用 `EditorContext`？看文件顶部注释：

> Note that this is a test which will be run in the Editor context as this test spawns objects based on Blueprints found on the local filesystem. Assets require to be cooked along the game to run in the game/client.

翻译：它靠 `CQTestAssetHelper::GetBlueprintClass("BP_GameplayEffectPad")` 从**磁盘上的 uasset** 拿蓝图类。打包后资产是 cook 过的二进制，编辑器路径就不好使了。

---

## 3.3 成员：测试的"棋盘"

```cpp
TUniquePtr<FMapTestSpawner> Spawner;              // 关卡加载器（自动析构）
ALyraCharacter* Player{ nullptr };                // 被测的玩家
AActor* GameplayEffectPad{ nullptr };             // 后 spawn 的垫子
ULyraAbilitySystemComponent* AbilitySystemComponent{ nullptr };
const ULyraHealthSet* HealthSet{ nullptr };
```

这些不是随便挑的——它们是"测一件事"所需的最小状态集：

```
Spawner ──加载──> L_ShooterTest_Basic
                        │
                        └──> Player (ALyraCharacter)
                                 ├── GetLyraAbilitySystemComponent() → ASC
                                 │        └── GetSetChecked<ULyraHealthSet>() → HealthSet
                                 └── GetTransform() → 垫子生成位置
```

`TUniquePtr` 那行很重要：CQTest 的规矩是**每个 `TEST_METHOD` 都重新 `Setup()`**，`Spawner` 自动析构保证上一个方法的关卡不残留。

---

## 3.4 三个辅助方法

### `DoDamageToPlayer(double Damage)`

```cpp
void DoDamageToPlayer(double Damage)
{
    const TSubclassOf<UGameplayEffect> DamageEffect =
        ULyraAssetManager::GetSubclass(ULyraGameData::Get().DamageGameplayEffect_SetByCaller);

    FGameplayEffectSpecHandle SpecHandle = AbilitySystemComponent->MakeOutgoingSpec(
        DamageEffect, 1.0, AbilitySystemComponent->MakeEffectContext());
    ASSERT_THAT(IsTrue(SpecHandle.IsValid()));

    SpecHandle.Data->SetSetByCallerMagnitude(LyraGameplayTags::SetByCaller_Damage, Damage);

    FActiveGameplayEffectHandle Handle =
        AbilitySystemComponent->ApplyGameplayEffectSpecToSelf(*SpecHandle.Data.Get());
    ASSERT_THAT(IsTrue(Handle.WasSuccessfullyApplied()));
}
```

四步，全是 GAS 的标准动作：

1. **拿 GE 类** —— 从 `ULyraGameData`（一个 `UDeveloperSettings`）里取软类指针 `TSoftClassPtr<UGameplayEffect> DamageGameplayEffect_SetByCaller`，再让 `ULyraAssetManager::GetSubclass()` 同步加载成 `TSubclassOf`。这是 Lyra 里获取 GE 的标准写法，别自己写 `LoadObject`。
2. **造 Spec** —— `MakeOutgoingSpec(GE类, Level, Context)`，`Level = 1.0`。
3. **传参** —— `SetSetByCallerMagnitude(Tag, 值)`。因为那个 GE 的 Modifier 用的是 `SetByCaller` 类型，伤害值不写在 GE 里，而是运行时由这条曲线传进去。这就是为什么测试能精确打 10 点。
4. **应用** —— `ApplyGameplayEffectSpecToSelf`，成功返回的 handle `.WasSuccessfullyApplied()` 为真。

> **API**
> `UAbilitySystemComponent::MakeOutgoingSpec(TSubclassOf<UGameplayEffect>, float Level, FGameplayEffectContextHandle) -> FGameplayEffectSpecHandle`
> `FGameplayEffectSpec::SetSetByCallerMagnitude(FGameplayTag, float) -> void`
> `UAbilitySystemComponent::ApplyGameplayEffectSpecToSelf(const FGameplayEffectSpec&) -> FActiveGameplayEffectHandle`

### `SpawnGameplayPad(const FString& EffectName)`

```cpp
void SpawnGameplayPad(const FString& EffectName)
{
    UClass* DesiredEffect = CQTestAssetHelper::GetBlueprintClass(EffectName);
    ASSERT_THAT(IsNotNull(DesiredEffect));

    UClass* GameplayEffectPadBp = CQTestAssetHelper::GetBlueprintClass(TEXT("BP_GameplayEffectPad"));
    ASSERT_THAT(IsNotNull(GameplayEffectPadBp));

    GameplayEffectPad = &TObjectBuilder<AActor>(*Spawner, GameplayEffectPadBp)
        .SetParam("GameplayEffectToApply", DesiredEffect)
        .Spawn(Player->GetTransform());

    ASSERT_THAT(IsNotNull(GameplayEffectPad));
}
```

两个知识点：

**`CQTestAssetHelper::GetBlueprintClass(FString)`** —— 按名字找蓝图类，返回 `UClass*`。找不到返回 `nullptr`，所以必须断言。

**`TObjectBuilder<AActor>`** —— 这是 CQTest 最有价值的小工具：

```
TObjectBuilder<ActorType>(Spawner, Class)
    .SetParam("属性名", 值)      ← 用名字设 UPROPERTY，支持 Blueprint 变量
    .Spawn(Transform)            ← 真正 spawn，返回引用
```

`SetParam` 用**字符串名字**设属性，所以能设蓝图里定义的变量（`GameplayEffectToApply` 是 `BP_GameplayEffectPad` 上的一个变量）。测试结束后 Spawner 统一销毁它们——不用你手动 `Destroy()`。

注意返回值是 `&`（引用）。`GameplayEffectPad = &TObjectBuilder<...>.Spawn(...)` 这个写法有点怪，但合法：`Spawn` 返回 `AActor&`。

### `IsPlayerDamaged()`

```cpp
bool IsPlayerDamaged()
{
    return HealthSet->GetHealth() < HealthSet->GetMaxHealth();
}
```

一行。但它被用在 `Until()` 里每帧求值——这就是**轮询条件**必须无副作用的典型约束。别在这里 `AddError`，会让每帧都记一条错。

---

## 3.5 `BEFORE_EACH`：整个文件的重点

```cpp
BEFORE_EACH()
{
    const FString LevelName = TEXT("L_ShooterTest_Basic");

    TOptional<FString> PackagePath = CQTestAssetHelper::FindAssetPackagePathByName(LevelName);
    ASSERT_THAT(IsTrue(PackagePath.IsSet(), "Could not find the level package."));

    Spawner = MakeUnique<FMapTestSpawner>(PackagePath.GetValue(), LevelName);
    Spawner->AddWaitUntilLoadedCommand(TestRunner);

    const FTimespan LoadingScreenTimeout = FTimespan::FromSeconds(30);
    TestCommandBuilder
        .StartWhen([this]() { return nullptr != Spawner->FindFirstPlayerPawn(); }, LoadingScreenTimeout)
        .Do([this]() {
            Player = CastChecked<ALyraCharacter>(Spawner->FindFirstPlayerPawn());
            AbilitySystemComponent = Player->GetLyraAbilitySystemComponent();
            ASSERT_THAT(IsNotNull(AbilitySystemComponent));

            HealthSet = AbilitySystemComponent->GetSetChecked<ULyraHealthSet>();
            ASSERT_THAT(IsTrue(HealthSet->GetHealth() > 0));
            ASSERT_THAT(IsTrue(HealthSet->GetHealth() == HealthSet->GetMaxHealth()));
        });
}
```

`BEFORE_EACH()` 展开是 `virtual void Setup() override`（`CQTest.h:333`）。逐个看：

**① 找关卡路径**

```cpp
TOptional<FString> PackagePath = CQTestAssetHelper::FindAssetPackagePathByName(LevelName);
```

`TOptional<FString>` —— 有值/无值两态，不用靠空字符串判断。找不到就让断言失败，避免后面拿空路径去加载导致一个莫名其妙的崩溃。

**② 建 Spawner 并挂"等加载完"命令**

```cpp
Spawner = MakeUnique<FMapTestSpawner>(PackagePath.GetValue(), LevelName);
Spawner->AddWaitUntilLoadedCommand(TestRunner);
```

`FMapTestSpawner(MapDirectory, MapName)` 两个参数。`AddWaitUntilLoadedCommand(TestRunner)` 把"流式加载完成"这件事塞进命令队列——**这一步和下面的 `StartWhen` 是两回事**：

| 等待对象 | 用什么 |
|---|---|
| 关卡资源加载完 | `Spawner->AddWaitUntilLoadedCommand(TestRunner)` |
| Player Pawn 出现 | `StartWhen(FindFirstPlayerPawn != nullptr)` |

加载完 ≠ Pawn 已 spawn。Lyra 还要走 Experience 加载 → 生成 Pawn → Possess，这中间有若干帧。所以必须额外等 Pawn。

**③ 等 Pawn + 抓组件**

```cpp
TestCommandBuilder
    .StartWhen([this]() { return nullptr != Spawner->FindFirstPlayerPawn(); }, LoadingScreenTimeout)
    .Do([this]() { /* 抓 Player / ASC / HealthSet */ });
```

`StartWhen(Query, Timeout)` 在 `TestCommandBuilder.h` 里的实现就是 `return Until(Query, Timeout)`——每帧求值直到为真，超时就判失败。

`FTimespan::FromSeconds(30)` —— 超时 30 秒。这个值不好定：太短会在慢机器上 flaky，太长会让真失败拖 30 秒。Lyra 选 30 秒是因为关卡不大。

`Do(...)` 里的三步：

```cpp
Player = CastChecked<ALyraCharacter>(Spawner->FindFirstPlayerPawn());
```

`CastChecked` —— 类型不对就直接崩。这里故意用崩溃而不是返回 nullptr，因为"关卡里的 Player 不是 LyraCharacter"是**配置错误**，不是测试失败，应该大声炸出来。

```cpp
AbilitySystemComponent = Player->GetLyraAbilitySystemComponent();
```

Lyra 特有的便捷方法，比 `GetAbilitySystemComponent()` 多了类型（返回 `ULyraAbilitySystemComponent*`）。

```cpp
HealthSet = AbilitySystemComponent->GetSetChecked<ULyraHealthSet>();
ASSERT_THAT(IsTrue(HealthSet->GetHealth() > 0));
ASSERT_THAT(IsTrue(HealthSet->GetHealth() == HealthSet->GetMaxHealth()));
```

`GetSetChecked<ULyraHealthSet>()` —— 从 ASC 里按类型取 AttributeSet，没有就崩。

最后两行是**前置条件断言**：开局必须满血。少了这两行，如果某个测试前一轮把玩家弄死了，下一轮 `IsPlayerDamaged()` 一上来就是 `true`，测试会"通过"但什么也没验证。

> **API**
> `FMapTestSpawner(const FString& MapDirectory, const FString& MapName)`
> `void FMapTestSpawner::AddWaitUntilLoadedCommand(TestRunner)`
> `APawn* FMapTestSpawner::FindFirstPlayerPawn() const`
> `UAbilitySystemComponent::GetSetChecked<T>() -> T*`

---

## 3.6 两个 `TEST_METHOD`

### 用例一：踩伤害垫会掉血

```cpp
TEST_METHOD(PlayerOnDamageSpawner_Eventually_LosesHealth)
{
    TestCommandBuilder
        .StartWhen([this]() { return !AbilitySystemComponent->HasMatchingGameplayTag(TAG_Gameplay_DamageImmunity); })
        .Then([this]() { SpawnGameplayPad(TEXT("GE_GameplayEffectPad_Damage")); })
        .Until([this]() { return IsPlayerDamaged(); });
}
```

读法像一句话：**等无敌结束 → 生成伤害垫 → 等玩家掉血**。

**为什么第一句要等 `TAG_Gameplay_DamageImmunity`？** 因为 Lyra 开局有出生保护。不等这个，垫子会生成但伤害被免疫吃掉，`Until` 一直为假，30 秒后超时失败——你会以为是垫子坏了。

这是"读测试学到游戏逻辑"的最佳例子：一行等待告诉你 Lyra 有出生无敌。

**三个命令的区别**（这是 CQTest 的核心心智模型）：

| 方法 | 求值次数 | 用途 |
|---|---|---|
| `Do(Action)` | 一次 | 动作，不等 |
| `Then(Action)` | 一次 | 同 `Do`，链式可读性用 |
| `Until(Query, Timeout)` | 每帧直到为真 | 等一个条件 |
| `StartWhen(Query, Timeout)` | 每帧直到为真 | 同 `Until`，语义是"前置条件" |

内部实现（`Commands/TestCommandBuilder.h`）：`StartWhen` 直接 `return Until(Query, Timeout)`。所以 `StartWhen` / `Until` 完全等价，只是让代码读起来更清楚。

**`Until` 默认超时**是 `CQTest::DefaultTimeout`。这个测试没传超时——意味着它接受默认值。如果你写自己的测试，**建议显式传超时**，让"这里可能会慢"这个事实写在代码里。

### 用例二：受伤后踩治疗垫会回血

```cpp
TEST_METHOD(PlayerMissingHealth_OnHealSpawner_RestoresHealth)
{
    TestCommandBuilder
        .StartWhen([this]() { return !AbilitySystemComponent->HasMatchingGameplayTag(TAG_Gameplay_DamageImmunity); })
        .Then([this]() { DoDamageToPlayer(10.0); })
        .Until([this]() { return IsPlayerDamaged(); })
        .Then([this]() { SpawnGameplayPad(TEXT("GE_GameplayEffectPad_Heal")); })
        .Until([this]() { return !IsPlayerDamaged(); });
}
```

链更长，但结构一样：**准备 → 动作 → 等结果 → 动作 → 等结果**。

注意最后 `Until([this]() { return !IsPlayerDamaged(); })` —— 恢复满血才算通过。如果治疗垫只回 5 点，`IsPlayerDamaged()` 仍是 `true`，测试失败。这就是"测的是行为不是实现"：它不关心治疗垫回多少，只关心能不能回到满血。

---

## 3.7 `ASSERT_THAT` 的一个陷阱

展开看（`CQTest.h:329`）：

```cpp
#define ASSERT_THAT(_assertion) if (!this->Assert._assertion) {return;}
```

它 `return` 的是**当前函数**。

- 在 `BEFORE_EACH`（`Setup`）里 → 整个 setup 中止，测试判失败。✅ 符合预期
- 在 `TEST_METHOD` 里 → 退出该测试方法。✅ 符合预期
- 在 `DoDamageToPlayer` 这类**辅助方法**里 → 只退出辅助方法，**调用方继续往下跑**

第三种情况是坑。假设 `DoDamageToPlayer` 里的 `SpecHandle.IsValid()` 失败了：错误被记录，函数返回，然后 `ApplyGameplayEffectSpecToSelf` 那句**不会执行**，回到 `TEST_METHOD` 继续跑 `Until(IsPlayerDamaged)` → 永远为假 → 30 秒后超时。

你会看到两条错误：一条"spec invalid"，一条"timeout"。前者是根因，后者是噪声。排查时**永远看第一条**。

---

## 3.8 怎么跑

### 编辑器

`Window → Test Automation` → 展开 `Project` → `Functional Tests` → `ShooterTests` → `GameplayAbility`

会看到两个测试：
- `AbilitySpawnerMapTest.PlayerOnDamageSpawner_Eventually_LosesHealth`
- `AbilitySpawnerMapTest.PlayerMissingHealth_OnHealSpawner_RestoresHealth`

勾上 → `Start Tests`。**编辑器会真的切关卡、真的生成 Player**，屏幕上会看到变化，这是正常的。

### 前置条件

```
Plugins/GameFeatures/ShooterTests/ShooterTests.uplugin
  → EnabledByDefault: false
  → ExplicitlyLoaded: true
  → BuiltInInitialFeatureState: "Registered"
```

它是 Game Feature，默认**不加载**。要么在编辑器里手动 Enable，要么在测试配置里指定。同时它的 `TargetConfigurationDenyList: ["Shipping"]` 说明 Shipping 构建里根本没有这个模块。

### 命令行

```
UnrealEditor.exe Lyra.uproject ^
  -ExecCmds="Automation RunTests Project.Functional Tests.ShooterTests; Quit" ^
  -unattended -nopause -stdout -fullstdoutlogoutput
```

注意不用 `-nullrhi`——这个测试要加载带渲染的关卡，无 GPU 环境下 `L_ShooterTest_Basic` 可能加载失败。

---

## 3.9 动手练习

### 练习 A（读）

回答三个问题：
1. `BEFORE_EACH` 里为什么要同时有 `AddWaitUntilLoadedCommand` 和 `StartWhen(FindFirstPlayerPawn)`？
2. 如果删掉 `ASSERT_THAT(IsTrue(HealthSet->GetHealth() == HealthSet->GetMaxHealth()))`，什么情况下测试会假阳性？
3. 两个 `TEST_METHOD` 各自用了两次 `Until`，分别等的是什么？

### 练习 B（小改）

把用例二的伤害从 `10.0` 改成 `1.0`，跑一遍。观察：
- 仍然通过（因为 `IsPlayerDamaged()` 只要求 `< MaxHealth`）
- 说明这个测试**没有验证伤害量**，只验证了"变了"

想让它更严格，可以改断言：

```cpp
.Until([this]() { return FMath::IsNearlyEqual(HealthSet->GetHealth(), HealthSet->GetMaxHealth() - 10.0, 0.1); })
```

但这会让测试变脆（任何伤害相关的数值调整都要改测试）。**这正是测试设计里最真实的取舍**：断言越精确，越容易被无关改动打红。

### 练习 C（新写）

加第三个用例：**玩家掉血后，`IsDeadOrDying()` 应该为假**（10 点伤害不该致死）。

```cpp
TEST_METHOD(PlayerDamaged_ButNotDead)
{
    ULyraHealthComponent* HealthComponent = ULyraHealthComponent::FindHealthComponent(Player);

    TestCommandBuilder
        .StartWhen([this]() { return !AbilitySystemComponent->HasMatchingGameplayTag(TAG_Gameplay_DamageImmunity); })
        .Then([this]() { DoDamageToPlayer(10.0); })
        .Until([this]() { return IsPlayerDamaged(); })
        .Then([HealthComponent]() { ASSERT_THAT(IsFalse(HealthComponent->IsDeadOrDying())); });
}
```

需要 `#include "Character/LyraHealthComponent.h"`。

再写第四个：**一次打掉全部血量会致死**。提示：
- 先读 `HealthSet->GetMaxHealth()` 拿到满血值
- 用 `DoDamageToPlayer(MaxHealth + 1.0)`
- `Until([this]() { return HealthComponent->IsDeadOrDying(); })`

**两个都要验证能失败**：把 `IsFalse` 改成 `IsTrue`，确认红灯。

> **API**
> `static ULyraHealthComponent* ULyraHealthComponent::FindHealthComponent(const AActor* Actor)` —— 在 Actor 上找血量组件，没有返 nullptr。
> `bool ULyraHealthComponent::IsDeadOrDying() const` —— `DeathState > ELyraDeathState::NotDead`，即进入死亡流程后为真。
> https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FunctionalTest

---

## 3.10 本篇小结

- CQTest = `FMapTestSpawner`（关卡）+ `TObjectBuilder`（造物）+ `TestCommandBuilder`（等待）
- `BEFORE_EACH` 展开成 `Setup()`，每轮重来；`ASSERT_THAT` 在此处失败才是真正的"前置条件失败"
- `Do`/`Then` 执行一次，`Until`/`StartWhen` 每帧求值直到为真或超时
- 等待条件必须无副作用
- `ASSERT_THAT` 在辅助函数里只退出辅助函数，会产生"根因 + 超时"两条错误——看第一条

下一篇进 Gameplay：这四个成员变量背后的类到底是什么，以及为什么你的空关卡一加载就崩。

---

*跳过的：`TObjectBuilder` 的完整 API（`SetParam` 之外还有 `SetFloatParam` 等重载，本例没用到）；`FMapTestSpawner::LoadMap` 的显式用法（`AddWaitUntilLoadedCommand` 已覆盖）。风险：`ShooterTests` 是 Game Feature 且 `EnabledByDefault: false`，如果你的编辑器里没启用它，Test Automation 窗口里根本看不到这两个测试。*
