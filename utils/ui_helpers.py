"""
=============================================================
UI 辅助工具库
=============================================================

提供编辑器 UI 相关的辅助函数：
- 对话框
- 通知
- 进度条
- 屏幕消息

=============================================================
"""

import unreal


# ─────────────────────────────────────────────────────────
# 屏幕消息
# ─────────────────────────────────────────────────────────

# 预定义颜色
COLORS = {
    "white":  [1.0, 1.0, 1.0, 1.0],
    "red":    [1.0, 0.2, 0.2, 1.0],
    "green":  [0.2, 1.0, 0.2, 1.0],
    "blue":   [0.2, 0.5, 1.0, 1.0],
    "yellow": [1.0, 0.9, 0.2, 1.0],
    "cyan":   [0.2, 1.0, 1.0, 1.0],
    "orange": [1.0, 0.6, 0.1, 1.0],
    "purple": [0.7, 0.3, 1.0, 1.0],
}

def show_message(text, color="white", duration=5.0):
    """在屏幕上显示消息"""
    c = COLORS.get(color, COLORS["white"])
    unreal.SystemLibrary.print_string(None, text, True, True, c, duration)

def show_success(text, duration=3.0):
    show_message(f"✅ {text}", "green", duration)

def show_warning(text, duration=5.0):
    show_message(f"⚠️ {text}", "yellow", duration)

def show_error(text, duration=5.0):
    show_message(f"❌ {text}", "red", duration)

def show_info(text, duration=3.0):
    show_message(f"ℹ️ {text}", "blue", duration)


# ─────────────────────────────────────────────────────────
# 编辑器通知
# ─────────────────────────────────────────────────────────

def notify(text, notification_type="info"):
    """
    显示编辑器通知（右下角弹出）

    参数:
        text: 通知文本
        notification_type: "info", "success", "warning", "error"
    """
    type_map = {
        "info": unreal.NotificationType.INFO if hasattr(unreal, 'NotificationType') else None,
        "success": unreal.NotificationType.SUCCESS if hasattr(unreal, 'NotificationType') else None,
        "warning": unreal.NotificationType.WARNING if hasattr(unreal, 'NotificationType') else None,
        "error": unreal.NotificationType.ERROR if hasattr(unreal, 'NotificationType') else None,
    }

    # 使用屏幕消息作为通知
    color = {
        "info": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }.get(notification_type, "white")

    show_message(text, color, 5.0)
    unreal.log(text)


# ─────────────────────────────────────────────────────────
# 对话框
# ─────────────────────────────────────────────────────────

def show_message_dialog(title, message, msg_type="ok"):
    """
    显示消息对话框

    参数:
        title: 标题
        message: 消息内容
        msg_type: "ok", "yes_no", "yes_no_cancel"
    """
    type_map = {
        "ok": unreal.AppMsgType.OK,
        "yes_no": unreal.AppMsgType.YES_NO,
        "yes_no_cancel": unreal.AppMsgType.YES_NO_CANCEL,
    }

    app_msg_type = type_map.get(msg_type, unreal.AppMsgType.OK)

    result = unreal.EditorDialog.show_message(title, message, app_msg_type)
    return result

def confirm_action(title, message):
    """确认操作对话框，返回 True/False"""
    result = show_message_dialog(title, message, "yes_no")
    return result == unreal.AppReturnType.YES

def input_dialog(title, message, default_value=""):
    """
    输入对话框（简单版本）

    注意：UE Python 的输入对话框支持有限
    这里使用消息对话框作为替代
    """
    unreal.log(f"[INPUT] {title}: {message}")
    unreal.log(f"  默认值: {default_value}")
    # 实际使用中，建议使用 Editor Utility Widget 创建自定义输入界面
    return default_value


# ─────────────────────────────────────────────────────────
# 进度条
# ─────────────────────────────────────────────────────────

class ProgressBar:
    """
    进度条封装

    用法:
        with ProgressBar(100, "处理中...") as pb:
            for i in range(100):
                if pb.should_cancel():
                    break
                pb.update(1, f"处理第 {i} 项")
                # ... 你的逻辑
    """

    def __init__(self, total, description="处理中..."):
        self.total = total
        self.description = description
        self.task = None
        self.current = 0

    def __enter__(self):
        self.task = unreal.ScopedSlowTask(self.total, self.description)
        self.task.make_dialog(True)
        return self

    def __exit__(self, *args):
        self.task = None

    def update(self, amount=1.0, text=""):
        """推进进度"""
        if self.task:
            self.task.enter_progress_frame(amount, text)
            self.current += amount

    def should_cancel(self):
        """检查用户是否点击了取消"""
        if self.task:
            return self.task.should_cancel()
        return False


# ─────────────────────────────────────────────────────────
# 选区工具
# ─────────────────────────────────────────────────────────

def require_selected_actors(min_count=1, message=None):
    """
    确保有足够数量的选中 Actor

    返回: 选中的 Actor 列表，或 None（不足数量时）
    """
    actors = unreal.EditorLevelLibrary.get_selected_level_actors()
    if len(actors) < min_count:
        msg = message or f"请至少选中 {min_count} 个 Actor"
        show_warning(msg)
        return None
    return actors

def require_selected_assets(min_count=1, message=None):
    """
    确保有足够数量的选中资产

    返回: 选中的资产数据列表，或 None
    """
    assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
    if len(assets) < min_count:
        msg = message or f"请至少选中 {min_count} 个资产"
        show_warning(msg)
        return None
    return assets


# ─────────────────────────────────────────────────────────
# 表格输出
# ─────────────────────────────────────────────────────────

def print_table(headers, rows, title=""):
    """
    在日志中打印格式化表格

    参数:
        headers: 列名列表
        rows: 行数据列表 (list of list)
        title: 表格标题
    """
    if title:
        log_section(title)

    # 计算列宽
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # 打印表头
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    separator = "-+-".join("-" * w for w in widths)

    unreal.log(f"  {header_line}")
    unreal.log(f"  {separator}")

    # 打印行
    for row in rows:
        line = " | ".join(str(c).ljust(w) for c, w in zip(row, widths))
        unreal.log(f"  {line}")

def log_section(title):
    """输出标题区域"""
    line = "=" * 50
    unreal.log(f"\n{line}")
    unreal.log(f"  {title}")
    unreal.log(f"{line}")
