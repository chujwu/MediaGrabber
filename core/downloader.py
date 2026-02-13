# -*- coding: utf-8 -*-
"""
视频下载核心模块 - 封装 yt-dlp 的下载功能
作者：小码酱
日期：2025-02-12
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import threading
import re


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"       # 等待中
    FETCHING = "fetching"     # 获取信息中
    DOWNLOADING = "downloading"  # 下载中
    CONVERTING = "converting"    # 转换中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


@dataclass
class VideoInfo:
    """视频信息数据类"""
    url: str
    title: str = ""
    duration: int = 0          # 秒
    thumbnail: str = ""
    uploader: str = ""
    view_count: int = 0
    description: str = ""
    formats: List[Dict] = None  # 可用格式列表
    
    def __post_init__(self):
        if self.formats is None:
            self.formats = []


@dataclass  
class DownloadProgress:
    """下载进度数据类"""
    status: DownloadStatus
    filename: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0           # bytes/s
    eta: int = 0               # 预计剩余时间（秒）
    percentage: float = 0      # 进度百分比
    error_message: str = ""    # 错误信息
    
    @property
    def progress_text(self) -> str:
        """生成进度显示文本"""
        return f"{self.percentage:.1f}%"


class VideoDownloader:
    """
    视频下载器类 - 封装 yt-dlp 的核心功能
    
    功能说明：
    1. 获取视频信息（标题、时长、格式等）
    2. 下载视频（支持质量选择、断点续传）
    3. 下载进度回调
    4. 格式转换
    """
    
    # 质量格式映射表
    QUALITY_FORMAT_MAP = {
        "best": "bestvideo+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "worst": "worstvideo+worstaudio/worst"
    }
    
    def __init__(
        self,
        output_dir: str = None,
        proxy: str = None,
        progress_callback: Callable[[DownloadProgress], None] = None,
        cookies_file: str = None,
        cookies_from_browser: str = None
    ):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录
            proxy: 代理地址（如 "socks5://127.0.0.1:7890"）
            progress_callback: 进度回调函数
            cookies_file: Cookies 文件路径（用于 YouTube 等需要认证的网站）
            cookies_from_browser: 从浏览器读取Cookies（chrome, edge, firefox等）
        """
        self.output_dir = Path(output_dir) if output_dir else Path.home() / "Downloads"
        self.proxy = proxy
        self.progress_callback = progress_callback
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self._stop_flag = threading.Event()
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_video_info(self, url: str) -> Optional[VideoInfo]:
        """
        获取视频信息（不下载）
        
        Args:
            url: 视频URL
            
        Returns:
            VideoInfo 对象，失败返回 None
        """
        ydl_opts = self._get_base_opts()
        ydl_opts['download'] = False  # 只获取信息，不下载
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                # 提取格式列表
                formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        # 过滤掉无效格式
                        if fmt.get('format_id') and (fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none'):
                            formats.append({
                                'format_id': fmt.get('format_id', ''),
                                'ext': fmt.get('ext', ''),
                                'resolution': fmt.get('resolution', '') or f"{fmt.get('width', '?')}x{fmt.get('height', '?')}",
                                'fps': fmt.get('fps', 0),
                                'vcodec': fmt.get('vcodec', 'none'),
                                'acodec': fmt.get('acodec', 'none'),
                                'filesize': fmt.get('filesize') or fmt.get('filesize_approx', 0),
                            })
                
                # 创建 VideoInfo 对象
                video_info = VideoInfo(
                    url=url,
                    title=info.get('title', '未知标题'),
                    duration=info.get('duration', 0) or 0,
                    thumbnail=info.get('thumbnail', ''),
                    uploader=info.get('uploader', '') or info.get('channel', '未知'),
                    view_count=info.get('view_count', 0) or 0,
                    description=info.get('description', '')[:200] if info.get('description') else '',
                    formats=formats
                )
                
                return video_info
                
        except yt_dlp.utils.DownloadError as e:
            print(f"下载错误: {e}")
            return None
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None
    
    def download(
        self,
        url: str,
        quality: str = "best",
        format_type: str = "video",  # "video" 或 "audio"
        audio_format: str = "mp3",
        subtitle_option: str = "none",
        output_filename: str = None
    ) -> bool:
        """
        下载视频或音频
        
        Args:
            url: 视频URL
            quality: 视频质量（"best", "1080p", "720p" 等）
            format_type: "video" 或 "audio"
            audio_format: 音频格式（"mp3", "m4a" 等）
            subtitle_option: 字幕选项（"none", "auto", "manual", "all"）
            output_filename: 自定义输出文件名
            
        Returns:
            是否成功启动下载
        """
        self._stop_flag.clear()
        ydl_opts = self._get_download_opts(
            quality, format_type, audio_format, subtitle_option, output_filename
        )
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            error_msg = str(e)
            if self._stop_flag.is_set():
                error_msg = "下载已取消"
            
            # 发送失败回调
            if self.progress_callback:
                progress = DownloadProgress(
                    status=DownloadStatus.FAILED,
                    error_message=error_msg
                )
                self.progress_callback(progress)
            
            print(f"下载失败: {error_msg}")
            return False
    
    def download_batch(
        self,
        urls: List[str],
        quality: str = "best",
        format_type: str = "video",
        audio_format: str = "mp3",
        subtitle_option: str = "none"
    ) -> Dict[str, bool]:
        """
        批量下载视频
        
        Args:
            urls: URL 列表
            quality: 视频质量
            format_type: 格式类型
            audio_format: 音频格式
            subtitle_option: 字幕选项
            
        Returns:
            每个URL的下载结果字典 {url: success}
        """
        results = {}
        
        for url in urls:
            if self._stop_flag.is_set():
                break
            
            success = self.download(
                url=url,
                quality=quality,
                format_type=format_type,
                audio_format=audio_format,
                subtitle_option=subtitle_option
            )
            results[url] = success
        
        return results
    
    def stop(self):
        """停止当前下载"""
        self._stop_flag.set()
    
    def get_available_formats(self, url: str) -> List[Dict]:
        """
        获取视频可用的格式列表
        
        Args:
            url: 视频URL
            
        Returns:
            格式列表，每个元素包含 format_id, ext, resolution, filesize 等
        """
        video_info = self.fetch_video_info(url)
        
        if not video_info:
            return []
        
        return video_info.formats
    
    def _get_base_opts(self) -> Dict[str, Any]:
        """
        获取 yt-dlp 基础配置选项
        
        Returns:
            配置字典
        """
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,  # 忽略错误继续
        }
        
        if self.proxy:
            opts['proxy'] = self.proxy
        
        # 添加 Cookies 支持（用于 YouTube 等需要认证的网站）
        # 优先使用从浏览器读取的 Cookies（更可靠）
        if self.cookies_from_browser:
            opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        elif self.cookies_file and Path(self.cookies_file).exists():
            opts['cookiefile'] = self.cookies_file
            
        return opts
    
    def _get_download_opts(
        self,
        quality: str,
        format_type: str,
        audio_format: str,
        subtitle_option: str,
        output_filename: str
    ) -> Dict[str, Any]:
        """
        获取下载配置选项
        
        Args:
            quality: 视频质量
            format_type: 格式类型
            audio_format: 音频格式
            subtitle_option: 字幕选项
            output_filename: 输出文件名
            
        Returns:
            配置字典
        """
        opts = self._get_base_opts()
        
        # 输出路径模板
        if output_filename:
            # 清理文件名中的非法字符
            safe_filename = self._sanitize_filename(output_filename)
            opts['outtmpl'] = str(self.output_dir / safe_filename)
        else:
            opts['outtmpl'] = str(self.output_dir / '%(title)s.%(ext)s')
        
        # 格式选择
        if format_type == "audio":
            # 音频格式下载
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }]
            # 音频文件命名
            if not output_filename:
                opts['outtmpl'] = str(self.output_dir / '%(title)s.%(ext)s')
        else:
            # 视频格式下载 - 根据质量选择
            format_string = self.QUALITY_FORMAT_MAP.get(quality, self.QUALITY_FORMAT_MAP["best"])
            opts['format'] = format_string
        
        # 字幕下载配置
        if subtitle_option != "none":
            if subtitle_option in ["manual", "all"]:
                opts['writesubtitles'] = True
            if subtitle_option in ["auto", "all"]:
                opts['writeautomaticsub'] = True
            opts['subtitleslangs'] = ['zh-Hans', 'zh-Hant', 'en', 'all']
        
        # 断点续传
        opts['continuedl'] = True
        
        # 不覆盖已存在文件
        opts['overwrites'] = False
        
        # 合并输出格式
        opts['merge_output_format'] = 'mp4'
        
        # 进度钩子
        opts['progress_hooks'] = [self._progress_hook]
        
        return opts
    
    def _progress_hook(self, d: Dict[str, Any]):
        """
        yt-dlp 进度回调钩子
        
        Args:
            d: 进度信息字典
        """
        # 检查是否被要求停止
        if self._stop_flag.is_set():
            raise Exception("Download cancelled by user")
        
        status = d.get('status')
        
        if status == 'downloading':
            # 计算进度百分比
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            percentage = 0
            if total > 0:
                percentage = (downloaded / total) * 100
            
            progress = DownloadProgress(
                status=DownloadStatus.DOWNLOADING,
                filename=d.get('filename', ''),
                downloaded_bytes=downloaded,
                total_bytes=total,
                speed=d.get('speed', 0) or 0,
                eta=d.get('eta', 0) or 0,
                percentage=percentage
            )
            
        elif status == 'finished':
            progress = DownloadProgress(
                status=DownloadStatus.CONVERTING,
                filename=d.get('filename', ''),
                percentage=100
            )
            
        elif status == 'error':
            progress = DownloadProgress(
                status=DownloadStatus.FAILED,
                error_message=d.get('error', '未知错误')
            )
            
        else:
            return
        
        # 调用回调函数
        if self.progress_callback:
            self.progress_callback(progress)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        if not filename:
            return "download"
        
        # Windows 非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(illegal_chars, '_', filename)
        
        # 移除开头和结尾的空格和点
        sanitized = sanitized.strip('. ')
        
        # 限制文件名长度
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized if sanitized else "download"
