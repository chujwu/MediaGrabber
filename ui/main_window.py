# -*- coding: utf-8 -*-
"""
主窗口 UI 模块 - YouTube 视频下载器主界面
作者：小码酱
日期：2025-02-12
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QGroupBox, QProgressBar, QCheckBox, QFileDialog,
    QMessageBox, QTabWidget, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from typing import Optional, List, Dict
import traceback

# 导入核心模块和配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings
from core.downloader import VideoDownloader, VideoInfo, DownloadProgress, DownloadStatus
from core.format_utils import FormatConverter
from ui.widgets.download_item import DownloadItemWidget
from utils.helpers import format_duration, open_folder, is_valid_url, extract_urls_from_text, get_system_proxy, get_proxy_for_yt_dlp
from utils.cookies_manager import CookiesManager


class FetchInfoThread(QThread):
    """获取视频信息的线程"""
    
    info_ready = pyqtSignal(object)  # VideoInfo
    info_failed = pyqtSignal(str)    # 错误消息
    
    def __init__(self, downloader: VideoDownloader, url: str):
        super().__init__()
        self.downloader = downloader
        self.url = url
    
    def run(self):
        try:
            info = self.downloader.fetch_video_info(self.url)
            if info:
                self.info_ready.emit(info)
            else:
                self.info_failed.emit("无法获取视频信息，请检查 URL 是否正确")
        except Exception as e:
            self.info_failed.emit(str(e))


class DownloadThread(QThread):
    """下载线程 - 在后台执行下载任务"""
    
    # 信号定义
    progress_signal = pyqtSignal(object)  # 进度更新信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号（成功/失败，消息）
    
    def __init__(self, downloader: VideoDownloader, url: str, options: dict):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.options = options
        self._is_cancelled = False
    
    def run(self):
        """执行下载任务"""
        try:
            # 设置进度回调，将信号发送到主线程
            def progress_callback(progress: DownloadProgress):
                if not self._is_cancelled:
                    self.progress_signal.emit(progress)
            
            # 更新下载器的回调
            self.downloader.progress_callback = progress_callback
            
            # 执行下载
            success = self.downloader.download(
                url=self.url,
                quality=self.options.get('quality', 'best'),
                format_type=self.options.get('format_type', 'video'),
                audio_format=self.options.get('audio_format', 'mp3'),
                subtitle_option=self.options.get('subtitle_option', 'none')
            )
            
            if success:
                self.finished_signal.emit(True, "下载完成")
            else:
                self.finished_signal.emit(False, "下载失败")
                
        except Exception as e:
            error_msg = str(e)
            if "cancelled" in error_msg.lower():
                self.finished_signal.emit(False, "下载已取消")
            else:
                self.finished_signal.emit(False, error_msg)
    
    def cancel(self):
        """取消下载"""
        self._is_cancelled = True
        self.downloader.stop()


class BatchDownloadDialog(QDialog):
    """批量下载对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量下载")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 说明文字
        label = QLabel("请输入要下载的视频 URL（每行一个）:")
        layout.addWidget(label)
        
        # URL 输入区域
        self.url_text = QTextEdit()
        self.url_text.setPlaceholderText(
            "https://www.youtube.com/watch?v=xxxxx\n"
            "https://www.bilibili.com/video/BVxxxxx\n"
            "..."
        )
        layout.addWidget(self.url_text)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_urls(self) -> List[str]:
        """获取输入的 URL 列表"""
        text = self.url_text.toPlainText()
        # 提取所有 URL
        urls = extract_urls_from_text(text)
        return urls


class MainWindow(QMainWindow):
    """
    主窗口类 - YouTube 视频下载器主界面
    """
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.current_video_info: Optional[VideoInfo] = None
        self.download_threads: List[DownloadThread] = []
        self.download_items: Dict[str, DownloadItemWidget] = {}  # url -> widget
        self.fetch_info_thread: Optional[FetchInfoThread] = None
        
        # 网络管理器（用于下载缩略图）
        self.network_manager = QNetworkAccessManager(self)
        
        # 初始化下载器
        self.downloader = VideoDownloader(
            output_dir=str(settings.DEFAULT_DOWNLOAD_DIR),
            proxy=settings.PROXY_URL if settings.PROXY_ENABLED else None
        )
        
        # 设置窗口
        self._setup_window()
        
        # 创建 UI
        self._create_ui()
        
        # 应用样式
        self.setStyleSheet(settings.STYLESHEET)
        
    def _setup_window(self):
        """设置窗口基本属性"""
        self.setWindowTitle(settings.WINDOW_TITLE)
        self.setMinimumSize(settings.WINDOW_MIN_WIDTH, settings.WINDOW_MIN_HEIGHT)
        self.resize(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
        
    def _create_ui(self):
        """创建 UI 界面"""
        # 主控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ========== URL 输入区域 ==========
        url_group = self._create_url_input_group()
        main_layout.addWidget(url_group)
        
        # ========== 信息和选项区域 ==========
        info_options_layout = QHBoxLayout()
        
        # 视频信息区域
        info_group = self._create_video_info_group()
        info_options_layout.addWidget(info_group)
        
        # 下载选项区域
        options_group = self._create_download_options_group()
        info_options_layout.addWidget(options_group)
        
        main_layout.addLayout(info_options_layout)
        
        # ========== 下载列表区域 ==========
        download_list_group = self._create_download_list_group()
        main_layout.addWidget(download_list_group)
        
        # ========== 状态栏 ==========
        self.statusBar().showMessage("就绪 - 请输入视频 URL 开始下载")
        
    def _create_url_input_group(self) -> QGroupBox:
        """创建 URL 输入区域"""
        group = QGroupBox("📥 输入视频 URL")
        layout = QHBoxLayout(group)
        
        # URL 输入框
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴 YouTube、B站或其他支持平台的视频链接...")
        self.url_input.setMinimumWidth(400)
        self.url_input.returnPressed.connect(self._on_fetch_info_clicked)
        layout.addWidget(self.url_input, stretch=1)
        
        # 获取信息按钮
        self.fetch_info_btn = QPushButton("🔍 获取信息")
        self.fetch_info_btn.clicked.connect(self._on_fetch_info_clicked)
        layout.addWidget(self.fetch_info_btn)
        
        # 下载按钮
        self.download_btn = QPushButton("⬇️ 开始下载")
        self.download_btn.clicked.connect(self._on_download_clicked)
        self.download_btn.setEnabled(False)
        layout.addWidget(self.download_btn)
        
        # 批量下载按钮
        self.batch_download_btn = QPushButton("📋 批量下载")
        self.batch_download_btn.clicked.connect(self._on_batch_download_clicked)
        layout.addWidget(self.batch_download_btn)
        
        return group
    
    def _create_video_info_group(self) -> QGroupBox:
        """创建视频信息展示区域"""
        group = QGroupBox("📺 视频信息")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 缩略图标签
        self.thumbnail_label = QLabel("暂无视频信息")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumSize(320, 180)
        self.thumbnail_label.setMaximumSize(320, 180)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.thumbnail_label, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # 信息容器
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        # 标题标签
        self.title_label = QLabel("标题: -")
        self.title_label.setWordWrap(True)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self.title_label)
        
        # 时长标签
        self.duration_label = QLabel("时长: -")
        info_layout.addWidget(self.duration_label)
        
        # 上传者标签
        self.uploader_label = QLabel("上传者: -")
        info_layout.addWidget(self.uploader_label)
        
        # 观看次数标签
        self.views_label = QLabel("观看次数: -")
        info_layout.addWidget(self.views_label)
        
        layout.addWidget(info_widget)
        layout.addStretch()
        return group
    
    def _create_download_options_group(self) -> QGroupBox:
        """创建下载选项区域"""
        group = QGroupBox("⚙️ 下载选项")
        main_layout = QVBoxLayout(group)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 15, 10, 10)
        
        # ========== 基本下载选项 ==========
        # 下载类型选择（视频/音频）
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("下载类型:"))
        self.format_type_combo = QComboBox()
        self.format_type_combo.addItems(["视频", "仅音频"])
        self.format_type_combo.currentIndexChanged.connect(self._on_format_type_changed)
        type_layout.addWidget(self.format_type_combo)
        type_layout.addStretch()
        main_layout.addLayout(type_layout)
        
        # 视频质量选择
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("视频质量:"))
        self.quality_combo = QComboBox()
        for opt in settings.VIDEO_QUALITY_OPTIONS:
            self.quality_combo.addItem(opt["label"], opt["id"])
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        main_layout.addLayout(quality_layout)
        
        # 音频格式选择
        audio_format_layout = QHBoxLayout()
        audio_format_layout.addWidget(QLabel("音频格式:"))
        self.audio_format_combo = QComboBox()
        for opt in settings.AUDIO_FORMAT_OPTIONS:
            self.audio_format_combo.addItem(opt["label"], opt["id"])
        audio_format_layout.addWidget(self.audio_format_combo)
        audio_format_layout.addStretch()
        main_layout.addLayout(audio_format_layout)
        
        # 字幕选项
        subtitle_layout = QHBoxLayout()
        subtitle_layout.addWidget(QLabel("字幕下载:"))
        self.subtitle_combo = QComboBox()
        for opt in settings.SUBTITLE_OPTIONS:
            self.subtitle_combo.addItem(opt["label"], opt["id"])
        subtitle_layout.addWidget(self.subtitle_combo)
        subtitle_layout.addStretch()
        main_layout.addLayout(subtitle_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # ========== 代理设置区域（简化版）==========
        proxy_section = QVBoxLayout()
        proxy_section.setSpacing(10)
        
        # 标题
        proxy_title = QLabel("🌐 网络代理设置")
        proxy_title.setStyleSheet("font-weight: bold; color: #2980b9; font-size: 11px;")
        proxy_title.setMinimumHeight(20)
        proxy_section.addWidget(proxy_title)
        
        # 代理模式选择（单选框）
        self.proxy_mode_group = QWidget()
        proxy_mode_layout = QVBoxLayout(self.proxy_mode_group)
        proxy_mode_layout.setContentsMargins(0, 0, 0, 0)
        proxy_mode_layout.setSpacing(8)
        
        # 选项1: 不使用代理
        self.no_proxy_radio = QCheckBox("不使用代理")
        self.no_proxy_radio.setChecked(False)
        self.no_proxy_radio.setMinimumHeight(22)
        self.no_proxy_radio.stateChanged.connect(self._on_proxy_mode_changed)
        proxy_mode_layout.addWidget(self.no_proxy_radio)
        
        # 选项2: 使用系统代理
        self.system_proxy_radio = QCheckBox("使用系统代理（自动检测）")
        self.system_proxy_radio.setChecked(True)  # 默认选中
        self.system_proxy_radio.setMinimumHeight(22)
        self.system_proxy_radio.stateChanged.connect(self._on_proxy_mode_changed)
        proxy_mode_layout.addWidget(self.system_proxy_radio)
        
        # 选项3: 使用自定义代理
        self.custom_proxy_radio = QCheckBox("使用自定义代理")
        self.custom_proxy_radio.setChecked(False)
        self.custom_proxy_radio.setMinimumHeight(22)
        self.custom_proxy_radio.stateChanged.connect(self._on_proxy_mode_changed)
        proxy_mode_layout.addWidget(self.custom_proxy_radio)
        
        proxy_section.addWidget(self.proxy_mode_group)
        
        # 代理状态显示
        self.proxy_status_label = QLabel("")
        self.proxy_status_label.setStyleSheet(
            "color: #7f8c8d; font-size: 11px; padding: 6px 8px; "
            "background-color: #ecf0f1; border-radius: 3px;"
        )
        self.proxy_status_label.setWordWrap(True)
        self.proxy_status_label.setMinimumHeight(24)
        proxy_section.addWidget(self.proxy_status_label)
        
        # 自定义代理输入区域
        custom_proxy_widget = QWidget()
        custom_proxy_layout = QHBoxLayout(custom_proxy_widget)
        custom_proxy_layout.setContentsMargins(20, 0, 0, 0)  # 左侧缩进
        custom_proxy_layout.setSpacing(6)
        
        custom_proxy_layout.addWidget(QLabel("地址:"))
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setPlaceholderText("socks5://127.0.0.1:7890 或 http://127.0.0.1:7890")
        self.proxy_url_input.setToolTip("支持 SOCKS5 和 HTTP 代理")
        self.proxy_url_input.setEnabled(False)
        custom_proxy_layout.addWidget(self.proxy_url_input, stretch=1)
        
        # 测试代理按钮
        self.test_proxy_btn = QPushButton("测试连接")
        self.test_proxy_btn.setFixedWidth(80)
        self.test_proxy_btn.setEnabled(False)
        self.test_proxy_btn.clicked.connect(self._on_test_proxy)
        custom_proxy_layout.addWidget(self.test_proxy_btn)
        
        proxy_section.addWidget(custom_proxy_widget)
        
        main_layout.addLayout(proxy_section)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator2)
        
        # ========== Cookies 设置 ==========
        cookies_section = QVBoxLayout()
        cookies_section.setSpacing(6)
        
        # 标题
        cookies_title = QLabel("🍪 Cookies 设置（YouTube 认证）")
        cookies_title.setStyleSheet("font-weight: bold; color: #2980b9; font-size: 11px;")
        cookies_section.addWidget(cookies_title)
        
        # Cookies 状态
        self.cookies_status_label = QLabel("")
        self.cookies_status_label.setStyleSheet(
            "color: #7f8c8d; font-size: 11px; padding: 4px; "
            "background-color: #ecf0f1; border-radius: 3px;"
        )
        self.cookies_status_label.setWordWrap(True)
        cookies_section.addWidget(self.cookies_status_label)
        
        # Cookies 操作按钮
        cookies_btn_layout = QHBoxLayout()
        cookies_btn_layout.setSpacing(6)
        
        self.view_cookies_btn = QPushButton("📄 查看")
        self.view_cookies_btn.setToolTip("查看已保存的 Cookies")
        self.view_cookies_btn.clicked.connect(self._on_view_cookies)
        cookies_btn_layout.addWidget(self.view_cookies_btn)
        
        self.import_cookies_btn = QPushButton("📥 导入")
        self.import_cookies_btn.setToolTip("从浏览器导出的 Cookies 导入")
        self.import_cookies_btn.clicked.connect(self._on_import_cookies)
        cookies_btn_layout.addWidget(self.import_cookies_btn)
        
        self.clear_cookies_btn = QPushButton("🗑️ 清除")
        self.clear_cookies_btn.setToolTip("删除已保存的 Cookies")
        self.clear_cookies_btn.clicked.connect(self._on_clear_cookies)
        cookies_btn_layout.addWidget(self.clear_cookies_btn)
        
        cookies_btn_layout.addStretch()
        cookies_section.addLayout(cookies_btn_layout)
        
        main_layout.addLayout(cookies_section)
        
        # 分隔线
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator3)
        
        # ========== 输出路径 ==========
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("保存路径:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setText(str(settings.DEFAULT_DOWNLOAD_DIR))
        self.output_path_edit.setReadOnly(True)
        output_layout.addWidget(self.output_path_edit, stretch=1)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._on_browse_output_path)
        output_layout.addWidget(browse_btn)
        main_layout.addLayout(output_layout)
        
        # 初始化设置
        QTimer.singleShot(100, self._init_proxy_settings)
        QTimer.singleShot(200, self._init_cookies_status)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        return group
    
    def _create_download_list_group(self) -> QGroupBox:
        """创建下载列表区域"""
        group = QGroupBox("📥 下载任务列表")
        layout = QVBoxLayout(group)
        
        # 下载任务列表
        self.download_list = QListWidget()
        self.download_list.setMinimumHeight(200)
        self.download_list.setSpacing(5)
        layout.addWidget(self.download_list)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        clear_completed_btn = QPushButton("清除已完成")
        clear_completed_btn.clicked.connect(self._on_clear_completed)
        btn_layout.addWidget(clear_completed_btn)
        
        cancel_all_btn = QPushButton("取消全部")
        cancel_all_btn.clicked.connect(self._on_cancel_all)
        btn_layout.addWidget(cancel_all_btn)
        
        btn_layout.addStretch()
        
        open_folder_btn = QPushButton("打开下载文件夹")
        open_folder_btn.clicked.connect(self._on_open_download_folder)
        btn_layout.addWidget(open_folder_btn)
        
        layout.addLayout(btn_layout)
        return group
    
    # ==================== 事件处理方法 ====================
    
    def _on_fetch_info_clicked(self):
        """获取视频信息按钮点击事件"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "提示", "请输入视频 URL！")
            return
        
        if not is_valid_url(url):
            QMessageBox.warning(self, "提示", "请输入有效的视频 URL！")
            return
        
        # 禁用按钮，显示加载状态
        self.fetch_info_btn.setEnabled(False)
        self.fetch_info_btn.setText("获取中...")
        self.thumbnail_label.setText("正在获取视频信息...")
        self.statusBar().showMessage(f"正在获取: {url}")
        
        # 创建并启动获取信息线程
        self.fetch_info_thread = FetchInfoThread(self.downloader, url)
        self.fetch_info_thread.info_ready.connect(self._on_info_ready)
        self.fetch_info_thread.info_failed.connect(self._on_info_failed)
        self.fetch_info_thread.finished.connect(self._on_fetch_finished)
        self.fetch_info_thread.start()
    
    def _on_info_ready(self, info: VideoInfo):
        """视频信息获取成功"""
        self.current_video_info = info
        
        # 更新显示
        self.title_label.setText(f"标题: {info.title}")
        self.duration_label.setText(f"时长: {format_duration(info.duration)}")
        self.uploader_label.setText(f"上传者: {info.uploader}")
        
        views_text = f"{info.view_count:,}" if info.view_count > 0 else "未知"
        self.views_label.setText(f"观看次数: {views_text}")
        
        # 下载并显示缩略图
        if info.thumbnail:
            self._load_thumbnail(info.thumbnail)
        else:
            self.thumbnail_label.setText("🎬 无缩略图")
        
        # 启用下载按钮
        self.download_btn.setEnabled(True)
        
        self.statusBar().showMessage(f"就绪 - {info.title}")
    
    def _on_info_failed(self, error: str):
        """视频信息获取失败"""
        self.thumbnail_label.setText("❌ 获取失败")
        QMessageBox.warning(self, "获取失败", f"无法获取视频信息:\n{error}")
        self.statusBar().showMessage("获取失败")
    
    def _on_fetch_finished(self):
        """获取信息线程结束"""
        self.fetch_info_btn.setEnabled(True)
        self.fetch_info_btn.setText("🔍 获取信息")
    
    def _load_thumbnail(self, url: str):
        """加载缩略图（支持系统代理和自定义代理）"""
        try:
            # 如果启用了代理，使用 requests 库加载
            if self.proxy_checkbox.isChecked():
                import requests
                
                # 确定使用的代理
                if self.use_custom_proxy_checkbox.isChecked():
                    proxy_url = self.proxy_url_input.text().strip()
                else:
                    proxy_url = get_proxy_for_yt_dlp()
                
                proxies = None
                if proxy_url:
                    proxies = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                
                # 在后台线程加载
                import threading
                def load_with_proxy():
                    try:
                        response = requests.get(
                            url, 
                            proxies=proxies, 
                            timeout=15,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        )
                        if response.status_code == 200:
                            data = response.content
                            QTimer.singleShot(0, lambda: self._set_thumbnail_data(data))
                        else:
                            QTimer.singleShot(0, lambda: self.thumbnail_label.setText("🎬 缩略图加载失败"))
                    except Exception as e:
                        QTimer.singleShot(0, lambda: self.thumbnail_label.setText("🎬 缩略图加载失败"))
                
                thread = threading.Thread(target=load_with_proxy, daemon=True)
                thread.start()
            else:
                # 不使用代理，直接用 Qt 网络库
                request = QNetworkRequest()
                request.setUrl(url)
                request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, 
                                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                reply = self.network_manager.get(request)
                reply.finished.connect(lambda: self._on_thumbnail_loaded(reply))
        except Exception as e:
            self.thumbnail_label.setText("🎬 缩略图加载失败")
    
    def _set_thumbnail_data(self, data: bytes):
        """设置缩略图数据"""
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            if pixmap.isNull():
                self.thumbnail_label.setText("🎬 缩略图格式错误")
                return
            
            # 缩放到合适大小
            scaled = pixmap.scaled(
                320, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled)
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
        except Exception as e:
            self.thumbnail_label.setText("🎬 缩略图显示失败")
    
    def _on_thumbnail_loaded(self, reply):
        """缩略图加载完成"""
        try:
            if reply.error() == reply.NetworkError.NoError:
                data = reply.readAll()
                pixmap = QPixmap()
                pixmap.loadFromData(data.data())
                
                # 检查图片是否有效
                if pixmap.isNull():
                    self.thumbnail_label.setText("🎬 缩略图格式错误")
                    return
                
                # 缩放到合适大小
                scaled = pixmap.scaled(
                    320, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail_label.setPixmap(scaled)
                self.thumbnail_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                    }
                """)
            else:
                error_msg = reply.errorString()
                self.thumbnail_label.setText(f"🎬 缩略图加载失败\n({error_msg})")
        except Exception as e:
            self.thumbnail_label.setText("🎬 缩略图处理失败")
        finally:
            reply.deleteLater()
    
    def _on_download_clicked(self):
        """开始下载按钮点击事件"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "提示", "请输入视频 URL！")
            return
        
        # 如果没有获取过视频信息，先获取
        if not self.current_video_info or self.current_video_info.url != url:
            # 获取信息后再下载
            self._on_fetch_info_clicked()
            # 延迟启动下载
            QTimer.singleShot(500, lambda: self._start_download(url))
        else:
            self._start_download(url)
    
    def _start_download(self, url: str):
        """启动下载任务"""
        # 获取下载选项
        quality = self.quality_combo.currentData()
        format_type = "video" if self.format_type_combo.currentIndex() == 0 else "audio"
        audio_format = self.audio_format_combo.currentData()
        subtitle_option = self.subtitle_combo.currentData()
        
        options = {
            'quality': quality,
            'format_type': format_type,
            'audio_format': audio_format,
            'subtitle_option': subtitle_option
        }
        
        # 创建下载项
        title = self.current_video_info.title if self.current_video_info else url
        download_item = DownloadItemWidget(title, url)
        download_item.cancel_requested.connect(lambda: self._cancel_download(url))
        
        # 添加到列表
        list_item = QListWidgetItem()
        list_item.setSizeHint(download_item.sizeHint())
        self.download_list.addItem(list_item)
        self.download_list.setItemWidget(list_item, download_item)
        self.download_items[url] = download_item
        
        # 创建并启动下载线程
        thread = DownloadThread(
            downloader=VideoDownloader(
                output_dir=str(self.downloader.output_dir),
                proxy=self.downloader.proxy,
                cookies_file=self.downloader.cookies_file
            ),
            url=url,
            options=options
        )
        thread.progress_signal.connect(lambda p, u=url: self._on_download_progress(u, p))
        thread.finished_signal.connect(lambda s, m, u=url: self._on_download_finished(u, s, m))
        thread.start()
        
        self.download_threads.append(thread)
        self.statusBar().showMessage(f"开始下载: {title}")
    
    def _on_download_progress(self, url: str, progress: DownloadProgress):
        """下载进度更新"""
        if url in self.download_items:
            self.download_items[url].update_progress(progress)
            
            # 更新状态栏
            if progress.status == DownloadStatus.DOWNLOADING:
                self.statusBar().showMessage(
                    f"下载中: {progress.percentage:.1f}% - {progress.downloaded_bytes}/{progress.total_bytes}"
                )
    
    def _on_download_finished(self, url: str, success: bool, message: str):
        """下载完成"""
        if url in self.download_items:
            item = self.download_items[url]
            if success:
                item.set_completed()
                self.statusBar().showMessage("下载完成！")
            else:
                item.set_failed(message)
                self.statusBar().showMessage(f"下载失败: {message}")
    
    def _cancel_download(self, url: str):
        """取消下载"""
        # 找到对应的线程并取消
        for thread in self.download_threads:
            if hasattr(thread, 'url') and thread.url == url:
                thread.cancel()
                break
        
        if url in self.download_items:
            self.download_items[url].set_cancelled()
    
    def _on_batch_download_clicked(self):
        """批量下载按钮点击事件"""
        dialog = BatchDownloadDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            urls = dialog.get_urls()
            
            if not urls:
                QMessageBox.warning(self, "提示", "没有找到有效的 URL！")
                return
            
            # 获取下载选项
            quality = self.quality_combo.currentData()
            format_type = "video" if self.format_type_combo.currentIndex() == 0 else "audio"
            audio_format = self.audio_format_combo.currentData()
            subtitle_option = self.subtitle_combo.currentData()
            
            options = {
                'quality': quality,
                'format_type': format_type,
                'audio_format': audio_format,
                'subtitle_option': subtitle_option
            }
            
            # 批量添加下载任务
            for url in urls[:10]:  # 限制最多10个
                self._start_download_with_options(url, options)
            
            self.statusBar().showMessage(f"已添加 {len(urls[:10])} 个下载任务")
    
    def _start_download_with_options(self, url: str, options: dict):
        """使用指定选项启动下载"""
        # 创建下载项
        download_item = DownloadItemWidget(url, url)
        download_item.cancel_requested.connect(lambda: self._cancel_download(url))
        
        # 添加到列表
        list_item = QListWidgetItem()
        list_item.setSizeHint(download_item.sizeHint())
        self.download_list.addItem(list_item)
        self.download_list.setItemWidget(list_item, download_item)
        self.download_items[url] = download_item
        
        # 创建并启动下载线程
        thread = DownloadThread(
            downloader=VideoDownloader(
                output_dir=str(self.downloader.output_dir),
                proxy=self.downloader.proxy,
                cookies_file=self.downloader.cookies_file
            ),
            url=url,
            options=options
        )
        thread.progress_signal.connect(lambda p, u=url: self._on_download_progress(u, p))
        thread.finished_signal.connect(lambda s, m, u=url: self._on_download_finished(u, s, m))
        thread.start()
        
        self.download_threads.append(thread)
    
    def _on_format_type_changed(self, index: int):
        """下载类型改变事件"""
        is_video = index == 0
        
        self.quality_combo.setEnabled(is_video)
        self.audio_format_combo.setEnabled(not is_video)
    
    def _init_proxy_settings(self):
        """初始化代理设置"""
        # 获取系统代理
        system_proxy = get_proxy_for_yt_dlp()
        
        # 更新状态显示
        if system_proxy:
            self.proxy_status_label.setText(f"✓ 已检测到系统代理: {system_proxy}")
            self.proxy_status_label.setStyleSheet(
                "color: #27ae60; font-size: 11px; padding: 4px; "
                "background-color: #d4edda; border-radius: 3px;"
            )
        else:
            self.proxy_status_label.setText("⚠ 未检测到系统代理设置，如需访问外网请使用自定义代理")
            self.proxy_status_label.setStyleSheet(
                "color: #856404; font-size: 11px; padding: 4px; "
                "background-color: #fff3cd; border-radius: 3px;"
            )
        
        # 设置初始代理
        if self.system_proxy_radio.isChecked() and system_proxy:
            self.downloader.proxy = system_proxy
    
    def _on_proxy_mode_changed(self, state: int):
        """代理模式改变 - 实现单选效果"""
        sender = self.sender()
        checked = state == Qt.CheckState.Checked.value
        
        # 实现单选效果：取消其他选项
        if checked:
            if sender == self.no_proxy_radio:
                self.system_proxy_radio.setChecked(False)
                self.custom_proxy_radio.setChecked(False)
                self._apply_no_proxy()
            elif sender == self.system_proxy_radio:
                self.no_proxy_radio.setChecked(False)
                self.custom_proxy_radio.setChecked(False)
                self._apply_system_proxy()
            elif sender == self.custom_proxy_radio:
                self.no_proxy_radio.setChecked(False)
                self.system_proxy_radio.setChecked(False)
                self._apply_custom_proxy()
    
    def _apply_no_proxy(self):
        """应用不使用代理"""
        self.downloader.proxy = None
        self.proxy_url_input.setEnabled(False)
        self.test_proxy_btn.setEnabled(False)
        
        self.proxy_status_label.setText("✓ 已禁用代理（直连模式）")
        self.proxy_status_label.setStyleSheet(
            "color: #6c757d; font-size: 11px; padding: 4px; "
            "background-color: #e2e3e5; border-radius: 3px;"
        )
        
        self.statusBar().showMessage("代理已禁用")
    
    def _apply_system_proxy(self):
        """应用系统代理"""
        system_proxy = get_proxy_for_yt_dlp()
        self.proxy_url_input.setEnabled(False)
        self.test_proxy_btn.setEnabled(False)
        
        if system_proxy:
            self.downloader.proxy = system_proxy
            self.proxy_status_label.setText(f"✓ 使用系统代理: {system_proxy}")
            self.proxy_status_label.setStyleSheet(
                "color: #27ae60; font-size: 11px; padding: 4px; "
                "background-color: #d4edda; border-radius: 3px;"
            )
            self.statusBar().showMessage(f"已启用系统代理: {system_proxy}")
        else:
            self.downloader.proxy = None
            self.proxy_status_label.setText("❌ 未检测到系统代理，请使用自定义代理")
            self.proxy_status_label.setStyleSheet(
                "color: #dc3545; font-size: 11px; padding: 4px; "
                "background-color: #f8d7da; border-radius: 3px;"
            )
            self.statusBar().showMessage("未检测到系统代理")
    
    def _apply_custom_proxy(self):
        """应用自定义代理"""
        self.proxy_url_input.setEnabled(True)
        self.test_proxy_btn.setEnabled(True)
        
        proxy_url = self.proxy_url_input.text().strip()
        
        if proxy_url:
            self.downloader.proxy = proxy_url
            self.proxy_status_label.setText(f"✓ 使用自定义代理: {proxy_url}")
            self.proxy_status_label.setStyleSheet(
                "color: #27ae60; font-size: 11px; padding: 4px; "
                "background-color: #d4edda; border-radius: 3px;"
            )
            self.statusBar().showMessage(f"已启用自定义代理: {proxy_url}")
        else:
            self.proxy_status_label.setText("⚠ 请输入代理地址")
            self.proxy_status_label.setStyleSheet(
                "color: #856404; font-size: 11px; padding: 4px; "
                "background-color: #fff3cd; border-radius: 3px;"
            )
            self.statusBar().showMessage("请输入自定义代理地址")
    
    def _on_test_proxy(self):
        """测试代理连接"""
        proxy_url = self.proxy_url_input.text().strip()
        
        if not proxy_url:
            self.proxy_status_label.setText("❌ 请输入代理地址")
            self.proxy_status_label.setStyleSheet(
                "color: #dc3545; font-size: 11px; padding: 4px; "
                "background-color: #f8d7da; border-radius: 3px;"
            )
            return
        
        # 禁用按钮，显示测试中
        self.test_proxy_btn.setEnabled(False)
        self.test_proxy_btn.setText("测试中...")
        self.proxy_status_label.setText("⏳ 正在测试代理连接...")
        self.proxy_status_label.setStyleSheet(
            "color: #004085; font-size: 11px; padding: 4px; "
            "background-color: #cce5ff; border-radius: 3px;"
        )
        
        # 在后台线程测试代理
        import threading
        
        def test_connection():
            try:
                import requests
                
                # 构建代理字典
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                
                # 测试 URL 列表
                test_urls = [
                    'https://www.google.com/generate_204',
                    'https://www.youtube.com/favicon.ico',
                    'https://api.ipify.org?format=json'
                ]
                
                last_error = None
                for test_url in test_urls:
                    try:
                        response = requests.get(
                            test_url,
                            proxies=proxies,
                            timeout=10,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        )
                        
                        # 检查响应状态
                        if response.status_code in [200, 204]:
                            QTimer.singleShot(0, lambda: self._on_proxy_test_success(proxy_url))
                            return
                    except requests.exceptions.ProxyError as e:
                        last_error = f"代理错误"
                    except requests.exceptions.ConnectTimeout:
                        last_error = "连接超时"
                    except requests.exceptions.SSLError as e:
                        last_error = "SSL错误"
                    except Exception as e:
                        last_error = str(e)[:30]
                
                # 所有测试都失败
                error_msg = last_error if last_error else "无法连接"
                QTimer.singleShot(0, lambda: self._on_proxy_test_failed(error_msg))
                
            except ImportError:
                QTimer.singleShot(0, lambda: self._on_proxy_test_failed("缺少 requests 库"))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_proxy_test_failed(str(e)[:30]))
        
        # 启动测试线程
        thread = threading.Thread(target=test_connection, daemon=True)
        thread.start()
    
    def _on_proxy_test_success(self, proxy_url: str):
        """代理测试成功"""
        self.test_proxy_btn.setEnabled(True)
        self.test_proxy_btn.setText("测试连接")
        
        self.proxy_status_label.setText(f"✓ 代理连接成功！")
        self.proxy_status_label.setStyleSheet(
            "color: #155724; font-size: 11px; padding: 4px; "
            "background-color: #d4edda; border-radius: 3px;"
        )
        
        # 自动应用代理
        self.downloader.proxy = proxy_url
        self.statusBar().showMessage("代理测试成功！")
        
        QMessageBox.information(
            self, 
            "测试成功", 
            f"代理连接成功！\n\n代理地址: {proxy_url}\n\n可以使用此代理下载视频了。"
        )
    
    def _on_proxy_test_failed(self, error: str):
        """代理测试失败"""
        self.test_proxy_btn.setEnabled(True)
        self.test_proxy_btn.setText("测试连接")
        
        self.proxy_status_label.setText(f"❌ 代理连接失败: {error}")
        self.proxy_status_label.setStyleSheet(
            "color: #721c24; font-size: 11px; padding: 4px; "
            "background-color: #f8d7da; border-radius: 3px;"
        )
        
        self.statusBar().showMessage(f"代理测试失败: {error}")
        
        QMessageBox.warning(
            self, 
            "测试失败", 
            f"代理连接失败！\n\n错误: {error}\n\n请检查代理地址是否正确。"
        )
    
    def _init_cookies_status(self):
        """初始化 Cookies 状态"""
        cookies_file = CookiesManager.get_cookies_file_path()
        
        if cookies_file.exists():
            # 加载并统计 Cookies 数量
            cookies = CookiesManager.load_cookies_file()
            if cookies:
                self.cookies_status_label.setText(
                    f"✓ 已加载 {len(cookies)} 个 Cookies (文件: {cookies_file.name})"
                )
                self.cookies_status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
                
                # 更新下载器使用 Cookies
                self.downloader.cookies_file = str(cookies_file)
            else:
                self.cookies_status_label.setText("⚠ Cookies 文件存在但格式错误")
                self.cookies_status_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        else:
            self.cookies_status_label.setText("⚠ 未找到 Cookies 文件（如需下载 YouTube 视频，请先导入 Cookies）")
            self.cookies_status_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
    
    def _on_view_cookies(self):
        """查看当前 Cookies"""
        cookies = CookiesManager.load_cookies_file()
        
        if not cookies:
            QMessageBox.information(
                self, 
                "Cookies 信息", 
                "当前没有保存的 Cookies。\n\n"
                "请点击「导入 Cookies」按钮，从浏览器导出的 Cookies 文件中导入。"
            )
            return
        
        # 显示 Cookies 信息
        info_lines = [f"共有 {len(cookies)} 个 Cookies:\n"]
        
        # 按 domain 分组
        domains = {}
        for cookie in cookies:
            if cookie.domain not in domains:
                domains[cookie.domain] = []
            domains[cookie.domain].append(cookie)
        
        for domain, domain_cookies in domains.items():
            info_lines.append(f"\n📦 {domain}:")
            for cookie in domain_cookies:
                info_lines.append(f"  • {cookie.name}: {cookie.value[:20]}...")
        
        info_text = '\n'.join(info_lines)
        
        # 创建对话框显示
        dialog = QDialog(self)
        dialog.setWindowTitle("Cookies 详情")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(info_text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def _on_import_cookies(self):
        """导入 Cookies"""
        # 创建导入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("导入 YouTube Cookies")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(dialog)
        
        # 说明文字
        help_label = QLabel(
            "📥 请将浏览器导出的 Cookies 内容粘贴到下方文本框中：\n\n"
            "💡 导出方法（推荐使用浏览器扩展）：\n"
            "1. 安装 Chrome/Edge 扩展: \"Get cookies.txt LOCALLY\"\n"
            "2. 访问 youtube.com 并登录\n"
            "3. 点击扩展图标，选择 \"Export\" 导出\n"
            "4. 将导出的内容粘贴到下方"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #2980b9; padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        layout.addWidget(help_label)
        
        # Cookies 输入框
        cookies_input = QTextEdit()
        cookies_input.setPlaceholderText(
            "粘贴浏览器导出的 Cookies 内容...\n\n"
            "支持格式：\n"
            "1. 表格格式（制表符分隔）：name\tvalue\tdomain\tpath\texpires\t...\n"
            "2. Netscape cookies.txt 格式"
        )
        layout.addWidget(cookies_input)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cookies_text = cookies_input.toPlainText().strip()
            
            if not cookies_text:
                QMessageBox.warning(self, "提示", "请粘贴 Cookies 内容！")
                return
            
            # 解析 Cookies
            try:
                # 判断格式类型
                if cookies_text.startswith('# Netscape') or '\tTRUE\t' in cookies_text or '\tFALSE\t' in cookies_text:
                    # Netscape 格式
                    cookies = CookiesManager.parse_netscape_format(cookies_text)
                else:
                    # 浏览器导出的表格格式
                    cookies = CookiesManager.parse_browser_export(cookies_text)
                
                if not cookies:
                    QMessageBox.warning(
                        self, 
                        "解析失败", 
                        "无法解析 Cookies 内容，请检查格式是否正确！"
                    )
                    return
                
                # 过滤只保留 youtube.com 的 Cookies
                youtube_cookies = [
                    c for c in cookies 
                    if 'youtube.com' in c.domain
                ]
                
                if not youtube_cookies:
                    QMessageBox.warning(
                        self, 
                        "提示", 
                        "未找到 youtube.com 的 Cookies，请确保已登录 YouTube！"
                    )
                    return
                
                # 保存 Cookies 文件
                if CookiesManager.save_cookies_file(youtube_cookies):
                    # 更新状态
                    self.cookies_status_label.setText(
                        f"✓ 已保存 {len(youtube_cookies)} 个 YouTube Cookies"
                    )
                    self.cookies_status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
                    
                    # 更新下载器
                    self.downloader.cookies_file = str(CookiesManager.get_cookies_file_path())
                    
                    QMessageBox.information(
                        self, 
                        "导入成功", 
                        f"成功导入并保存 {len(youtube_cookies)} 个 Cookies！\n\n"
                        f"保存路径: {CookiesManager.get_cookies_file_path()}"
                    )
                    
                    self.statusBar().showMessage("Cookies 导入成功！现在可以下载 YouTube 视频了")
                else:
                    QMessageBox.critical(self, "错误", "保存 Cookies 文件失败！")
                    
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "导入失败", 
                    f"解析 Cookies 时出错：\n{str(e)}"
                )
    
    def _on_clear_cookies(self):
        """清除 Cookies"""
        cookies_file = CookiesManager.get_cookies_file_path()
        
        if not cookies_file.exists():
            QMessageBox.information(self, "提示", "当前没有保存的 Cookies 文件。")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除",
            "确定要删除已保存的 Cookies 吗？\n\n"
            "删除后将无法下载需要认证的 YouTube 视频。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if CookiesManager.clear_cookies_file():
                self.cookies_status_label.setText("⚠ Cookies 已清除")
                self.cookies_status_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
                
                # 清除下载器的 Cookies 设置
                self.downloader.cookies_file = None
                
                self.statusBar().showMessage("Cookies 已清除")
            else:
                QMessageBox.critical(self, "错误", "删除 Cookies 文件失败！")
    
    def _on_browse_output_path(self):
        """浏览输出路径"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择下载保存路径", 
            self.output_path_edit.text()
        )
        if folder:
            self.output_path_edit.setText(folder)
            self.downloader.output_dir = Path(folder)
    
    def _on_clear_completed(self):
        """清除已完成的任务"""
        # 从后向前遍历，避免索引问题
        for i in range(self.download_list.count() - 1, -1, -1):
            item = self.download_list.item(i)
            widget = self.download_list.itemWidget(item)
            
            if widget and not widget.is_active:
                self.download_list.takeItem(i)
                
                # 从字典中移除
                for url, w in list(self.download_items.items()):
                    if w == widget:
                        del self.download_items[url]
                        break
    
    def _on_cancel_all(self):
        """取消全部下载"""
        for thread in self.download_threads:
            if thread.isRunning():
                thread.cancel()
        
        # 更新所有下载项状态
        for item in self.download_items.values():
            if item.is_active:
                item.set_cancelled()
        
        self.statusBar().showMessage("已取消所有下载")
    
    def _on_open_download_folder(self):
        """打开下载文件夹"""
        path = self.output_path_edit.text()
        if not open_folder(path):
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {path}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 检查是否有正在进行的下载
        active_threads = [t for t in self.download_threads if t.isRunning()]
        
        if active_threads:
            reply = QMessageBox.question(
                self, "确认退出",
                f"还有 {len(active_threads)} 个下载任务正在进行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            # 停止所有下载
            for thread in active_threads:
                thread.cancel()
                thread.wait(1000)  # 等待1秒
        
        event.accept()
