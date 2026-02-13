# -*- coding: utf-8 -*-
"""
下载任务项控件 - 显示单个下载任务的进度
作者：小码酱
日期：2025-02-12
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.downloader import DownloadProgress, DownloadStatus

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.helpers import format_filesize, format_speed, format_eta


class DownloadItemWidget(QFrame):
    """
    下载任务项控件
    
    布局：
    ┌─────────────────────────────────────────────┐
    │  📹 视频标题                      [取消按钮] │
    │  ████████████░░░░░░░░░░  60%               │
    │  已下载: 50MB / 85MB  速度: 2.5MB/s  剩余: 14s │
    └─────────────────────────────────────────────┘
    """
    
    # 信号：取消下载
    cancel_requested = pyqtSignal()
    # 信号：重试下载
    retry_requested = pyqtSignal()
    
    def __init__(self, title: str, url: str):
        super().__init__()
        self.title = title
        self.url = url
        self._is_completed = False
        self._is_failed = False
        
        # 设置样式
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
            QFrame:hover {
                border-color: #3498db;
            }
        """)
        
        self._create_ui()
        
    def _create_ui(self):
        """创建 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        
        # 第一行：标题和取消按钮
        header_layout = QHBoxLayout()
        
        # 状态图标 + 标题
        self.status_icon = QLabel("⏳")
        self.status_icon.setFixedWidth(20)
        header_layout.addWidget(self.status_icon)
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-weight: bold;")
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label, stretch=1)
        
        # 取消按钮
        self.cancel_btn = QPushButton("✖")
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        header_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(header_layout)
        
        # 第二行：进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # 第三行：详细信息
        info_layout = QHBoxLayout()
        
        self.downloaded_label = QLabel("已下载: --")
        self.downloaded_label.setMinimumWidth(150)
        info_layout.addWidget(self.downloaded_label)
        
        self.speed_label = QLabel("速度: --")
        self.speed_label.setMinimumWidth(120)
        info_layout.addWidget(self.speed_label)
        
        self.eta_label = QLabel("剩余: --")
        self.eta_label.setMinimumWidth(80)
        info_layout.addWidget(self.eta_label)
        
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
    def _on_cancel_clicked(self):
        """取消/重试按钮点击"""
        if self._is_failed:
            self.retry_requested.emit()
        else:
            self.cancel_requested.emit()
    
    def update_progress(self, progress: DownloadProgress):
        """
        更新下载进度显示
        
        Args:
            progress: 下载进度数据
        """
        # 更新状态图标
        status_icons = {
            DownloadStatus.PENDING: "⏳",
            DownloadStatus.FETCHING: "🔍",
            DownloadStatus.DOWNLOADING: "⬇️",
            DownloadStatus.CONVERTING: "🔄",
            DownloadStatus.COMPLETED: "✅",
            DownloadStatus.FAILED: "❌",
            DownloadStatus.CANCELLED: "🚫"
        }
        self.status_icon.setText(status_icons.get(progress.status, "❓"))
        
        # 更新进度条
        self.progress_bar.setValue(int(progress.percentage))
        
        # 格式化并更新详细信息
        downloaded = format_filesize(progress.downloaded_bytes)
        total = format_filesize(progress.total_bytes)
        self.downloaded_label.setText(f"已下载: {downloaded} / {total}")
        
        # 更新速度
        if progress.speed > 0:
            speed_text = format_speed(progress.speed)
            self.speed_label.setText(f"速度: {speed_text}")
        else:
            self.speed_label.setText("速度: --")
        
        # 更新剩余时间
        if progress.eta > 0:
            eta_text = format_eta(progress.eta)
            self.eta_label.setText(f"剩余: {eta_text}")
        else:
            self.eta_label.setText("剩余: --")
        
        # 根据状态更新显示
        if progress.status == DownloadStatus.DOWNLOADING:
            self._update_downloading_style()
        elif progress.status == DownloadStatus.CONVERTING:
            self._update_converting_style()
    
    def _update_downloading_style(self):
        """更新下载中样式"""
        self.setStyleSheet("""
            QFrame {
                background-color: #e8f4fc;
                border: 1px solid #3498db;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
    
    def _update_converting_style(self):
        """更新转换中样式"""
        self.status_icon.setText("🔄")
        self.speed_label.setText("转换中...")
        self.eta_label.setText("请稍候...")
    
    def set_completed(self):
        """设置为完成状态"""
        self._is_completed = True
        self.progress_bar.setValue(100)
        self.status_icon.setText("✅")
        self.cancel_btn.hide()
        
        self.downloaded_label.setText("✅ 下载完成")
        self.speed_label.setText("")
        self.eta_label.setText("")
        
        # 更新样式为完成状态
        self.setStyleSheet("""
            QFrame {
                background-color: #d5f5e3;
                border: 1px solid #27ae60;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #27ae60;
                border-radius: 4px;
                text-align: center;
                background-color: #d5f5e3;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
    
    def set_failed(self, error_message: str = ""):
        """设置为失败状态"""
        self._is_failed = True
        self.status_icon.setText("❌")
        self.cancel_btn.setText("↻")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        
        # 更新样式为失败状态
        self.setStyleSheet("""
            QFrame {
                background-color: #fadbd8;
                border: 1px solid #e74c3c;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e74c3c;
                border-radius: 4px;
                text-align: center;
                background-color: #fadbd8;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
                border-radius: 3px;
            }
        """)
        
        if error_message:
            # 截断过长的错误信息
            display_error = error_message[:50] + "..." if len(error_message) > 50 else error_message
            self.downloaded_label.setText(f"❌ 错误: {display_error}")
            self.speed_label.setText("")
            self.eta_label.setText("点击重试")
    
    def set_cancelled(self):
        """设置为已取消状态"""
        self.status_icon.setText("🚫")
        self.cancel_btn.hide()
        
        self.downloaded_label.setText("已取消下载")
        self.speed_label.setText("")
        self.eta_label.setText("")
        
        self.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #95a5a6;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)
    
    @property
    def is_active(self) -> bool:
        """是否处于活跃状态（下载中或等待中）"""
        return not (self._is_completed or self._is_failed)
