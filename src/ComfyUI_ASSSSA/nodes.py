import datetime
import logging
import os
import re
import subprocess

import folder_paths


class FFMpegSettingsNode:
    def __init__(self):
        self.ffmpeg_options = {
            "format": "mp4",
            "codec": "copy",
            "resolution": "source",
            "framerate": "source",
            "audio_codec": "copy",
            "audio_bitrate": "192k",
            "preset": "medium",
            "crf": "23",
            "additional_params": "",
        }

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "format": (
                    [
                        "mp4",
                        "mkv",
                        "mov",
                        "avi",
                        "webm",
                        "gif",
                        "flv",
                        "wmv",
                        "ts",
                        "mxf",
                    ],
                    {"default": "mkv", "tooltip": "Output container format"},
                ),
                "codec": (
                    [
                        "copy",  # Copy codec from source
                        "libx264",
                        "libx265",
                        "libvpx-vp9",
                        "libvpx",
                        "prores_ks",
                        "dnxhd",
                        "av1",
                        "h264_nvenc",
                        "hevc_nvenc",
                        "h264_videotoolbox",
                        "hevc_videotoolbox",
                        "prores_videotoolbox",
                        "libaom-av1",
                        "libsvtav1",
                        "mpeg2video",
                        "mpeg4",
                    ],
                    {
                        "default": "copy",
                        "tooltip": "Video codec to use for encoding, use 'copy' to keep source codec.",
                    },
                ),
                "resolution": (
                    "STRING",
                    {
                        "default": "source",
                        "multiline": False,
                        "tooltip": "Output resolution in format WIDTHxHEIGHT or 'source' to keep original resolution",
                    },
                ),
                "framerate": (
                    "STRING",
                    {
                        "default": "source",
                        "multiline": False,
                        "tooltip": "Target frame rate or 'source' to keep original",
                    },
                ),
                "preset": (
                    [
                        "ultrafast",
                        "superfast",
                        "veryfast",
                        "faster",
                        "fast",
                        "medium",
                        "slow",
                        "slower",
                        "veryslow",
                    ],
                    {
                        "default": "medium",
                        "tooltip": "Encoding preset (speed vs quality tradeoff)",
                    },
                ),
                "crf": (
                    "INT",
                    {
                        "default": 23,
                        "min": 0,
                        "max": 51,
                        "step": 1,
                        "tooltip": "Constant Rate Factor: lower values = higher quality",
                    },
                ),
            },
            "optional": {
                "audio_codec": (
                    [
                        "copy",
                        "aac",
                        "mp3",
                        "opus",
                        "flac",
                        "none",
                        "vorbis",
                        "ac3",
                        "eac3",
                        "libfdk_aac",
                        "pcm_s16le",
                        "pcm_s24le",
                        "pcm_f32le",
                    ],
                    {
                        "default": "copy",
                        "tooltip": "Audio codec to use for encoding, use 'copy' to keep source codec",
                    },
                ),
                "audio_bitrate": (
                    [
                        "source",
                        "64k",
                        "96k",
                        "128k",
                        "160k",
                        "192k",
                        "224k",
                        "256k",
                        "320k",
                        "384k",
                        "448k",
                        "512k",
                    ],
                    {
                        "default": "source",
                        "tooltip": "Audio bitrate for encoding or 'source' to maintain original",
                    },
                ),
                "additional_params": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Additional FFmpeg parameters (advanced)",
                    },
                ),
            },
        }

    RETURN_TYPES = ("FFMPEG_SETTINGS",)
    RETURN_NAMES = ("settings",)
    FUNCTION = "get_settings"
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = "Configure FFmpeg settings for video processing with advanced options"

    def get_settings(
        self,
        format,
        codec,
        resolution,
        framerate,
        preset,
        crf,
        audio_codec="copy",
        audio_bitrate="192k",
        additional_params="",
    ):
        settings = {
            "format": format,
            "codec": codec,
            "resolution": resolution,
            "framerate": framerate,
            "preset": preset,
            "crf": crf,
            "audio_codec": audio_codec,
            "audio_bitrate": audio_bitrate,
            "additional_params": additional_params.strip() if additional_params else "",
        }
        return (settings,)


class VideoTranscodingNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_path": ("STRING", {"multiline": False, "default": "input.mp4"}),
                "filename_prefix": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "Transcoded",
                        "tooltip": "Prefix for the output video file",
                    },
                ),
                "settings": ("FFMPEG_SETTINGS",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "transcode_video"
    OUTPUT_NODE = True
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = "Transcode video using FFmpeg settings"

    def transcode_video(self, video_path, filename_prefix, settings):
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        if filename_prefix.strip() == "":
            output_path = os.path.join(
                folder_paths.get_output_directory(),
                f"{video_basename}.{settings['format']}",
            )
        else:
            output_path = os.path.join(
                folder_paths.get_output_directory(),
                f"{filename_prefix}_{video_basename}{settings['format']}",
            )
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(video_path):
            logging.error("Error: Input file '{video_path}' not found")
            return (output_path,)

        try:
            # Build the ffmpeg command based on settings
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i",
                video_path,
            ]

            # Add video codec and parameters
            if settings["codec"] != "copy":
                cmd += ["-c:v", settings["codec"]]
                # Only apply these settings when not copying
                if settings["resolution"] != "source":
                    cmd += ["-vf", f"scale={settings['resolution']}"]
                if settings["framerate"] != "source":
                    cmd += ["-r", settings["framerate"]]
                if settings["preset"]:
                    cmd += ["-preset", settings["preset"]]
                if settings["crf"]:
                    cmd += ["-crf", str(settings["crf"])]
            else:
                # When copying, just set the codec
                cmd += ["-c:v", "copy"]

            # Add audio codec and bitrate
            if settings["audio_codec"] != "copy":
                cmd += ["-c:a", settings["audio_codec"]]
                if settings["audio_bitrate"] != "source":
                    cmd += ["-b:a", settings["audio_bitrate"]]
            else:
                cmd += ["-c:a", "copy"]

            # Add additional parameters
            if settings["additional_params"]:
                cmd += settings["additional_params"].split()

            # Set output file path
            cmd.append(output_path)

            # Run the command
            logging.info(f"Running command: {" ".join(cmd)}")
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if process.returncode != 0:
                logging.error(f"FFmpeg error: {process.stderr}")
                return (output_path,)
            else:
                logging.info(f"Video transcoded to: {output_path}")
                return (output_path,)
        except Exception as e:
            logging.error(f"Error transcoding video: {str(e)}")
            return (output_path,)


class SubtitleExtractionNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_path": ("STRING", {"multiline": False, "default": "video.mp4"}),
                "stream": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 100,
                        "step": 1,
                        "tooltip": "Subtitle stream index to extract (0 for first stream)",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "extract_subtitles"
    OUTPUT_NODE = True
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = "Extract subtitles from video file"

    def extract_subtitles(self, video_path, stream=0):
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        # Create output path with video name included
        output_path = os.path.join(
            folder_paths.get_temp_directory(), f"{video_basename}"
        )
        # Check if the video file exists
        if not os.path.exists(video_path):
            logging.error(f"Error: Video file '{video_path}' not found")
            return (output_path,)
        check_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_name,codec_type,codec_tag_string",
            "-of",
            "default=noprint_wrappers=1",
            video_path,
        ]
        try:
            logging.info(f"Running command: {check_cmd}")
            process = subprocess.run(
                check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if process.returncode != 0:
                logging.error(f"FFprobe error: {process.stderr}")
                return (output_path,)
            else:
                # get indet and codec_name from output
                subtitle_streams = []
                for line in process.stdout.splitlines():
                    if line.startswith("index="):
                        index = line.split("=")[1].strip()
                    elif line.startswith("codec_name="):
                        codec_name = line.split("=")[1].strip()
                        subtitle_streams.append((index, codec_name))
                if not subtitle_streams:
                    logging.error("No subtitle streams found in the video file.")
                    return (output_path,)
                else:
                    output_path += f".{subtitle_streams[stream][1]}"
        except subprocess.CalledProcessError:
            logging.error(f"Error checking subtitle streams: {process.stderr}")
            return (output_path,)
        # "ffmpeg -i input.mkv -map 0:s:0 subs.ass"
        # Build the ffmpeg command to extract subtitles
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i",
            video_path,
            "-map",
            f"0:s:{stream}",  # Map the first subtitle stream
            f"{output_path}",  # Output file path
        ]
        try:
            # Run the command
            logging.info(f"Running command: {" ".join(cmd)}")
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if process.returncode != 0:
                logging.error(f"FFmpeg error: {process.stderr}")
                return (output_path,)
            else:
                logging.info(f"Subtitles extracted to: {output_path}")
        except Exception as e:
            logging.error(f"Error extracting subtitles: {str(e)}")
            return (output_path,)
        return (output_path,)


class SubtitleEmbeddingNode:
    def __init__(self):
        self.default_settings = {
            "format": "mkv",
            "codec": "copy",
            "resolution": "source",
            "framerate": "source",
            "audio_codec": "copy",
            "audio_bitrate": "192k",
            "preset": "medium",
            "crf": 20,
            "additional_params": "",
        }

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_path": ("STRING", {"multiline": False, "default": "video.mp4"}),
                "subtitle_path": (
                    "STRING",
                    {"multiline": False, "default": "subtitles.srt"},
                ),
                "filename_prefix": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "Embedded",
                        "tooltip": "Prefix for the output video file",
                    },
                ),
                "embed_method": (["soft", "hard"], {"default": "soft"}),
            },
            "optional": {
                "settings": ("FFMPEG_SETTINGS",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "embed_subtitles"
    OUTPUT_NODE = True
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = "Embed subtitles into video"

    def embed_subtitles(
        self, video_path, subtitle_path, filename_prefix, embed_method, settings={}
    ):
        if settings is None or settings == {}:
            settings = self.default_settings
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        if filename_prefix.strip() == "":
            output_path = os.path.join(
                folder_paths.get_output_directory(),
                f"{video_basename}.{settings['format']}",
            )
        else:
            output_path = os.path.join(
                folder_paths.get_output_directory(),
                f"{filename_prefix}_{video_basename}.{settings['format']}",
            )
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Implementation would go here
        # ffmpeg -i input.mp4 -vf "subtitles=subtitle.ass" -c:a copy output.mp4
        if not os.path.exists(video_path):
            logging.error(f"Error: Video file '{video_path}' not found")
            return (output_path,)
        if not os.path.exists(subtitle_path):
            logging.error(f"Error: Subtitle file '{subtitle_path}' not found")
            return (output_path,)
        if embed_method not in ["soft", "hard"]:
            logging.error(f"Error: Invalid embed method '{embed_method}'")
            return (output_path,)
        # Determine subtitle format based on file extension
        # subtitle_format = os.path.splitext(subtitle_path)[1][1:].lower()
        if embed_method == "soft":
            # Build the ffmpeg command to embed subtitles
            if settings["format"] != "mkv":
                logging.error("Error: Soft embedding is only supported for MKV format.")
                return (output_path,)
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i",
                video_path,
                "-i",
                subtitle_path,
                # f"-c:s {subtitle_format}",
            ]

            # Add video codec and parameters
            if settings["codec"] != "copy":
                cmd += ["-c:v", settings["codec"]]
                # Only apply these settings when not copying
                if settings["resolution"] != "source":
                    cmd += ["-vf", f"scale={settings['resolution']}"]
                if settings["framerate"] != "source":
                    cmd += ["-r", settings["framerate"]]
                if settings["preset"]:
                    cmd += ["-preset", settings["preset"]]
                if settings["crf"]:
                    cmd += ["-crf", str(settings["crf"])]
            else:
                # When copying, just set the codec
                cmd += ["-c:v", "copy"]

            # Add audio codec and bitrate
            if settings["audio_codec"] != "copy":
                cmd += ["-c:a", settings["audio_codec"]]
                if settings["audio_bitrate"] != "source":
                    cmd += ["-b:a", settings["audio_bitrate"]]
            else:
                cmd += ["-c:a", "copy"]

            if settings["additional_params"]:
                cmd += settings["additional_params"].split()

            cmd.append(output_path)

        elif embed_method == "hard":
            # Build the ffmpeg command to embed subtitles
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i",
                video_path,
                "-vf",
                f"subtitles={subtitle_path}",
            ]
            # Add video codec and parameters
            if settings["codec"] != "copy":
                cmd += ["-c:v", settings["codec"]]
                if settings["resolution"] != "source":
                    cmd += ["-vf", f"scale={settings['resolution']}"]
                if settings["framerate"] != "source":
                    cmd += ["-r", settings["framerate"]]
                if settings["preset"]:
                    cmd += ["-preset", settings["preset"]]
                if settings["crf"]:
                    cmd += ["-crf", str(settings["crf"])]

            # Add audio codec and bitrate
            if settings["audio_codec"] != "copy":
                cmd += ["-c:a", settings["audio_codec"]]
                if settings["audio_bitrate"] != "source":
                    cmd += ["-b:a", settings["audio_bitrate"]]

            # Set output file path
            cmd.append(output_path)

        try:
            # Run the command
            logging.info(f"Running command: {" ".join(cmd)}")
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if process.returncode != 0:
                logging.error(f"FFmpeg error: {process.stderr}")
                return (output_path,)
            else:
                logging.info(f"Subtitles embedded to: {output_path}")
                return (output_path,)
        except Exception as e:
            logging.error(f"Error embedding subtitles: {str(e)}")
            return (output_path,)


class ASSSubtitleReaderNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "ass_file_path": (
                    "STRING",
                    {"multiline": False, "default": "subtitles.ass"},
                ),
            },
            "optional": {
                "encoding": (
                    [
                        "utf-8",
                        "utf-8-sig",
                        "latin-1",
                        "cp1252",
                        "shift-jis",
                        "euc-jp",
                        "gbk",
                        "big5",
                    ],
                    {
                        "default": "utf-8",
                        "tooltip": "Character encoding of the ASS file",
                    },
                ),
                "max_lines": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10000,
                        "step": 1,
                        "tooltip": "Maximum number of lines to read (0 = all lines)",
                    },
                ),
                "filter_style": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "tooltip": "Only include lines with this style name (leave empty for all styles)",
                    },
                ),
                "strip_formatting": (
                    ["True", "False"],
                    {
                        "default": "False",
                        "tooltip": "Remove ASS formatting codes from text",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("all_text", "dialog_only", "styles_info")
    FUNCTION = "read_ass"
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = "Read ASS subtitle file contents with formatting options"

    def read_ass(
        self,
        ass_file_path,
        encoding="utf-8",
        max_lines=0,
        filter_style="",
        strip_formatting="False",
    ):
        if not os.path.exists(ass_file_path):
            logging.error(f"Error: ASS file '{ass_file_path}' not found")
            return ("", "", "")
        try:
            with open(ass_file_path, "r", encoding=encoding) as file:
                content = file.read()

            # Parse sections

            current_section = None
            dialog_lines = []
            styles_info = []

            for line in content.splitlines():
                line = line.strip()
                # Track sections
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1]
                    continue

                # Process dialog lines
                if current_section == "Events" and line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) >= 10:
                        style = parts[3].strip()
                        text = parts[9].strip()

                        # Apply filters
                        if filter_style and style != filter_style:
                            continue

                        # Strip formatting if requested
                        if strip_formatting == "True":
                            # Remove ASS formatting codes like {\\...}
                            text = re.sub(r"{\\[^}]*}", "", text)

                        dialog_lines.append(text)

                # Collect styles information
                if current_section == "V4+ Styles" and line.startswith("Style:"):
                    styles_info.append(line)

            # Apply max_lines limit if set
            if max_lines > 0:
                dialog_lines = dialog_lines[:max_lines]

            dialog_text = "\n".join(dialog_lines)
            styles_text = "\n".join(styles_info)

            return (content, dialog_text, styles_text)

        except Exception as e:
            logging.error(f"Error reading ASS file: {str(e)}")
            return (f"Error: {str(e)}", "", "")


class ASSSubtitleCacheNode:
    """
    Save received string to subtitle file (.ass or .srt) in cache.
    """

    def __init__(self):
        self.cache_dir = folder_paths.get_temp_directory()
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "subtitle_text": ("STRING", {"multiline": True, "default": ""}),
                "filename_prefix": (
                    "STRING",
                    {"multiline": False, "default": "subs/ComfyUI"},
                ),
                "format": (
                    ["ass", "srt"],
                    {"default": "ass", "tooltip": "Subtitle format"},
                ),
            },
            "optional": {
                "encoding": (
                    [
                        "utf-8",
                        "utf-8-sig",
                        "latin-1",
                        "cp1252",
                        "shift-jis",
                        "euc-jp",
                        "gbk",
                        "big5",
                    ],
                    {
                        "default": "utf-8",
                        "tooltip": "Character encoding for the subtitle file",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    FUNCTION = "save_subtitle"
    OUTPUT_NODE = True
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = (
        "Save string content to a subtitle file (.ass or .srt) in cache directory"
    )

    def save_subtitle(
        self, subtitle_text, filename_prefix, format="ass", encoding="utf-8"
    ):
        filename_prefix += self.prefix_append
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.{format}"

        # Create full filepath in cache directory
        filepath = os.path.join(self.cache_dir, filename)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, mode="w", encoding=encoding) as f:
                f.write(subtitle_text)

            logging.info(f"Subtitle saved to: {filepath}")
            return (filepath,)

        except Exception as e:
            logging.error(f"Error saving {format} file: {str(e)}")
            return (filepath,)


class MultilineTextInputNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Enter your text here...",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    CATEGORY = "ComfyUI_ASSSSA"
    DESCRIPTION = (
        "A simple multiline text input node for entering and storing text content"
    )

    def process_text(self, text):
        return (text,)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "FFMpegSettings": FFMpegSettingsNode,
    "VideoTranscoding": VideoTranscodingNode,
    "SubtitleExtraction": SubtitleExtractionNode,
    "SubtitleEmbedding": SubtitleEmbeddingNode,
    "ASSSubtitleReader": ASSSubtitleReaderNode,
    "ASSSubtitleCache": ASSSubtitleCacheNode,
    "MultilineTextInput": MultilineTextInputNode,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "FFMpegSettings": "FFmpeg Settings",
    "VideoTranscoding": "Video Transcoding",
    "SubtitleExtraction": "Subtitle Extraction",
    "SubtitleEmbedding": "Subtitle Embedding",
    "ASSSubtitleReader": "Load ASS Subtitles",
    "ASSSubtitleCache": "Temporary save subtitle file",
    "MultilineTextInput": "Multi line Input",
}
