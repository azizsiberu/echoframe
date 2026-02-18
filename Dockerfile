# Use Python 3.10 slim as base
FROM python:3.10-slim

# Install system dependencies (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p assets/backgrounds assets/frames outputs

# Expose no ports needed for polling bot, but good practice if adding a webhook later
# EXPOSE 8080

# Environment variables (default values)
ENV ASSETS_PATH=/app/assets
ENV OUTPUTS_PATH=/app/outputs
ENV FFMPEG_PATH=ffmpeg

# Start the bot
CMD ["python", "bot.py"]
