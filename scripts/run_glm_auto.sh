#!/bin/bash
#
# run_glm_auto.sh - Autonomous GLM-4.7 batch-analys för podcast-transkript
#
# Användning:
#   bash scripts/run_glm_auto.sh
#
# Features:
#   - Auto-restart (3-4 transkript per batch)
#   - Progress tracking via completion-log.json
#   - Retry logic (3 försök vid fel, hanteras av glm_driver.py)
#   - Kan stoppas och återupptas
#

set -euo pipefail

PROJECT_ROOT="/Users/pontus/Developer/podcast-transcriber"
TRANSCRIPT_QUEUE="$PROJECT_ROOT/data/podcasts/analyses-v2/transcript-queue.txt"
COMPLETION_LOG="$PROJECT_ROOT/data/podcasts/analyses-v2/completion-log.json"
OUTPUT_DIR="$PROJECT_ROOT/data/podcasts/analyses-v2"
GLM_DRIVER="$PROJECT_ROOT/scripts/glm_driver.py"
BATCH_SIZE=8

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
banner() {
    echo ""
    echo "=============================================="
    echo "  GLM-4.7 Autonomous Batch Analysis"
    echo "=============================================="
    echo ""
}

# Progress info
show_progress() {
    local total_processed
    local failed_count
    local total_files
    
    if [ -f "$COMPLETION_LOG" ]; then
        total_processed=$(jq -r '.total_processed // 0' "$COMPLETION_LOG")
        failed_count=$(jq '.failed | length' "$COMPLETION_LOG")
    else
        total_processed=0
        failed_count=0
    fi
    
    if [ -f "$TRANSCRIPT_QUEUE" ]; then
        total_files=$(wc -l < "$TRANSCRIPT_QUEUE" | tr -d ' ')
    else
        total_files=$(find "$PROJECT_ROOT/data/transcripts" -name "*.txt" | wc -l | tr -d ' ')
    fi
    
    local percentage
    if [ "$total_files" -gt 0 ]; then
        percentage=$(echo "scale=1; ($total_processed * 100) / $total_files" | bc)
    else
        percentage="0.0"
    fi
    
    echo -e "${BLUE}Progress:${NC} $total_processed/$total_files ($percentage%)"
    echo -e "${YELLOW}Failed:${NC} $failed_count"
}

# Hitta nästa batch av transkript att analysera
get_next_batch() {
    local temp_completed="/tmp/completed_basenames_$$.txt"

    # Skapa lista med basenames från completed-listan
    if [ -f "$COMPLETION_LOG" ]; then
        jq -r '.completed[]? // empty' "$COMPLETION_LOG" 2>/dev/null | sort -u > "$temp_completed" || true
    else
        : > "$temp_completed"  # Tom fil
    fi

    if [ ! -f "$TRANSCRIPT_QUEUE" ]; then
        rm -f "$temp_completed"
        # Fallback: hitta alla transkript
        find "$PROJECT_ROOT/data/transcripts" -name "*.txt" | sort
        return
    fi

    # Läs queue och filtrera - explicit loop för att undvika grep pipe-problem
    local count=0
    while IFS= read -r filepath || [ -n "$filepath" ]; do
        [ -z "$filepath" ] && continue

        # Extrahera basename för jämförelse
        local basename
        basename="${filepath##*/}"

        # Kolla om basename finns i completed-listan
        if ! grep -qxF "$basename" "$temp_completed" 2>/dev/null; then
            echo "$filepath"
            count=$((count + 1))
            [ "$count" -ge "$BATCH_SIZE" ] && break
        fi
    done < "$TRANSCRIPT_QUEUE"

    rm -f "$temp_completed"
}

# Processera en transkript
process_transcript() {
    local transcript_file="$1"
    local transcript_name
    transcript_name=$(basename "$transcript_file")
    
    echo -e "${GREEN}Processing:${NC} $transcript_name"
    
    python3 "$GLM_DRIVER" "$transcript_file" "$OUTPUT_DIR"
    
    return $?
}

# Main loop
main_loop() {
    local iteration=0
    
    while true; do
        iteration=$((iteration + 1))
        
        banner
        echo -e "${BLUE}Batch:${NC} $iteration"
        show_progress
        echo ""
        
        # Hämta nästa batch
        local batch
        batch=$(get_next_batch)
        
        # Om ingen batch kvar, vi är klara!
        if [ -z "$batch" ]; then
            echo ""
            echo -e "${GREEN}✅ Alla transkript är analyserade!${NC}"
            echo ""
            show_progress
            break
        fi
        
        # Processera varje transkript i batchen
        local batch_count=0
        local success_count=0
        local fail_count=0
        
        while IFS= read -r transcript_file; do
            if [ -n "$transcript_file" ]; then
                batch_count=$((batch_count + 1))
                
                echo ""
                echo -e "${BLUE}[$batch_count/$BATCH_SIZE]${NC} $transcript_file"
                
                if process_transcript "$transcript_file"; then
                    success_count=$((success_count + 1))
                    echo -e "  ${GREEN}✅ Success${NC}"
                else
                    fail_count=$((fail_count + 1))
                    echo -e "  ${RED}❌ Failed (logged to completion-log)${NC}"
                fi
            fi
        done <<< "$batch"
        
        # Visa batch-summary
        echo ""
        echo "----------------------------------------------"
        echo -e "Batch $iteration complete:"
        echo -e "  Processed: $batch_count"
        echo -e "  ${GREEN}Success:${NC} $success_count"
        echo -e "  ${RED}Failed:${NC} $fail_count"
        echo "----------------------------------------------"
        
        # Progress uppdaterad
        echo ""
        show_progress
        
        # Short pause innan nästa batch
        echo ""
        echo "Pausing for 2 seconds before next batch..."
        sleep 2
        echo ""
    done
}

# Cleanup on Ctrl+C
cleanup() {
    echo ""
    echo -e "${YELLOW}Interrupted by user${NC}"
    echo ""
    echo "Progress saved. Run again to continue."
    show_progress
    exit 130
}

trap cleanup SIGINT SIGTERM

# Check prerequisites
if [ ! -f "$TRANSCRIPT_QUEUE" ]; then
    echo -e "${YELLOW}Warning: transcript-queue.txt not found${NC}"
    echo "Will search for transcripts automatically..."
fi

if [ ! -f "$GLM_DRIVER" ]; then
    echo -e "${RED}Error: glm_driver.py not found${NC}"
    exit 1
fi

# Start main loop
main_loop

echo ""
echo -e "${GREEN}🎉 Batch analysis complete!${NC}"
echo ""
