# Report Template

Mall för orchestration-slutrapport.

## Filnamn

- **Arkiv:** `logs/orchestration/YYYY-MM-DDTHH-MM-SS.md`
- **Senaste:** `logs/orchestration/latest.md`

## Mall

```markdown
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════
Körning: {timestamp}
Status: {SUCCESS | PARTIAL | FAILED}

RESULTAT
────────
{status_icon} Downloaded:  {n_downloaded} transcripts ({n_apple} Apple, {n_whisper} Whisper)
{status_icon} Analyzed:    {n_analyzed} episodes → {n_recs} recommendations
{status_icon} DB synced:   {n_synced_analyses} analyses, {n_synced_recs} recs, {n_insights} insights
{status_icon} Prices:      {n_prices_matched}/{n_total_recs} recs matched ({n_missing_prices} saknar prishistorik)
{status_icon} Published:   Commit {git_hash} pushed → Vercel deploying

SJÄLVFÖRBÄTTRINGAR
──────────────────
{improvements_list or '(inga förbättringar gjordes)'}

SKIPPADE (kräver manuell åtgärd)
────────────────────────────────
{skipped_list or '(inga skippade)'}

FEL
───
{errors_list or '(inga fel)'}

TIMING
──────
Total tid:     {total_time}
  Pre-flight:  {preflight_time}
  Download:    {download_time}
  Analyze:     {analyze_time}
  Sync:        {sync_time}
  Publish:     {publish_time}

════════════════════════════════════════════════════════════════════
```

## Status Icons

- `✓` - Steget lyckades helt
- `⚠` - Steget lyckades delvis (några items skippade)
- `✗` - Steget misslyckades

## Generera Rapport

```python
from datetime import datetime
from pathlib import Path

def generate_report(results: dict) -> str:
    """Generera slutrapport från körningsresultat."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Bestäm övergripande status
    if results.get('critical_failure'):
        status = "FAILED"
    elif results.get('skipped') or results.get('partial_failures'):
        status = "PARTIAL"
    else:
        status = "SUCCESS"

    # Status icons per steg
    def icon(step_results):
        if step_results.get('failed'):
            return '✗'
        elif step_results.get('skipped'):
            return '⚠'
        return '✓'

    # Formatera listor
    def format_list(items, prefix="• "):
        if not items:
            return "(inga)"
        return "\n".join(f"{prefix}{item}" for item in items)

    # Formatera tid
    def format_time(seconds):
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:.0f}m {secs:.0f}s"

    # Bygg rapport
    report = f"""
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════
Körning: {timestamp}
Status: {status}

RESULTAT
────────
{icon(results.get('download', {}))} Downloaded:  {results.get('n_downloaded', 0)} transcripts ({results.get('n_apple', 0)} Apple, {results.get('n_whisper', 0)} Whisper)
{icon(results.get('analyze', {}))} Analyzed:    {results.get('n_analyzed', 0)} episodes → {results.get('n_recs', 0)} recommendations
{icon(results.get('sync', {}))} DB synced:   {results.get('n_synced_analyses', 0)} analyses, {results.get('n_synced_recs', 0)} recs
{icon(results.get('prices', {}))} Prices:      {results.get('n_prices_matched', 0)}/{results.get('n_total_recs', 0)} recs matched
{icon(results.get('publish', {}))} Published:   Commit {results.get('git_hash', 'N/A')} pushed

SJÄLVFÖRBÄTTRINGAR
──────────────────
{format_list(results.get('improvements', []))}

SKIPPADE (kräver manuell åtgärd)
────────────────────────────────
{format_list(results.get('skipped', []))}

FEL
───
{format_list(results.get('errors', []))}

TIMING
──────
Total tid:     {format_time(results.get('total_time', 0))}
  Pre-flight:  {format_time(results.get('preflight_time', 0))}
  Download:    {format_time(results.get('download_time', 0))}
  Analyze:     {format_time(results.get('analyze_time', 0))}
  Sync:        {format_time(results.get('sync_time', 0))}
  Publish:     {format_time(results.get('publish_time', 0))}

════════════════════════════════════════════════════════════════════
"""
    return report.strip()


def save_report(report: str):
    """Spara rapport till fil."""

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    logs_dir = Path("logs/orchestration")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Spara med timestamp
    archive_path = logs_dir / f"{timestamp}.md"
    archive_path.write_text(report)

    # Uppdatera latest
    latest_path = logs_dir / "latest.md"
    latest_path.write_text(report)

    return archive_path, latest_path
```

## Exempel: Lyckad Körning

```
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════
Körning: 2026-01-09 20:30:00
Status: SUCCESS

RESULTAT
────────
✓ Downloaded:  5 transcripts (4 Apple, 1 Whisper)
✓ Analyzed:    5 episodes → 18 recommendations
✓ DB synced:   5 analyses, 18 recs
✓ Prices:      14/18 recs matched
✓ Published:   Commit abc123f pushed

SJÄLVFÖRBÄTTRINGAR
──────────────────
(inga förbättringar gjordes)

SKIPPADE (kräver manuell åtgärd)
────────────────────────────────
• 4 tickers saknar prishistorik - kör /price-sync för Yahoo-anrop

FEL
───
(inga fel)

TIMING
──────
Total tid:     8m 42s
  Pre-flight:  0m 3s
  Download:    2m 15s
  Analyze:     5m 3s
  Sync:        0m 34s
  Publish:     0m 47s

════════════════════════════════════════════════════════════════════
```

## Exempel: Delvis Lyckad

```
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════
Körning: 2026-01-09 20:30:00
Status: PARTIAL

RESULTAT
────────
⚠ Downloaded:  4 transcripts (3 Apple, 1 Whisper) - 1 skippade
✓ Analyzed:    4 episodes → 12 recommendations
✓ DB synced:   4 analyses, 12 recs
✓ Prices:      10/12 recs matched
✓ Published:   Commit def456g pushed

SJÄLVFÖRBÄTTRINGAR
──────────────────
• podcast_mapping.json: La till "Nya Podden" → "nyapodden"

SKIPPADE (kräver manuell åtgärd)
────────────────────────────────
• veckanstrade-2026-01-08: Whisper timeout efter 3 försök
• 2 tickers saknar prishistorik

FEL
───
(inga fel)

TIMING
──────
Total tid:     12m 18s
  Pre-flight:  0m 3s
  Download:    6m 45s
  Analyze:     4m 12s
  Sync:        0m 28s
  Publish:     0m 50s

════════════════════════════════════════════════════════════════════
```
