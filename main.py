# -*- coding: utf-8 -*-
"""
YouTube 视频下载器 - 主程序入口
作者：小码酱
日期：2025-02-12

功能特性：
✅ 支持 YouTube、B站等多平台视频下载
✅ 支持多种视频质量选择（1080p、720p、480p等）
✅ 支持音频提取和格式转换（MP3、M4A等）
✅ 支持字幕下载（自动生成、手动字幕）
✅ 支持批量下载和播放列表下载
✅ 显示下载进度和速度
✅ 支持断点续传
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

# 确保能找到项目模块
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from ui.main_window import MainWindow
from utils.helpers import check_dependencies


def check_environment():
    """
    检查运行环境
    
    Returns:
        (is_ok: bool, message: str)
    """
    deps = check_dependencies()
    
    messages = []
    
    # 检查 ffmpeg
    if not deps.get("ffmpeg"):
        messages.append("⚠️ 未检测到 ffmpeg，视频转换功能将不可用。\n"
                       "请从 https://ffmpeg.org 下载并安装。")
    
    # 检查 yt-dlp 版本
    yt_dlp_version = deps.get("yt-dlp")
    if not yt_dlp_version:
        messages.append("❌ 未检测到 yt-dlp，请运行：pip install yt-dlp")
    
    if messages:
        return False, "\n\n".join(messages)
    
    return True, "环境检查通过！"


def main():
    """主函数 - 应用程序入口"""
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("YouTube 视频下载器")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("小码酱")
    
    # 设置字体（解决中文显示问题）
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # TODO: 主人需要实现启动画面（可选）
    # 提示：可以创建 QSplashScreen 显示加载动画
    # 提示：加载完成后关闭 splash screen
    
    # 检查运行环境
    is_ok, message = check_environment()
    
    if not is_ok:
        QMessageBox.warning(
            None,
            "环境检查",
            message + "\n\n程序将继续运行，但部分功能可能受限。"
        )
    
    # 创建主窗口
    window = MainWindow()
    
    # 显示主窗口
    window.show()
    
    # 更新状态栏
    window.statusBar().showMessage(
        f"就绪 | yt-dlp 版本: {check_dependencies().get('yt-dlp', '未知')} | "
        f"下载路径: {settings.DEFAULT_DOWNLOAD_DIR}"
    )
    
    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
