"""REST API untuk EchoFrame — dipakai web lain via HTTP + X-API-Key."""
import os
import uuid
import asyncio
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from database import DatabaseManager

load_dotenv()

API_KEY = os.getenv("API_KEY", "")
OUTPUTS_PATH = os.getenv("OUTPUTS_PATH", "./outputs")

db = DatabaseManager()

# Di-set oleh bot.py saat startup (satu proses, satu loop asyncio)
job_queue: Optional[asyncio.Queue] = None

def set_queue(q: asyncio.Queue):
    global job_queue
    job_queue = q


def check_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    # Kalau API_KEY kosong di .env -> auth dinonaktifkan (mode lokal)
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid X-API-Key")
    return True


app = FastAPI(title="EchoFrame API", version="1.0.0")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    frame_only: bool = Form(default=False),
    notify_chat_id: int = Form(default=0),
    _auth: bool = Depends(check_api_key),
):
    if job_queue is None:
        raise HTTPException(status_code=503, detail="Worker belum siap")

    if not file.content_type or not file.content_type.startswith("video/"):
        # tetap terima by ekstensi, karena sebagian client kirim octet-stream
        if not (file.filename or "").lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            raise HTTPException(status_code=400, detail="File harus video")

    os.makedirs(OUTPUTS_PATH, exist_ok=True)
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    input_filename = f"input_api_{uuid.uuid4().hex}{ext}"
    input_path = os.path.join(OUTPUTS_PATH, input_filename)

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video maksimal 20MB (limit Telegram getFile)")
    with open(input_path, "wb") as f:
        f.write(content)

    # user_id 0 = job dari API/web; atau pakai notify_chat_id supaya tercatat di histori user Telegram
    user_id = notify_chat_id or 0
    db.add_user(user_id, "api")
    job_id = db.create_job(user_id, input_path)
    pos = db.get_queue_position(job_id)

    await job_queue.put({
        "job_id": job_id,
        "chat_id": notify_chat_id or 0,
        "msg_id": None,
        "input_path": input_path,
        "frame_only": bool(frame_only),
        "via_api": True,
    })

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "queue_position": pos,
        "frame_only": bool(frame_only),
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, _auth: bool = Depends(check_api_key)):
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, status, output_path, error_msg, created_at, finished_at FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")

    _id, user_id, status, output_path, error_msg, created_at, finished_at = row
    out = {
        "job_id": _id,
        "user_id": user_id,
        "status": status,
        "error": error_msg,
        "created_at": created_at,
        "finished_at": finished_at,
        "queue_position": db.get_queue_position(_id) if status == "QUEUED" else 0,
        "download_url": f"/api/jobs/{_id}/download" if status == "COMPLETED" and output_path and os.path.exists(output_path) else None,
    }
    return out


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: int, _auth: bool = Depends(check_api_key)):
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, output_path FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    status, output_path = row
    if status != "COMPLETED" or not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=409, detail=f"Belum bisa diunduh (status={status})")
    return FileResponse(output_path, media_type="video/mp4", filename=f"echoframe_{job_id}.mp4")
