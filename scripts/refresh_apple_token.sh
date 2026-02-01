#!/bin/bash
# Apple Podcasts Bearer Token Refresh
#
# Refreshes the bearer token used for downloading Apple Podcasts transcripts.
# The token is valid for 30 days.
#
# Usage: ./scripts/refresh_apple_token.sh

set -e

cd "$(dirname "$0")/../tools/apple-transcripts"

echo "Refreshing Apple Podcasts bearer token..."

# Use GetBearerToken which avoids fork() crash issues
./GetBearerToken > bearer_token.txt 2>/dev/null

if [ ! -s bearer_token.txt ]; then
    echo "Failed to get token"
    exit 1
fi

echo "Token saved to: tools/apple-transcripts/bearer_token.txt"
echo ""

# Show token expiration
token=$(cat bearer_token.txt)
payload=$(echo "$token" | cut -d'.' -f2)
exp=$(echo "$payload" | base64 -D 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['exp'])" 2>/dev/null || echo "unknown")
if [ "$exp" != "unknown" ]; then
    exp_date=$(python3 -c "from datetime import datetime; print(datetime.fromtimestamp($exp).strftime('%Y-%m-%d'))")
    echo "Token expires: $exp_date"
fi

echo ""
echo "Now you can run: python3 scripts/fetch_transcript_pure_python.py --year 2026"
