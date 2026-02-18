import subprocess
import os
import random
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

class VideoProcessor:
    def __init__(self, assets_path="./assets", outputs_path="./outputs"):
        self.assets_path = assets_path
        self.outputs_path = outputs_path
        self.backgrounds_path = os.path.join(assets_path, "backgrounds")
        self.frames_path = os.path.join(assets_path, "frames")
        os.makedirs(outputs_path, exist_ok=True)

    def get_duration(self, file_path):
        """Get duration of a media file using ffprobe."""
        import shutil
        # Robustly find ffprobe relative to ffmpeg
        if os.path.isabs(FFMPEG_PATH):
            dir_name = os.path.dirname(FFMPEG_PATH)
            base_name = os.path.basename(FFMPEG_PATH)
            ffprobe_name = base_name.replace("ffmpeg", "ffprobe").replace("FFMPEG", "FFPROBE")
            ffprobe_path = os.path.join(dir_name, ffprobe_name)
            
            # If not found in same directory, try system path
            if not os.path.exists(ffprobe_path):
                ffprobe_path = shutil.which("ffprobe") or "ffprobe"
        else:
            ffprobe_path = FFMPEG_PATH.replace("ffmpeg", "ffprobe").replace("FFMPEG", "FFPROBE")
            if not shutil.which(ffprobe_path):
                ffprobe_path = "ffprobe"
        
        cmd = [
            ffprobe_path, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except FileNotFoundError:
            logger.error(f"Error: {ffprobe_path} not found. Please install FFmpeg and add it to your PATH.")
            return None
        except Exception as e:
            logger.error(f"Error getting duration for {file_path}: {e}")
            return None

    def extract_audio(self, video_path, output_audio_path):
        """Extract audio from video."""
        cmd = [
            FFMPEG_PATH, "-i", video_path, "-vn", "-acodec", "libmp3lame", "-y", output_audio_path
        ]
        try:
            # We use capture_output=True here because we don't want audio extraction logs flooding 
            # if we just want the main video processing logs to be visible.
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except FileNotFoundError:
            logger.error(f"Error: {FFMPEG_PATH} not found. Please install FFmpeg and add it to your PATH.")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting audio: {e.stderr.decode()}")
            return False

    def process_video(self, input_video_path, output_filename):
        """Main processing logic."""
        audio_path = os.path.join(self.outputs_path, "temp_audio.mp3")
        if not self.extract_audio(input_video_path, audio_path):
            return None

        audio_duration = self.get_duration(audio_path)
        if audio_duration is None:
            return None

        # Pick random background
        backgrounds = [f for f in os.listdir(self.backgrounds_path) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
        if not backgrounds:
            logger.error("No background videos found in assets/backgrounds")
            return None
        
        bg_file = random.choice(backgrounds)
        bg_path = os.path.join(self.backgrounds_path, bg_file)
        bg_duration = self.get_duration(bg_path)
        
        frame_path = os.path.join(self.frames_path, "frame.png")
        if not os.path.exists(frame_path):
            logger.error("Frame overlay not found in assets/frames/frame.png")
            return None

        output_path = os.path.join(self.outputs_path, output_filename)

        # Build FFmpeg command
        # Logic:
        # 1. Scale background to fill 1080x1920 (crop if necessary)
        # 2. Loop background if duration < audio
        # 3. Overlay frame.png
        # 4. Add audio from extracted mp3
        # 5. Trim to audio length (-shortest)
        
        # FFmpeg filter complex:
        # [0:v] scale to 1080x1920 while maintaining aspect ratio, then crop center
        # [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[vbg];
        # [vbg][1:v]overlay=0:0[vout]
        
        filter_complex = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[vbg];"
            "[vbg][1:v]overlay=0:0[vout]"
        )

        cmd = [
            FFMPEG_PATH,
            "-stream_loop", "-1", "-i", bg_path,     # Input 0: Background (looped)
            "-i", frame_path,                         # Input 1: Frame Overlay
            "-i", audio_path,                         # Input 2: Audio
            "-filter_complex", filter_complex,
            "-map", "[vout]",                         # Map processed video
            "-map", "2:a",                            # Map audio from input 2
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",                              # Finish when the shortest stream (audio) ends
            "-y",                                     # Overwrite output
            output_path
        ]

        try:
            logger.info(f"Starting FFmpeg processing for {output_path}")
            # Use subprocess.run without capture_output to let it stream to terminal, 
            # or pipe it manually if you want to capture it. 
            # For server/production, streaming to stdout is usually preferred for logs.
            subprocess.run(cmd, check=True)
            return output_path
        except FileNotFoundError:
            logger.error(f"Error: {FFMPEG_PATH} not found. Please install FFmpeg and add it to your PATH.")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg Error occurred")
            return None
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
