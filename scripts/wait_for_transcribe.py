#!/usr/bin/env python3
import json
import time
import sys
from pathlib import Path

status_file = Path('data/transcripts/glm-transcription/transcribe-status.json')
completion_log_file = Path('data/transcripts/glm-transcription/completion-log.json')

print('Väntar på att transkribering ska bli klar...')
print('Detta kan ta 30-60 minuter...')
print()

# Check status every 10 seconds
while True:
    time.sleep(10)
    
    try:
        with open(status_file) as f:
            status = json.load(f)
        
        if status.get('status') == 'complete':
            print('✓ Transkribering klar!')
            print(f'  Transkript: {status.get("transcript_path")}')
            print()
            
            # Update completion-log
            episode_id = status['episode']
            
            with open(completion_log_file) as f:
                log = json.load(f)
            
            # Remove from failed, add to completed
            if 'failed' in log and episode_id in log['failed']:
                log['failed'].remove(episode_id)
            
            if 'completed' not in log:
                log['completed'] = []
            
            if episode_id not in log['completed']:
                log['completed'].append(episode_id)
                log['total_processed'] = log.get('total_processed', 0) + 1
            
            from datetime import datetime
            log['last_updated'] = datetime.now().isoformat()
            
            with open(completion_log_file, 'w') as f:
                json.dump(log, f, indent=2)
            
            print(f'✓ Uppdaterat completion-log')
            print(f'  Moved from failed to completed: {episode_id}')
            print()
            print('SESSION COMPLETE!')
            sys.exit(0)
        
        elif status.get('status') == 'failed':
            print(f'✗ Transkribering misslyckades: {status.get("error")}')
            sys.exit(1)
        
        else:
            # Still running
            elapsed = time.time() - status_file.stat().st_mtime
            elapsed_min = int(elapsed / 60)
            print(f'  Körs fortfarande... ({elapsed_min} minuter)', end='\r')
            
    except FileNotFoundError:
        print('  Väntar på att statusfil ska skapas...', end='\r')
    except Exception as e:
        print(f'  Fel vid läsning av status: {e}', end='\r')
