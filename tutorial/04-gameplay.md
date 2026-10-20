# 第 4 篇：Gameplay 四个类，和 Experience 加载链

> 目标：搞清楚第 3 篇里那四个成员变量背后的类到底是什么，以及为什么你新建一个空关卡一加载就崩。

---

## 4.1 先破一个常见误解：ASC 不在角色身上

新手看 Lyra 代码，第一反应是"角色身上有 ASC"。**不是。**

```cpp
// Character/LyraCharacter.cpp:182
ULyraAbilitySystemComponent* ALyraCharacter::GetLyraAbilitySystemComponent() const
{
    return Cast<ULyraAbilitySystemComponent>(GetAbilitySystemComponent());
}

// Character/LyraCharacter.cpp:187
UAbilitySystemComponent* ALyraCharacter::GetAbilitySystemComponent() const
{
    if (PawnExtComponent == nullptr)
        return nullptr;
    return PawnExtComponent->GetLyraAbilitySystemComponent();
}
```

一路追下去，ASC 实际住在 **PlayerState** 上。`LyraHeroComponent.cpp:166` 那句话写得很直白：

```cpp
// The player state holds the persistent data for this player
// (state that persists across deaths and multiple pawns).
// The ability system component and attribute sets live on the player state.
PawnExtComp->InitializeAbilitySystem(LyraPS->GetLyraAbilitySystemComponent(), LyraPS);
```

**为什么这样设计？** 因为角色会死、会重生、会被 Possess/UnPossess。而"你学了哪些技能、还剩多少血"不该因为换了个身体就清空。放在 PlayerState 上，Pawn 只是 ASC 的一个"外壳"。

**这对测试的影响**：你拿到 `Player->GetLyraAbilitySystemComponent()` 时，拿到的是 PlayerState 的那个。所以：
- 伤害打在这个 ASC 上，血量存在 PlayerState 上
- 换 Pawn 不会丢血
- 但 PlayerState 是**每个玩家一个**，测试里如果有两个 Player，它们是两套独立的 ASC

---

## 4.2 四个类

### `ULyraAbilitySystemComponent`（简称 ASC）

位置：`Source/LyraGame/AbilitySystem/LyraAbilitySystemComponent.h`

GAS 的 `UAbilitySystemComponent` 子类。Lyra 加了三样东西：

| 能力 | 用途 |
|---|---|
| Ability 激活策略（`ELyraAbilityActivationPolicy`） | `OnInputTriggered` / `WhileInputActive` / `OnSpawn` |
| 输入绑定（`BindAbilityActions`） | 把 `InputAction` 映射到 `AbilityInputTag` |
| Tag Relationship | 一个技能激活时，动态屏蔽/取消其他技能 |

测试里用到的方法：

```cpp
FGameplayEffectSpecHandle MakeOutgoingSpec(TSubclassOf<UGameplayEffect> GE, float Level, FGameplayEffectContextHandle Context);
FActiveGameplayEffectHandle ApplyGameplayEffectSpecToSelf(const FGameplayEffectSpec& Spec);
TT* GetSetChecked<T>();              // 按类型取 AttributeSet，没有就崩
bool HasMatchingGameplayTag(FGameplayTag Tag) const;
```

`GetSetChecked<ULyraHealthSet>()` 是第 3 篇里那句。它要求 **ASC 上确实挂了 HealthSet**——这由 `ULyraPawnData::AbilitySets` 里的 `ULyraAbilitySet` 负责授予。

> **API**
> `ULyraAbilitySystemComponent::GetSetChecked<T>() -> T*` —— 从 ASC 的活动 AttributeSet 列表里按类型查找，未找到时 `check()` 断言失败。

### `ULyraHealthSet`（AttributeSet）

位置：`Source/LyraGame/AbilitySystem/Attributes/LyraHealthSet.h`

四个属性，全部用 `ATTRIBUTE_ACCESSORS` 宏展开：

```cpp
ATTRIBUTE_ACCESSORS(ULyraHealthSet, Health);      // 当前血量
ATTRIBUTE_ACCESSORS(ULyraHealthSet, MaxHealth);   // 最大血量
ATTRIBUTE_ACCESSORS(ULyraHealthSet, Healing);     // 「治疗中」的瞬时值
ATTRIBUTE_ACCESSORS(ULyraHealthSet, Damage);      // 「受伤中」的瞬时值
```

宏会生成 `GetHealth()` / `SetHealth(float)` / `InitHealth(float)` / `GetHealthAttribute()` 四个函数。

**关键理解**：`Healing` 和 `Damage` 不是"累计伤害/累计治疗"，它们是 **Meta Attribute** —— 当它们变化时，`PreAttributeChange` 会立刻把值加到 `Health` 上并把自身归零。所以测试里能读到的是 `Health`，`Damage` 永远是 0。

`OnRep_Health` / `OnRep_MaxHealth` 是网络同步回调，客户端靠它更新 UI。

> **API**
> `ATTRIBUTE_ACCESSORS(ClassName, PropertyName)` —— 为 `FGameplayAttributeData PropertyName` 生成 getter/setter/init/attribute 四个方法。

### `ULyraHealthComponent`

位置：`Source/LyraGame/Character/LyraHealthComponent.h`

这是"外面的人"访问血量的门。它本质上是一层**委托包装**：

```cpp
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLyraHealth_DeathEvent, AActor*, OwningActor);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FLyraHealth_AttributeChanged,
    ULyraHealthComponent*, HealthComponent, float, OldValue, float, NewValue, AActor*, Instigator);

static ULyraHealthComponent* FindHealthComponent(const AActor* Actor);

float GetHealth() const;
float GetMaxHealth() const;
float GetHealthNormalized() const;    // [0, 1]
ELyraDeathState GetDeathState() const;
bool IsDeadOrDying() const { return (DeathState > ELyraDeathState::NotDead); }
```

**`HealthComponent::GetHealth()` vs `HealthSet::GetHealth()`** —— 两者返回同一个数，区别在缓存：

- `HealthSet->GetHealth()` 直接读 GAS 属性，每次都是最新值
- `HealthComponent->GetHealth()` 读的是它自己同步的一份缓存（靠 `HealthSet` 的 `OnHealthChanged` 委托更新）

测试里第 3 篇用的是 `HealthSet->GetHealth()`，因为它更快、更直接。但你要测"死亡事件有没有触发"，就必须用 `HealthComponent`。

> **API**
> `static ULyraHealthComponent* ULyraHealthComponent::FindHealthComponent(const AActor* Actor)` —— 在 Actor 上查找血量组件，没有返回 `nullptr`。
> `bool ULyraHealthComponent::IsDeadOrDying() const` —— `DeathState > ELyraDeathState::NotDead`，进入死亡流程即为真。

### `ULyraWeaponInstance`

位置：`Source/LyraGame/Weapons/LyraWeaponInstance.h`（**不是** `Equipment/`）

它继承自 `ULyraEquipmentInstance`，是"装备系统里的武器"。

```cpp
virtual void OnEquipped() override;
virtual void OnUnequipped() override;

UFUNCTION(BlueprintCallable) void UpdateFiringTime();
UFUNCTION(BlueprintPure) float GetTimeSinceLastInteractedWith() const;

protected:
    FLyraAnimLayerSelectionSet EquippedAnimSet;     // 拿着时的动画层
    FLyraAnimLayerSelectionSet UneuippedAnimSet;    // 收起时的动画层
    TArray<TObjectPtr<UInputDeviceProperty>> ApplicableDeviceProperties;  // 手柄震动等
```

**它管什么**：动画层切换、`GetTimeSinceLastInteractedWith()`（用于"多久没开火"这类逻辑）、手柄设备属性。

**它不管什么**：开火、伤害、弹药。那些在 `LyraGameplayAbility_RangedWeapon` 和 `ULyraRangedWeaponInstance` 里。

`ULyraRangedWeaponInstance`（`Source/LyraGame/Weapons/LyraRangedWeaponInstance.h`）是它的子类，管**散布（spread）**：

```cpp
// Spread|Fire Params
float SpreadExponent;
float SpreadRecoilKick;
float SpreadMinDegrees;
float SpreadMaxDegrees;

// Spread|Player Params
float SpreadYawScale;
float SpreadPitchScale;
bool bUseSpread;
```

`GetCurrentSpread()` 是所有散布参数合成后的结果。**测武器手感**就是测这些——但 Lyra 里没有对应测试，因为"手感"没法自动判对错。

**怎么拿到武器实例**：

```cpp
ULyraEquipmentManagerComponent* EquipMgr =
    Player->FindComponentByClass<ULyraEquipmentManagerComponent>();
TArray<ULyraEquipmentInstance*> Weapons =
    EquipMgr->GetEquipmentInstancesOfType(ULyraWeaponInstance::StaticClass());
// Weapons[0] → 当前武器
```

第 3 篇没测武器，因为伤害垫测试不需要开火。

> **API**
> `TArray<ULyraEquipmentInstance*> ULyraEquipmentManagerComponent::GetEquipmentInstancesOfType(TSubclassOf<ULyraEquipmentInstance> InstanceType) const` —— 按类型筛选当前装备实例。

---

## 4.3 Experience 加载链：为什么空关卡会崩

这是新手最常踩的坑。你在编辑器里 `File → New Level → Empty Level`，Play，编辑器崩了：

```
Assertion failed: ExperienceComponent
[File: .../Source/LyraGame/GameModes/AsyncAction_ExperienceReady.cpp] [Line: 68]
```

### 崩在哪

```cpp
// GameModes/AsyncAction_ExperienceReady.cpp:62-65
void UAsyncAction_ExperienceReady::Step2_ListenToExperienceLoading(AGameStateBase* GameState)
{
    check(GameState);
    ULyraExperienceManagerComponent* ExperienceComponent =
        GameState->FindComponentByClass<ULyraExperienceManagerComponent>();
    check(ExperienceComponent);       // ← 第 65 行，崩在这
```

`check()` 在 Development 构建里是**硬断言**，失败就崩，不是失败返回。

### 为什么找不到组件

再看组件是谁挂的：

```cpp
// GameModes/LyraGameState.cpp:32
ExperienceManagerComponent = CreateDefaultSubobject<ULyraExperienceManagerComponent>(TEXT("ExperienceManagerComponent"));
```

它挂在 `ALyraGameState` 上。

而空关卡用的是引擎默认的 `AGameStateBase`，不是 `ALyraGameState`。所以组件根本不存在。

**触发链**：

```
你 Play 空关卡
  → 用的是 Project Settings 的 GlobalDefaultGameMode = B_LyraGameMode
  → ALyraGameMode 构造时设了 GameStateClass = ALyraGameState
  → 但……你的关卡 WorldSettings 可能覆盖了 GameMode
  → 或者 Experience 从 WorldSettings 拿不到（空关卡没设）
  → ALyraGameMode::HandleMatchAssignmentIfNotExpectingOne 拿不到 ExperienceId
  → 有人调用 AsyncAction_ExperienceReady（等 Experience 加载完）
  → 找到 GameState，但它是 AGameStateBase，没那个组件
  → check() 崩
```

反过来说：**只要 GameState 是 `ALyraGameState`，组件一定在**。所以更常见的真实原因是——关卡 WorldSettings 里的 `GameMode Override` 是空的或错的，或者你直接从 Content 里双击打开了一个 `L_xxx` 但它的 WorldSettings 没配 Experience。

### Experience 是什么

一个 `ULyraExperienceDefinition`（`Source/LyraGame/GameModes/LyraExperienceDefinition.h`）：

```cpp
UPROPERTY(EditDefaultsOnly, Category = Gameplay)
TArray<FString> GameFeaturesToEnable;                    // 要启用哪些 Game Feature

UPROPERTY(EditDefaultsOnly, Category = Gameplay)
TObjectPtr<const ULyraPawnData> DefaultPawnData;         // 默认用什么 Pawn

UPROPERTY(EditDefaultsOnly, Instanced, Category = "Actions")
TArray<TObjectPtr<UGameFeatureAction>> Actions;          // 加载时要执行的动作

UPROPERTY(EditDefaultsOnly, Category = Gameplay)
TArray<TObjectPtr<ULyraExperienceActionSet>> ActionSets; // 可复用的动作集合
```

一个 Experience = **一组 GameFeature + 一个 PawnData + 一堆加载动作**。

举例：`B_LyraShooterGame_Elimination` 这个 Experience 会启用 `ShooterCore` 这个 Game Feature、指定 `PawnData_Shooter`、执行"生成武器""配 HUD"等动作。

### Experience 从哪来

`ALyraGameMode::HandleMatchAssignmentIfNotExpectingOne()`（`LyraGameMode.cpp:89`）按优先级找：

```
1. 匹配服务分配（Matchmaking）
2. URL 参数 ?Experience=xxx
3. DeveloperSettings（仅 PIE）
4. 命令行 -Experience=
5. WorldSettings 的 DefaultGameplayExperience    ← 测试关卡用这个
6. 专用服务器
7. 默认 Experience
```

**第 5 条是你在编辑器里该用的**：打开测试关卡的 `World Settings`，找到 `Default Gameplay Experience`，设成你要的那个。

### PawnData 从哪来

拿到 Experience 之后：

```cpp
// GameModes/LyraGameMode.cpp:64-73
if (ExperienceComponent->IsExperienceLoaded())
{
    const ULyraExperienceDefinition* Experience = ExperienceComponent->GetCurrentExperienceChecked();
    if (Experience->DefaultPawnData != nullptr)
        return Experience->DefaultPawnData;

    // 加载完了但没配 PawnData，退回默认
    return ULyraAssetManager::Get().GetDefaultPawnData();
}
return nullptr;    // 还没加载完，现在没有 PawnData
```

### PawnData 里有什么

`ULyraPawnData`（`Source/LyraGame/Character/LyraPawnData.h`）：

```cpp
TSubclassOf<APawn> PawnClass;                              // 生成什么 Pawn
TArray<TObjectPtr<ULyraAbilitySet>> AbilitySets;           // 授予哪些技能/GE/AttributeSet
TObjectPtr<ULyraAbilityTagRelationshipMapping> TagRelationshipMapping;
TObjectPtr<ULyraInputConfig> InputConfig;                  // 输入映射
TSubclassOf<ULyraCameraMode> DefaultCameraMode;
```

**这就是测试里 `HealthSet` 非空的根源**：`AbilitySets` 里有一个 `ULyraAbilitySet`，它的 `GrantedAttributeSets` 列出了 `ULyraHealthSet`。Lyra 在 Pawn 初始化时把这个 set 授予 ASC，HealthSet 才存在。

如果 PawnData 配错了（漏了 HealthSet），`GetSetChecked<ULyraHealthSet>()` 会崩，而不是返回 nullptr。

### 完整链路图

```
World Settings
  └── Default Gameplay Experience
        └── ULyraExperienceDefinition
              ├── GameFeaturesToEnable[]  ──> 加载 ShooterCore 等
              ├── Actions[]               ──> 执行加载动作
              └── DefaultPawnData
                    └── ULyraPawnData
                          ├── PawnClass        ──> 生成 ALyraCharacter
                          ├── AbilitySets[]    ──> 授予 LyraHealthSet / 技能 / GE
                          ├── InputConfig      ──> 绑定输入
                          └── DefaultCameraMode
```

**初始化顺序**（`ALyraCharacter` + `ULyraHeroComponent`）：

```
1. ALyraGameMode::InitGame
2. 下一帧 → HandleMatchAssignmentIfNotExpectingOne → 确定 ExperienceId
3. ExperienceManagerComponent->SetCurrentExperience
4. StartExperienceLoad → 加载 GameFeature、执行 Actions
5. OnExperienceLoadComplete → 广播 OnExperienceLoaded
6. GameMode 生成 Pawn（用 Experience 的 PawnData->PawnClass）
7. PawnExtensionComponent 授予 AbilitySets 到 ASC
8. HeroComponent::InitializePlayerInput
9. 进入 InitState_GameplayReady
```

第 3 篇的 `StartWhen(FindFirstPlayerPawn != nullptr, 30s)` 就是在等第 6 步。而 `HealthSet` 非空要等第 7 步——所以那句 `GetSetChecked` 在 `StartWhen` 之后的 `Do` 里，不能提前。

---

## 4.4 在测试里怎么用这四个类

### 读血量（最常用）

```cpp
// 首选：直接读 AttributeSet，最新值、无中间层
const ULyraHealthSet* HealthSet = ASC->GetSetChecked<ULyraHealthSet>();
float Current = HealthSet->GetHealth();
float Max     = HealthSet->GetMaxHealth();
bool bHurt    = Current < Max;
```

### 读死亡状态

```cpp
// 必须用 HealthComponent：死亡状态不在 AttributeSet 里
ULyraHealthComponent* HC = ULyraHealthComponent::FindHealthComponent(Player);
bool bDead = HC->IsDeadOrDying();
ELyraDeathState State = HC->GetDeathState();
```

### 精确打伤害

```cpp
const TSubclassOf<UGameplayEffect> GE =
    ULyraAssetManager::GetSubclass(ULyraGameData::Get().DamageGameplayEffect_SetByCaller);

FGameplayEffectSpecHandle Spec =
    ASC->MakeOutgoingSpec(GE, 1.0, ASC->MakeEffectContext());
Spec.Data->SetSetByCallerMagnitude(LyraGameplayTags::SetByCaller_Damage, 25.0);
ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
```

`SetByCaller` 是关键：同一个 GE 类，传不同的值就打出不同的伤害。测试里不需要为每个伤害值准备一个 GE 资产。

### 读武器

```cpp
ULyraEquipmentManagerComponent* EquipMgr =
    Player->FindComponentByClass<ULyraEquipmentManagerComponent>();
if (EquipMgr)
{
    TArray<ULyraEquipmentInstance*> Weapons =
        EquipMgr->GetEquipmentInstancesOfType(ULyraWeaponInstance::StaticClass());

    if (ULyraWeaponInstance* Weapon = Weapons.Num() > 0 ? Cast<ULyraWeaponInstance>(Weapons[0]) : nullptr)
    {
        float Idle = Weapon->GetTimeSinceLastInteractedWith();
    }
}
```

注意 `FindComponentByClass` 可能返回 nullptr——**空手时没有 EquipmentManager 组件**（取决于 PawnData）。所以要判空，不能像 HealthComponent 那样假定存在。

---

## 4.5 怎么造自己的测试关卡

不要自己 New Empty Level。**复制现成的**：

1. 打开 `Plugins/GameFeatures/ShooterTests/Content/Maps/L_ShooterTest_Basic.umap`
2. `File → Save Current Level As` → 存到你的测试目录，比如 `/Game/Tests/L_MyTest`
3. 打开新关卡的 `World Settings`，确认：
   - `GameMode Override` 留空（用 Project Settings 的 `B_LyraGameMode`）
   - `Default Gameplay Experience` 指向一个有效的 Experience（`B_LyraShooterGame_Elimination` 之类）
4. 在场景里摆你要测的东西（垫子、靶子、触发区）
5. 代码里把关卡名换掉：

```cpp
const FString LevelName = TEXT("L_MyTest");
```

**为什么要复制而不能新建**：`L_ShooterTest_Basic` 里已经配好了 PlayerStart、WorldSettings 的 Experience、必要的 GameFeature 状态。新建空关卡这些全没有，你会花两小时补配置，而且很容易漏掉某一项导致 `check()` 崩溃。

---

## 4.6 动手练习

### 练习 A（读）

1. `ALyraCharacter::GetLyraAbilitySystemComponent()` 最终从哪个对象上取 ASC？为什么这么设计？
2. `HealthSet->GetHealth()` 和 `HealthComponent->GetHealth()` 有什么区别？什么情况下必须用后者？
3. 空关卡崩溃的**直接原因**是什么（哪一行）？**根本原因**是什么？

### 练习 B（查）

打开 `Plugins/GameFeatures/ShooterTests/Content/Maps/L_ShooterTest_Basic.umap`（在编辑器里），看它的 `World Settings`：
- `Default Gameplay Experience` 指向哪个资产？
- 那个 Experience 的 `DefaultPawnData` 指向哪个 PawnData？
- 那个 PawnData 的 `AbilitySets` 里有几个 set？哪个提供了 `LyraHealthSet`？

这条链查通了，你就真的懂 Lyra 的初始化了。

### 练习 C（写）

给第 3 篇的测试加一个用例：**玩家血量归零后 `IsDeadOrDying()` 为真，且 `GetDeathState()` 不再是 `NotDead`**。

```cpp
TEST_METHOD(PlayerLosesAllHealth_BecomesDead)
{
    ULyraHealthComponent* HealthComponent = ULyraHealthComponent::FindHealthComponent(Player);
    ASSERT_THAT(IsNotNull(HealthComponent));

    const double MaxHealth = HealthSet->GetMaxHealth();

    TestCommandBuilder
        .StartWhen([this]() { return !AbilitySystemComponent->HasMatchingGameplayTag(TAG_Gameplay_DamageImmunity); })
        .Then([this, MaxHealth]() { DoDamageToPlayer(MaxHealth + 1.0); })
        .Until([HealthComponent]() { return HealthComponent->IsDeadOrDying(); }, FTimespan::FromSeconds(10))
        .Then([HealthComponent]() {
            ASSERT_THAT(AreNotEqual(HealthComponent->GetDeathState(), ELyraDeathState::NotDead));
        });
}
```

需要 `#include "GameModes/AsyncAction_ExperienceReady.h"` 之外的：
```cpp
#include "Character/LyraHealthComponent.h"
```

**验证它能失败**：把 `DoDamageToPlayer(MaxHealth + 1.0)` 改成 `DoDamageToPlayer(1.0)`，确认 `Until` 超时、红灯。

> **API**
> `ELyraDeathState ULyraHealthComponent::GetDeathState() const` —— 返回 `NotDead` / `DeathStarted` / `DeathFinished` 等。
> `FTimespan::FromSeconds(double Seconds) -> FTimespan` —— 构造时间跨度，用于 `Until` / `StartWhen` 的超时参数。

---

## 4.7 四篇串起来看

```
第 1 篇  Python 自制框架
          └─ 测试 = 收集 + 执行 + 汇报
第 2 篇  Simple Test / Spec
          └─ 无 World 的检查；有清理钩子的 UI 流程
第 3 篇  CQTest
          └─ 有 World、有 Player、有等待命令
第 4 篇  Gameplay 四类 + Experience 链
          └─ 那些成员变量到底是什么，世界怎么搭起来
```

现在回头看 `ShooterTestsMapTests.cpp`，每一行你应该都能说出"为什么"了。

**下一步能力升级路径**（本篇不展开，等你需要时再查）：

| 目标 | 学什么 |
|---|---|
| 测多玩家 / 网络 | `ULyraNetworkTestInstance`、`CQTestEnhancedInput` |
| 打包后跑测试 | Gauntlet（`UnrealTestNode` C#） |
| 性能回归 | `AutomatedPerfTesting` 插件 |
| 用 Python 驱动 C++ 测试 | `PythonAutomationTest` 插件 + `unreal.AutomationLibrary` |

---

## 4.8 本篇小结

- ASC 在 **PlayerState** 上，不在 Character 上；Pawn 只是外壳
- `HealthSet` 是 GAS 属性（快、直接），`HealthComponent` 是委托包装（有死亡状态和事件）
- `LyraWeaponInstance` 管动画和交互时间，伤害/散布在 `RangedWeaponInstance` 和 GameplayAbility 里
- Experience = GameFeature + PawnData + 加载动作；从 WorldSettings 的 `Default Gameplay Experience` 指定
- **空关卡崩溃**：`ALyraGameState` 才挂 `ExperienceManagerComponent`，空关卡用的是 `AGameStateBase` → `check()` 硬断言
- 造测试关卡：复制 `L_ShooterTest_Basic`，不要新建

---

*跳过的：`ULyraGameFeaturePolicy` 的插件加载细节（`LyraExperienceManagerComponent::StartExperienceLoad` 里的分阶段逻辑）、`ULyraPawnExtensionComponent` 的 InitState 状态机（`Spawned → DataAvailable → DataInitialized → GameplayReady`，只够写测试用）、Equipment/Inventory 全套。风险：`GetEquipmentInstancesOfType` 在空手时返回空数组，但 `FindComponentByClass<ULyraEquipmentManagerComponent>` 是否返回 nullptr 取决于 PawnData 配置——练习里要判空，不要假定。*
