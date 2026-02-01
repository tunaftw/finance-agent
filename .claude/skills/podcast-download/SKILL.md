---
name: podcast-download
description: Sync podcast transcripts. Use when user asks "vilka podcasts har kommit som inte ar synkade", wants to check unsynced episodes, or download missing transcripts. Identifies episodes from current year lacking transcripts and syncs using Apple Podcasts (preferred) or Whisper (fallback).
---

# Podcast Download Skill

Sync podcast transcripts for unsynced episodes.

## Quick Start

1. Run sync status script to see what's missing
2. User selects which podcasts to sync
3. Execute sync using Apple Podcasts or Whisper
4. Report summary

---

## Step 1: Check Sync Status

**Run the sync status script:**

```bash
python3 scripts/podcast/check_sync_status.py
```

This compares Apple Podcasts database with local transcripts and shows:
- Episodes in Apple vs local transcripts per podcast
- List of missing episodes with dates and titles
- Validation warnings (stale podcasts, unmapped podcasts)

**Options:**
```bash
# Filter to specific year
python3 scripts/podcast/check_sync_status.py --year 2025

# Filter to specific podcast
python3 scripts/podcast/check_sync_status.py --podcast fillorkill

# Output as JSON
python3 scripts/podcast/check_sync_status.py --json
```

---

## Step 2: Validate Results

**BEFORE showing results to user, verify:**

1. **Reasonableness check**: If < 5 missing episodes total, question if that's realistic
   - When was the last sync? If weeks ago, expect more missing episodes
   - Check if Apple Podcasts app has been opened recently (episodes may not be updated)

2. **Date sanity**: Active podcasts should have recent episodes (within 1-2 weeks)
   - If a podcast shows "latest: 2025-02" but it's currently 2026, something's wrong
   - Either the podcast stopped, or it's not synced in Apple Podcasts

3. **Completeness**: Check the "VALIDERING" section of output for warnings

---

## Step 3: User Selection

Ask user with AskUserQuestion:

```
Hittade X avsnitt som saknar transkript.

Vad vill du gora?
1. Synka alla osynkade avsnitt
2. Synka specifika podcasts (ange vilka)
3. Visa detaljerad lista forst
4. Avbryt
```

---

## Step 4: Execute Sync

**Method priority:**
1. Apple Podcasts cached transcript -> immediate extraction
2. Apple Podcasts downloadable -> requires viewing episode in app
3. Whisper -> download audio from RSS, transcribe locally

### For Apple Podcasts method

See [references/apple-method.md](references/apple-method.md)

**Key points:**
- Uses bearer token to authenticate with Apple API
- Token valid 30 days, refresh with `./scripts/refresh_apple_token.sh`
- Downloads TTML and extracts text in one step
- Transcript stored in `data/transcripts/{podcast_id}/`

**Exempel:**
```bash
# 1. Refresh token if needed (valid 30 days)
./scripts/refresh_apple_token.sh

# 2. Download missing transcripts
python3 scripts/fetch_transcript_pure_python.py --year 2026

# 3. Limit if many missing
python3 scripts/fetch_transcript_pure_python.py --year 2026 --max 10
```

### For Whisper method

See [references/whisper-method.md](references/whisper-method.md)

**Key points:**
- Requires RSS URL (get from Apple Podcasts database: `ZFEEDURL` in `ZMTPODCAST` table)
- Download audio, transcribe with whisper-large-v3
- ~10-15 min per hour of audio

---

## Step 5: Completion Summary

After syncing, report:

```
================================================================================
SYNC KLAR
================================================================================

Synkade: X/Y avsnitt
  - Apple Podcasts: N avsnitt
  - Whisper: M avsnitt

Misslyckades: Z avsnitt
  - episode-id: anledning

Transkript sparade i:
  data/transcripts/{podcast_id}/
================================================================================
```

---

## Data Locations

| Data | Location |
|------|----------|
| Apple Podcasts DB | `~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite` |
| Podcast mapping | `data/podcast_mapping.json` |
| Transcripts | `data/transcripts/{podcast_id}/{episode_id}.txt` |
| Sync script | `scripts/podcast/check_sync_status.py` |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Apple Podcasts database not found" | Open Apple Podcasts app and ensure podcasts are synced |
| Podcast not in mapping | Add to `data/podcast_mapping.json` |
| Transcript shows as missing but file exists | Check filename format: `{podcast_id}-{YYYY}-{MM}-{DD}-{hash}.txt` |
| No new episodes for active podcast | Open Apple Podcasts app to trigger sync |
| 401 Unauthorized error | Bearer token expired - run `./scripts/refresh_apple_token.sh` |
| "No bearer token found" | Run `./scripts/refresh_apple_token.sh` to create one |
| FetchTranscript fork() crash | **Deprecated tool** - use `fetch_transcript_pure_python.py` instead |

### Bearer Token Management

Apple's API requires a signed JWT token (valid 30 days). The token is managed automatically:

```bash
# Check/refresh token
./scripts/refresh_apple_token.sh

# Sync transcripts (uses cached token)
python3 scripts/fetch_transcript_pure_python.py --year 2026
```

If you get 401 errors, the token has expired. Just run the refresh script.

---

## Adding New Podcasts

1. Subscribe in Apple Podcasts app
2. Add mapping to `data/podcast_mapping.json`:
   ```json
   {
     "apple_to_id": {
       "New Podcast Name": "newpodcast"
     }
   }
   ```
3. Create transcript directory: `mkdir -p data/transcripts/newpodcast`
4. Run sync status to verify: `python3 scripts/podcast/check_sync_status.py --podcast newpodcast`
