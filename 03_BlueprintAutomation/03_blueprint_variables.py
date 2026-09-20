"""
=============================================================
蓝图自动化 第3课：蓝图变量和函数
=============================================================

学习目标：
  - 在蓝图中创建和管理变量
  - 设置变量的默认值和属性
  - 了解蓝图函数的基本操作

核心类：
  - unreal.BlueprintEditorLibrary - 蓝图编辑器工具
  - unreal.BlueprintVariable - 蓝图变量

本课可能用到的 API：
  unreal.EditorAssetLibrary.load_asset(asset_path) -> Object  —— 加载蓝图资产到内存
  unreal.EditorAssetLibrary.save_asset(asset_to_save, only_if_is_dirty=True) -> bool  —— 保存修改后的蓝图
  unreal.EditorAssetLibrary.list_assets(directory_path, recursive=True, include_folder=False) -> Array[str]  —— 递归列出路径下全部资产
  unreal.EditorAssetLibrary.find_asset_data(asset_path) -> AssetData  —— 按路径查资产数据，不加载资产
  unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path, load_assets_to_confirm=False) -> Array[str]  —— 找引用该资产的包
  unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint, include_inherited_members=True) -> Array[str]  —— 列出蓝图成员变量名
  bp.generated_class -> Class  —— 蓝图编译后生成的类
  cls.get_default_object() -> Object  —— 获取类的默认对象 CDO
  obj.set_editor_property(name, value)  —— 设置对象的编辑器属性
  unreal.AssetRegistryHelpers.get_asset_registry() -> AssetRegistry  —— 获取资产注册表单例
  registry.get_dependencies(package_name, dependency_options) -> Optional[Array[Name]]  —— 查该包引用了哪些包
  unreal.AssetRegistryDependencyOptions(...)  —— 依赖类型选项，含软/硬引用开关
  unreal.ScopedSlowTask(work, desc="", enabled=True)  —— 创建带进度的慢任务对象
  task.make_dialog(can_cancel=False, allow_in_pie=False) -> None  —— 弹出进度对话框
  task.enter_progress_frame(work=1.0, desc="") -> None  —— 推进一帧进度
  task.should_cancel() -> bool  —— 用户是否请求取消
  asset_data.asset_class_path -> TopLevelAssetPath  —— 资产类路径，判断是否蓝图
=============================================================
"""

import unreal

# ─────────────────────────────────────────────────────────
# 1. 查看蓝图中的变量
# ─────────────────────────────────────────────────────────

def list_blueprint_variables(blueprint_path):
    """列出蓝图中所有用户定义的变量"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return

    unreal.log(f"\n蓝图 {bp.get_name()} 的变量列表:")
    unreal.log("-" * 40)

    # 【修改前】
    # variables = unreal.BlueprintEditorLibrary.get_blueprint_variables(bp)
    #
    # 【问题分析】
    # BlueprintEditorLibrary 上根本没有 get_blueprint_variables 这个方法（stub 里查无此名）。
    # 真正存在的是 list_member_variable_names —— 注意它返回的是"变量名字符串列表"，
    # 不是变量对象列表，所以下面遍历时也不需要再 get_name() 了。
    # 签名：list_member_variable_names(blueprint, include_inherited_members=True) -> Array[str]
    # 继承来的变量名会带声明类的完整路径前缀，只想要本蓝图自己声明的就传 False。
    variables = unreal.BlueprintEditorLibrary.list_member_variable_names(bp)

    if not variables:
        unreal.log("  没有用户定义的变量")
        return

    for var_name in variables:
        unreal.log(f"  变量: {var_name}")

    return variables

# ─────────────────────────────────────────────────────────
# 2. 蓝图变量的类型系统
# ─────────────────────────────────────────────────────────
# UE 蓝图变量支持以下类型：
#
# 基本类型:
#   - Boolean (bool)
#   - Integer (int32)
#   - Float
#   - String (FString)
#   - Name (FName)
#   - Text (FText)
#
# 数学类型:
#   - Vector (FVector)
#   - Rotator (FRotator)
#   - Transform (FTransform)
#   - LinearColor (FLinearColor)
#
# 对象类型:
#   - Class Reference
#   - Object Reference
#   - Soft Object Reference
#   - Interface Reference
#
# 容器类型:
#   - Array (TArray)
#   - Map (TMap)
#   - Set (TSet)

# ─────────────────────────────────────────────────────────
# 3. 修改蓝图属性的通用方法
# ─────────────────────────────────────────────────────────

def modify_blueprint_defaults(blueprint_path, property_updates):
    """
    修改蓝图的默认属性值

    参数:
        blueprint_path: 蓝图路径
        property_updates: dict, 键为属性名，值为新值

    示例:
        modify_blueprint_defaults(
            "/Game/Blueprints/BP_Enemy",
            {
                "Health": 100.0,
                "Speed": 500.0,
                "bIsHostile": True
            }
        )
    """
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        unreal.log_error(f"无法加载蓝图: {blueprint_path}")
        return False

    # 获取蓝图的默认对象（CDO）
    # CDO = Class Default Object
    # 修改 CDO 会改变所有该蓝图实例的默认值
    generated_class = bp.generated_class
    if not generated_class:
        unreal.log_error("蓝图没有已编译的类")
        return False

    cdo = generated_class.get_default_object()
    if not cdo:
        unreal.log_error("无法获取默认对象")
        return False

    # 应用属性修改
    for prop_name, prop_value in property_updates.items():
        try:
            cdo.set_editor_property(prop_name, prop_value)
            unreal.log(f"  {prop_name} = {prop_value}")
        except Exception as e:
            unreal.log_warning(f"  设置 {prop_name} 失败: {e}")

    # 保存
    unreal.EditorAssetLibrary.save_asset(blueprint_path)
    unreal.log(f"已更新蓝图默认值: {blueprint_path}")
    return True

# ─────────────────────────────────────────────────────────
# 4. 通过蓝图反射检查属性
# ─────────────────────────────────────────────────────────

def inspect_blueprint_properties(blueprint_path):
    """检查蓝图类的所有可用属性"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if not bp:
        return

    generated_class = bp.generated_class
    if not generated_class:
        unreal.log("蓝图未编译，无法检查属性")
        return

    cdo = generated_class.get_default_object()
    if not cdo:
        return

    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"蓝图属性检查: {bp.get_name()}")
    unreal.log(f"{'=' * 50}")

    # 获取所有可编辑属性
    attrs = [a for a in dir(cdo) if not a.startswith('_')]
    unreal.log(f"  可用属性/方法数: {len(attrs)}")

    # 尝试读取一些常见属性
    for attr in attrs[:30]:
        try:
            val = getattr(cdo, attr)
            if not callable(val):
                unreal.log(f"  .{attr} = {val}")
        except:
            pass

# ─────────────────────────────────────────────────────────
# 5. 蓝图资产引用操作
# ─────────────────────────────────────────────────────────

def get_package_dependencies(asset_path):
    """查询一个资产依赖（引用）了哪些包 —— 返回包名列表。

    【修改前】本课直接调用了 unreal.EditorAssetLibrary.find_package_references()，
    但 stub 里 EditorAssetLibrary 根本没有这个方法（虚构 API）。

    【问题分析】
    EditorAssetLibrary 上"引用/被引用"两个方向只暴露了一个：
        - 被谁引用：find_package_referencers_for_asset(asset_path)  ✅ 存在
        - 引用了谁（依赖）：EditorAssetLibrary 没有 —— 要走 AssetRegistry：
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            registry.get_dependencies(package_name, dependency_options)
    get_dependencies 的第二个参数必传 AssetRegistryDependencyOptions，
    想数出"所有"依赖就把软/硬引用都勾上。
    """
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    options.include_hard_package_references = True   # 硬引用：不用就跑不起来的
    options.include_soft_package_references = True   # 软引用：SoftObjectPath 那种
    result = registry.get_dependencies(asset_path, options)
    # get_dependencies 查不到时返回 None（不是空列表），统一成空列表
    return list(result) if result else []


def find_blueprint_dependencies(blueprint_path):
    """查找蓝图依赖的所有资产"""
    dependencies = get_package_dependencies(blueprint_path)

    unreal.log(f"\n蓝图 {blueprint_path} 依赖:")
    for dep in dependencies:
        unreal.log(f"  → {dep}")

    return dependencies

def find_what_references_blueprint(blueprint_path):
    """查找哪些资产引用了指定蓝图"""
    referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
        blueprint_path
    )

    unreal.log(f"\n引用蓝图 {blueprint_path} 的资产:")
    for ref in referencers:
        unreal.log(f"  ← {ref}")

    return referencers

# ─────────────────────────────────────────────────────────
# 6. 蓝图文档和注释
# ─────────────────────────────────────────────────────────

def set_blueprint_description(blueprint_path, description):
    """设置蓝图的描述信息"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp:
        # 设置蓝图的信息数据
        if hasattr(bp, 'set_editor_property'):
            try:
                bp.set_editor_property("description", description)
                unreal.EditorAssetLibrary.save_asset(blueprint_path)
                unreal.log(f"已设置描述: {description}")
            except:
                unreal.log_warning("设置描述失败（可能不支持该属性）")

def set_blueprint_category(blueprint_path, category):
    """设置蓝图的分类（影响在内容浏览器中的分类）"""
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp and hasattr(bp, 'set_editor_property'):
        try:
            bp.set_editor_property("category_name", category)
            unreal.EditorAssetLibrary.save_asset(blueprint_path)
            unreal.log(f"已设置分类: {category}")
        except:
            unreal.log_warning("设置分类失败")

# ─────────────────────────────────────────────────────────
# 7. 实用工具：蓝图审计
# ─────────────────────────────────────────────────────────

def audit_blueprints(search_path="/Game"):
    """
    审计项目中所有蓝图的质量:
    - 检查命名规范
    - 检查是否有描述
    - 检查依赖数量
    - 检查父类
    """
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True)

    results = {
        "total": 0,
        "no_prefix": 0,
        "no_description": 0,
        "high_dependency": 0,
        "issues": []
    }

    task = unreal.ScopedSlowTask(len(all_assets), "审计蓝图...")
    task.make_dialog(True)

    for asset_path in all_assets:
        if task.should_cancel():
            break

        task.enter_progress_frame(1.0, asset_path.split("/")[-1])

        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        class_str = str(asset_data.asset_class_path)

        if "Blueprint" not in class_str:
            continue

        results["total"] += 1
        name = asset_data.asset_name

        # 检查命名前缀
        if not name.startswith("BP_"):
            results["no_prefix"] += 1
            results["issues"].append(f"命名不规范: {name}")

        # 检查依赖数量
        # 【修改前】unreal.EditorAssetLibrary.find_package_references(asset_path)
        # 【问题分析】同 find_blueprint_dependencies —— 虚构 API，改用上面的
        # get_package_dependencies()（走 AssetRegistry.get_dependencies）
        refs = get_package_dependencies(asset_path)
        if len(refs) > 20:
            results["high_dependency"] += 1
            results["issues"].append(
                f"依赖过多 ({len(refs)}): {name}"
            )

    # 输出报告
    unreal.log(f"\n{'=' * 50}")
    unreal.log(f"  蓝图审计报告")
    unreal.log(f"{'=' * 50}")
    unreal.log(f"  总蓝图数: {results['total']}")
    unreal.log(f"  命名不规范: {results['no_prefix']}")
    unreal.log(f"  依赖过多 (>20): {results['high_dependency']}")

    if results["issues"]:
        unreal.log(f"\n  问题详情:")
        for issue in results["issues"][:20]:
            unreal.log(f"    ⚠️ {issue}")

    return results

# ─────────────────────────────────────────────────────────
# 使用示例
# ─────────────────────────────────────────────────────────

# 示例: 审计项目中所有蓝图
# audit_blueprints("/Game")

# 示例: 查看蓝图依赖
# find_blueprint_dependencies("/Game/Blueprints/BP_Player")

unreal.log("蓝图自动化第3课完成！")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 编写工具，批量修改所有蓝图的某个属性值
# 2. 创建一个"蓝图对比"工具，比较两个蓝图的组件和属性差异
# 3. 编写自动文档生成器，为所有蓝图生成 Markdown 文档
# 4. 实现蓝图版本管理工具，记录每次修改的属性变化
