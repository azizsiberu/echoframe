# 🎬 EchoFrame Bot

**EchoFrame** is a powerful Telegram bot designed to transform standard videos into aesthetic, vertical (9:16) content ready for social media. It automatically extracts audio, overlays a custom frame, and adds a dynamic background.

---

## ✨ Features

- **Dual Processing Modes**:
  - **Full Echo** (default): Converts videos to vertical 9:16 format with random background + frame overlay
  - **Frame Only**: Adds frame overlay to your video without changing background (output size matches frame)
- **Automated Vertical Conversion**: Automatically scales and crops content to 1080x1920 (9:16) in Full Echo mode.
- **Randomized Backgrounds**: Picks a random video background from your collection for every Full Echo job.
- **Queue System**: Handles multiple users simultaneously using an asynchronous job queue (FIFO).
- **History & Status tracking**: Users can check their active jobs and history directly via the bot interface.
- **Smart Compression**: Automatically attempts to compress videos to fit within Telegram's 50MB limit.
- **Auto Cleanup**: Automatically cleans up old completed/failed jobs and files (default: 3 days old).
- **Database Integrated**: Uses SQLite for robust tracking of user data and job statuses.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Bot Framework**: [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- **Video Engine**: FFmpeg
- **Database**: SQLite3
- **Image Processing**: Pillow (for frame validation)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- **FFmpeg** installed and added to your system PATH (or specified in `.env`)
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd echoframe
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token_here
   ASSETS_PATH=./assets
   OUTPUTS_PATH=./outputs
   FFMPEG_PATH=ffmpeg
   ```

4. **Prepare Assets**:
   - **For Full Echo mode**: Place background videos in `assets/backgrounds/` (e.g., `.mp4`, `.mov`).
   - **For both modes**: Place your overlay frame (PNG) at `assets/frames/frame.png`. Output size will match frame dimensions.
   - You can use `python create_assets.py` to generate a placeholder frame (1080x1920).

5. **Run the Bot**:
   ```bash
   python bot.py
   ```

---

## 🐳 Docker Deployment

You can also run EchoFrame using Docker:

```bash
docker-compose up -d --build
```

---

## 📁 Project Structure

```text
echoframe/
├── assets/             # Backgrounds, frames, and overlays
├── outputs/            # Temporary processing folder
├── bot.py              # Main bot entry point & handlers
├── processor.py        # Video & FFmpeg logic
├── database.py         # SQLite database management
├── Dockerfile          # Container configuration
└── docker-compose.yml  # Multi-container orchestration
```

---

## 🤖 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Welcome message and menu initialization |
| `/help` | Detailed guide on how to use the bot |
| `/jobs` | View your current queue status |
| `/history` | View your last 5 completed videos |
| `/cleanup [days]` | Manually cleanup old jobs and files (default: 3 days) |

### Keyboard Menu Buttons

- **🖼 Hanya Frame**: Switch to frame-only mode (no background change)
- **📹 Full Echo**: Switch to full echo mode (vertical conversion + background)
- **📊 Status Kerja**: View active jobs in queue
- **📜 Riwayat**: View last 5 completed videos
- **🧹 Cleanup**: Cleanup old jobs and files (3 days default)
- **❓ Bantuan**: Show help guide

### Usage

1. **Default Mode (Full Echo)**: Simply send a video - bot will convert it to vertical 9:16 with random background + frame.
2. **Frame Only Mode**: Press **🖼 Hanya Frame** button, then send your video - bot will only add frame overlay.

**Note**: Maximum video size for upload is **20MB** (Telegram Bot API limit). Output videos are limited to **50MB**.

---

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather | *Required* |
| `ASSETS_PATH` | Path to the assets folder | `./assets` |
| `OUTPUTS_PATH` | Path where videos are processed | `./outputs` |
| `FFMPEG_PATH` | Path to the FFmpeg executable | `ffmpeg` |
| `DATABASE_PATH` | Path to SQLite database file | `echoframe.db` |

## 🧹 Cleanup

The bot automatically cleans up old completed/failed jobs and files when it starts (default: 3 days old). You can also manually trigger cleanup:

- Use `/cleanup` command or press **🧹 Cleanup** button for default cleanup (3 days)
- Use `/cleanup 7` to cleanup files older than 7 days

Cleanup removes:
- Database entries for completed/failed jobs older than specified days
- Associated output video files (`echoframe_*.mp4`)
- Any remaining input files (`input_*.mp4`)

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
