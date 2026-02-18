import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from processor import VideoProcessor

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSETS_PATH = os.getenv("ASSETS_PATH", "./assets")
OUTPUTS_PATH = os.getenv("OUTPUTS_PATH", "./outputs")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

processor = VideoProcessor(assets_path=ASSETS_PATH, outputs_path=OUTPUTS_PATH)

def check_assets():
    """Verify that necessary assets and tools are available."""
    logger.info("Initializing EchoFrame Bot...")
    
    # 1. Check Backgrounds
    bg_dir = os.path.join(ASSETS_PATH, "backgrounds")
    if not os.path.exists(bg_dir) or not any(f.endswith(('.mp4', '.mov', '.avi', '.mkv')) for f in os.listdir(bg_dir)):
        logger.warning(f"⚠️ Warning: Folder '{bg_dir}' is empty or missing. Please add some background videos!")
    else:
        num_bgs = len([f for f in os.listdir(bg_dir) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))])
        logger.info(f"✅ Found {num_bgs} background videos.")

    # 2. Check Frame
    frame_path = os.path.join(ASSETS_PATH, "frames", "frame.png")
    if not os.path.exists(frame_path):
        logger.error(f"❌ Error: Frame overlay missing at '{frame_path}'. Run create_assets.py first.")
        return False
    logger.info("✅ Frame overlay detected.")

    # 3. Check FFmpeg
    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
    try:
        import subprocess
        subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
        logger.info(f"✅ FFmpeg detected at: {ffmpeg_path}")
    except Exception:
        logger.error(f"❌ Error: FFmpeg not found at '{ffmpeg_path}'. Update .env or install FFmpeg.")
        return False
        
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Saya *EchoFrame Bot*.\n\n"
        "Kirimkan video ke saya, dan saya akan mengubahnya menjadi konten vertikal (9:16) "
        "estetis dengan audio dari video Anda dan visual random dari koleksi saya.",
        parse_mode='Markdown'
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received message from {update.effective_user.username}")
    
    # Determine video file
    if update.message.video:
        video = update.message.video
        logger.info(f"Detected video: {video.file_id}")
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        video = update.message.document
        logger.info(f"Detected video document: {video.file_id}")
    else:
        logger.info("Message received but no video detected.")
        return

    msg = await update.message.reply_text("📥 **EchoFrame**: Menerima video... Sedang mengunduh.")
    
    # Download file
    file = await context.bot.get_file(video.file_id)
    input_path = os.path.join(OUTPUTS_PATH, f"input_{video.file_id}.mp4")
    await file.download_to_drive(input_path)
    
    try:
        await msg.edit_text("⚙️ **EchoFrame Status**: \n1. [DONE] Unduh video \n2. [/] Memproses Audio & Visual...")
        
        # Step 1: Extract audio & Process video (Merging into one blocking call for simplicity)
        # We run this in a separate thread to avoid blocking the Telegram event loop
        output_filename = f"echoframe_{video.file_id}.mp4"
        
        # INCREASED TIMEOUT: File processing can take time.
        # to_thread is available in Python 3.9+
        final_path = await asyncio.to_thread(processor.process_video, input_path, output_filename)
        
        if final_path and os.path.exists(final_path):
            await msg.edit_text("⏳ **EchoFrame**: Rendering selesai! Mengirim file...")
            # Use 'with' to ensure the file is closed
            with open(final_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="✨ **EchoFrame Pro Sukses!**\n\nVideo Anda telah diproses dengan frame branding dan visual random.",
                    write_timeout=300 # Increased to 5 minutes for large files
                )
            await msg.delete()
            # Cleanup
            os.remove(final_path)
        else:
            await msg.edit_text("❌ **EchoFrame Error**: Gagal saat merakit video. Pastikan FFmpeg path benar dan folder backgrounds tidak kosong.")
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        await msg.edit_text("❌ Error: Koneksi ke Telegram timeout. File mungkin terlalu besar.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await msg.edit_text(f"❌ Terjadi kesalahan sistem: `{str(e)}`")
    finally:
        # Cleanup input
        if os.path.exists(input_path):
            os.remove(input_path)

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)
        
    if not check_assets():
        print("Initialization failed. Please check the logs above.")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    video_handler = MessageHandler(filters.VIDEO | filters.Document.Category("video"), handle_video)
    
    application.add_handler(start_handler)
    application.add_handler(video_handler)
    
    logger.info("EchoFrame Bot started...")
    application.run_polling()
