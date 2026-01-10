#!/bin/bash
# Deploy Dashboard to Vercel
# This script ensures all data files are properly copied and verified before push

set -e  # Exit on any error

echo "=========================================="
echo "PODSTOCK DASHBOARD DEPLOYMENT"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Regenerate dashboard
echo -e "\n${YELLOW}[1/5] Regenerating dashboard...${NC}"
source .venv/bin/activate
python -m podstock dashboard --output data/dashboard generate --no-embed

# Step 2: Copy files to production locations
echo -e "\n${YELLOW}[2/5] Copying files to production...${NC}"
cp data/dashboard/index.html index.html
cp -r data/dashboard/assets/* assets/
cp data/dashboard/data/*.json data/

# Step 3: Verify critical files exist and have content
echo -e "\n${YELLOW}[3/5] Verifying data files...${NC}"

CRITICAL_FILES=(
    "data/podcasts.json"
    "data/recommendations.json"
    "data/analyses.json"
    "data/metadata.json"
    "data/sources.json"
    "data/twitter.json"
    "data/youtube.json"
)

ALL_OK=true
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}  MISSING: $file${NC}"
        ALL_OK=false
    elif [ ! -s "$file" ]; then
        echo -e "${RED}  EMPTY: $file${NC}"
        ALL_OK=false
    else
        SIZE=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}  OK: $file ($SIZE)${NC}"
    fi
done

# Verify podcasts.json has actual episode data
EPISODE_COUNT=$(python3 -c "import json; d=json.load(open('data/podcasts.json')); print(len([e for e in d.get('episodes', []) if e.get('date')]))" 2>/dev/null || echo "0")
if [ "$EPISODE_COUNT" -lt 100 ]; then
    echo -e "${RED}  WARNING: podcasts.json has only $EPISODE_COUNT episodes with dates!${NC}"
    ALL_OK=false
else
    echo -e "${GREEN}  VERIFIED: $EPISODE_COUNT podcast episodes with data${NC}"
fi

# Verify recommendations count
REC_COUNT=$(python3 -c "import json; d=json.load(open('data/recommendations.json')); print(len(d))" 2>/dev/null || echo "0")
if [ "$REC_COUNT" -lt 1000 ]; then
    echo -e "${RED}  WARNING: recommendations.json has only $REC_COUNT items!${NC}"
    ALL_OK=false
else
    echo -e "${GREEN}  VERIFIED: $REC_COUNT recommendations${NC}"
fi

if [ "$ALL_OK" = false ]; then
    echo -e "\n${RED}VERIFICATION FAILED - Aborting deployment${NC}"
    exit 1
fi

# Step 4: Git commit
echo -e "\n${YELLOW}[4/5] Committing changes...${NC}"
git add index.html assets/ data/*.json

if git diff --cached --quiet; then
    echo -e "${YELLOW}  No changes to commit${NC}"
else
    COMMIT_MSG="${1:-chore: update dashboard}"
    git commit -m "$COMMIT_MSG

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
    echo -e "${GREEN}  Committed: $COMMIT_MSG${NC}"
fi

# Step 5: Push to remote
echo -e "\n${YELLOW}[5/5] Pushing to remote...${NC}"
git push origin main

echo -e "\n${GREEN}=========================================="
echo "DEPLOYMENT COMPLETE"
echo "==========================================${NC}"
echo ""
echo "Vercel will auto-deploy from main branch."
echo "Check your Vercel dashboard for deployment status."
echo ""
