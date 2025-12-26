#!/usr/bin/env python3
"""
Batch-transkribering av podcast-avsnitt.
Körs autonomt tills alla avsnitt i aktuell fas är klara.

Användning:
    python3 scripts/batch_transcribe.py

Stoppa med Ctrl+C - progress sparas efter varje avsnitt.
"""

import sys
import json
import time
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from podstock.transcribe.whisper import transcribe, save_transcript
from podstock.rss.downloader import download_episode
import requests

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
GLM_DIR = DATA_DIR / 'transcripts' / 'glm-transcription'
COMPLETION_LOG = GLM_DIR / 'completion-log.json'
AUDIO_DIR = DATA_DIR / 'audio'
TRANSCRIPTS_DIR = DATA_DIR / 'transcripts'


def load_completion_log():
    with open(COMPLETION_LOG) as f:
        return json.load(f)


def save_completion_log(log):
    log['last_updated'] = datetime.now().isoformat()
    with open(COMPLETION_LOG, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def load_queue(phase: int):
    queue_file = GLM_DIR / f'phase{phase}-queue.json'
    with open(queue_file) as f:
        return json.load(f)


def get_next_episode(log, queue):
    """Hitta nästa avsnitt att transkribera."""
    completed = set(log.get('completed', []))
    failed = set(log.get('failed', []))

    for episode in queue['episodes']:
        episode_id = episode['episode_id']
        if episode_id not in completed and episode_id not in failed:
            return episode

    return None


def download_audio(episode):
    """Ladda ner ljudfil om den inte finns."""
    podcast_id = episode['podcast_id']
    episode_id = episode['episode_id']
    audio_url = episode['audio_url']

    audio_dir = AUDIO_DIR / podcast_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f'{episode_id}.mp3'

    if audio_path.exists():
        print(f'  ✓ Ljudfil finns redan: {audio_path.name}')
        return audio_path

    print(f'  ⬇ Laddar ner: {audio_url[:60]}...')

    # Headers för att undvika 403 från Acast CDN
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'audio/mpeg,audio/*;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,sv;q=0.8',
        'Referer': 'https://play.acast.com/',
    }

    resp = requests.get(audio_url, stream=True, timeout=300, headers=headers)
    resp.raise_for_status()

    total_size = int(resp.headers.get('content-length', 0))
    downloaded = 0

    with open(audio_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = downloaded * 100 // total_size
                print(f'\r  ⬇ Laddar ner: {pct}%', end='', flush=True)

    print(f'\r  ✓ Nedladdat: {audio_path.name} ({downloaded // 1024 // 1024} MB)')
    return audio_path


def transcribe_episode(episode, audio_path):
    """Transkribera ett avsnitt."""
    podcast_id = episode['podcast_id']
    episode_id = episode['episode_id']

    transcript_dir = TRANSCRIPTS_DIR / podcast_id
    transcript_path = transcript_dir / f'{episode_id}.txt'

    if transcript_path.exists():
        print(f'  ✓ Transkript finns redan: {transcript_path.name}')
        return transcript_path

    print(f'  🎙 Transkriberar med Whisper large-v3...')
    print(f'    (Detta tar 30-60 minuter)')

    start_time = time.time()

    text = transcribe(audio_path, model='large-v3')

    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)

    # Spara transkript
    transcript_path = save_transcript(
        episode_id=episode_id,
        text=text,
        transcript_dir=TRANSCRIPTS_DIR,
        podcast_id=podcast_id,
        metadata={'model': 'large-v3'}
    )

    print(f'  ✓ Transkriberat på {elapsed_min} min: {transcript_path.name}')
    print(f'    Längd: {len(text):,} tecken')

    return transcript_path


def main():
    print('=' * 60)
    print('BATCH-TRANSKRIBERING')
    print('=' * 60)
    print()

    # Ladda status
    log = load_completion_log()
    phase = log['current_phase']
    queue = load_queue(phase)

    total_in_phase = len(queue['episodes'])
    completed_count = len(log.get('completed', []))

    print(f'Fas {phase}: {queue["description"]}')
    print(f'Totalt i fas: {total_in_phase} avsnitt')
    print(f'Redan klara: {completed_count} avsnitt')
    print()
    print('Tryck Ctrl+C för att avbryta (progress sparas)')
    print('=' * 60)
    print()

    episodes_done_this_session = 0

    try:
        while True:
            # Hitta nästa avsnitt
            episode = get_next_episode(log, queue)

            if not episode:
                print()
                print('=' * 60)
                print(f'✅ FAS {phase} KLAR!')
                print(f'Alla {total_in_phase} avsnitt är transkriberade.')
                print()

                if phase < 3:
                    print(f'Nästa steg: Ändra current_phase till {phase + 1} i completion-log.json')
                else:
                    print('🎉 ALLA FASER KLARA!')

                print('=' * 60)
                break

            episode_id = episode['episode_id']
            podcast_id = episode['podcast_id']
            title = episode.get('title', 'Okänd titel')

            episodes_done_this_session += 1
            completed_so_far = len(log.get('completed', [])) + 1

            print(f'[{completed_so_far}/{total_in_phase}] {episode_id}')
            print(f'  Titel: {title[:50]}...')

            try:
                # 1. Ladda ner
                audio_path = download_audio(episode)

                # 2. Transkribera
                transcript_path = transcribe_episode(episode, audio_path)

                # 3. Uppdatera log
                if 'completed' not in log:
                    log['completed'] = []
                log['completed'].append(episode_id)
                log['total_processed'] = log.get('total_processed', 0) + 1
                save_completion_log(log)

                print(f'  ✓ Sparat i completion-log')
                print()

            except Exception as e:
                print(f'  ✗ FEL: {e}')
                if 'failed' not in log:
                    log['failed'] = []
                if episode_id not in log['failed']:
                    log['failed'].append(episode_id)
                save_completion_log(log)
                print(f'  → Markerad som failed, fortsätter med nästa...')
                print()
                continue

    except KeyboardInterrupt:
        print()
        print()
        print('=' * 60)
        print('⏸ AVBRUTEN AV ANVÄNDARE')
        print(f'Transkriberade {episodes_done_this_session} avsnitt denna session.')
        print(f'Progress sparad i completion-log.json')
        print('Kör scriptet igen för att fortsätta.')
        print('=' * 60)


if __name__ == '__main__':
    main()
