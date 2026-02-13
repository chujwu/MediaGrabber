# -*- coding: utf-8 -*-
"""
Cookies 管理模块 - 处理 YouTube 等网站的 Cookies 认证
作者：小码酱
日期：2025-02-12
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class CookieItem:
    """Cookie 数据项"""
    name: str
    value: str
    domain: str
    path: str
    expires: str
    secure: bool = False
    http_only: bool = False
    same_site: str = ""
    priority: str = "Medium"


class CookiesManager:
    """
    Cookies 管理器 - 支持多种格式的 Cookies 解析和转换
    
    支持格式：
    1. 浏览器导出的表格格式（制表符分隔）
    2. Netscape cookies.txt 格式
    3. JSON 格式
    """
    
    # 默认 Cookies 文件路径
    DEFAULT_COOKIES_DIR = Path.home() / ".yt-dlp-downloader" / "cookies"
    DEFAULT_COOKIES_FILE = DEFAULT_COOKIES_DIR / "youtube_cookies.txt"
    
    @classmethod
    def parse_browser_export(cls, text: str) -> List[CookieItem]:
        """
        解析浏览器导出的表格格式 Cookies
        
        格式示例（制表符分隔）：
        name    value    domain    path    expires    ...
        
        Args:
            text: 浏览器导出的原始文本
            
        Returns:
            CookieItem 列表
        """
        cookies = []
        lines = text.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # 按制表符分割
            parts = line.split('\t')
            
            # 至少需要 5 个字段：name, value, domain, path, expires
            if len(parts) < 5:
                continue
            
            # 提取字段
            cookie = CookieItem(
                name=parts[0].strip(),
                value=parts[1].strip(),
                domain=parts[2].strip(),
                path=parts[3].strip(),
                expires=parts[4].strip(),
                # 扩展字段
                secure=len(parts) > 10 and parts[10].strip() == '✓',
                http_only=len(parts) > 11 and parts[11].strip() == '✓',
                same_site=parts[12].strip() if len(parts) > 12 else "",
                priority=parts[14].strip() if len(parts) > 14 else "Medium"
            )
            
            cookies.append(cookie)
        
        return cookies
    
    @classmethod
    def to_netscape_format(cls, cookies: List[CookieItem]) -> str:
        """
        转换为 Netscape cookies.txt 格式
        
        格式：
        # Netscape HTTP Cookie File
        domain    flag    path    secure    expires    name    value
        
        Args:
            cookies: CookieItem 列表
            
        Returns:
            Netscape 格式的字符串
        """
        lines = [
            "# Netscape HTTP Cookie File",
            "# https://curl.haxx.se/rfc/cookie_spec.html",
            "# This is a generated file!  Do not edit.",
            ""
        ]
        
        for cookie in cookies:
            # 计算域名标志（是否包含所有子域名）
            domain_flag = "TRUE" if cookie.domain.startswith('.') else "FALSE"
            
            # secure 标志
            secure_flag = "TRUE" if cookie.secure else "FALSE"
            
            # 转换过期时间为 Unix 时间戳
            expires_timestamp = cls._parse_expiry_to_timestamp(cookie.expires)
            
            # 格式化行
            line = "\t".join([
                cookie.domain,
                domain_flag,
                cookie.path,
                secure_flag,
                str(expires_timestamp),
                cookie.name,
                cookie.value
            ])
            
            lines.append(line)
        
        return '\n'.join(lines)
    
    @classmethod
    def _parse_expiry_to_timestamp(cls, expiry_str: str) -> int:
        """
        将过期时间字符串转换为 Unix 时间戳
        
        支持格式：
        - ISO 8601: "2027-03-18T11:44:34.748Z"
        - Unix 时间戳（数字）
        
        Args:
            expiry_str: 过期时间字符串
            
        Returns:
            Unix 时间戳
        """
        # 如果是纯数字，直接返回
        if expiry_str.isdigit():
            return int(expiry_str)
        
        # 尝试解析 ISO 8601 格式
        try:
            # 移除毫秒部分
            if '.' in expiry_str:
                expiry_str = expiry_str.split('.')[0] + 'Z'
            
            # 解析 ISO 格式
            dt = datetime.strptime(expiry_str, "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            pass
        
        # 解析失败，返回一个未来的时间戳（10年后）
        return int(datetime.now().timestamp()) + 315360000
    
    @classmethod
    def to_dict(cls, cookies: List[CookieItem]) -> Dict[str, str]:
        """
        转换为字典格式 {name: value}
        
        Args:
            cookies: CookieItem 列表
            
        Returns:
            Cookies 字典
        """
        return {cookie.name: cookie.value for cookie in cookies}
    
    @classmethod
    def save_cookies_file(cls, cookies: List[CookieItem], file_path: Path = None) -> bool:
        """
        保存 Cookies 到文件（Netscape 格式）
        
        Args:
            cookies: CookieItem 列表
            file_path: 文件路径，默认为 ~/.yt-dlp-downloader/cookies/youtube_cookies.txt
            
        Returns:
            是否保存成功
        """
        if file_path is None:
            file_path = cls.DEFAULT_COOKIES_FILE
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为 Netscape 格式
            content = cls.to_netscape_format(cookies)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"保存 Cookies 文件失败: {e}")
            return False
    
    @classmethod
    def load_cookies_file(cls, file_path: Path = None) -> Optional[List[CookieItem]]:
        """
        从文件加载 Cookies
        
        Args:
            file_path: 文件路径，默认为 ~/.yt-dlp-downloader/cookies/youtube_cookies.txt
            
        Returns:
            CookieItem 列表，失败返回 None
        """
        if file_path is None:
            file_path = cls.DEFAULT_COOKIES_FILE
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 Netscape 格式
            return cls.parse_netscape_format(content)
        except Exception as e:
            print(f"加载 Cookies 文件失败: {e}")
            return None
    
    @classmethod
    def parse_netscape_format(cls, content: str) -> List[CookieItem]:
        """
        解析 Netscape cookies.txt 格式
        
        格式：
        domain    flag    path    secure    expires    name    value
        
        Args:
            content: 文件内容
            
        Returns:
            CookieItem 列表
        """
        cookies = []
        lines = content.strip().split('\n')
        
        for line in lines:
            # 跳过注释和空行
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split('\t')
            
            if len(parts) < 7:
                continue
            
            cookie = CookieItem(
                domain=parts[0],
                name=parts[5],
                value=parts[6],
                path=parts[2],
                expires=parts[4],
                secure=parts[3] == "TRUE"
            )
            
            cookies.append(cookie)
        
        return cookies
    
    @classmethod
    def is_cookies_file_exists(cls, file_path: Path = None) -> bool:
        """
        检查 Cookies 文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        if file_path is None:
            file_path = cls.DEFAULT_COOKIES_FILE
        
        return file_path.exists()
    
    @classmethod
    def get_cookies_file_path(cls) -> Path:
        """
        获取默认 Cookies 文件路径
        
        Returns:
            Cookies 文件路径
        """
        return cls.DEFAULT_COOKIES_FILE
    
    @classmethod
    def clear_cookies_file(cls, file_path: Path = None) -> bool:
        """
        清除 Cookies 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否清除成功
        """
        if file_path is None:
            file_path = cls.DEFAULT_COOKIES_FILE
        
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"清除 Cookies 文件失败: {e}")
            return False
