# Unreal Engine Python 脚本学习指南

> 从零开始，全面掌握 UE5 的 Python 脚本开发能力。

---

## 📋 前置准备

### 启用 Python 插件
1. 打开 UE5 编辑器
2. 进入 **Edit → Plugins**
3. 搜索 **Python Editor Script Plugin** 并启用
4. 同时启用 **Editor Scripting Utilities**
5. 重启编辑器

### 打开 Python 控制台
- **Window → Developer Tools → Python Console** (或按 `Alt+Shift+P`)
- 在控制台中可以直接输入 Python 代码

### 运行脚本的方式
| 方式 | 说明 |
|------|------|
| Python Console | 交互式执行，适合测试 |
| 命令行 | `UnrealEditor.exe ProjectName.uproject -ExecutePythonScript="path/to/script.py"` |
| 编辑器菜单 | 通过 Editor Utility Widget/Blueprint 调用 |
| 本项目 | 在 Python Console 中 `exec(open("path/to/script.py").read())` |

---

## 📚 课程大纲

### 第一章：基础入门 `01_Basics/`
| 文件 | 内容 |
|------|------|
| `01_hello_unreal.py` | 第一个 UE Python 脚本，了解 `unreal` 模块 |
| `02_logging.py` | 日志系统，掌握调试技巧 |
| `03_editor_basics.py` | 编辑器基础交互，获取编辑器信息 |

### 第二章：资产管理 `02_AssetManagement/`
| 文件 | 内容 |
|------|------|
| `01_list_assets.py` | 列出、搜索项目中的资产 |
| `02_import_export.py` | 导入导出资产（FBX、纹理等） |
| `03_asset_actions.py` | 批量重命名、移动、删除等资产操作 |

### 第三章：蓝图自动化 `03_BlueprintAutomation/`
| 文件 | 内容 |
|------|------|
| `01_blueprint_basics.py` | 创建和修改蓝图 |
| `02_blueprint_components.py` | 管理蓝图组件 |
| `03_blueprint_variables.py` | 操作蓝图变量和函数 |

### 第四章：编辑器脚本 `04_EditorScripting/`
| 文件 | 内容 |
|------|------|
| `01_editor_utility.py` | 编辑器工具窗口 |
| `02_menu_extension.py` | 自定义菜单和工具栏 |
| `03_custom_tools.py` | 构建自定义编辑器工具 |

### 第五章：关卡与Actor `05_LevelAndActors/`
| 文件 | 内容 |
|------|------|
| `01_spawn_actors.py` | 在关卡中生成 Actor |
| `02_modify_actors.py` | 修改 Actor 属性和变换 |
| `03_level_management.py` | 关卡的加载、保存和管理 |

### 第六章：材质与纹理 `06_MaterialAndTexture/`
| 文件 | 内容 |
|------|------|
| `01_create_materials.py` | 创建和编辑材质 |
| `02_material_instances.py` | 材质实例和参数控制 |
| `03_texture_management.py` | 纹理导入和批量处理 |

### 第七章：序列与过场动画 `07_SequenceAndCinematic/`
| 文件 | 内容 |
|------|------|
| `01_level_sequence.py` | 创建和操控 Level Sequence |
| `02_camera_animation.py` | 相机动画和镜头控制 |

### 第八章：高级主题 `08_AdvancedTopics/`
| 文件 | 内容 |
|------|------|
| `01_batch_operations.py` | 大规模批量处理实战 |
| `02_external_data.py` | 与外部数据交互（CSV、JSON） |
| `03_automation_testing.py` | 自动化测试脚本 |

### 工具库 `utils/`
| 文件 | 内容 |
|------|------|
| `helpers.py` | 通用辅助函数 |
| `ui_helpers.py` | UI 相关辅助工具 |

---

## 🎯 学习建议

1. **按顺序学习** — 每章建立在前一章的基础上
2. **动手实践** — 每个脚本都在 UE 中实际运行
3. **修改实验** — 修改示例代码，观察不同效果
4. **组合运用** — 尝试将多个章节的知识组合使用

## 📖 参考资源

- [UE5 Python API 文档](https://docs.unrealengine.com/5.0/en-US/PythonAPI/)
- [Python Editor Script Plugin](https://docs.unrealengine.com/5.0/en-US/python-in-unreal-engine/)
- [unreal 模块参考](https://docs.unrealengine.com/5.0/en-US/PythonAPI/class_tree.html)

## 💡 提示

- 所有脚本都包含详细的中文注释
- 每个脚本都可以独立运行
- 建议在 Python Console 中逐行测试
- 使用 `unreal.log()` 输出调试信息