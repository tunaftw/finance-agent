---
name: youtube-download
description: Download YouTube video transcripts. Use when user wants to download, fetch, or save a transcript from a YouTube video URL. Saves with descriptive filename including channel name, video title, and date.
---

# YouTube Download Skill

Download transcripts from YouTube videos with automatic naming and storage.

## Quick Start

1. Get **YouTube URL** from user
2. Extract video info (title, channel, date)
3. Download transcript via yt-dlp
4. Save with formatted filename
5. Report results

## Workflow

### Step 1: Get YouTube URL

Ask user for the YouTube video URL. Accept formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- Just the video ID (11 characters)

### Step 2: Download Transcript

Run the download script:

```bash
python /Users/pontus/Developer/podcast-transcriber/.claude/skills/youtube-download/scripts/download_youtube.py "YOUTUBE_URL"
```

The script will:
1. Extract video ID from URL
2. Fetch video metadata (title, channel, publish date)
3. Download transcript (prefers English/Swedish)
4. Save with formatted filename

### Step 3: Report Results

After successful download, report:
- Video title
- Channel name
- File location
- Word count

## Storage Format

Files are saved to `data/youtube/raw/{channel-slug}/` with format:

```
{Channel Name} - {Video Title} - {YYYY-MM-DD}.txt
```

Example:
```
Lex Fridman Podcast - Sam Altman on OpenAI - 2024-03-15.txt
```

The transcript file includes a header with metadata followed by the full transcript text.

## Error Handling

| Error | Solution |
|-------|----------|
| `No transcript available` | Video has no captions. Try a different video. |
| `Video unavailable` | Video is private, deleted, or region-locked. |
| `yt-dlp not found` | Install with: `pip install yt-dlp` |
| `Invalid URL` | Check URL format and video ID. |

## Examples

**User request:** "Download transcript from https://www.youtube.com/watch?v=abc123xyz"

**Response:**
```
Downloaded transcript:
- Title: Interview with Sam Altman
- Channel: Lex Fridman Podcast
- Date: 2024-03-15
- Words: 45,230
- Saved to: data/youtube/raw/lex-fridman-podcast/Lex Fridman Podcast - Interview with Sam Altman - 2024-03-15.txt
```
