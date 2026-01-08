#!/bin/bash
# Batch download ChartGuys transcripts from 2024-2025
# 334 videos total

VIDEO_LIST="/Users/pontus/Developer/podcast-transcriber/data/youtube/chartguys_2024_2025.txt"
DOWNLOAD_SCRIPT="/Users/pontus/Developer/podcast-transcriber/.claude/skills/youtube-download/scripts/download_youtube.py"
LOG_FILE="/Users/pontus/Developer/podcast-transcriber/data/youtube/chartguys_download.log"
PROGRESS_FILE="/Users/pontus/Developer/podcast-transcriber/data/youtube/chartguys_progress.txt"

# Count total videos
TOTAL=$(wc -l < "$VIDEO_LIST")
CURRENT=0
SUCCESS=0
FAILED=0

echo "Starting batch download of $TOTAL ChartGuys videos" | tee "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

while IFS='|' read -r video_id upload_date title; do
    CURRENT=$((CURRENT + 1))

    # Update progress file
    echo "$CURRENT/$TOTAL - $SUCCESS succeeded, $FAILED failed" > "$PROGRESS_FILE"

    echo "[$CURRENT/$TOTAL] Downloading: $title ($video_id)" | tee -a "$LOG_FILE"

    # Check if transcript already exists
    OUTPUT_DIR="/Users/pontus/Developer/podcast-transcriber/data/youtube/raw/thechartguys"
    if ls "$OUTPUT_DIR"/*"$video_id"* 2>/dev/null | grep -q .; then
        echo "  -> Already exists, skipping" | tee -a "$LOG_FILE"
        SUCCESS=$((SUCCESS + 1))
        continue
    fi

    # Download transcript
    if python "$DOWNLOAD_SCRIPT" "$video_id" >> "$LOG_FILE" 2>&1; then
        echo "  -> Success" | tee -a "$LOG_FILE"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "  -> FAILED (no transcript available?)" | tee -a "$LOG_FILE"
        echo "$video_id|$upload_date|$title" >> "/Users/pontus/Developer/podcast-transcriber/data/youtube/chartguys_failed.txt"
        FAILED=$((FAILED + 1))
    fi

    # Small delay to avoid rate limiting
    sleep 1

done < "$VIDEO_LIST"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Batch download complete!" | tee -a "$LOG_FILE"
echo "End time: $(date)" | tee -a "$LOG_FILE"
echo "Total: $TOTAL" | tee -a "$LOG_FILE"
echo "Success: $SUCCESS" | tee -a "$LOG_FILE"
echo "Failed: $FAILED" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Final progress update
echo "COMPLETE: $SUCCESS/$TOTAL succeeded, $FAILED failed" > "$PROGRESS_FILE"
