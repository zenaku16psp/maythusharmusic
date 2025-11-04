import asyncio
import os
import re
import json
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from maythusharmusic.utils.database import is_on_off
from maythusharmusic.utils.formatters import time_to_seconds

import glob
import random
import logging

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0?]*[ -/]*[@-~])")

        # Cache for faster repeated access
        self.download_cache = {}
        
        # Cookie handling
        self.cookie_file_path = "cookies.txt"
        self.cookie_arg = []
        self.cookie_dict = {}
        
        if os.path.exists(self.cookie_file_path):
            logging.info(f"'{self.cookie_file_path}' file found. Using it for yt-dlp.")
            self.cookie_arg = ["--cookie", self.cookie_file_path]
            self.cookie_dict = {"cookiefile": self.cookie_file_path}
        else:
            logging.warning(f"'{self.cookie_file_path}' not found. yt-dlp will run without cookies.")

    async def check_file_size(self, link):
        async def get_format_info(link):
            cmd_args = ["yt-dlp", "-J"] + self.cookie_arg + [link]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                print(f'Error:\n{stderr.decode()}')
                return None
            return json.loads(stdout.decode())

        def parse_size(formats):
            total_size = 0
            for format in formats:
                if 'filesize' in format:
                    total_size += format['filesize']
            return total_size

        info = await get_format_info(link)
        if info is None:
            return None
        
        formats = info.get('formats', [])
        if not formats:
            print("No formats found.")
            return None
        
        total_size = parse_size(formats)
        return total_size

    async def get_instant_stream(self, link: str, video: bool = False):
        """အမြန်ဆုံး stream URL - 1 second အတွင်း"""
        try:
            if video:
                # အမြန်ဆုံး video streaming - အနိမ့်ဆုံး quality
                format_filter = "worst[height<=144][filesize<2M]/worst[height<=240][filesize<5M]"
            else:
                # အမြန်ဆုံး audio streaming - m4a format ကိုဦးစားပေး
                format_filter = "worstaudio[ext=m4a][filesize<1M]/worstaudio[ext=webm][filesize<2M]/worstaudio"
            
            cmd_args = [
                "yt-dlp",
                "-g",
                "-f",
                format_filter,
                "--no-check-certificate",
                "--geo-bypass",
                "--socket-timeout", "2",
            ] + self.cookie_arg + [f"{link}"]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # 2 seconds timeout for ultra fast response
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=2.0)
            
            if stdout:
                stream_url = stdout.decode().split("\n")[0].strip()
                if stream_url and stream_url.startswith('http'):
                    logging.info(f"Instant stream URL found: {stream_url}")
                    return stream_url
                    
        except asyncio.TimeoutError:
            logging.warning(f"Stream URL fetch timeout for {link}")
        except Exception as e:
            logging.error(f"Stream URL error: {e}")
        
        return None

    async def ultra_fast_download(self, link: str, video: bool = False):
        """1 second download အတွက် ultra optimized function"""
        
        # Cache check - ဒီ link ကိုအရင်ဒေါင်းလုပ်ချထားပြီးသားဆိုပြန်သုံး
        cache_key = f"{link}_{'video' if video else 'audio'}"
        if cache_key in self.download_cache:
            cached_file = self.download_cache[cache_key]
            if os.path.exists(cached_file):
                logging.info(f"Using cached file: {cached_file}")
                return cached_file
        
        loop = asyncio.get_running_loop()
        
        def lightning_download():
            """အမြန်ဆုံး download settings"""
            try:
                if video:
                    # Video - အရမ်းသေးတဲ့ size နဲ့ quality
                    format_spec = "worst[height<=144][filesize<2M]/worst[height<=240][filesize<5M]"
                    ext_filter = "mp4"
                else:
                    # Audio - အသေးဆုံး audio format
                    format_spec = "worstaudio[ext=m4a][filesize<1M]/worstaudio[ext=webm][filesize<2M]/worstaudio"
                    ext_filter = "m4a"
                
                ydl_opts = {
                    "format": format_spec,
                    "outtmpl": "downloads/%(id)s.%(ext)s",
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "socket_timeout": 3,
                    "retries": 1,
                    "extractaudio": not video,
                    "audioformat": ext_filter,
                    "noplaylist": True,
                    "max_filesize": 2 * 1024 * 1024 if video else 1 * 1024 * 1024,
                    "http_chunk_size": 4096,
                    "buffersize": 1024,
                    **self.cookie_dict,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Extract info without full download first
                    info = ydl.extract_info(link, download=False)
                    file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                    
                    # If file already exists, return immediately
                    if os.path.exists(file_path):
                        return file_path
                    
                    # Fast download
                    ydl.download([link])
                    
                    # Verify file was downloaded
                    if os.path.exists(file_path):
                        return file_path
                    else:
                        return None
                        
            except Exception as e:
                logging.error(f"Lightning download error: {e}")
                return None

        # Download with short timeout
        try:
            downloaded_file = await asyncio.wait_for(
                loop.run_in_executor(None, lightning_download), 
                timeout=5.0  # 5 seconds timeout for download
            )
            
            # Cache the result
            if downloaded_file and os.path.exists(downloaded_file):
                self.download_cache[cache_key] = downloaded_file
                logging.info(f"Download completed and cached: {downloaded_file}")
                return downloaded_file
                
        except asyncio.TimeoutError:
            logging.warning(f"Download timeout for {link}")
        
        return None

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        # အရင်ဆုံး instant stream ကြိုးစား
        stream_url = await self.get_instant_stream(link, video=True)
        if stream_url:
            return 1, stream_url
        
        # Fallback to original method
        cmd_args = [
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
        ] + self.cookie_arg + [f"{link}"]
            
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
            
        cookie_cmd = f"--cookie {self.cookie_file_path}" if self.cookie_arg else ""
            
        playlist = await shell_cmd(
            f"yt-dlp -i {cookie_cmd} --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
            
        ytdl_opts = {"quiet": True, **self.cookie_dict}
        
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()
        
        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                **self.cookie_dict,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "bestvideo[height<=?360]+bestaudio/best[height<=?360]",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                **self.cookie_dict,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
                **self.cookie_dict,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                **self.cookie_dict,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        # Special song download cases
        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath, True
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath, True

        # Main download logic with ultra fast optimization
        if video:
            # Video download - try ultra fast first
            if await is_on_off(1):
                # Try ultra fast download first
                downloaded_file = await self.ultra_fast_download(link, video=True)
                if downloaded_file:
                    return downloaded_file, True
                else:
                    # Fallback to original download
                    direct = True
                    downloaded_file = await loop.run_in_executor(None, video_dl)
            else:
                # Try instant stream first
                stream_url = await self.get_instant_stream(link, video=True)
                if stream_url:
                    return stream_url, False
                else:
                    # Fallback logic
                    file_size = await self.check_file_size(link)
                    if not file_size:
                        print("None file Size")
                        return None, True
                    total_size_mb = file_size / (1024 * 1024)
                    if total_size_mb > 250:
                        print(f"File size {total_size_mb:.2f} MB exceeds 250MB limit.")
                        return None, True
                    
                    # Try ultra fast download
                    downloaded_file = await self.ultra_fast_download(link, video=True)
                    if downloaded_file:
                        return downloaded_file, True
                    else:
                        direct = True
                        downloaded_file = await loop.run_in_executor(None, video_dl)
        else:
            # Audio download - optimized for 1 second response
            if await is_on_off(1):
                # Mode 1: Try ultra fast download
                downloaded_file = await self.ultra_fast_download(link, video=False)
                if downloaded_file:
                    return downloaded_file, True
                else:
                    # Fallback to original download
                    direct = True
                    downloaded_file = await loop.run_in_executor(None, audio_dl)
            else:
                # Mode 2: Try instant stream first (fastest)
                stream_url = await self.get_instant_stream(link, video=False)
                if stream_url:
                    return stream_url, False
                else:
                    # Fallback to ultra fast download
                    downloaded_file = await self.ultra_fast_download(link, video=False)
                    if downloaded_file:
                        return downloaded_file, True
                    else:
                        # Final fallback
                        direct = True
                        downloaded_file = await loop.run_in_executor(None, audio_dl)
            
        return downloaded_file, direct
