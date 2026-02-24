import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
from dotenv import load_dotenv
from processor import VideoProcessor
from database import DatabaseManager

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSETS_PATH = os.getenv("ASSETS_PATH", "./assets")
OUTPUTS_PATH = os.getenv("OUTPUTS_PATH", "./outputs")
MAX_INPUT_MB = 20   # Batas unduh bot (limit Telegram getFile); video yang dikirim user harus ≤ ini
MAX_VIDEO_MB = 50   # Batas ukuran hasil saat kirim balik ke user (limit Telegram sendVideo)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialization
db = DatabaseManager()
processor = VideoProcessor(assets_path=ASSETS_PATH, outputs_path=OUTPUTS_PATH)
job_queue = asyncio.Queue()

def get_main_menu():
    keyboard = [
        [KeyboardButton("🖼 Hanya Frame"), KeyboardButton("📹 Full Echo")],
        [KeyboardButton("📊 Status Kerja"), KeyboardButton("📜 Riwayat")],
        [KeyboardButton("🧹 Cleanup"), KeyboardButton("❓ Bantuan")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def check_assets():
    """Verify that necessary assets and tools are available."""
    logger.info("Initializing EchoFrame Bot...")
    bg_dir = os.path.join(ASSETS_PATH, "backgrounds")
    if not os.path.exists(bg_dir) or not any(f.endswith(('.mp4', '.mov', '.avi', '.mkv')) for f in os.listdir(bg_dir)):
        logger.warning(f"Warning: Folder '{bg_dir}' is empty.")
    
    frame_path = os.path.join(ASSETS_PATH, "frames", "frame.png")
    if not os.path.exists(frame_path):
        logger.error(f"Error: Frame overlay missing at '{frame_path}'.")
        return False

    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
    try:
        import subprocess
        subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
    except Exception:
        logger.error(f"Error: FFmpeg not found at '{ffmpeg_path}'.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_chat.id, update.effective_user.username)
    context.user_data['frame_only'] = False  # default = Full Echo
    await update.message.reply_text(
        "Halo! Saya *EchoFrame Bot*.\n\n"
        "*Default:* Langsung kirim video = *Full Echo* (vertikal 9:16 + background + frame).\n\n"
        "Atau pilih *🖼 Hanya Frame* kalau mau cuma tambah frame saja.",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*Panduan Penggunaan EchoFrame Bot*:\n\n"
        "• *Default*: Kalau cuma kirim video (tanpa pilih mode) = *Full Echo* (9:16 + background + frame).\n"
        "• *🖼 Hanya Frame*: Pilih ini dulu kalau mau output cuma video + frame saja (ukuran = ukuran frame).\n"
        "• *📹 Full Echo*: Pilih ini untuk konversi vertikal dengan background acak + frame.\n\n"
        "Kirim file video ke chat. Cek status atau histori lewat menu di bawah."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def set_frame_only(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['frame_only'] = True
    await update.message.reply_text(
        "Mode: *Hanya Frame*. Kirim video ke sini, bot hanya akan menambah frame overlay. Ukuran output mengikuti ukuran frame.",
        parse_mode='Markdown'
    )

async def set_full_echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['frame_only'] = False
    await update.message.reply_text(
        "Mode: *Full Echo*. Kirim video untuk konversi vertikal 9:16 dengan background acak + frame.",
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_jobs = db.get_active_jobs(update.effective_chat.id)
    if not active_jobs:
        await update.message.reply_text("Anda tidak memiliki pekerjaan yang sedang berjalan/mengantre.")
        return
    
    text = "*Pekerjaan Aktif Anda*:\n"
    for job in active_jobs:
        pos = db.get_queue_position(job[0])
        text += f"- Job #{job[0]}: {job[1]} (Urutan: {pos})\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = db.get_user_history(update.effective_chat.id)
    if not history:
        await update.message.reply_text("Anda belum memiliki riwayat video yang sukses.")
        return
    
    text = "*5 Video Terakhir Anda*:\n"
    for item in history:
        text += f"- Job #{item[0]}: Selesai pada {item[2]}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

def cleanup_old_outputs(days=3):
    """
    Cleanup file output lama dan entry database.
    Returns: (deleted_jobs_count, deleted_files_count)
    """
    deleted_jobs, jobs_data = db.cleanup_old_jobs(days=days)
    deleted_files = 0
    
    for job_id, output_path, input_path in jobs_data:
        # Hapus output file jika ada
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
                deleted_files += 1
            except Exception as e:
                logger.warning(f"Gagal hapus output file {output_path}: {e}")
        
        # Hapus input file jika masih ada (seharusnya sudah dihapus di worker, tapi jaga-jaga)
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
                deleted_files += 1
            except Exception as e:
                logger.warning(f"Gagal hapus input file {input_path}: {e}")
    
    return deleted_jobs, deleted_files

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command untuk cleanup manual."""
    days = 3
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
            if days < 1:
                days = 3
        except ValueError:
            days = 3
    
    await update.message.reply_text(f"Cleanup: Menghapus data & file lebih dari {days} hari...")
    deleted_jobs, deleted_files = await asyncio.to_thread(cleanup_old_outputs, days)
    await update.message.reply_text(
        f"✅ Cleanup selesai!\n"
        f"- Jobs dihapus: {deleted_jobs}\n"
        f"- File dihapus: {deleted_files}",
        parse_mode='Markdown'
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        video = update.message.video
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        video = update.message.document
    else:
        return

    # Cek ukuran jika tersedia (Telegram getFile max 20MB)
    if getattr(video, "file_size", None) and video.file_size > MAX_INPUT_MB * 1024 * 1024:
        await update.message.reply_text(
            f"Video terlalu besar untuk diunduh bot. Maksimal *{MAX_INPUT_MB}MB* (batas Telegram).",
            parse_mode="Markdown"
        )
        return

    input_filename = f"input_{video.file_id}.mp4"
    input_path = os.path.join(OUTPUTS_PATH, input_filename)

    msg = await update.message.reply_text("EchoFrame: Mengunduh video...")
    try:
        file = await context.bot.get_file(video.file_id)
        await file.download_to_drive(input_path)
    except BadRequest as e:
        if "too big" in str(e).lower() or "file" in str(e).lower():
            await msg.edit_text(
                f"Video terlalu besar untuk diunduh bot. Maksimal *{MAX_INPUT_MB}MB* (batas Telegram). "
                "Kompres video atau kirim yang lebih kecil.",
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(f"Gagal mengunduh: {e.message}")
        return

    job_id = db.create_job(update.effective_chat.id, input_path)
    pos = db.get_queue_position(job_id)
    frame_only = context.user_data.get('frame_only', False)

    mode_label = "Hanya Frame" if frame_only else "Full Echo"
    await msg.edit_text(
        f"EchoFrame: Berhasil masuk antrean! \nJob ID: *#{job_id}* \nMode: *{mode_label}* \nUrutan ke: *{pos}*",
        parse_mode='Markdown'
    )

    # Put in queue for worker
    await job_queue.put({
        'job_id': job_id,
        'chat_id': update.effective_chat.id,
        'msg_id': msg.message_id,
        'input_path': input_path,
        'frame_only': frame_only,
    })

async def worker():
    """Background worker to process jobs one by one."""
    logger.info("Background Worker started...")
    while True:
        job_data = await job_queue.get()
        job_id = job_data['job_id']
        chat_id = job_data['chat_id']
        msg_id = job_data['msg_id']
        input_path = job_data['input_path']
        frame_only = job_data.get('frame_only', False)

        try:
            db.update_job_status(job_id, 'PROCESSING')
            from telegram import Bot
            bot = Bot(TOKEN)

            status_label = "Menambah frame..." if frame_only else "Merakit Video..."
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"EchoFrame Status Job *#{job_id}*: \n- [DONE] Unduh \n- [/] {status_label}",
                parse_mode='Markdown'
            )

            output_filename = f"echoframe_{job_id}.mp4"
            if frame_only:
                final_path = await asyncio.to_thread(processor.process_video_frame_only, input_path, output_filename, crf=28)
            else:
                final_path = await asyncio.to_thread(processor.process_video, input_path, output_filename, crf=28)

            if final_path and os.path.exists(final_path):
                file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
                
                # If STILL too big, try high compression
                if file_size_mb > 50:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg_id,
                        text=f"EchoFrame Job *#{job_id}*: File terlalu besar ({file_size_mb:.1f}MB). Mengompres ulang...",
                        parse_mode='Markdown'
                    )
                    if frame_only:
                        final_path = await asyncio.to_thread(processor.process_video_frame_only, input_path, output_filename, crf=32)
                    else:
                        final_path = await asyncio.to_thread(processor.process_video, input_path, output_filename, crf=32)
                    file_size_mb = os.path.getsize(final_path) / (1024 * 1024)

                if file_size_mb > 50:
                    raise Exception(f"Ukuran video ({file_size_mb:.1f}MB) melebihi batas 50MB Telegram Bot API.")

                db.update_job_status(job_id, 'COMPLETED', output_path=final_path)
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"EchoFrame Job *#{job_id}*: Selesai! Mengirim...")
                mode_caption = "Hanya Frame" if frame_only else "Full Echo"
                with open(final_path, 'rb') as vf:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=vf,
                        caption=f"*EchoFrame – {mode_caption}*\nJob ID: #{job_id}",
                        parse_mode='Markdown',
                        write_timeout=300
                    )
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                if os.path.exists(final_path):
                    os.remove(final_path)
            else:
                raise Exception("Rendering gagal")

        except Exception as e:
            logger.error(f"Worker Error on Job {job_id}: {e}")
            db.update_job_status(job_id, 'FAILED', error_msg=str(e))
            try:
                from telegram import Bot
                bot = Bot(TOKEN)
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"EchoFrame Error pada Job *#{job_id}*: {str(e)}", parse_mode='Markdown')
            except: pass
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            job_queue.task_done()

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found")
        exit(1)
        
    if not check_assets():
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('jobs', status_command))
    application.add_handler(CommandHandler('history', history_command))
    application.add_handler(CommandHandler('cleanup', cleanup_command))
    
    # Button Handlers
    application.add_handler(MessageHandler(filters.Text("🖼 Hanya Frame"), set_frame_only))
    application.add_handler(MessageHandler(filters.Text("📹 Full Echo"), set_full_echo))
    application.add_handler(MessageHandler(filters.Text("📊 Status Kerja"), status_command))
    application.add_handler(MessageHandler(filters.Text("📜 Riwayat"), history_command))
    application.add_handler(MessageHandler(filters.Text("🧹 Cleanup"), cleanup_command))
    application.add_handler(MessageHandler(filters.Text("❓ Bantuan"), help_command))
    
    # Video Handler
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.Category("video"), handle_video))
    
    # Start worker as a background task
    loop = asyncio.get_event_loop()
    loop.create_task(worker())
    
    # Auto-cleanup saat bot start (opsional, bisa di-comment jika tidak mau)
    logger.info("Running initial cleanup...")
    try:
        deleted_jobs, deleted_files = cleanup_old_outputs(days=3)
        logger.info(f"Initial cleanup: {deleted_jobs} jobs, {deleted_files} files deleted")
    except Exception as e:
        logger.warning(f"Initial cleanup error: {e}")
    
    logger.info("EchoFrame Bot with Queue started...")
    application.run_polling()
