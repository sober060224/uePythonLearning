import math
import contextlib

import unreal


@contextlib.contextmanager
def editor_transaction(description, primary_object):
    transaction = unreal.SystemLibrary.begin_transaction("开始事务", description, primary_object)
    try:
        yield transaction
    except BaseException:
        unreal.SystemLibrary.cancel_transaction(transaction)
        raise
    else:
        unreal.SystemLibrary.end_transaction()


# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 【练习 1】把选中的 Actor 均匀摆在一个圆上
#   输入： 视口中选中 ≥3 个 Actor；不足 3 个就提示后退出，一个都不许动
#   任务： 圆心 = 这些 Actor 当前位置的平均值（X/Y/Z 各取均值，即质心）；
#          半径 = 300.0（写成函数参数 radius=300.0）；
#          从 +X 方向起算，第 i 个 Actor 的角度 = i * 360°/N；
#          每个 Actor 的 Yaw 设成该角度本身（= 指向圆心外侧），Roll/Pitch 归零
#          （UE 里 Yaw=0 指向 +X、Yaw=90 指向 +Y，所以圆周上 θ 角处的外法线就是 Yaw=θ；
#           写成 θ+90 会变成沿切线方向 —— 编辑器实测确认，Yaw 与方位角一一对应）
#   输出： 圆周上出现 N 个等距 Actor；日志打印「已排列 N 个 Actor，半径 R」
#   验收： 选中 5 个跑一次 → 5 个点应构成正五边形（相邻点夹角 72°）；
#          再按 Ctrl+Z 一次 → 全部回到原位（说明事务包对了）
def first_sub(center : unreal.Vector, selected_actor : list[unreal.Actor], radius):
    sum = len(selected_actor)
    per_radian = 2 * math.pi / sum

    for i, actor in enumerate(selected_actor):
        # 设置每个Actor位置
        loc = actor.get_actor_location()
        new_x = center.x + radius * math.cos(per_radian * i)
        new_y = center.y + radius * math.sin(per_radian * i)
        new_loc = unreal.Vector(new_x, new_y, loc.z)
        actor.set_actor_location(new_loc, False, True)

        # 设置每个Actor方向
        new_rotator = unreal.MathLibrary.find_look_at_rotation(loc, center)




def first(selected_actor : list[unreal.Actor], radius=300.0):
    # 算出质心
    x_sum, y_sum, z_sum = 0, 0, 0
    for actor in selected_actor:
        loc = actor.get_actor_location()
        x_sum += loc.x
        y_sum += loc.y
        z_sum += loc.z
    sum = len(selected_actor)
    center = unreal.Vector(x_sum / sum, y_sum / sum, z_sum / sum)



# 【练习 2】把选中的 Actor 复制成 cols × rows 的网格
#   输入： 选中 1 个或多个 Actor；一个都没选就提示后退出
#   任务： 每个选中的 Actor 各复制出 cols*rows 份（cols 默认 3、rows 默认 2），
#          复制体按行列偏移：第 (row, col) 个的偏移 = (col*spacing, row*spacing, 0)，
#          spacing 默认 200.0，行列都从原 Actor 的 +X / +Y 方向增长；
#          偏移量相对原 Actor 的原始位置，不要累加
#   输出： 视口里出现整齐的网格阵列；日志打印「复制了 N 个 Actor」
#   验收： 选中 1 个跑 cols=3 rows=2 → 场景多出 6 个（连原件共 7 个），
#          相邻间距严格是 200；Ctrl+Z 一次全部消失

# 【练习 3】测量两个选中 Actor 之间的距离
#   输入： 选中恰好 2 个 Actor；少于或多于 2 个都提示后退出（不要偷偷取前两个）
#   任务： 算三维直线距离（X/Y/Z 三个轴都算），同时打印 XY 平面距离；
#          不做任何修改，所以不需要事务
#   输出： 日志「A → B 直线距离 123.4 cm（平面距离 100.0 cm）」
#   验收： 把两个 Actor 摆在同 X/Y、Z 差 100 → 应打印「100.0 cm（平面距离 0.0 cm）」

# 【练习 4】把上面三个工具收拾成一个可导入的模块
#   输入： 本文件里已经写好的工具函数
#   任务： 新建 04_EditorScripting/editor_tools.py，只暴露 3 个公有函数
#          （下划线开头的内部函数不导出），并在文件末尾提供
#          TOOLS = {"命令名": 函数} 字典，供 Editor Utility Widget 做下拉选择
#   输出： 新文件 editor_tools.py 可被其他脚本导入
#   验收： 另写 3 行脚本 `import editor_tools` + `editor_tools.place_in_circle()`
#          能跑通；改完 editor_tools.py 后不重启编辑器，用 importlib.reload 生效
