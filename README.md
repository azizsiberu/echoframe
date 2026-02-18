# 🎬 EchoFrame Bot

**EchoFrame** is a powerful Telegram bot designed to transform standard videos into aesthetic, vertical (9:16) content ready for social media. It automatically extracts audio, overlays a custom frame, and adds a dynamic background.

---

## ✨ Features

- **Automated Vertical Conversion**: Automatically scales and crops content to 1080x1920 (9:16).
- **Randomized Backgrounds**: Picks a random video background from your collection for every job.
- **Queue System**: Handles multiple users simultaneously using an asynchronous job queue (FIFO).
- **History & Status tracking**: Users can check their active jobs and history directly via the bot interface.
- **Smart Compression**: Automatically attempts to compress videos to fit within Telegram's 50MB limit.
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
   - Place background videos in `assets/backgrounds/` (e.g., `.mp4`, `.mov`).
   - Place your overlay frame (1080x1920 PNG) at `assets/frames/frame.png`.
   - You can use `python create_assets.py` if provided to generate placeholders.

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

Users can also use the custom keyboard buttons: **📊 Status Kerja**, **📜 Riwayat**, and **❓ Bantuan**.

---

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather | *Required* |
| `ASSETS_PATH` | Path to the assets folder | `./assets` |
| `OUTPUTS_PATH` | Path where videos are processed | `./outputs` |
| `FFMPEG_PATH` | Path to the FFmpeg executable | `ffmpeg` |

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
