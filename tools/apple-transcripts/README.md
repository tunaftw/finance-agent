# Apple Podcasts Transcript Downloader

Download transcripts from Apple Podcasts using the API.

## Quick Start

```bash
# 1. Refresh bearer token (valid 30 days)
./scripts/refresh_apple_token.sh

# 2. Download transcripts
python3 scripts/fetch_transcript_pure_python.py --year 2026
```

## How It Works

1. **Bearer Token**: Apple's API requires a signed JWT token obtained via private macOS frameworks
2. **Pure Python Download**: `fetch_transcript_pure_python.py` uses the token to download TTML files via HTTP
3. **Text Extraction**: TTML files are parsed and saved as plain text transcripts

## Tools

### GetBearerToken

Fetches a fresh bearer token from Apple's API.

```bash
cd tools/apple-transcripts
./GetBearerToken > bearer_token.txt
```

**Token validity:** 30 days

**How it works:** Uses Apple's private `AMSMescal` framework to sign requests, mimicking the official Podcasts app.

### refresh_apple_token.sh

Convenience script that runs GetBearerToken and shows token expiration.

```bash
./scripts/refresh_apple_token.sh
```

### fetch_transcript_pure_python.py

Downloads transcripts using the cached bearer token.

```bash
# Check what's missing (dry run)
python3 scripts/fetch_transcript_pure_python.py --dry-run --year 2026

# Download all missing
python3 scripts/fetch_transcript_pure_python.py --year 2026

# Limit downloads
python3 scripts/fetch_transcript_pure_python.py --year 2026 --max 10
```

## File Locations

| File | Purpose |
|------|---------|
| `tools/apple-transcripts/bearer_token.txt` | Cached bearer token |
| `tools/apple-transcripts/GetBearerToken` | Token fetcher binary |
| `data/transcripts/{podcast_id}/` | Downloaded transcripts |
| `data/podcast_mapping.json` | Apple name -> our ID mapping |

## Troubleshooting

### 401 Unauthorized Error

The bearer token has expired. Refresh it:

```bash
./scripts/refresh_apple_token.sh
```

### "No bearer token found"

Run the refresh script to create one:

```bash
./scripts/refresh_apple_token.sh
```

### Missing podcast in output

The podcast must be in `data/podcast_mapping.json`. Add it:

```json
{
  "apple_to_id": {
    "Podcast Name In Apple": "our-podcast-id"
  }
}
```

## Technical Details

### Why GetBearerToken exists

Apple's original FetchTranscript tool (from dado3212) uses `fork()` internally to wrap potential segfaults. However, on modern macOS, calling `fork()` after the Objective-C runtime is initialized causes crashes:

```
objc[...]: +[NSDateFormatter initialize] may have been in progress in another thread when fork() was called
```

**GetBearerToken** solves this by:
1. Using `continueWithBlock:` instead of `thenWithBlock:` for promise handling
2. Making synchronous HTTP requests inside the callback
3. Calling `_exit(0)` immediately after printing the token to avoid promise cleanup crashes

### Bearer Token Format

The token is a JWT (JSON Web Token) with ~30 day validity:

```
eyJraWQiOi... (header)
.eyJpc3Mi... (payload with iat/exp timestamps)
.rsPoQDGR... (signature)
```

### Apple API Endpoint

```
https://amp-api.podcasts.apple.com/v1/catalog/us/podcast-episodes/{episode_id}/transcripts
```

Requires `Authorization: Bearer {token}` header.

## Legacy Tools (Deprecated)

- `FetchTranscript` - Original tool, crashes due to fork() issues
- `download_apple_transcripts.py` - Wrapper that tried osascript workaround (didn't work reliably)

Use `fetch_transcript_pure_python.py` instead.
