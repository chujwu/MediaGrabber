# -*- coding: utf-8 -*-
"""
配置文件模块 - 存储应用程序的所有配置项
作者：小码酱
日期：2025-02-12
"""

import os
from pathlib import Path


class Settings:
    """应用程序配置类"""
    
    # ==================== 基础路径配置 ====================
    # 应用程序根目录
    APP_DIR = Path(__file__).parent.parent.absolute()
    
    # 默认下载目录（用户桌面下的 Downloads 文件夹）
    DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "YTDownloader"
    
    # ==================== 支持的平台 ====================
    SUPPORTED_PLATFORMS = {
        "youtube": {
            "name": "YouTube",
            "domains": ["youtube.com", "youtu.be"],
            "icon": "🎬"
        },
        "bilibili": {
            "name": "B站 (bilibili)",
            "domains": ["bilibili.com", "b23.tv"],
            "icon": "📺"
        },
        "twitter": {
            "name": "Twitter/X",
            "domains": ["twitter.com", "x.com"],
            "icon": "🐦"
        },
        "vimeo": {
            "name": "Vimeo",
            "domains": ["vimeo.com"],
            "icon": "🎥"
        }
    }
    
    # ==================== 视频质量选项 ====================
    VIDEO_QUALITY_OPTIONS = [
        {"id": "best", "label": "最高画质", "format": "bestvideo+bestaudio/best"},
        {"id": "1080p", "label": "1080p (Full HD)", "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"},
        {"id": "720p", "label": "720p (HD)", "format": "bestvideo[height<=720]+bestaudio/best[height<=720]"},
        {"id": "480p", "label": "480p (SD)", "format": "bestvideo[height<=480]+bestaudio/best[height<=480]"},
        {"id": "360p", "label": "360p", "format": "bestvideo[height<=360]+bestaudio/best[height<=360]"},
        {"id": "worst", "label": "最低画质", "format": "worstvideo+worstaudio/worst"}
    ]
    
    # ==================== 音频格式选项 ====================
    AUDIO_FORMAT_OPTIONS = [
        {"id": "mp3", "label": "MP3 (推荐)", "codec": "mp3", "bitrate": "192"},
        {"id": "m4a", "label": "M4A (AAC)", "codec": "aac", "bitrate": "192"},
        {"id": "opus", "label": "Opus (高压缩)", "codec": "opus", "bitrate": "128"},
        {"id": "wav", "label": "WAV (无损)", "codec": "pcm_s16le", "bitrate": None}
    ]
    
    # ==================== 字幕选项 ====================
    SUBTITLE_OPTIONS = [
        {"id": "none", "label": "不下载字幕"},
        {"id": "auto", "label": "自动生成字幕"},
        {"id": "manual", "label": "手动字幕（如有）"},
        {"id": "all", "label": "全部字幕"}
    ]
    
    # ==================== 代理配置 ====================
    # 默认代理设置（如果需要翻墙）
    PROXY_ENABLED = False
    PROXY_URL = "socks5://127.0.0.1:7890"  # 默认代理地址
    
    # ==================== 下载配置 ====================
    # 最大并发下载数
    MAX_CONCURRENT_DOWNLOADS = 3
    
    # 下载速度限制（None 表示不限制）
    RATE_LIMIT = None  # 例如: "1M" 表示 1MB/s
    
    # 重试次数
    MAX_RETRIES = 3
    
    # ==================== yt-dlp 配置 ====================
    YDL_OPTS_BASE = {
        # 提取视频信息时不下载
        'quiet': True,
        'no_warnings': True,
        # 启用断点续传
        'continuedl': True,
        # 覆盖已存在文件
        'overwrites': False,
        # 合并输出格式
        'merge_output_format': 'mp4',
    }
    
    # ==================== UI 配置 ====================
    WINDOW_TITLE = "YouTube 视频下载器 v2.0"
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 940
    WINDOW_MIN_WIDTH = 900
    WINDOW_MIN_HEIGHT = 810
    
    # 样式配置
    STYLESHEET = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #3498db;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #3498db;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1f618d;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
        QLineEdit, QTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #3498db;
        }
        QComboBox {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 6px;
        }
        QProgressBar {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 3px;
        }
    """


# 创建全局配置实例
settings = Settings()
