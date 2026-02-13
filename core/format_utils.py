# -*- coding: utf-8 -*-
"""
格式转换工具模块 - 处理视频/音频格式转换
作者：小码酱
日期：2025-02-12
"""

from pathlib import Path
from typing import Optional
import subprocess
import shutil
import json
import platform


class FormatConverter:
    """
    格式转换工具类
    
    功能说明：
    1. 视频格式转换
    2. 音频提取和转换
    3. 使用 ffmpeg 进行转换
    """
    
    # 质量预设（CRF 值，越小质量越高）
    QUALITY_PRESETS = {
        "high": 18,      # 高质量
        "medium": 23,    # 中等质量
        "low": 28        # 低质量（小文件）
    }
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """
        检查系统是否安装了 ffmpeg
        
        Returns:
            是否已安装 ffmpeg
        """
        return shutil.which('ffmpeg') is not None
    
    @staticmethod
    def check_ffprobe() -> bool:
        """
        检查系统是否安装了 ffprobe
        
        Returns:
            是否已安装 ffprobe
        """
        return shutil.which('ffprobe') is not None
    
    @staticmethod
    def convert_video(
        input_path: str,
        output_path: str,
        output_format: str = "mp4",
        quality: str = "high"
    ) -> bool:
        """
        转换视频格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            output_format: 输出格式（mp4, mkv, avi 等）
            quality: 质量（"high", "medium", "low"）
            
        Returns:
            是否转换成功
        """
        if not FormatConverter.check_ffmpeg():
            print("错误: 未安装 ffmpeg")
            return False
        
        if not Path(input_path).exists():
            print(f"错误: 输入文件不存在: {input_path}")
            return False
        
        # 获取 CRF 值
        crf = FormatConverter.QUALITY_PRESETS.get(quality, 23)
        
        # 构建 ffmpeg 命令
        cmd = [
            'ffmpeg',
            '-i', input_path,           # 输入文件
            '-c:v', 'libx264',          # 视频编码器
            '-crf', str(crf),           # 质量控制
            '-preset', 'medium',        # 编码速度预设
            '-c:a', 'aac',              # 音频编码器
            '-b:a', '192k',             # 音频比特率
            '-y',                       # 覆盖输出文件
            output_path
        ]
        
        try:
            # 运行转换命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                print(f"转换成功: {output_path}")
                return True
            else:
                print(f"转换失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("转换超时")
            return False
        except Exception as e:
            print(f"转换错误: {e}")
            return False
    
    @staticmethod
    def extract_audio(
        video_path: str,
        audio_path: str,
        audio_format: str = "mp3",
        bitrate: str = "192k"
    ) -> bool:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 输出音频路径
            audio_format: 音频格式（mp3, m4a, wav 等）
            bitrate: 比特率（"128k", "192k", "320k"）
            
        Returns:
            是否提取成功
        """
        if not FormatConverter.check_ffmpeg():
            print("错误: 未安装 ffmpeg")
            return False
        
        if not Path(video_path).exists():
            print(f"错误: 视频文件不存在: {video_path}")
            return False
        
        # 音频编码器映射
        codec_map = {
            "mp3": "libmp3lame",
            "m4a": "aac",
            "aac": "aac",
            "wav": "pcm_s16le",
            "flac": "flac",
            "opus": "libopus",
            "ogg": "libvorbis"
        }
        
        codec = codec_map.get(audio_format.lower(), "libmp3lame")
        
        # 构建 ffmpeg 命令
        cmd = [
            'ffmpeg',
            '-i', video_path,           # 输入视频文件
            '-vn',                       # 不包含视频
            '-acodec', codec,           # 音频编码器
            '-ab', bitrate,             # 音频比特率
            '-y',                       # 覆盖输出文件
            audio_path
        ]
        
        # WAV 格式特殊处理（不需要比特率参数）
        if audio_format.lower() == 'wav':
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-y',
                audio_path
            ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            if result.returncode == 0:
                print(f"音频提取成功: {audio_path}")
                return True
            else:
                print(f"音频提取失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("音频提取超时")
            return False
        except Exception as e:
            print(f"音频提取错误: {e}")
            return False
    
    @staticmethod
    def get_video_info(file_path: str) -> Optional[dict]:
        """
        获取视频文件信息
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            包含视频信息的字典（时长、分辨率、编码等）
        """
        if not FormatConverter.check_ffprobe():
            print("错误: 未安装 ffprobe")
            return None
        
        if not Path(file_path).exists():
            print(f"错误: 文件不存在: {file_path}")
            return None
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # 提取关键信息
                info = {
                    'duration': float(data.get('format', {}).get('duration', 0)),
                    'size': int(data.get('format', {}).get('size', 0)),
                    'bit_rate': int(data.get('format', {}).get('bit_rate', 0)),
                    'format_name': data.get('format', {}).get('format_name', ''),
                }
                
                # 提取视频流信息
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        info['width'] = stream.get('width', 0)
                        info['height'] = stream.get('height', 0)
                        info['video_codec'] = stream.get('codec_name', '')
                        info['fps'] = eval(stream.get('r_frame_rate', '0/1'))
                        break
                
                # 提取音频流信息
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        info['audio_codec'] = stream.get('codec_name', '')
                        info['sample_rate'] = int(stream.get('sample_rate', 0))
                        info['channels'] = stream.get('channels', 0)
                        break
                
                return info
            else:
                print(f"获取视频信息失败: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"获取视频信息错误: {e}")
            return None
    
    @staticmethod
    def merge_video_audio(
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> bool:
        """
        合并视频和音频文件
        
        Args:
            video_path: 视频文件路径（无音频）
            audio_path: 音频文件路径
            output_path: 输出文件路径
            
        Returns:
            是否合并成功
        """
        if not FormatConverter.check_ffmpeg():
            print("错误: 未安装 ffmpeg")
            return False
        
        if not Path(video_path).exists():
            print(f"错误: 视频文件不存在: {video_path}")
            return False
        
        if not Path(audio_path).exists():
            print(f"错误: 音频文件不存在: {audio_path}")
            return False
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',              # 直接复制视频流
            '-c:a', 'aac',               # 音频编码为 AAC
            '-map', '0:v:0',             # 使用第一个输入的视频
            '-map', '1:a:0',             # 使用第二个输入的音频
            '-y',                        # 覆盖输出文件
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode == 0:
                print(f"合并成功: {output_path}")
                return True
            else:
                print(f"合并失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"合并错误: {e}")
            return False
    
    @staticmethod
    def trim_video(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float
    ) -> bool:
        """
        裁剪视频片段
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            
        Returns:
            是否裁剪成功
        """
        if not FormatConverter.check_ffmpeg():
            print("错误: 未安装 ffmpeg")
            return False
        
        duration = end_time - start_time
        
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),      # 开始时间
            '-i', input_path,
            '-t', str(duration),         # 持续时间
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode == 0:
                print(f"裁剪成功: {output_path}")
                return True
            else:
                print(f"裁剪失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"裁剪错误: {e}")
            return False
    
    @staticmethod
    def compress_video(
        input_path: str,
        output_path: str,
        target_size_mb: int = 50
    ) -> bool:
        """
        压缩视频到目标大小
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            target_size_mb: 目标大小（MB）
            
        Returns:
            是否压缩成功
        """
        if not FormatConverter.check_ffmpeg():
            print("错误: 未安装 ffmpeg")
            return False
        
        # 获取视频时长
        info = FormatConverter.get_video_info(input_path)
        if not info:
            return False
        
        duration = info.get('duration', 0)
        if duration <= 0:
            print("错误: 无法获取视频时长")
            return False
        
        # 计算目标比特率
        target_size_bytes = target_size_mb * 1024 * 1024
        # 减去音频大小（约 128kbps）
        audio_bitrate = 128 * 1024
        video_bitrate = (target_size_bytes * 8 / duration) - audio_bitrate
        
        if video_bitrate <= 0:
            print("错误: 目标大小太小")
            return False
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-b:v', f'{int(video_bitrate)}',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                print(f"压缩成功: {output_path}")
                return True
            else:
                print(f"压缩失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"压缩错误: {e}")
            return False
