#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/pontus/Developer/podcast-transcriber/src')

from podstock.transcribe.whisper import transcribe, save_transcript
from pathlib import Path
import json

audio_path = Path('data/audio/gotttjot/gotttjot-2025-12-23-c440.mp3')
episode_id = 'gotttjot-2025-12-23-c440'
podcast_id = 'gotttjot'
transcripts_dir = Path('data/transcripts')
status_file = Path('data/transcripts/glm-transcription/transcribe-status.json')

def progress(msg):
    print(f'  {msg}')
    # Update status file
    with open(status_file, 'w') as f:
        json.dump({'status': 'running', 'message': msg, 'episode': episode_id}, f)

# Initialize status
with open(status_file, 'w') as f:
    json.dump({'status': 'starting', 'episode': episode_id}, f)

print(f'Transkriberar {episode_id}...')
print('Detta tar ca 30-60 minuter...')

try:
    text = transcribe(audio_path, model='large-v3', progress_callback=progress)
    
    transcript_path = save_transcript(
        episode_id=episode_id,
        text=text,
        transcript_dir=transcripts_dir,
        podcast_id=podcast_id,
        metadata={'model': 'large-v3'}
    )
    
    # Mark as complete
    with open(status_file, 'w') as f:
        json.dump({
            'status': 'complete',
            'transcript_path': str(transcript_path),
            'episode': episode_id,
            'length': len(text)
        }, f)
    
    print(f'✓ Sparad till: {transcript_path}')
    
except Exception as e:
    # Mark as failed
    with open(status_file, 'w') as f:
        json.dump({
            'status': 'failed',
            'error': str(e),
            'episode': episode_id
        }, f)
    print(f'✗ Error: {e}')
    sys.exit(1)
