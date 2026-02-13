# -*- coding: utf-8 -*-
"""
辅助函数模块 - 提供常用的工具函数
作者：小码酱
日期：2025-02-12
"""

import os
import re
import sys
import shutil
import subprocess
import platform
from typing import Optional


def format_duration(seconds) -> str:
    """
    格式化时长（秒转为 时:分:秒 或 分:秒）
    
    Args:
        seconds: 秒数（可以是 int 或 float）
        
    Returns:
        格式化的时长字符串，如 "1:23:45" 或 "5:30"
    """
    if seconds is None:
        return "--:--"
    
    # 转换为整数
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return "--:--"
    
    if seconds < 0:
        return "--:--"
    
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}:{int(minutes):02d}:{int(secs):02d}"
    else:
        return f"{int(minutes)}:{int(secs):02d}"


def format_filesize(bytes_size: int) -> str:
    """
    格式化文件大小（字节转为 B/KB/MB/GB）
    
    Args:
        bytes_size: 字节数
        
    Returns:
        格式化的文件大小字符串，如 "1.5 GB" 或 "256 MB"
    """
    if bytes_size is None or bytes_size < 0:
        return "-- B"
    
    if bytes_size == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_size)
    
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            else:
                return f"{size:.1f} {unit}"
        size /= 1024
    
    return f"{size:.1f} {units[-1]}"


def format_speed(bytes_per_second: float) -> str:
    """
    格式化下载速度（字节/秒转为 KB/s 或 MB/s）
    
    Args:
        bytes_per_second: 字节每秒
        
    Returns:
        格式化的速度字符串，如 "2.5 MB/s" 或 "512 KB/s"
    """
    if bytes_per_second is None or bytes_per_second <= 0:
        return "-- B/s"
    
    return format_filesize(bytes_per_second) + "/s"


def format_eta(seconds: int) -> str:
    """
    格式化剩余时间
    
    Args:
        seconds: 剩余秒数
        
    Returns:
        格式化的时间字符串，如 "5分钟" 或 "1小时23分"
    """
    if seconds is None or seconds < 0:
        return "--"
    
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        if secs > 0:
            return f"{minutes}分{secs}秒"
        return f"{minutes}分钟"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}小时{minutes}分"
        return f"{hours}小时"


def open_folder(path: str) -> bool:
    """
    打开文件夹（跨平台）
    
    Args:
        path: 文件夹路径
        
    Returns:
        是否成功打开
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", path], check=True)
        
        return True
    except Exception as e:
        print(f"打开文件夹失败: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    清理文件名（移除非法字符）
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    if not filename:
        return "untitled"
    
    # Windows 非法字符: < > : " / \ | ? *
    # 以及控制字符
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(illegal_chars, '_', filename)
    
    # 移除开头和结尾的空格和点
    sanitized = sanitized.strip('. ')
    
    # 限制文件名长度（Windows 最大 255 字符）
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized if sanitized else "untitled"


def get_system_proxy() -> dict:
    """
    获取系统代理设置
    
    Returns:
        包含代理设置的字典 {
            "http": "http://proxy:port",
            "https": "http://proxy:port",
            "all": "socks5://proxy:port"  # 如果有的话
        }
    """
    import os
    import platform
    
    proxies = {}
    system = platform.system()
    
    if system == "Windows":
        # Windows: 从注册表读取代理设置
        try:
            import winreg
            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            )
            
            # 检查是否启用代理
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            
            if proxy_enable:
                proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                
                if proxy_server:
                    # 格式可能是 "proxy:port" 或 "http=proxy:port;https=proxy:port"
                    if "=" in proxy_server:
                        # 解析格式: http=proxy:port;https=proxy:port
                        for part in proxy_server.split(";"):
                            if "=" in part:
                                protocol, addr = part.split("=", 1)
                                if protocol.lower() in ["http", "https"]:
                                    proxies[protocol.lower()] = f"http://{addr}"
                    else:
                        # 简单格式: proxy:port
                        proxies["http"] = f"http://{proxy_server}"
                        proxies["https"] = f"http://{proxy_server}"
            
            winreg.CloseKey(key)
        except Exception:
            pass
        
        # 也检查环境变量
        if not proxies:
            http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
            https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")
            
            if http_proxy:
                proxies["http"] = http_proxy
            if https_proxy:
                proxies["https"] = https_proxy
            if all_proxy:
                proxies["all"] = all_proxy
    
    else:  # Linux / macOS
        # 从环境变量读取
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")
        
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        if all_proxy:
            proxies["all"] = all_proxy
    
    return proxies


def get_proxy_for_yt_dlp() -> Optional[str]:
    """
    获取用于 yt-dlp 的代理地址
    
    Returns:
        代理地址字符串，如 "socks5://127.0.0.1:7890" 或 None
    """
    proxies = get_system_proxy()
    
    # 优先使用 all_proxy（通常是 SOCKS5）
    if "all" in proxies:
        return proxies["all"]
    
    # 其次使用 https 代理
    if "https" in proxies:
        return proxies["https"]
    
    # 最后使用 http 代理
    if "http" in proxies:
        return proxies["http"]
    
    return None


def check_dependencies() -> dict:
    """
    检查必要的依赖是否安装
    
    Returns:
        包含检查结果的字典 {
            "python": "3.x.x",
            "ffmpeg": True/False,
            "yt-dlp": "2025.x.x"
        }
    """
    result = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "ffmpeg": False,
        "yt-dlp": None
    }
    
    # 检查 ffmpeg
    result["ffmpeg"] = shutil.which('ffmpeg') is not None
    
    # 检查 yt-dlp
    try:
        import yt_dlp
        # 尝试多种方式获取版本号
        version = None
        
        # 方法1: 从 version 模块获取
        try:
            from yt_dlp import version as yt_version
            version = getattr(yt_version, '__version__', None)
        except (ImportError, AttributeError):
            pass
        
        # 方法2: 从 yt_dlp 模块直接获取
        if not version:
            version = getattr(yt_dlp, '__version__', None)
        
        # 方法3: 使用 version_info 元组
        if not version:
            try:
                from yt_dlp import version as yt_version
                version_info = getattr(yt_version, 'version_info', None)
                if version_info and len(version_info) >= 3:
                    version = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
            except (ImportError, AttributeError):
                pass
        
        result["yt-dlp"] = version if version else 'installed'
        
    except ImportError:
        result["yt-dlp"] = None
    
    return result


def get_platform_info() -> dict:
    """
    获取平台信息
    
    Returns:
        包含平台信息的字典 {
            "system": "Windows/Linux/Darwin",
            "release": "10/20.04/...",
            "arch": "x86_64/arm64/..."
        }
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "arch": platform.machine()
    }


def is_valid_url(url: str) -> bool:
    """
    检查 URL 是否有效
    
    Args:
        url: URL 字符串
        
    Returns:
        是否是有效的 URL
    """
    if not url or not isinstance(url, str):
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP 地址
        r'(?::\d+)?'  # 端口
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def extract_urls_from_text(text: str) -> list:
    """
    从文本中提取所有 URL
    
    Args:
        text: 包含 URL 的文本
        
    Returns:
        URL 列表
    """
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .-]*/?(?:\?[^\\s]*)?'
    )
    return url_pattern.findall(text)
