"""Command-line interface for PodStock.

This module provides the CLI commands for managing podcasts,
downloading episodes, transcribing audio, and generating reports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from podstock.core.config import Config, load_config
from podstock.core.state import State

console = Console()


def get_config(data_dir: str | None = None) -> Config:
    """Load configuration with optional data_dir override."""
    if data_dir:
        return load_config(data_dir=Path(data_dir))
    return load_config()


# =============================================================================
# Podcast Commands
# =============================================================================


def cmd_podcast_list(args: argparse.Namespace) -> int:
    """List all configured podcasts."""
    from podstock.rss.manager import load_podcasts

    config = get_config(args.data_dir)
    podcasts = load_podcasts(config.podcasts_file)

    if not podcasts:
        console.print("[yellow]No podcasts configured.[/yellow]")
        console.print("Add one with: podstock podcast add <name> <rss_url>")
        return 0

    table = Table(title="Configured Podcasts")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Hosts")
    table.add_column("Active", justify="center")

    for podcast in podcasts:
        hosts = ", ".join(podcast.hosts[:2])
        if len(podcast.hosts) > 2:
            hosts += f" (+{len(podcast.hosts) - 2})"

        active = "✓" if podcast.active else "✗"
        table.add_row(podcast.id, podcast.name, hosts, active)

    console.print(table)
    return 0


def cmd_podcast_add(args: argparse.Namespace) -> int:
    """Add a new podcast."""
    from podstock.core.exceptions import ConfigError, RSSError
    from podstock.rss.manager import add_podcast

    config = get_config(args.data_dir)

    try:
        with console.status(f"Validating RSS feed: {args.url}"):
            podcast = add_podcast(
                name=args.name,
                rss_url=args.url,
                podcasts_file=config.podcasts_file,
                validate_url=not args.skip_validation,
            )

        console.print(f"[green]✓[/green] Added podcast: {podcast.name} (ID: {podcast.id})")
        return 0

    except RSSError as e:
        console.print(f"[red]✗[/red] Invalid RSS feed: {e}")
        return 1
    except ConfigError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_podcast_remove(args: argparse.Namespace) -> int:
    """Remove a podcast."""
    from podstock.rss.manager import remove_podcast

    config = get_config(args.data_dir)

    if remove_podcast(args.id, config.podcasts_file):
        console.print(f"[green]✓[/green] Removed podcast: {args.id}")
        return 0
    else:
        console.print(f"[red]✗[/red] Podcast not found: {args.id}")
        return 1


def cmd_podcast_info(args: argparse.Namespace) -> int:
    """Show podcast details."""
    from podstock.rss.manager import get_podcast

    config = get_config(args.data_dir)
    podcast = get_podcast(args.id, config.podcasts_file)

    if not podcast:
        console.print(f"[red]✗[/red] Podcast not found: {args.id}")
        return 1

    console.print(f"[bold]{podcast.name}[/bold]")
    console.print(f"  ID: {podcast.id}")
    console.print(f"  RSS: {podcast.rss_url}")
    console.print(f"  Hosts: {', '.join(podcast.hosts) or 'Unknown'}")
    console.print(f"  Active: {'Yes' if podcast.active else 'No'}")

    if podcast.description:
        console.print(f"  Description: {podcast.description[:100]}...")

    return 0


# =============================================================================
# List Commands
# =============================================================================


def cmd_list(args: argparse.Namespace) -> int:
    """Handle list subcommands."""
    from podstock.lists.manager import ListManager, ListError
    from podstock.rss.manager import load_podcasts, get_podcast

    config = get_config(args.data_dir)
    manager = ListManager(config.lists_file)

    if args.list_command == "show":
        return cmd_list_show(args, manager, config)
    elif args.list_command == "create":
        return cmd_list_create(args, manager)
    elif args.list_command == "add":
        return cmd_list_add(args, manager, config)
    elif args.list_command == "remove":
        return cmd_list_remove(args, manager)
    elif args.list_command == "delete":
        return cmd_list_delete(args, manager)
    else:
        console.print("[yellow]Usage: podstock list <show|create|add|remove|delete>[/yellow]")
        return 1


def cmd_list_show(args: argparse.Namespace, manager, config) -> int:
    """Show all lists or a specific list."""
    from podstock.rss.manager import get_podcast

    if hasattr(args, 'list_id') and args.list_id:
        # Show specific list
        lst = manager.get_list(args.list_id)
        if not lst:
            console.print(f"[red]✗[/red] List not found: {args.list_id}")
            return 1

        console.print(f"\n[bold]{lst.name}[/bold] ({lst.id})")
        console.print(f"  Type: {lst.type}")
        if lst.description:
            console.print(f"  Description: {lst.description}")
        console.print(f"  Active: {'Yes' if lst.active else 'No'}")
        console.print(f"  Podcasts: {len(lst.podcast_ids)}")

        if lst.podcast_ids:
            console.print("\n  [bold]Included Podcasts:[/bold]")
            for pid in lst.podcast_ids:
                podcast = get_podcast(pid, config.podcasts_file)
                name = podcast.name if podcast else f"[dim](unknown: {pid})[/dim]"
                console.print(f"    • {pid}: {name}")
        else:
            console.print("\n  [dim]No podcasts in this list yet.[/dim]")
            console.print(f"  Add with: podstock list add {lst.id} <podcast_id>")
    else:
        # Show all lists
        lists = manager.get_all_lists()

        if not lists:
            console.print("[yellow]No lists configured.[/yellow]")
            console.print("Create one with: podstock list create <name> --type broad|niche|custom")
            return 0

        table = Table(title="Podcast Lists")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type")
        table.add_column("Podcasts", justify="right")
        table.add_column("Active", justify="center")

        for lst in lists:
            active = "✓" if lst.active else "✗"
            table.add_row(
                lst.id,
                lst.name,
                lst.type,
                str(len(lst.podcast_ids)),
                active
            )

        console.print(table)
        console.print("\n[dim]View details: podstock list show <list_id>[/dim]")

    return 0


def cmd_list_create(args: argparse.Namespace, manager) -> int:
    """Create a new list."""
    from podstock.lists.manager import ListError

    try:
        lst = manager.create_list(
            list_id=args.name.lower().replace(" ", "-"),
            name=args.name,
            list_type=args.type,
            description=args.description,
        )
        console.print(f"[green]✓[/green] Created list: {lst.name} (ID: {lst.id})")
        return 0
    except ListError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_list_add(args: argparse.Namespace, manager, config) -> int:
    """Add a podcast to a list."""
    from podstock.lists.manager import ListError
    from podstock.rss.manager import get_podcast

    # Verify podcast exists
    podcast = get_podcast(args.podcast_id, config.podcasts_file)
    if not podcast:
        console.print(f"[red]✗[/red] Podcast not found: {args.podcast_id}")
        console.print("[dim]Available podcasts: podstock podcast list[/dim]")
        return 1

    try:
        if manager.add_podcast_to_list(args.list_id, args.podcast_id):
            console.print(f"[green]✓[/green] Added {podcast.name} to list '{args.list_id}'")
            return 0
        else:
            console.print(f"[yellow]![/yellow] {podcast.name} is already in list '{args.list_id}'")
            return 0
    except ListError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_list_remove(args: argparse.Namespace, manager) -> int:
    """Remove a podcast from a list."""
    from podstock.lists.manager import ListError

    try:
        if manager.remove_podcast_from_list(args.list_id, args.podcast_id):
            console.print(f"[green]✓[/green] Removed {args.podcast_id} from list '{args.list_id}'")
            return 0
        else:
            console.print(f"[yellow]![/yellow] {args.podcast_id} is not in list '{args.list_id}'")
            return 0
    except ListError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_list_delete(args: argparse.Namespace, manager) -> int:
    """Delete a list."""
    from podstock.lists.manager import ListError

    try:
        if manager.delete_list(args.list_id):
            console.print(f"[green]✓[/green] Deleted list: {args.list_id}")
            return 0
        else:
            console.print(f"[red]✗[/red] List not found: {args.list_id}")
            return 1
    except ListError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


# =============================================================================
# Sync Commands
# =============================================================================


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync new podcast episodes."""
    from podstock.sync.orchestrator import SyncOrchestrator
    from podstock.rss.manager import get_podcast, load_podcasts

    config = get_config(args.data_dir)
    config.ensure_directories()
    state = State(config.state_file)
    orchestrator = SyncOrchestrator(config, state)

    latest_n = args.latest or 1
    dry_run = args.dry_run
    force = args.force

    # Determine what to sync
    if args.podcast:
        # Sync specific podcast
        podcast = get_podcast(args.podcast, config.podcasts_file)
        if not podcast:
            console.print(f"[red]✗[/red] Podcast not found: {args.podcast}")
            return 1

        console.print(f"\n[bold]{podcast.name}[/bold]")
        results = orchestrator.sync_podcast(podcast, latest_n, force, dry_run)

        # Print summary
        synced = sum(1 for r in results if r.status == "synced")
        skipped = sum(1 for r in results if r.status == "skipped")
        failed = sum(1 for r in results if r.status == "failed")

        console.print(f"\n[bold]Results:[/bold] {synced} synced, {skipped} skipped, {failed} failed")

    elif args.list:
        # Sync podcasts in list
        summary = orchestrator.sync_list(args.list, latest_n, force, dry_run)

        console.print(f"\n[bold]Sync Summary:[/bold]")
        console.print(f"  Podcasts checked: {summary.podcasts_checked}")
        console.print(f"  New episodes: {summary.new_episodes}")
        console.print(f"  Transcribed: {summary.transcribed}")
        console.print(f"  Failed: {summary.failed}")

        if summary.errors:
            console.print("\n[red]Errors:[/red]")
            for error in summary.errors:
                console.print(f"  • {error}")

    else:
        # Sync all active podcasts
        summary = orchestrator.sync_all(latest_n, force, dry_run)

        console.print(f"\n[bold]Sync Summary:[/bold]")
        console.print(f"  Podcasts checked: {summary.podcasts_checked}")
        console.print(f"  New episodes: {summary.new_episodes}")
        console.print(f"  Transcribed: {summary.transcribed}")
        console.print(f"  Failed: {summary.failed}")

        if summary.errors:
            console.print("\n[red]Errors:[/red]")
            for error in summary.errors:
                console.print(f"  • {error}")

    return 0


# =============================================================================
# Summary Commands
# =============================================================================


def cmd_summary(args: argparse.Namespace) -> int:
    """Handle summary subcommands."""
    if args.summary_command == "prepare":
        return cmd_summary_prepare(args)
    elif args.summary_command == "info":
        return cmd_summary_info(args)
    elif args.summary_command == "save":
        return cmd_summary_save(args)
    else:
        console.print("[yellow]Usage: podstock summary <prepare|info|save>[/yellow]")
        return 1


def cmd_summary_prepare(args: argparse.Namespace) -> int:
    """Prepare summary data for LLM processing."""
    from datetime import datetime
    from podstock.reports.generator import SummaryReportGenerator

    config = get_config(args.data_dir)
    state = State(config.state_file)
    generator = SummaryReportGenerator(config, state)

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        console.print("[red]✗[/red] Invalid date format. Use YYYY-MM-DD")
        return 1

    report_type = args.type or "broad"
    list_id = args.list or ("niche" if report_type == "detailed" else "broad")

    if args.opencode:
        # Export for Opencode/GLM-4.7
        output_path = generator.prepare_for_opencode(
            start_date, end_date, list_id, report_type
        )
        console.print(f"[green]✓[/green] Exporterat för Opencode: {output_path}")
        console.print("\n[bold]Nästa steg:[/bold]")
        console.print(f"1. Öppna {output_path} i Opencode")
        console.print("2. Be Opencode: \"Läs filen och generera rapporten enligt instruktionerna\"")
    else:
        # Prepare for Claude Code
        output_path = generator.prepare_for_claude_code(
            start_date, end_date, list_id, report_type
        )
        console.print(f"[green]✓[/green] Prompt sparad: {output_path}")
        console.print("\n[bold]Nästa steg:[/bold]")
        console.print(f"1. Läs {output_path}")
        console.print("2. Generera rapporten enligt instruktionerna")
        console.print("3. Spara med: podstock summary save --output rapport.md")

    return 0


def cmd_summary_info(args: argparse.Namespace) -> int:
    """Show available data for a period."""
    from datetime import datetime
    from podstock.reports.generator import SummaryReportGenerator

    config = get_config(args.data_dir)
    state = State(config.state_file)
    generator = SummaryReportGenerator(config, state)

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        console.print("[red]✗[/red] Invalid date format. Use YYYY-MM-DD")
        return 1

    list_id = args.list or "broad"

    info = generator.get_available_data(start_date, end_date, list_id)

    console.print(f"\n[bold]Data för {info['period']}[/bold]")
    console.print(f"  Lista: {info['list_name']} ({info['list_id']})")
    console.print(f"  Podcasts: {info['podcast_count']} st")
    for p in info['podcasts']:
        console.print(f"    • {p}")
    console.print(f"  Avsnitt: {info['episode_count']} st")
    console.print(f"    Med transkript: {info['episodes_with_transcripts']} st")
    console.print(f"  Rekommendationer: {info['recommendation_count']} st")

    return 0


def cmd_summary_save(args: argparse.Namespace) -> int:
    """Save a generated report."""
    from podstock.reports.generator import SummaryReportGenerator
    from pathlib import Path

    config = get_config(args.data_dir)
    state = State(config.state_file)
    generator = SummaryReportGenerator(config, state)

    # Read content from stdin or file
    if args.input:
        content = Path(args.input).read_text()
    else:
        console.print("[yellow]Läser rapport från stdin...[/yellow]")
        import sys
        content = sys.stdin.read()

    if not content.strip():
        console.print("[red]✗[/red] Ingen innehåll att spara")
        return 1

    output_path = Path(args.output) if args.output else None
    saved_path = generator.save_report(content, output_path)

    console.print(f"[green]✓[/green] Rapport sparad: {saved_path}")
    return 0


# =============================================================================
# Download Commands
# =============================================================================


def cmd_download(args: argparse.Namespace) -> int:
    """Download podcast episodes."""
    from podstock.core.exceptions import DownloadError, RSSError
    from podstock.rss.downloader import download_episode
    from podstock.rss.manager import get_podcast, load_podcasts
    from podstock.rss.parser import get_latest_episodes

    config = get_config(args.data_dir)
    config.ensure_directories()
    state = State(config.state_file)

    # Get podcasts to process
    if args.podcast:
        podcast = get_podcast(args.podcast, config.podcasts_file)
        if not podcast:
            console.print(f"[red]✗[/red] Podcast not found: {args.podcast}")
            return 1
        podcasts = [podcast]
    else:
        podcasts = [p for p in load_podcasts(config.podcasts_file) if p.active]

    if not podcasts:
        console.print("[yellow]No podcasts to process.[/yellow]")
        return 0

    n_latest = args.latest or 1
    total_downloaded = 0

    for podcast in podcasts:
        console.print(f"\n[bold]{podcast.name}[/bold]")

        try:
            with console.status("Fetching RSS feed..."):
                episodes = get_latest_episodes(str(podcast.rss_url), podcast.id, n=n_latest)
        except RSSError as e:
            console.print(f"  [red]✗[/red] Failed to fetch feed: {e}")
            continue

        for episode in episodes:
            if state.is_downloaded(episode.id) and not args.force:
                console.print(f"  [dim]Skipping (already downloaded): {episode.title}[/dim]")
                continue

            try:
                dest_dir = config.audio_dir / podcast.id
                path = download_episode(episode, dest_dir, show_progress=True)
                state.mark_downloaded(episode.id, path)
                console.print(f"  [green]✓[/green] Downloaded: {episode.title}")
                total_downloaded += 1
            except DownloadError as e:
                console.print(f"  [red]✗[/red] Failed: {episode.title} - {e}")

    console.print(f"\n[bold]Downloaded {total_downloaded} episode(s)[/bold]")
    return 0


# =============================================================================
# Transcribe Commands
# =============================================================================


def cmd_transcribe(args: argparse.Namespace) -> int:
    """Transcribe downloaded episodes."""
    from podstock.core.exceptions import TranscribeError
    from podstock.rss.manager import load_podcasts

    config = get_config(args.data_dir)
    config.ensure_directories()
    state = State(config.state_file)

    # Handle --list-apple: show available Apple transcripts
    if args.list_apple:
        return _cmd_list_apple_transcripts(config)

    # Handle --source apple: extract from Apple Podcasts
    if args.source == "apple":
        return _cmd_transcribe_apple(args, config, state)

    # Default: Whisper transcription
    return _cmd_transcribe_whisper(args, config, state)


def _cmd_list_apple_transcripts(config: Config) -> int:
    """List available Apple Podcast transcripts."""
    from podstock.rss.manager import load_podcasts
    from podstock.transcribe.apple import get_transcript_stats, list_available_transcripts

    try:
        stats = get_transcript_stats()
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        return 1

    if "error" in stats:
        console.print(f"[red]✗[/red] {stats['error']}")
        return 1

    console.print(f"\n[bold]Apple Podcasts Transcripts[/bold]")
    console.print(f"Total in database: {stats['total_in_database']}")
    console.print(f"Cached locally: {stats['total_cached']}")

    # Show configured podcasts that have transcripts
    podcasts = load_podcasts(config.podcasts_file)
    configured_names = {p.name.lower() for p in podcasts}

    table = Table(title="\nBy Podcast")
    table.add_column("Podcast", style="cyan")
    table.add_column("In Database", justify="right")
    table.add_column("Cached", justify="right")
    table.add_column("Configured", justify="center")

    for podcast_name, counts in sorted(stats["by_podcast"].items()):
        is_configured = any(
            podcast_name.lower() in name or name in podcast_name.lower()
            for name in configured_names
        )
        configured_mark = "[green]✓[/green]" if is_configured else ""
        table.add_row(
            podcast_name,
            str(counts["total"]),
            str(counts["cached"]),
            configured_mark,
        )

    console.print(table)

    if stats["total_cached"] == 0:
        console.print("\n[yellow]No transcripts cached locally.[/yellow]")
        console.print("View transcripts in Apple Podcasts app to cache them.")

    return 0


def _cmd_transcribe_apple(args: argparse.Namespace, config: Config, state: State) -> int:
    """Extract transcripts from Apple Podcasts."""
    from podstock.core.exceptions import TranscribeError
    from podstock.rss.manager import get_podcast, load_podcasts
    from podstock.transcribe.apple import (
        extract_and_save,
        list_available_transcripts,
        match_to_podcast,
    )

    podcasts = load_podcasts(config.podcasts_file)
    if not podcasts:
        console.print("[red]✗[/red] No podcasts configured.")
        return 1

    # Filter by podcast if specified
    if args.podcast:
        podcast = get_podcast(args.podcast, config.podcasts_file)
        if not podcast:
            console.print(f"[red]✗[/red] Podcast not found: {args.podcast}")
            return 1
        podcasts = [podcast]

    with_timestamps = not args.no_timestamps

    console.print(f"\n[bold]Extracting Apple Podcast transcripts[/bold]")
    console.print(f"Timestamps: {'Yes' if with_timestamps else 'No'}")

    try:
        transcripts = list_available_transcripts(podcasts=podcasts)
    except TranscribeError as e:
        console.print(f"[red]✗[/red] {e}")
        return 1

    # Filter to only cached transcripts
    cached_transcripts = [t for t in transcripts if t.is_cached]

    if not cached_transcripts:
        console.print("[yellow]No cached transcripts found for configured podcasts.[/yellow]")
        console.print("View transcripts in Apple Podcasts app to cache them.")
        console.print(f"\nAvailable in database (not cached): {len(transcripts)}")
        return 0

    total_extracted = 0
    total_skipped = 0

    for transcript in cached_transcripts:
        # Match to configured podcast
        matched_podcast = match_to_podcast(transcript.podcast_name, podcasts)
        if not matched_podcast:
            continue

        try:
            transcript_path, episode_id = extract_and_save(
                transcript=transcript,
                transcript_dir=config.transcripts_dir,
                podcast=matched_podcast,
                with_timestamps=with_timestamps,
            )

            # Check if already transcribed
            existing_status = state.get_status(episode_id)
            if existing_status and existing_status.transcribed and not args.force:
                console.print(f"[dim]Skipping (already transcribed): {episode_id}[/dim]")
                total_skipped += 1
                continue

            state.mark_transcribed(
                episode_id,
                transcript_path,
                source="apple",
                has_timestamps=with_timestamps,
            )

            console.print(f"[green]✓[/green] {transcript.episode_title}")
            console.print(f"    → {transcript_path}")
            total_extracted += 1

        except TranscribeError as e:
            console.print(f"[red]✗[/red] {transcript.episode_title}: {e}")

    console.print(f"\n[bold]Extracted {total_extracted} transcript(s)[/bold]")
    if total_skipped > 0:
        console.print(f"[dim]Skipped {total_skipped} (already transcribed)[/dim]")

    return 0


def _cmd_transcribe_whisper(args: argparse.Namespace, config: Config, state: State) -> int:
    """Transcribe episodes using Whisper."""
    from podstock.core.exceptions import TranscribeError
    from podstock.transcribe.whisper import save_transcript, transcribe

    # Get episodes to transcribe
    if args.episode:
        episodes_to_process = [args.episode]
    elif args.podcast:
        # Get downloaded episodes for this podcast
        all_episodes = state.get_all_episodes()
        episodes_to_process = [
            ep_id
            for ep_id, status in all_episodes.items()
            if status.downloaded
            and not status.transcribed
            and ep_id.startswith(args.podcast)
        ]
    else:
        episodes_to_process = state.get_pending_transcription()

    if not episodes_to_process:
        console.print("[yellow]No episodes to transcribe.[/yellow]")
        return 0

    model = args.model or config.whisper_model
    console.print(f"Using model: [cyan]{model}[/cyan]")

    total_transcribed = 0

    for episode_id in episodes_to_process:
        status = state.get_status(episode_id)
        if not status or not status.audio_path:
            console.print(f"[red]✗[/red] Audio not found for: {episode_id}")
            continue

        if status.transcribed and not args.force:
            console.print(f"[dim]Skipping (already transcribed): {episode_id}[/dim]")
            continue

        audio_path = status.audio_path
        if not audio_path.exists():
            console.print(f"[red]✗[/red] Audio file missing: {audio_path}")
            continue

        # Extract podcast_id from episode_id
        parts = episode_id.rsplit("-", 2)
        podcast_id = parts[0] if len(parts) >= 3 else episode_id.split("-")[0]

        console.print(f"\n[bold]Transcribing: {episode_id}[/bold]")

        try:
            def progress_cb(msg: str) -> None:
                console.print(f"  {msg}")

            text = transcribe(audio_path, model=model, progress_callback=progress_cb)

            transcript_path = save_transcript(
                episode_id=episode_id,
                text=text,
                transcript_dir=config.transcripts_dir,
                podcast_id=podcast_id,
                metadata={"model": model},
            )

            state.mark_transcribed(episode_id, transcript_path, source="whisper")
            console.print(f"  [green]✓[/green] Saved to: {transcript_path}")
            total_transcribed += 1

        except TranscribeError as e:
            console.print(f"  [red]✗[/red] Failed: {e}")

    console.print(f"\n[bold]Transcribed {total_transcribed} episode(s)[/bold]")
    return 0


# =============================================================================
# Analyze Commands
# =============================================================================


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze transcripts for stock recommendations."""
    from podstock.analyze.prompt_builder import build_analysis_prompt
    from podstock.analyze.result_parser import parse_claude_response, save_recommendations
    from podstock.rss.manager import get_podcast
    from podstock.transcribe.whisper import load_transcript

    config = get_config(args.data_dir)
    state = State(config.state_file)

    episode_id = args.episode

    # Get episode status
    status = state.get_status(episode_id)
    if not status or not status.transcribed:
        console.print(f"[red]✗[/red] Episode not transcribed: {episode_id}")
        return 1

    # Extract podcast_id
    parts = episode_id.rsplit("-", 2)
    podcast_id = parts[0] if len(parts) >= 3 else episode_id.split("-")[0]

    # Load transcript
    try:
        transcript = load_transcript(episode_id, config.transcripts_dir, podcast_id)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load transcript: {e}")
        return 1

    # Get podcast info
    podcast = get_podcast(podcast_id, config.podcasts_file)
    podcast_name = podcast.name if podcast else podcast_id
    hosts = podcast.hosts if podcast else []

    if args.input:
        # Parse existing Claude response
        try:
            response = Path(args.input).read_text(encoding="utf-8")
            recommendations = parse_claude_response(response, episode_id)

            save_recommendations(
                recommendations,
                config.recommendations_dir,
                podcast_id,
                episode_id,
            )

            state.mark_analyzed(episode_id, len(recommendations))

            console.print(f"[green]✓[/green] Parsed {len(recommendations)} recommendations")

            for rec in recommendations:
                console.print(f"  • {rec.company_name} ({rec.confidence.value})")

            return 0

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to parse response: {e}")
            return 1
    else:
        # Generate prompt
        prompt = build_analysis_prompt(
            transcript=transcript,
            podcast_name=podcast_name,
            episode_title=episode_id,
            episode_date=episode_id,
            hosts=hosts,
        )

        console.print("[bold]Analysis Prompt[/bold]")
        console.print("-" * 60)
        console.print(prompt)
        console.print("-" * 60)
        console.print("\n[yellow]Copy the prompt above and paste it into Claude.[/yellow]")
        console.print("Then run: podstock analyze {episode_id} --input response.txt")

        return 0


# =============================================================================
# Report Commands
# =============================================================================


def cmd_report(args: argparse.Namespace) -> int:
    """Generate recommendations report."""
    from podstock.analyze.result_parser import load_recommendations
    from podstock.report.markdown import generate_and_save_report, generate_report

    config = get_config(args.data_dir)
    state = State(config.state_file)

    # Collect all recommendations
    all_recommendations = []

    for episode_id, status in state.get_all_episodes().items():
        if not status.analyzed:
            continue

        parts = episode_id.rsplit("-", 2)
        podcast_id = parts[0] if len(parts) >= 3 else episode_id.split("-")[0]

        if args.podcast and podcast_id != args.podcast:
            continue

        try:
            recs = load_recommendations(config.recommendations_dir, podcast_id, episode_id)
            all_recommendations.extend(recs)
        except Exception:
            continue

    if not all_recommendations:
        console.print("[yellow]No recommendations found.[/yellow]")
        return 0

    if args.output:
        path = generate_and_save_report(
            all_recommendations,
            config.reports_dir,
            filename=args.output,
        )
        console.print(f"[green]✓[/green] Report saved to: {path}")
    else:
        report = generate_report(all_recommendations)
        console.print(report)

    return 0


# =============================================================================
# Status Command
# =============================================================================


def cmd_status(args: argparse.Namespace) -> int:
    """Show processing status."""
    from podstock.rss.manager import load_podcasts

    config = get_config(args.data_dir)
    state = State(config.state_file)
    podcasts = load_podcasts(config.podcasts_file)

    # Create status table
    table = Table(title="PodStock Status")
    table.add_column("Podcast", style="cyan")
    table.add_column("Downloaded", justify="right")
    table.add_column("Transcribed", justify="right")
    table.add_column("Analyzed", justify="right")

    all_episodes = state.get_all_episodes()

    # Group by podcast
    for podcast in podcasts:
        downloaded = 0
        transcribed = 0
        analyzed = 0

        for ep_id, status in all_episodes.items():
            if not ep_id.startswith(podcast.id):
                continue

            if status.downloaded:
                downloaded += 1
            if status.transcribed:
                transcribed += 1
            if status.analyzed:
                analyzed += 1

        table.add_row(
            podcast.name,
            str(downloaded),
            str(transcribed),
            str(analyzed),
        )

    console.print(table)

    # Pending work
    pending_transcription = state.get_pending_transcription()
    pending_analysis = state.get_pending_analysis()

    if pending_transcription:
        console.print(f"\n[yellow]Pending transcription:[/yellow] {len(pending_transcription)}")

    if pending_analysis:
        console.print(f"[yellow]Pending analysis:[/yellow] {len(pending_analysis)}")

    return 0


# =============================================================================
# Extract Commands
# =============================================================================


def cmd_extract(args: argparse.Namespace) -> int:
    """Handle extract subcommands."""
    import os
    from pathlib import Path

    config = get_config(args.data_dir)
    base_dir = config.data_dir
    transcripts_dir = base_dir / "transcripts"
    extracted_dir = base_dir / "extracted"
    processing_dir = base_dir / "processing"

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if args.extract_command == "process":
        is_ollama = args.model.startswith("ollama:")

        if not is_ollama and not api_key:
            console.print("[red]Error:[/red] ANTHROPIC_API_KEY not set")
            console.print("Set it with: export ANTHROPIC_API_KEY=your-key")
            console.print("\nOr use local model: --model ollama:llama3.3")
            return 1

        from podstock.extract.batch_runner import BatchRunner
        from podstock.extract.process_transcript import TranscriptProcessor

        if args.file:
            # Process single file
            processor = TranscriptProcessor(api_key, model=args.model)
            filepath = Path(args.file)
            if not filepath.exists():
                console.print(f"[red]Error:[/red] File not found: {filepath}")
                return 1

            with console.status(f"Processing {filepath.name}..."):
                analysis = processor.process_transcript(filepath)
                output_file = processor.save_analysis(analysis, extracted_dir)

            console.print(f"[green]✓[/green] Extracted {len(analysis.recommendations)} recommendations")
            console.print(f"  Saved to: {output_file}")
        else:
            # Batch process
            runner = BatchRunner(
                api_key=api_key,
                transcripts_dir=transcripts_dir,
                output_dir=extracted_dir,
                processing_dir=processing_dir,
                model=args.model,
            )
            runner.run(
                skip_completed=True,
                max_files=args.max,
                delay_between=args.delay,
                podcast_filter=args.podcast,
            )

    elif args.extract_command == "search":
        from podstock.extract.search import RecommendationSearch

        try:
            search = RecommendationSearch(extracted_dir)
        except FileNotFoundError:
            console.print("[yellow]No extracted data found.[/yellow]")
            console.print("Run 'podstock extract process' first.")
            return 1

        if args.top:
            top_stocks = search.get_top_stocks(args.top)
            table = Table(title=f"Top {args.top} Most Mentioned Stocks")
            table.add_column("#", justify="right", style="dim")
            table.add_column("Stock", style="cyan")
            table.add_column("Mentions", justify="right")
            table.add_column("Latest Action", style="green")

            for i, stock in enumerate(top_stocks, 1):
                latest = stock.get("latest_recommendation", {})
                latest_action = latest.get("action", "?").upper() if latest else "?"
                table.add_row(str(i), stock["name"], str(stock["mention_count"]), latest_action)

            console.print(table)
            return 0

        results = []
        if args.stock:
            results = search.get_recommendations_for_stock(args.stock, args.action)
        elif args.recent:
            results = search.get_recent_recommendations(args.recent, args.action)
        elif args.speaker:
            results = search.search_by_speaker(args.speaker)
        elif args.podcast:
            results = search.search_by_podcast(args.podcast)
        elif args.action:
            results = [r for r in search.recommendations if r["action"] == args.action]

        if results:
            console.print(f"\n[green]Found {len(results)} recommendations:[/green]\n")
            for r in results[:15]:
                action_color = {
                    "buy": "green",
                    "sell": "red",
                    "hold": "yellow",
                    "watch": "blue",
                    "avoid": "magenta",
                }.get(r["action"], "white")

                console.print(f"  [{r['date']}] [cyan]{r['stock']}[/cyan] - [{action_color}]{r['action'].upper()}[/{action_color}]")
                console.print(f"    Podcast: {r['podcast']}")
                if r.get("speaker"):
                    console.print(f"    Speaker: {r['speaker']}")
                if r.get("reasoning"):
                    reasoning = r["reasoning"][:80] + "..." if len(r["reasoning"]) > 80 else r["reasoning"]
                    console.print(f"    [dim]{reasoning}[/dim]")
                console.print()

            if len(results) > 15:
                console.print(f"  [dim]... and {len(results) - 15} more[/dim]")
        else:
            console.print("[yellow]No results found.[/yellow]")

    elif args.extract_command == "stats":
        from podstock.extract.search import RecommendationSearch

        try:
            search = RecommendationSearch(extracted_dir)
        except FileNotFoundError:
            console.print("[yellow]No extracted data found.[/yellow]")
            return 1

        stats = search.get_stats()

        console.print("\n[bold]PodStock Extraction Statistics[/bold]")
        console.print("=" * 40)
        console.print(f"Total episodes:        {stats['total_episodes']}")
        console.print(f"Total recommendations: {stats['total_recommendations']}")
        console.print(f"Unique stocks:         {stats['unique_stocks']}")

        console.print("\n[bold]By Action:[/bold]")
        for action, count in stats["recommendations_by_action"].items():
            console.print(f"  {action}: {count}")

        console.print("\n[bold]By Podcast:[/bold]")
        for podcast, count in stats["recommendations_by_podcast"].items():
            console.print(f"  {podcast}: {count}")

        console.print(f"\nLast updated: {stats['last_updated']}")

    elif args.extract_command == "rebuild-index":
        from podstock.extract.build_index import save_index

        try:
            with console.status("Rebuilding index..."):
                save_index(extracted_dir)
            console.print("[green]✓[/green] Index rebuilt successfully")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1

    elif args.extract_command == "list":
        from podstock.extract.batch_runner import BatchRunner

        runner = BatchRunner(
            api_key="dummy",
            transcripts_dir=transcripts_dir,
            output_dir=extracted_dir,
            processing_dir=processing_dir,
        )

        files = runner.find_transcripts()
        completed = runner.get_completed()

        if args.pending:
            files = [f for f in files if f.name not in completed]
            console.print(f"\n[bold]Pending transcripts ({len(files)} files):[/bold]\n")
        else:
            console.print(f"\n[bold]All transcripts ({len(files)} files):[/bold]\n")

        for f in files[:30]:
            status = "[green]✓[/green]" if f.name in completed else "[dim]○[/dim]"
            console.print(f"  {status} {f.parent.name}/{f.name}")

        if len(files) > 30:
            console.print(f"\n  [dim]... and {len(files) - 30} more[/dim]")

    else:
        console.print("Usage: podstock extract <command>")
        console.print("Commands: process, search, stats, rebuild-index, list")
        return 1

    return 0


# =============================================================================
# Twitter Commands
# =============================================================================


def cmd_twitter(args: argparse.Namespace) -> int:
    """Handle twitter subcommands."""
    config = get_config(args.data_dir)

    if args.twitter_command == "add":
        return cmd_twitter_add(args, config)
    elif args.twitter_command == "list":
        return cmd_twitter_list(args, config)
    elif args.twitter_command == "remove":
        return cmd_twitter_remove(args, config)
    elif args.twitter_command == "collect":
        return cmd_twitter_collect(args, config)
    elif args.twitter_command == "info":
        return cmd_twitter_info(args, config)
    elif args.twitter_command == "coverage":
        return cmd_twitter_coverage(args, config)
    elif args.twitter_command == "url":
        return cmd_twitter_url(args, config)
    elif args.twitter_command == "search":
        return cmd_twitter_search(args, config)
    elif args.twitter_command == "stats":
        return cmd_twitter_stats(args, config)
    elif args.twitter_command == "rebuild-index":
        return cmd_twitter_rebuild_index(args, config)
    elif args.twitter_command == "analyze":
        return cmd_twitter_analyze(args, config)
    elif args.twitter_command == "report":
        return cmd_twitter_report(args, config)
    else:
        console.print("Usage: podstock twitter <command>")
        console.print("Commands: add, list, remove, collect, coverage, url, search, stats, rebuild-index, analyze, report")
        return 1


def cmd_twitter_add(args: argparse.Namespace, config: Config) -> int:
    """Add a Twitter source to follow."""
    from podstock.twitter.manager import add_twitter_source
    from podstock.twitter.exceptions import TwitterError

    sources_file = config.twitter_sources_file

    try:
        source = add_twitter_source(
            handle=args.handle,
            sources_file=sources_file,
            category=getattr(args, "category", None),
            description=getattr(args, "description", None),
        )

        console.print(f"[green]✓[/green] Added: @{source.handle} (ID: {source.id})")
        if source.category:
            console.print(f"  Category: {source.category}")
        return 0

    except TwitterError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_twitter_list(args: argparse.Namespace, config: Config) -> int:
    """List all Twitter sources."""
    from podstock.twitter.manager import load_twitter_sources
    from podstock.twitter.state import TwitterState

    sources_file = config.twitter_sources_file
    state_file = config.twitter_state_file

    sources = load_twitter_sources(sources_file)
    state = TwitterState(state_file)

    if not sources:
        console.print("[yellow]No Twitter sources configured.[/yellow]")
        console.print("Add one with: podstock twitter add @username")
        return 0

    table = Table(title="Twitter Sources")
    table.add_column("Handle", style="cyan")
    table.add_column("Category")
    table.add_column("Tweets", justify="right")
    table.add_column("Last Collected")
    table.add_column("Active", justify="center")

    for source in sources:
        source_state = state.get_state(source.id)
        tweet_count = source_state.tweet_count if source_state else 0
        last_collected = (
            source_state.last_collected_at.strftime("%Y-%m-%d")
            if source_state and source_state.last_collected_at
            else "Never"
        )
        active = "✓" if source.active else "✗"

        table.add_row(
            f"@{source.handle}",
            source.category or "-",
            str(tweet_count),
            last_collected,
            active,
        )

    console.print(table)
    return 0


def cmd_twitter_remove(args: argparse.Namespace, config: Config) -> int:
    """Remove a Twitter source."""
    from podstock.twitter.manager import remove_twitter_source
    from podstock.twitter.exceptions import TwitterSourceNotFoundError

    sources_file = config.twitter_sources_file

    try:
        source = remove_twitter_source(args.id, sources_file)
        console.print(f"[green]✓[/green] Removed: @{source.handle}")
        return 0
    except TwitterSourceNotFoundError:
        console.print(f"[red]✗[/red] Source not found: {args.id}")
        return 1


def cmd_twitter_collect(args: argparse.Namespace, config: Config) -> int:
    """Collect tweets from Twitter sources via API.

    Uses twitterapi.io to fetch tweets automatically.
    With --since/--until, uses Advanced Search for cost-effective date-filtered collection.
    """
    from datetime import date as date_type
    from podstock.twitter.manager import load_twitter_sources, add_twitter_source
    from podstock.twitter.state import TwitterState

    sources_file = config.twitter_sources_file
    state_file = config.twitter_state_file

    # Parse date arguments
    since_date = None
    until_date = None
    if args.since:
        try:
            parts = args.since.split("-")
            since_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            console.print(f"[red]✗[/red] Invalid date format for --since: {args.since}")
            console.print("Use YYYY-MM-DD format (e.g., 2024-01-01)")
            return 1

    if args.until:
        try:
            parts = args.until.split("-")
            until_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            console.print(f"[red]✗[/red] Invalid date format for --until: {args.until}")
            console.print("Use YYYY-MM-DD format (e.g., 2025-12-31)")
            return 1

    # Load or create sources
    sources = load_twitter_sources(sources_file)

    # If source specified but doesn't exist, offer to add it
    if args.source:
        matching = [s for s in sources if s.id == args.source.lower().lstrip("@")]
        if not matching:
            # Source not found - add it
            console.print(f"[yellow]Source not found: {args.source}[/yellow]")
            console.print(f"Adding @{args.source.lstrip('@')} as a new source...")
            try:
                new_source = add_twitter_source(
                    handle=args.source,
                    sources_file=sources_file,
                )
                sources = [new_source]
                console.print(f"[green]✓[/green] Added: @{new_source.handle}")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to add source: {e}")
                return 1
        else:
            sources = matching
    elif not sources:
        console.print("[yellow]No Twitter sources configured.[/yellow]")
        console.print("Add one with: podstock twitter add @username")
        console.print("Or specify directly: podstock twitter collect --source @username")
        return 0

    # Filter to active only by default
    if not args.all:
        sources = [s for s in sources if s.active]

    max_tweets = args.max or 10000
    incremental = not args.full
    include_replies = getattr(args, "include_replies", True)

    # Use API collection
    try:
        from podstock.twitter.api_collector import TwitterAPICollector
    except ImportError as e:
        console.print(f"[red]✗[/red] API collector not available: {e}")
        return 1

    try:
        collector = TwitterAPICollector(data_dir=config.data_dir)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        console.print("\nSet your API key:")
        console.print("  export TWITTER_API_KEY=your_key_here")
        console.print("\nGet a key at: https://twitterapi.io")
        return 1

    state = TwitterState(state_file)

    console.print(f"\n[bold]Twitter API Collection[/bold]")
    console.print(f"Sources: {len(sources)}")
    if since_date or until_date:
        console.print(f"Date range: {since_date or 'start'} to {until_date or 'now'}")
        console.print(f"Method: [green]Advanced Search[/green] (cost-effective)")
    else:
        console.print(f"Mode: {'Full' if args.full else 'Incremental'}")
    console.print(f"Max tweets per source: {max_tweets}")
    console.print(f"Include replies: {include_replies}")
    console.print()

    total_collected = 0
    errors = 0

    for source in sources:
        source_state = state.get_or_create_state(source.id)

        console.print(f"[cyan]@{source.handle}[/cyan]", end=" ")
        console.print(f"[dim](current: {source_state.tweet_count} tweets)[/dim]")

        with console.status(f"  Fetching tweets..."):
            result = collector.collect_source(
                source_id=source.id,
                max_tweets=max_tweets,
                incremental=incremental,
                since=since_date,
                until=until_date,
                include_replies=include_replies,
            )

        if result.success:
            if result.tweets_collected > 0:
                console.print(f"  [green]✓[/green] Collected {result.tweets_collected} new tweets")
                console.print(f"    Total now: {result.total_tweets}")
                total_collected += result.tweets_collected
            else:
                console.print(f"  [dim]No new tweets[/dim]")

            if result.is_complete:
                console.print(f"    [dim]Timeline complete[/dim]")
        else:
            console.print(f"  [red]✗[/red] {result.error}")
            errors += 1

    console.print()
    console.print(f"[bold]Summary[/bold]")
    console.print(f"  Collected: {total_collected} new tweets")
    if total_collected > 0:
        estimated_cost = total_collected * 0.00015
        console.print(f"  Estimated cost: ~${estimated_cost:.4f}")
    if errors > 0:
        console.print(f"  Errors: [red]{errors}[/red]")

    return 0 if errors == 0 else 1


def cmd_twitter_info(args: argparse.Namespace, config: Config) -> int:
    """Show detailed info for a Twitter source including collection history."""
    from podstock.twitter.state import TwitterState
    from podstock.twitter.storage import TweetStorage

    source_id = args.source.lower().lstrip("@")
    state_file = config.twitter_state_file

    state = TwitterState(state_file)
    storage = TweetStorage(config.data_dir)

    source_state = state.get_state(source_id)
    if not source_state:
        console.print(f"[yellow]No data found for @{source_id}[/yellow]")
        return 1

    # Get actual date range from tweets
    tweets = list(storage.load_tweets(source_id, limit=None))
    actual_oldest = None
    actual_newest = None
    if tweets:
        dates = [t.posted_at for t in tweets if t.posted_at]
        if dates:
            actual_oldest = min(dates)
            actual_newest = max(dates)

    console.print(f"\n[bold cyan]@{source_id}[/bold cyan]")
    console.print(f"{'─' * 50}")

    # Basic stats
    console.print(f"\n[bold]Summary[/bold]")
    console.print(f"  Total tweets: {source_state.tweet_count}")
    if actual_oldest and actual_newest:
        console.print(f"  Actual date range: {actual_oldest.strftime('%Y-%m-%d')} → {actual_newest.strftime('%Y-%m-%d')}")
    if source_state.last_collected_at:
        console.print(f"  Last collected: {source_state.last_collected_at.strftime('%Y-%m-%d %H:%M')}")

    # Collection history
    console.print(f"\n[bold]Collection History[/bold]")
    if source_state.collection_history:
        for run in source_state.collection_history:
            date_str = run.collected_at.strftime("%Y-%m-%d %H:%M") if run.collected_at else "Unknown"
            since_str = run.requested_since or "start"
            until_str = run.requested_until or "now"
            method_badge = "[green]Advanced Search[/green]" if run.method == "advanced_search" else "[dim]Last Tweets[/dim]"

            console.print(f"  {date_str}: {since_str} → {until_str}")
            console.print(f"    Method: {method_badge}, Tweets added: {run.tweets_added}")
    else:
        console.print("  [dim]No collection history recorded[/dim]")
        console.print("  [dim](History tracking was added after initial collection)[/dim]")

    console.print()
    return 0


def cmd_twitter_coverage(args: argparse.Namespace, config: Config) -> int:
    """Show tweet coverage analysis for a source."""
    from collections import defaultdict
    from podstock.twitter.storage import TweetStorage

    source_id = args.source

    storage = TweetStorage(config.data_dir)
    tweets = list(storage.load_tweets(source_id))

    if not tweets:
        console.print(f"[yellow]No tweets found for @{source_id}[/yellow]")
        return 0

    # Group by month
    by_month: dict[str, list] = defaultdict(list)
    for tweet in tweets:
        month_key = tweet.posted_at.strftime("%Y-%m")
        by_month[month_key].append(tweet)

    # Find date range
    dates = [t.posted_at for t in tweets]
    oldest = min(dates)
    newest = max(dates)

    # Generate all months in range
    all_months = []
    current = oldest.replace(day=1)
    end = newest.replace(day=1)
    while current <= end:
        all_months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # Categorize months (20+ tweets = complete)
    min_tweets = 20
    complete_months = []
    incomplete_months = []
    missing_months = []

    for month in all_months:
        count = len(by_month.get(month, []))
        if count == 0:
            missing_months.append(month)
        elif count < min_tweets:
            incomplete_months.append((month, count))
        else:
            complete_months.append((month, count))

    # Print results
    console.print(f"\n[bold]Coverage Analysis: @{source_id}[/bold]")
    console.print("=" * 60)
    console.print(f"\nTotal tweets: {len(tweets)}")
    console.print(f"Date range: {oldest.strftime('%Y-%m-%d')} -> {newest.strftime('%Y-%m-%d')}")

    if complete_months:
        console.print(f"\n[green]Complete months ({len(complete_months)}):[/green]")
        for month, count in complete_months:
            console.print(f"  {month}: {count} tweets")

    if incomplete_months:
        console.print(f"\n[yellow]Incomplete months ({len(incomplete_months)}):[/yellow]")
        for month, count in incomplete_months:
            console.print(f"  {month}: {count} tweets (< {min_tweets})")

    if missing_months:
        console.print(f"\n[red]Missing months ({len(missing_months)}):[/red]")
        for month in missing_months:
            console.print(f"  {month}")

    # Recommendations
    console.print("\n" + "=" * 60)
    console.print("[bold]Recommendations:[/bold]")
    if missing_months:
        console.print(f"  - Collect missing periods: {', '.join(missing_months[:5])}" +
                      (f" (+{len(missing_months)-5} more)" if len(missing_months) > 5 else ""))
    if incomplete_months:
        months = [m for m, _ in incomplete_months]
        console.print(f"  - Re-scan incomplete periods: {', '.join(months[:5])}" +
                      (f" (+{len(months)-5} more)" if len(months) > 5 else ""))
    if not missing_months and not incomplete_months:
        console.print("  - All periods appear complete!")

    # Show JSON output if requested
    if args.json:
        import json
        data = {
            "source_id": source_id,
            "total_tweets": len(tweets),
            "oldest_date": oldest.isoformat(),
            "newest_date": newest.isoformat(),
            "complete_months": complete_months,
            "incomplete_months": incomplete_months,
            "missing_months": missing_months,
        }
        console.print("\n[dim]JSON:[/dim]")
        console.print(json.dumps(data, indent=2, default=str))

    return 0


def cmd_twitter_url(args: argparse.Namespace, config: Config) -> int:
    """Generate Twitter search URL for a date range."""
    source_id = args.source
    since = args.since
    until = args.until

    # Generate URL
    query = f"from:{source_id} since:{since} until:{until}"
    encoded = query.replace(":", "%3A").replace(" ", "%20")
    url = f"https://x.com/search?q={encoded}&src=typed_query&f=live"

    console.print(f"\n[bold]Twitter Search URL[/bold]")
    console.print(f"Source: @{source_id}")
    console.print(f"Period: {since} to {until}")
    console.print(f"\n[cyan]{url}[/cyan]")

    return 0


def cmd_twitter_search(args: argparse.Namespace, config: Config) -> int:
    """Search tweets by ticker or user."""
    from podstock.twitter.search import TweetSearch

    try:
        search = TweetSearch(config.data_dir)
    except Exception:
        console.print("[yellow]No indexed data found.[/yellow]")
        console.print("Run 'podstock twitter rebuild-index' first.")
        return 1

    if not search.has_data():
        console.print("[yellow]No tweets indexed.[/yellow]")
        console.print("Collect tweets first, then run 'podstock twitter rebuild-index'.")
        return 0

    results = []

    if args.ticker:
        results = search.get_ticker_history(
            args.ticker,
            days=args.recent if args.recent else None
        )
        title = f"Tweets mentioning ${args.ticker.upper()}"

    elif args.user:
        results = search.search_user(args.user, with_tickers_only=args.with_tickers)
        title = f"Tweets from @{args.user}"

    elif args.top_tickers:
        top = search.get_top_tickers(args.top_tickers)
        table = Table(title=f"Top {args.top_tickers} Mentioned Tickers")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Ticker", style="cyan")
        table.add_column("Mentions", justify="right")

        for i, item in enumerate(top, 1):
            table.add_row(str(i), f"${item['ticker']}", str(item["mention_count"]))

        console.print(table)
        return 0

    elif args.top_users:
        top = search.get_top_sources(args.top_users)
        table = Table(title=f"Top {args.top_users} Sources")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Source", style="cyan")
        table.add_column("Tweets", justify="right")
        table.add_column("With Tickers", justify="right")

        for i, item in enumerate(top, 1):
            table.add_row(
                str(i),
                f"@{item['source_id']}",
                str(item["tweet_count"]),
                str(item.get("tweets_with_tickers", 0)),
            )

        console.print(table)
        return 0

    else:
        # Show recent tweets with tickers
        results = search.get_recent_tweets(
            days=args.recent or 7,
            with_tickers_only=True,
            limit=50,
        )
        title = f"Recent tweets with tickers (last {args.recent or 7} days)"

    if results:
        console.print(f"\n[bold]{title}[/bold]")
        console.print(f"Found: {len(results)} tweets\n")

        limit = args.limit or 20
        for r in results[:limit]:
            posted = r.get("posted_at", "unknown")[:10]
            source = r.get("source_id") or r.get("author", "unknown")
            preview = r.get("text_preview", "")[:60]
            tickers = r.get("tickers", [])

            console.print(f"  [{posted}] @{source}")
            if tickers:
                ticker_str = " ".join(f"${t}" for t in tickers)
                console.print(f"    Tickers: [cyan]{ticker_str}[/cyan]")
            console.print(f"    [dim]{preview}...[/dim]")
            console.print()

        if len(results) > limit:
            console.print(f"  [dim]... and {len(results) - limit} more[/dim]")
    else:
        console.print("[yellow]No results found.[/yellow]")

    return 0


def cmd_twitter_stats(args: argparse.Namespace, config: Config) -> int:
    """Show Twitter statistics."""
    from podstock.twitter.search import TweetSearch
    from podstock.twitter.state import TwitterState
    from podstock.twitter.manager import load_twitter_sources

    sources_file = config.twitter_sources_file
    state_file = config.twitter_state_file

    sources = load_twitter_sources(sources_file)
    state = TwitterState(state_file)

    console.print("\n[bold]Twitter Collection Statistics[/bold]")
    console.print("=" * 40)

    # Source stats
    state_stats = state.get_stats()
    console.print(f"Sources configured: {len(sources)}")
    console.print(f"Sources with data:  {state_stats['source_count']}")
    console.print(f"Total tweets:       {state_stats['total_tweets']}")
    console.print(f"Complete sources:   {state_stats['complete_sources']}")

    if state_stats['sources_with_errors'] > 0:
        console.print(f"Sources with errors: [red]{state_stats['sources_with_errors']}[/red]")

    # Try to load index stats
    try:
        search = TweetSearch(config.data_dir)
        if search.has_data():
            index_stats = search.get_stats()
            console.print(f"\n[bold]Index Statistics[/bold]")
            console.print(f"Unique tickers:     {index_stats['unique_tickers']}")
            console.print(f"Tweets with tickers: {index_stats['tweets_with_tickers']}")

            date_range = index_stats.get("date_range", {})
            if date_range.get("earliest"):
                console.print(f"Date range:         {date_range['earliest'][:10]} to {date_range['latest'][:10]}")

            console.print(f"Last indexed:       {index_stats.get('last_updated', 'Unknown')[:19]}")

            # Top tickers
            if index_stats.get("top_tickers"):
                console.print(f"\n[bold]Top 5 Tickers:[/bold]")
                for item in index_stats["top_tickers"][:5]:
                    console.print(f"  ${item['ticker']}: {item['mention_count']} mentions")
    except Exception:
        console.print("\n[dim]Index not built. Run 'podstock twitter rebuild-index'.[/dim]")

    return 0


def cmd_twitter_rebuild_index(args: argparse.Namespace, config: Config) -> int:
    """Rebuild Twitter search indexes."""
    from podstock.twitter.index import TwitterIndexBuilder

    builder = TwitterIndexBuilder(config.data_dir)

    with console.status("Building indexes..."):
        stats = builder.build_all()

    console.print(f"[green]✓[/green] Index rebuilt successfully")
    console.print(f"  Tweets indexed: {stats['tweet_count']}")
    console.print(f"  Sources: {stats['source_count']}")
    console.print(f"  Unique tickers: {stats['unique_tickers']}")

    return 0


def cmd_twitter_analyze(args: argparse.Namespace, config: Config) -> int:
    """Analyze tweets using LLM to extract stock recommendations."""
    from podstock.twitter.analyze import TweetAnalyzer, analyze_source_tweets
    from podstock.twitter.storage import TweetStorage

    source_id = args.source
    if not source_id:
        console.print("[red]✗[/red] Source required. Use --source <handle>")
        return 1

    storage = TweetStorage(config.data_dir)

    # Load tweets and filter to those with tickers
    tweets = list(storage.load_tweets(source_id))
    tweets_with_tickers = []
    for tweet in tweets:
        tweet.extract_entities()
        if tweet.mentioned_tickers:
            tweets_with_tickers.append(tweet)

    if not tweets_with_tickers:
        console.print(f"[yellow]No tweets with tickers found for @{source_id}[/yellow]")
        return 0

    max_tweets = args.max or len(tweets_with_tickers)
    tweets_to_analyze = tweets_with_tickers[:max_tweets]

    console.print(f"\n[bold]Analyzing tweets from @{source_id}[/bold]")
    console.print(f"Tweets with tickers: {len(tweets_with_tickers)}")
    console.print(f"Will analyze: {len(tweets_to_analyze)}")
    console.print(f"Model: {args.model}")
    console.print()

    try:
        analyzer = TweetAnalyzer(model=args.model)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        return 1

    analyses = []
    for i, tweet in enumerate(tweets_to_analyze, 1):
        tickers = ", ".join(f"${t}" for t in tweet.mentioned_tickers)
        console.print(f"[{i}/{len(tweets_to_analyze)}] {tickers}")

        with console.status("  Analyzing..."):
            analysis = analyzer.analyze_tweet(tweet)

        if analysis:
            analyses.append(analysis)
            for mention in analysis.stock_mentions:
                action_color = {
                    "buy": "green",
                    "sell": "red",
                    "hold": "yellow",
                    "watch": "blue",
                }.get(mention.action.value, "white")
                console.print(f"  [{action_color}]{mention.action.value.upper()}[/{action_color}] {mention.ticker or mention.stock_name} ({mention.confidence})")
        else:
            console.print("  [dim]No analysis[/dim]")

    # Save analyses
    if analyses:
        output_dir = config.twitter_analyses_dir
        output_path = analyzer.save_analyses(analyses, output_dir, source_id)
        console.print(f"\n[green]✓[/green] Saved {len(analyses)} analyses to {output_path}")

    return 0


def cmd_twitter_report(args: argparse.Namespace, config: Config) -> int:
    """Generate a markdown report from tweet analyses."""
    import json
    from podstock.twitter.models import TweetAnalysis
    from podstock.twitter.report import generate_twitter_report, save_twitter_report

    source_id = args.source
    if not source_id:
        console.print("[red]✗[/red] Source required. Use --source <handle>")
        return 1

    # Load analyses
    analyses_file = config.twitter_analyses_dir / f"{source_id}-tweet-analyses.json"

    if not analyses_file.exists():
        console.print(f"[yellow]No analyses found for @{source_id}[/yellow]")
        console.print(f"Run 'podstock twitter analyze --source {source_id}' first.")
        return 1

    with open(analyses_file, encoding="utf-8") as f:
        data = json.load(f)

    analyses = [TweetAnalysis(**a) for a in data.get("analyses", [])]

    if not analyses:
        console.print("[yellow]No analyses in file[/yellow]")
        return 0

    console.print(f"\n[bold]Generating report for @{source_id}[/bold]")
    console.print(f"Analyses: {len(analyses)}")

    if args.output:
        # Save to file
        output_dir = config.data_dir / "reports" / "twitter"
        output_path = save_twitter_report(analyses, output_dir, source_id)
        console.print(f"\n[green]✓[/green] Report saved to {output_path}")
    else:
        # Print to console
        report = generate_twitter_report(analyses, source_id)
        console.print()
        console.print(report)

    return 0


# =============================================================================
# YouTube Commands
# =============================================================================


def cmd_youtube(args: argparse.Namespace) -> int:
    """Handle youtube subcommands."""
    config = get_config(args.data_dir)

    if args.youtube_command == "add":
        return cmd_youtube_add(args, config)
    elif args.youtube_command == "list":
        return cmd_youtube_list(args, config)
    elif args.youtube_command == "remove":
        return cmd_youtube_remove(args, config)
    elif args.youtube_command == "collect":
        return cmd_youtube_collect(args, config)
    elif args.youtube_command == "stats":
        return cmd_youtube_stats(args, config)
    else:
        console.print("Usage: podstock youtube <command>")
        console.print("Commands: add, list, remove, collect, stats")
        return 1


def cmd_youtube_add(args: argparse.Namespace, config: Config) -> int:
    """Add a YouTube channel to collect from."""
    from podstock.youtube.channel_manager import YouTubeChannelManager
    from podstock.youtube.exceptions import YouTubeStorageError

    manager = YouTubeChannelManager(config.data_dir)

    try:
        with console.status(f"Fetching channel info: {args.url}"):
            channel = manager.add_channel(
                channel_url=args.url,
                category=getattr(args, "category", None),
                description=getattr(args, "description", None),
                language=getattr(args, "language", "en"),
            )

        console.print(f"[green]✓[/green] Added: {channel.name} (ID: {channel.id})")
        if channel.handle:
            console.print(f"  Handle: {channel.handle}")
        if channel.category:
            console.print(f"  Category: {channel.category}")
        return 0

    except YouTubeStorageError as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_youtube_list(args: argparse.Namespace, config: Config) -> int:
    """List all YouTube channels."""
    from podstock.youtube.channel_manager import YouTubeChannelManager
    from podstock.youtube.state import YouTubeState

    manager = YouTubeChannelManager(config.data_dir)
    state = YouTubeState(config.data_dir)

    channels = manager.list_channels()

    if not channels:
        console.print("[yellow]No YouTube channels configured.[/yellow]")
        console.print("Add one with: podstock youtube add <channel_url>")
        return 0

    table = Table(title="YouTube Channels")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category")
    table.add_column("Videos", justify="right")
    table.add_column("Transcripts", justify="right")
    table.add_column("Active", justify="center")

    for channel in channels:
        channel_state = state.get_channel_state(channel.id)
        videos = channel_state.videos_collected
        transcripts = channel_state.videos_with_transcripts
        active = "✓" if channel.active else "✗"

        table.add_row(
            channel.id,
            channel.name,
            channel.category or "-",
            str(videos),
            str(transcripts),
            active,
        )

    console.print(table)
    return 0


def cmd_youtube_remove(args: argparse.Namespace, config: Config) -> int:
    """Remove a YouTube channel."""
    from podstock.youtube.channel_manager import YouTubeChannelManager

    manager = YouTubeChannelManager(config.data_dir)

    if manager.remove_channel(args.id):
        console.print(f"[green]✓[/green] Removed: {args.id}")
        return 0
    else:
        console.print(f"[red]✗[/red] Channel not found: {args.id}")
        return 1


def cmd_youtube_collect(args: argparse.Namespace, config: Config) -> int:
    """Collect transcripts from YouTube channels."""
    from podstock.youtube.channel_manager import YouTubeChannelManager
    from podstock.youtube.extractor import YouTubeExtractor
    from podstock.youtube.storage import YouTubeStorage
    from podstock.youtube.state import YouTubeState
    from podstock.youtube.exceptions import YouTubeTranscriptNotAvailable, YtDlpError

    manager = YouTubeChannelManager(config.data_dir)
    storage = YouTubeStorage(config.data_dir)
    state = YouTubeState(config.data_dir)

    try:
        extractor = YouTubeExtractor(config.data_dir)
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        return 1

    # Get channels
    channels = manager.list_channels(active_only=not args.all)

    if args.channel:
        channels = [c for c in channels if c.id == args.channel]
        if not channels:
            console.print(f"[red]✗[/red] Channel not found: {args.channel}")
            return 1

    if not channels:
        console.print("[yellow]No channels to collect from.[/yellow]")
        return 0

    max_videos = args.max or 50

    console.print(f"\n[bold]YouTube Transcript Collection[/bold]")
    console.print(f"Channels: {len(channels)}")
    console.print(f"Max videos per channel: {max_videos}")
    console.print()

    total_collected = 0
    total_errors = 0

    for channel in channels:
        channel_url = manager.get_channel_url(channel)
        console.print(f"[cyan]{channel.name}[/cyan] ({channel.id})")

        # Get video list
        with console.status("  Fetching video list..."):
            try:
                videos = extractor.get_channel_videos(
                    channel_url,
                    channel.id,
                    max_videos=max_videos,
                )
            except YtDlpError as e:
                console.print(f"  [red]✗[/red] Failed to list videos: {e}")
                total_errors += 1
                continue

        console.print(f"  Found {len(videos)} videos")

        # Save video metadata
        new_count = storage.save_videos(videos)
        if new_count > 0:
            console.print(f"  [green]+{new_count} new videos[/green]")

        # Collect transcripts
        collected = 0
        skipped = 0

        for video in videos:
            if storage.has_transcript(channel.id, video.id):
                skipped += 1
                continue

            try:
                with console.status(f"  Extracting transcript: {video.title[:40]}..."):
                    transcript = extractor.extract_transcript(
                        video.id,
                        channel_id=channel.id,
                    )

                storage.save_transcript(transcript)
                collected += 1
                console.print(f"  [green]✓[/green] {video.title[:50]}")

            except YouTubeTranscriptNotAvailable:
                console.print(f"  [dim]○ No transcript: {video.title[:50]}[/dim]")
            except YtDlpError as e:
                console.print(f"  [red]✗[/red] Error: {video.title[:40]} - {e}")
                total_errors += 1

        # Update state
        state.mark_collected(
            channel.id,
            videos_collected=len(videos),
            videos_with_transcripts=collected + skipped,
            newest_date=videos[0].published_at if videos else None,
            oldest_date=videos[-1].published_at if videos else None,
        )

        total_collected += collected
        console.print(f"  Collected: {collected}, Skipped: {skipped}")
        console.print()

    console.print(f"[bold]Summary[/bold]")
    console.print(f"  New transcripts: {total_collected}")
    if total_errors > 0:
        console.print(f"  Errors: [red]{total_errors}[/red]")

    return 0 if total_errors == 0 else 1


def cmd_youtube_stats(args: argparse.Namespace, config: Config) -> int:
    """Show YouTube collection statistics."""
    from podstock.youtube.storage import YouTubeStorage
    from podstock.youtube.state import YouTubeState

    storage = YouTubeStorage(config.data_dir)
    state = YouTubeState(config.data_dir)

    stats = storage.get_stats()
    state_summary = state.get_summary()

    console.print("\n[bold]YouTube Collection Statistics[/bold]")
    console.print("=" * 40)
    console.print(f"Channels configured: {state_summary['total_channels']}")
    console.print(f"Complete channels:   {state_summary['complete_channels']}")
    console.print(f"Total videos:        {state_summary['total_videos_collected']}")
    console.print(f"Total transcripts:   {state_summary['total_transcripts']}")

    if state_summary['channels_with_errors'] > 0:
        console.print(f"Channels with errors: [red]{state_summary['channels_with_errors']}[/red]")

    return 0


# =============================================================================
# =============================================================================
# Prices Commands
# =============================================================================


def cmd_prices(args: argparse.Namespace) -> int:
    """Handle prices subcommands."""
    config = get_config(args.data_dir)

    if args.prices_command == "mapping":
        return cmd_prices_mapping(args, config)
    elif args.prices_command == "verify":
        return cmd_prices_verify(args, config)
    elif args.prices_command == "accuracy":
        return cmd_prices_accuracy(args, config)
    elif args.prices_command == "list":
        return cmd_prices_list(args, config)
    elif args.prices_command == "track":
        return cmd_prices_track(args, config)
    elif args.prices_command == "import":
        return cmd_prices_import(args, config)
    else:
        console.print("Usage: podstock prices <command>")
        console.print("Commands: mapping, verify, accuracy, list, track, import")
        return 1


def cmd_prices_mapping(args: argparse.Namespace, config: Config) -> int:
    """Manage ticker mappings."""
    from podstock.prices import TickerMapper

    mapper = TickerMapper(config.data_dir / "prices" / "ticker_mapping.json")

    if args.mapping_command == "add":
        mapper.add_mapping(args.name, args.ticker)
        console.print(f"[green]\u2713[/green] Added: {args.name} -> {args.ticker}")
        return 0

    elif args.mapping_command == "list":
        mappings = mapper.list_all()
        if not mappings:
            console.print("[yellow]No mappings found.[/yellow]")
            return 0

        console.print(f"\n[bold]Ticker Mappings ({len(mappings)} total):[/bold]\n")
        for name, ticker in sorted(mappings.items()):
            console.print(f"  {name}: [cyan]{ticker}[/cyan]")
        return 0

    elif args.mapping_command == "search":
        results = mapper.search(args.query)
        if not results:
            console.print(f"[yellow]No matches for '{args.query}'[/yellow]")
            return 0

        console.print(f"\n[bold]Search results for '{args.query}':[/bold]\n")
        for name, ticker, score in results:
            console.print(f"  [{score}%] {name}: [cyan]{ticker}[/cyan]")
        return 0

    elif args.mapping_command == "stats":
        stats = mapper.get_stats()
        console.print("\n[bold]Mapping Statistics:[/bold]\n")
        console.print(f"  Total mappings: {stats['total_mappings']}")
        console.print(f"  Total aliases: {stats['total_aliases']}")
        console.print(f"  Crypto symbols: {stats['crypto_symbols']}")
        console.print("\n  By market:")
        for market, count in stats['by_market'].items():
            console.print(f"    {market}: {count}")
        return 0

    console.print("Usage: podstock prices mapping <add|list|search|stats>")
    return 1


def cmd_prices_verify(args: argparse.Namespace, config: Config) -> int:
    """Verify recommendations against current prices."""
    from podstock.prices import PriceTracker

    tracker = PriceTracker(config.data_dir)

    if args.all:
        console.print("[bold]Verifying all due recommendations...[/bold]")
        results = tracker.verify_all_due()
        if not results:
            console.print("[yellow]No recommendations due for verification.[/yellow]")
            return 0

        console.print(f"\n[bold]Verified {len(results)} recommendations:[/bold]\n")
        for rec, result in results:
            color = "green" if result.percentage_return > 0 else "red"
            direction = "\u2713" if result.direction_correct else "\u2717"
            console.print(
                f"  [{color}]{direction}[/{color}] {rec.asset_name}: "
                f"[{color}]{result.percentage_return:+.1f}%[/{color}] "
                f"({result.interval_months}m)"
            )
        return 0

    elif args.today:
        console.print("[bold]Checking current prices...[/bold]")
        results = tracker.verify_today(args.id)
        if not results:
            console.print("[yellow]No recommendations to verify.[/yellow]")
            return 0

        console.print(f"\n[bold]Current returns ({len(results)} recommendations):[/bold]\n")
        for rec, result in results:
            color = "green" if result.percentage_return > 0 else "red"
            console.print(
                f"  {rec.asset_name} ({rec.symbol}): "
                f"[{color}]{result.percentage_return:+.1f}%[/{color}] "
                f"from {rec.entry_price.price:.2f} to {result.price_snapshot.price:.2f}"
            )
        return 0

    elif args.id:
        result = tracker.verify_recommendation(args.id, 0)
        if not result:
            console.print(f"[red]\u2717[/red] Could not verify '{args.id}'")
            return 1

        rec = tracker.get_recommendation(args.id)
        if rec:
            color = "green" if result.percentage_return > 0 else "red"
            console.print(f"\n[bold]{rec.asset_name} ({rec.symbol}):[/bold]")
            console.print(f"  Entry: {rec.entry_price.price:.2f} {rec.entry_price.currency}")
            console.print(f"  Current: {result.price_snapshot.price:.2f}")
            console.print(f"  Return: [{color}]{result.percentage_return:+.1f}%[/{color}]")
        return 0

    # Show pending
    pending = tracker.storage.get_pending_verifications()
    console.print(f"\n[bold]Pending verifications: {len(pending)}[/bold]\n")
    for rec in pending[:10]:
        intervals = rec.pending_intervals()
        console.print(f"  {rec.asset_name}: pending at {intervals} months")
    return 0


def cmd_prices_accuracy(args: argparse.Namespace, config: Config) -> int:
    """Show accuracy statistics."""
    from podstock.prices import PriceTracker

    tracker = PriceTracker(config.data_dir)
    stats = tracker.get_accuracy_stats(
        source_name=args.podcast,
        speaker=args.speaker,
        action=args.action,
    )

    console.print("\n[bold]Accuracy Statistics:[/bold]\n")
    console.print(f"  Total recommendations: {stats.total_recommendations}")
    console.print(f"  Verified: {stats.verified_recommendations}")
    console.print(f"  Direction accuracy: {stats.hit_rate}")

    if stats.average_return is not None:
        console.print(f"\n[bold]Returns:[/bold]")
        console.print(f"  Average: {stats.average_return:+.1f}%")
        console.print(f"  Median: {stats.median_return:+.1f}%")
        console.print(f"  Best: {stats.best_return:+.1f}%")
        console.print(f"  Worst: {stats.worst_return:+.1f}%")

    return 0


def cmd_prices_list(args: argparse.Namespace, config: Config) -> int:
    """List tracked recommendations."""
    from podstock.prices import PriceTracker

    tracker = PriceTracker(config.data_dir)
    recs = tracker.get_all_recommendations()

    if not recs:
        console.print("[yellow]No tracked recommendations.[/yellow]")
        return 0

    console.print(f"\n[bold]Tracked Recommendations ({len(recs)} total):[/bold]\n")

    for rec in recs:
        latest = rec.get_latest_verification()
        if latest:
            color = "green" if latest.percentage_return > 0 else "red"
            ret = f"[{color}]{latest.percentage_return:+.1f}%[/{color}]"
        else:
            ret = "[dim]not verified[/dim]"

        console.print(
            f"  {rec.tracking_id}: {rec.asset_name} ({rec.action}) - {ret}"
        )

    return 0


def cmd_prices_track(args: argparse.Namespace, config: Config) -> int:
    """Track a new recommendation manually."""
    from datetime import datetime
    from podstock.prices import PriceTracker, TickerNotFoundError

    tracker = PriceTracker(config.data_dir)

    try:
        rec_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    except ValueError:
        console.print(f"[red]\u2717[/red] Invalid date format. Use YYYY-MM-DD")
        return 1

    try:
        rec = tracker.track_recommendation(
            source_type="podcast",
            source_id=f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            source_name=args.source or "Manual",
            asset_name=args.stock,
            action=args.action,
            recommendation_date=rec_date,
            speaker=args.speaker,
        )

        console.print(f"[green]\u2713[/green] Tracking {rec.asset_name}")
        console.print(f"  Symbol: {rec.symbol}")
        if rec.entry_price:
            console.print(f"  Entry price: {rec.entry_price.price:.2f} {rec.entry_price.currency}")
        console.print(f"  Tracking ID: {rec.tracking_id}")
        return 0

    except TickerNotFoundError as e:
        console.print(f"[red]\u2717[/red] {e}")
        console.print(f"  Add mapping with: podstock prices mapping add '{args.stock}' <TICKER>")
        return 1
    except Exception as e:
        console.print(f"[red]\u2717[/red] Error: {e}")
        return 1


def cmd_prices_import(args: argparse.Namespace, config: Config) -> int:
    """Import recommendations from extracted episode data."""
    from datetime import datetime
    from podstock.prices import PriceTracker

    tracker = PriceTracker(config.data_dir)

    # Parse since date
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]\u2717[/red] Invalid date format. Use YYYY-MM-DD")
            return 1

    # Parse episode IDs
    episode_ids = [args.episode] if args.episode else None

    def ask_for_ticker(stock_name: str, rec_info: dict) -> str | None:
        """Interactive prompt for missing ticker."""
        console.print(f"\n[yellow]\u26a0[/yellow] Saknar ticker för '[bold]{stock_name}[/bold]'")
        console.print(f"  Podcast: {rec_info['podcast']} ({rec_info['date']})")
        if rec_info.get("speaker"):
            console.print(f"  Speaker: {rec_info['speaker']}")
        console.print(f"  Action: {rec_info['action']}")

        response = console.input("  Ange ticker (s=skippa, q=avbryt): ").strip()

        if response.lower() == "s":
            return None
        if response.lower() == "q":
            raise KeyboardInterrupt

        # Save mapping for future use
        ticker = response.upper()
        tracker.mapper.add_mapping(stock_name, ticker)
        console.print(f"  [green]\u2713[/green] Sparade: {stock_name} \u2192 {ticker}")
        return ticker

    # In dry-run mode, don't ask for tickers interactively
    on_missing = None if getattr(args, "dry_run", False) else ask_for_ticker

    try:
        result = tracker.import_from_extractions(
            episode_ids=episode_ids,
            stock_name=args.stock,
            podcast=args.podcast,
            since_date=since_date,
            actions=args.action,
            force=args.force,
            dry_run=getattr(args, "dry_run", False),
            on_missing_ticker=on_missing,
        )

        # Show results
        if getattr(args, "dry_run", False):
            console.print(f"\n[cyan]Dry-run resultat:[/cyan]")
            console.print(f"  Skulle importera: {result.imported}")
            console.print(f"  Skulle skippa: {result.skipped}")
            console.print(f"  Skulle misslyckas: {result.failed}")
        else:
            console.print(f"\n[green]\u2713[/green] Import klar!")
            console.print(f"  Importerade: {result.imported}")
            console.print(f"  Skippade: {result.skipped}")
            console.print(f"  Misslyckade: {result.failed}")

        if result.errors and len(result.errors) <= 10:
            console.print("\n[yellow]Fel:[/yellow]")
            for error in result.errors:
                console.print(f"  - {error}")
        elif result.errors:
            console.print(f"\n[yellow]Fel:[/yellow] {len(result.errors)} (visar första 10)")
            for error in result.errors[:10]:
                console.print(f"  - {error}")

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Avbröt import.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]\u2717[/red] Error: {e}")
        return 1


# =============================================================================
# Crypto Commands
# =============================================================================


def cmd_crypto(args: argparse.Namespace) -> int:
    """Handle crypto subcommands."""
    config = get_config(args.data_dir)

    if args.crypto_command == "prepare-batch":
        return cmd_crypto_prepare_batch(args, config)
    elif args.crypto_command == "search":
        return cmd_crypto_search(args, config)
    elif args.crypto_command == "predictions":
        return cmd_crypto_predictions(args, config)
    elif args.crypto_command == "report":
        return cmd_crypto_report(args, config)
    elif args.crypto_command == "bias":
        return cmd_crypto_bias(args, config)
    elif args.crypto_command == "stats":
        return cmd_crypto_stats(args, config)
    else:
        console.print("Usage: podstock crypto <command>")
        console.print("Commands: prepare-batch, search, predictions, report, bias, stats")
        return 1


def cmd_crypto_prepare_batch(args: argparse.Namespace, config: Config) -> int:
    """Prepare a batch of transcripts for GLM analysis."""
    import json
    from datetime import datetime
    from podstock.youtube.storage import YouTubeStorage
    from podstock.crypto.prompt_templates import (
        CRYPTO_EXTRACTION_SYSTEM_PROMPT,
        CRYPTO_EXTRACTION_USER_PROMPT,
    )

    # Setup directories
    glm_batch_dir = config.data_dir / "crypto" / "glm-batch"
    glm_batch_dir.mkdir(parents=True, exist_ok=True)

    # Find transcripts based on source
    transcripts: list[str] = []
    channel_name = ""

    if args.channel:
        # YouTube channel
        storage = YouTubeStorage(config.data_dir)
        channel_dir = config.data_dir / "youtube" / "transcripts" / args.channel
        if not channel_dir.exists():
            console.print(f"[red]✗[/red] Channel not found: {args.channel}")
            return 1

        txt_files = sorted(channel_dir.glob("*.txt"))
        transcripts = [str(f) for f in txt_files]
        channel_name = args.channel.replace("-", " ").title()

    elif args.source == "youtube" and args.all:
        # All YouTube channels
        youtube_dir = config.data_dir / "youtube" / "transcripts"
        if youtube_dir.exists():
            for channel_dir in youtube_dir.iterdir():
                if channel_dir.is_dir():
                    txt_files = sorted(channel_dir.glob("*.txt"))
                    transcripts.extend(str(f) for f in txt_files)
        channel_name = "All YouTube Channels"

    if not transcripts:
        console.print("[yellow]No transcripts found.[/yellow]")
        return 0

    # Apply max limit
    max_transcripts = getattr(args, "max", None)
    if max_transcripts:
        transcripts = transcripts[:max_transcripts]

    # Read video dates from videos.jsonl
    video_dates: dict[str, str] = {}
    if args.channel:
        videos_jsonl = channel_dir / "videos.jsonl"
        if videos_jsonl.exists():
            for line in videos_jsonl.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    video = json.loads(line)
                    # Extract YYYY-MM-DD from ISO datetime
                    published = video.get("published_at", "")
                    if published:
                        video_dates[video["id"]] = published[:10]

        # Check if dates look wrong (all same or today's date)
        today = datetime.now().strftime("%Y-%m-%d")
        unique_dates = set(video_dates.values())
        if len(unique_dates) == 1 and (list(unique_dates)[0] == today or len(video_dates) > 1):
            console.print("[yellow]⚠ Dates in videos.jsonl look incorrect, fetching from YouTube...[/yellow]")
            import subprocess
            for video_id in video_dates.keys():
                try:
                    result = subprocess.run(
                        ["yt-dlp", "--print", "upload_date", "--skip-download",
                         f"https://www.youtube.com/watch?v={video_id}"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        raw_date = result.stdout.strip()
                        if len(raw_date) == 8:  # YYYYMMDD format
                            video_dates[video_id] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                except Exception as e:
                    console.print(f"[yellow]  Could not fetch date for {video_id}: {e}[/yellow]")

    # Create transcript queue
    queue_file = glm_batch_dir / "transcript-queue.txt"
    queue_file.write_text("\n".join(transcripts), encoding="utf-8")

    # Initialize completion log
    log_file = glm_batch_dir / "completion-log.json"
    log_data = {
        "completed": [],
        "failed": [],
        "total_processed": 0,
        "last_updated": datetime.now().isoformat(),
        "notes": f"Crypto sentiment batch for {channel_name}",
    }
    log_file.write_text(json.dumps(log_data, indent=2), encoding="utf-8")

    # Generate instructions file
    instructions_path = config.data_dir.parent / "docs" / "CRYPTO-ANALYSIS-INSTRUCTIONS.md"
    instructions_content = _generate_crypto_instructions(
        transcripts=transcripts,
        channel_name=channel_name,
        glm_batch_dir=glm_batch_dir,
        video_dates=video_dates,
        channel_id=args.channel if args.channel else None,
    )
    instructions_path.write_text(instructions_content, encoding="utf-8")

    # Display summary
    console.print(f"\n[bold green]GLM Batch Prepared![/bold green]")
    console.print(f"  Channel: {channel_name}")
    console.print(f"  Transcripts queued: {len(transcripts)}")
    console.print(f"\n[bold]Files created:[/bold]")
    console.print(f"  Queue: {queue_file}")
    console.print(f"  Log: {log_file}")
    console.print(f"  Instructions: {instructions_path}")
    console.print(f"\n[cyan]Run Opencode/GLM-4.7 with:[/cyan]")
    console.print(f"  @{instructions_path.relative_to(config.data_dir.parent)}")

    return 0


# Known hosts per YouTube channel for speaker attribution
CHANNEL_HOSTS = {
    "technicalroundup": {
        "hosts": ["Cred", "Duck"],
        "aliases": {
            "Cred": ["CryptoCred", "CC"],
            "Duck": ["Don", "DonAlt", "CryptoDonAlt"],
        },
        "notes": "Cred (CryptoCred) is usually the main host. Duck/Don/DonAlt is the same person.",
    }
}


def _generate_crypto_instructions(
    transcripts: list[str],
    channel_name: str,
    glm_batch_dir,
    video_dates: dict[str, str],
    channel_id: str | None = None,
) -> str:
    """Generate the dynamic instructions markdown file."""
    from datetime import datetime
    from pathlib import Path
    from podstock.crypto.prompt_templates import CRYPTO_EXTRACTION_SYSTEM_PROMPT

    transcript_list = "\n".join(f"{i+1}. `{t}`" for i, t in enumerate(transcripts))

    # Generate date lookup table
    date_table_rows = []
    for t in transcripts:
        video_id = Path(t).stem  # Get filename without extension
        date = video_dates.get(video_id, "⚠️ OKÄNT")
        date_table_rows.append(f"| {video_id} | {date} |")
    date_table = "\n".join(date_table_rows)

    # Generate host info section if channel has known hosts
    host_section = ""
    if channel_id and channel_id in CHANNEL_HOSTS:
        host_info = CHANNEL_HOSTS[channel_id]
        host_rows = []
        for host in host_info["hosts"]:
            aliases = ", ".join(host_info["aliases"].get(host, []))
            host_rows.append(f"| {host} | {aliases} |")
        host_table = "\n".join(host_rows)
        host_section = f"""
---

## 👥 Hosts för denna kanal

| Host | Aliases |
|------|---------|
{host_table}

**OBS:** {host_info.get("notes", "")}

**Tips för speaker-identifiering:**
- Lyssna efter namn som nämns i dialogen (t.ex. "Isn't that right, Don?")
- `>>` markerar talarbyte i transkriptet

**VIKTIGT:** Varje mention MÅSTE ha korrekt `speaker`-fält om det går att identifiera!
"""

    return f'''# Crypto Sentiment Analysis - GLM Batch

## Batch-info
- **Källa:** {channel_name}
- **Transkript:** {len(transcripts)}
- **Genererad:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## ⚠️ KRITISKT: Datum-tabell

**Använd ALLTID denna tabell för att sätta `date`-fältet. GISSA ALDRIG datum!**

| Video ID | Publish Date |
|----------|--------------|
{date_table}
{host_section}
---

## VIKTIGT: Context Window-hantering

**Batch-storlek:** 3-4 transkript per session (MAX 4)
**Efter varje transkript:** Spara JSON + uppdatera completion-log OMEDELBART
**Efter 3-4 transkript:** STOPPA och starta ny session

⚠️ **KRITISKT:** Om du känner att context blir fullt (svar blir långsamma,
saker glöms bort), STOPPA OMEDELBART även om du inte nått 3-4.

---

## Starta en session

### 1. Läs completion-log

```
Läs: {glm_batch_dir}/completion-log.json
```

Kontrollera:
- Hur många är `completed`?
- Vilka transkript är redan klara?

### 2. Hitta nästa transkript

Välj 3-4 transkript från listan nedan som INTE finns i `completed`-arrayen.

### 3. Analysera varje transkript

För varje transkript:
1. Läs hela filen
2. Analysera med prompten nedan
3. Spara JSON till `{glm_batch_dir}/[source_id].json`
4. Uppdatera completion-log.json OMEDELBART

### 4. Efter 3-4 transkript

```
⚠️ BATCH COMPLETE ⚠️

Du har analyserat [antal] transkript i denna session.
STOPPA NU och vänta på ny session.

Progress är sparad i completion-log.json.
Användaren behöver starta en ny konversation för att fortsätta.
```

---

## Transkript att analysera

{transcript_list}

---

## Analysera ett transkript

### Steg 1: Läs transkriptet + HÄMTA DATUM

1. Läs hela innehållet i transkriptfilen
2. ⚠️ **KRITISKT:** Slå upp datum i Datum-tabellen ovan (använd video_id från filnamnet)
3. **GISSA ALDRIG datum** - det är katastrofalt om fel!

### Steg 2: Analysera med följande prompt

{CRYPTO_EXTRACTION_SYSTEM_PROMPT}

### Steg 3: Generera JSON

OUTPUT: Returnera ENDAST valid JSON enligt schemat nedan.

### Steg 4: Spara JSON

Filnamn: `{glm_batch_dir}/[source_id].json`

Där `source_id` = filnamnet utan .txt (t.ex. `K4XV1bEovtY` från `K4XV1bEovtY.txt`)

### Steg 5: Uppdatera completion-log

Efter varje sparat transkript, läs och uppdatera `completion-log.json`:

1. Lägg till filnamnet i `completed`-arrayen
2. Öka `total_processed` med 1
3. Uppdatera `last_updated` med aktuell timestamp

---

## JSON-schema för Crypto Sentiment

```json
{{
  "source_id": "K4XV1bEovtY",
  "source_type": "youtube",
  "channel_or_podcast": "{channel_name}",
  "date": "2025-12-20",
  "speakers": ["Speaker1", "Speaker2"],
  "main_topics": ["Bitcoin ETF", "Alt season"],
  "assets_discussed": ["BTC", "ETH", "SOL"],
  "mentions": [
    {{
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin",
      "sentiment": "very_bullish",
      "confidence": "high",
      "speaker": "Speaker1",
      "timestamp": "05:30",
      "quote": "Exact quote from transcript (max 500 chars)",
      "reasoning": "Why this sentiment was assigned",
      "price_prediction": "Going to 150k",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "mentioned_catalysts": ["ETF inflows", "halving"],
      "risk_factors_mentioned": ["regulation"],
      "recommendation_type": "active_position",
      "invalidation_price": 108000,
      "is_new_position": true
    }}
  ],
  "overall_market_sentiment": "bullish",
  "bitcoin_dominance_view": "increasing",
  "alt_season_prediction": false,
  "summary": "3-5 sentence summary of crypto discussion",
  "key_takeaways": ["Takeaway 1", "Takeaway 2"],
  "transcript_word_count": 5000,
  "has_timestamps": true,
  "model_used": "glm-4.7"
}}
```

### Schema-regler

**sentiment**: `very_bullish | bullish | neutral | bearish | very_bearish`
- Var KONSERVATIV: "could go up" = neutral, INTE bullish
- "interesting" eller "watching" = neutral
- "buying", "accumulating", "moon" = bullish/very_bullish
- "selling", "taking profits" = bearish

**confidence**: `high | medium | low | speculative`
**asset_type**: `coin | token | stablecoin | nft | defi`
**overall_market_sentiment**: `very_bullish | bullish | neutral | bearish | very_bearish`
**bitcoin_dominance_view**: `increasing | decreasing | stable | not_discussed`

**recommendation_type** (KRITISKT för accuracy tracking):
- `active_position`: "I own BTC", "I'm long ETH" (har position)
- `entry_signal`: "I'm buying here", "Good entry" (rekommenderar köp)
- `exit_signal`: "Taking profits", "I sold" (rekommenderar sälj)
- `price_call`: "BTC to 150k" (prediktion utan entry)
- `commentary`: "BTC looks interesting" (ingen action)

**invalidation_price**: Pris som invaliderar tesen (null om ej nämnt)
- "Bullish unless 108k breaks" → 108000

**is_new_position**: `true | false`
- true = NY call/position
- false = upprepar tidigare stance

---

## Completion-log format

```json
{{
  "completed": [
    "K4XV1bEovtY.txt",
    "abc123def.txt"
  ],
  "failed": [],
  "last_updated": "2025-12-26T14:30:00",
  "total_processed": 2
}}
```

---

## Vanliga fel att undvika

1. **Sponsorer som mentions** - Undvik att extrahera sponsormeddelanden som crypto-mentions
2. **Osäker sentiment** - Var konservativ, använd "neutral" vid tveksamhet
3. **JSON-syntaxfel** - Validera att JSON är korrekt innan du sparar
4. **Glömd completion-log** - Uppdatera ALLTID efter varje transkript
5. **Mer än 4 per session** - STOPPA efter 3-4 (context-gräns!)

---

## Checklista per transkript

- [ ] Läst transkriptet
- [ ] Analyserat med prompt
- [ ] Genererat valid JSON
- [ ] Sparat till glm-batch/
- [ ] Uppdaterat completion-log.json
- [ ] (Efter 3-4: STOPPA)
'''


def cmd_crypto_search(args: argparse.Namespace, config: Config) -> int:
    """Search crypto sentiment analyses."""
    from podstock.crypto.aggregator import SentimentAggregator

    aggregator = SentimentAggregator(config.data_dir)

    asset = getattr(args, "asset", None)
    days = getattr(args, "recent", 30)

    if asset:
        aggregated = aggregator.aggregate_by_period(
            asset=asset,
            period="week",
            lookback_days=days,
        )

        if not aggregated:
            console.print(f"[yellow]No data found for {asset}[/yellow]")
            return 0

        table = Table(title=f"${asset.upper()} Sentiment (Last {days} days)")
        table.add_column("Period", style="cyan")
        table.add_column("Sentiment", justify="right")
        table.add_column("Bullish", justify="right", style="green")
        table.add_column("Bearish", justify="right", style="red")
        table.add_column("Mentions", justify="right")

        for agg in aggregated:
            period = agg.period_start.strftime("%Y-%m-%d")
            score = f"{agg.sentiment_score:+.2f}"
            table.add_row(
                period,
                score,
                str(agg.bullish_count),
                str(agg.bearish_count),
                str(agg.total_mentions),
            )

        console.print(table)
    else:
        # Show recent analyses
        analyses = aggregator.load_analyses()
        if not analyses:
            console.print("[yellow]No analyses found.[/yellow]")
            return 0

        console.print(f"\n[bold]Recent Crypto Analyses ({len(analyses)} total)[/bold]\n")

        for analysis in analyses[-10:]:
            console.print(f"  [{analysis.date}] {analysis.channel_or_podcast}")
            console.print(f"    Sentiment: {analysis.overall_market_sentiment.value}")
            console.print(f"    Assets: {', '.join(analysis.assets_discussed[:5])}")
            console.print()

    return 0


def cmd_crypto_predictions(args: argparse.Namespace, config: Config) -> int:
    """Manage crypto predictions."""
    from podstock.crypto.price_tracker import PriceTracker

    tracker = PriceTracker(config.data_dir)

    if getattr(args, "verify", False):
        # Verify due predictions
        with console.status("Verifying predictions..."):
            verified = tracker.verify_due_predictions()

        if verified:
            console.print(f"[green]✓[/green] Verified {len(verified)} predictions")
            for pred in verified:
                result = "[green]✓[/green]" if pred.prediction_correct else "[red]✗[/red]"
                console.print(f"  {result} {pred.asset_symbol}: {pred.price_change_percent:+.1f}%")
        else:
            console.print("[yellow]No predictions due for verification[/yellow]")
    else:
        # Show prediction summary
        summary = tracker.get_prediction_summary()

        console.print("\n[bold]Crypto Predictions[/bold]")
        console.print("=" * 40)
        console.print(f"Total predictions:  {summary['total_predictions']}")
        console.print(f"Pending:            {summary['pending']}")
        console.print(f"Due for verify:     {summary['due_for_verification']}")
        console.print(f"Verified:           {summary['verified']}")

        if summary['accuracy'] is not None:
            console.print(f"Accuracy:           {summary['accuracy']:.1%}")

    return 0


def cmd_crypto_report(args: argparse.Namespace, config: Config) -> int:
    """Generate crypto sentiment report."""
    from podstock.crypto.report import CryptoReportGenerator

    source = args.source
    days = getattr(args, "period", 90)

    generator = CryptoReportGenerator(config.data_dir)

    console.print(f"\n[bold]Generating crypto report for {source}[/bold]")

    report = generator.generate_source_report(
        source_id=source,
        days=days,
        save=True,
    )

    console.print(report)
    return 0


def cmd_crypto_bias(args: argparse.Namespace, config: Config) -> int:
    """Analyze source bias in crypto coverage."""
    from podstock.crypto.aggregator import SentimentAggregator

    source = args.source
    days = getattr(args, "period", 90)

    aggregator = SentimentAggregator(config.data_dir)
    metrics = aggregator.calculate_bias_metrics(source, lookback_days=days)

    console.print(f"\n[bold]Bias Analysis: {source}[/bold]")
    console.print("=" * 40)
    console.print(f"Period: Last {days} days")
    console.print(f"Overall Bias: {metrics.bias_label} ({metrics.overall_bias:+.2f})")
    console.print(f"Consistency:  {metrics.consistency:.1%}")
    console.print(f"BTC Bias:     {metrics.btc_bias:+.2f}")
    console.print(f"Alt Bias:     {metrics.alt_bias:+.2f}")
    console.print(f"Trend:        {metrics.sentiment_trend}")

    if metrics.most_mentioned_assets:
        console.print(f"\nMost mentioned: {', '.join(metrics.most_mentioned_assets)}")

    return 0


def cmd_crypto_stats(args: argparse.Namespace, config: Config) -> int:
    """Show crypto analysis statistics."""
    from podstock.crypto.aggregator import SentimentAggregator
    from podstock.crypto.price_tracker import PriceTracker

    aggregator = SentimentAggregator(config.data_dir)
    tracker = PriceTracker(config.data_dir)

    analyses = aggregator.load_analyses()
    pred_summary = tracker.get_prediction_summary()

    console.print("\n[bold]Crypto Analysis Statistics[/bold]")
    console.print("=" * 40)
    console.print(f"Total analyses:     {len(analyses)}")

    # Count by source type
    by_type: dict = {}
    for a in analyses:
        by_type[a.source_type] = by_type.get(a.source_type, 0) + 1

    for source_type, count in by_type.items():
        console.print(f"  {source_type}: {count}")

    # Predictions
    console.print(f"\nPredictions tracked: {pred_summary['total_predictions']}")
    if pred_summary['accuracy'] is not None:
        console.print(f"Prediction accuracy: {pred_summary['accuracy']:.1%}")

    return 0


# =============================================================================
# Unified Search Commands
# =============================================================================


def cmd_search(args: argparse.Namespace) -> int:
    """Search unified signals across all sources."""
    from datetime import datetime

    from podstock.unified.search import (
        count_signals,
        format_signal_output,
        get_signal_stats,
        search_signals,
    )

    config = get_config(args.data_dir)

    # Handle subcommands
    if hasattr(args, "search_command") and args.search_command == "stats":
        return cmd_search_stats(args)
    elif hasattr(args, "search_command") and args.search_command == "import":
        return cmd_search_import(args)
    elif hasattr(args, "search_command") and args.search_command == "enrich-prices":
        return cmd_search_enrich_prices(args)
    elif hasattr(args, "search_command") and args.search_command == "report":
        return cmd_search_report(args)

    # Parse dates
    from_date = None
    to_date = None

    if hasattr(args, "start") and args.start:
        try:
            from_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError:
            console.print(f"[red]Invalid date format: {args.start}[/red]")
            return 1

    if hasattr(args, "end") and args.end:
        try:
            to_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            console.print(f"[red]Invalid date format: {args.end}[/red]")
            return 1

    # Get results
    signals = search_signals(
        asset=args.asset if hasattr(args, "asset") else None,
        speaker=args.speaker if hasattr(args, "speaker") else None,
        signal_type=args.signal if hasattr(args, "signal") else None,
        source_type=args.source if hasattr(args, "source") else None,
        from_date=from_date,
        to_date=to_date,
        limit=args.limit if hasattr(args, "limit") else 50,
    )

    if not signals:
        console.print("[yellow]No signals found matching criteria.[/yellow]")
        return 0

    # Count total
    total = count_signals(
        asset=args.asset if hasattr(args, "asset") else None,
        speaker=args.speaker if hasattr(args, "speaker") else None,
        signal_type=args.signal if hasattr(args, "signal") else None,
        source_type=args.source if hasattr(args, "source") else None,
        from_date=from_date,
        to_date=to_date,
    )

    console.print(f"Found {total} signals (showing {len(signals)}):\n")

    # Display results
    verbose = args.verbose if hasattr(args, "verbose") else False

    for signal in signals:
        output = format_signal_output(signal, verbose=verbose)
        console.print(output)

    return 0


def cmd_search_stats(args: argparse.Namespace) -> int:
    """Show signal statistics."""
    from datetime import datetime

    from podstock.unified.search import get_signal_stats

    # Parse dates
    from_date = None
    to_date = None

    if hasattr(args, "start") and args.start:
        try:
            from_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError:
            pass

    if hasattr(args, "end") and args.end:
        try:
            to_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            pass

    stats = get_signal_stats(from_date=from_date, to_date=to_date)

    console.print(f"\n[bold]Total signals:[/bold] {stats['total']}")

    console.print("\n[bold]By source:[/bold]")
    for source, count in stats["by_source"].items():
        console.print(f"  {source}: {count}")

    console.print("\n[bold]By signal type:[/bold]")
    for signal, count in stats["by_signal"].items():
        emoji = {"bullish": "+", "bearish": "-", "neutral": "~"}.get(signal, "?")
        console.print(f"  [{emoji}] {signal}: {count}")

    console.print("\n[bold]Top assets:[/bold]")
    for asset in stats["top_assets"][:10]:
        console.print(f"  {asset['symbol']}: {asset['count']}")

    console.print("\n[bold]Top speakers:[/bold]")
    for speaker in stats["top_speakers"][:10]:
        console.print(f"  {speaker['name']}: {speaker['count']}")

    return 0


def cmd_search_import(args: argparse.Namespace) -> int:
    """Import signals from all sources."""
    from podstock.unified.importers import (
        import_podcast_analyses,
        import_twitter_analyses,
        import_youtube_analyses,
    )

    source = args.source if hasattr(args, "source") else "all"
    dry_run = args.dry_run if hasattr(args, "dry_run") else False

    total_stats = {
        "files_processed": 0,
        "signals_created": 0,
        "signals_skipped": 0,
        "errors": 0,
    }

    if source in ("all", "podcast"):
        console.print("[bold]Importing podcast analyses...[/bold]")
        stats = import_podcast_analyses(dry_run=dry_run)
        console.print(f"  Processed: {stats.get('files_processed', 0)} files")
        console.print(f"  Created: {stats.get('signals_created', 0)} signals")
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    if source in ("all", "youtube"):
        console.print("\n[bold]Importing YouTube analyses...[/bold]")
        stats = import_youtube_analyses(dry_run=dry_run)
        console.print(f"  Processed: {stats.get('files_processed', 0)} files")
        console.print(f"  Created: {stats.get('signals_created', 0)} signals")
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    if source in ("all", "twitter"):
        console.print("\n[bold]Importing Twitter analyses...[/bold]")
        stats = import_twitter_analyses(dry_run=dry_run)
        console.print(f"  Processed: {stats.get('files_processed', 0)} files")
        console.print(f"  Created: {stats.get('signals_created', 0)} signals")
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    console.print(f"\n[green]Total:[/green]")
    console.print(f"  Files processed: {total_stats['files_processed']}")
    console.print(f"  Signals created: {total_stats['signals_created']}")
    console.print(f"  Signals skipped: {total_stats['signals_skipped']}")
    if total_stats["errors"]:
        console.print(f"  [red]Errors: {total_stats['errors']}[/red]")

    return 0


def cmd_search_enrich_prices(args: argparse.Namespace) -> int:
    """Enrich signals with entry prices from Yahoo Finance."""
    from podstock.unified.enrichment import enrich_signals_with_prices, get_enrichment_coverage

    since = args.since if hasattr(args, "since") else None
    limit = args.limit if hasattr(args, "limit") else None
    dry_run = args.dry_run if hasattr(args, "dry_run") else False

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/yellow]\n")

    # Show current coverage first
    console.print("[bold]Current price coverage:[/bold]")
    coverage = get_enrichment_coverage(since=since)
    console.print(f"  Total signals: {coverage['total_signals']}")
    console.print(f"  Enriched: {coverage['enriched_signals']} ({coverage['coverage_percent']}%)")

    console.print("\n[bold]By asset type:[/bold]")
    for asset_type, type_stats in coverage.get("by_asset_type", {}).items():
        pct = round(100 * type_stats["enriched"] / type_stats["total"], 1) if type_stats["total"] > 0 else 0
        console.print(f"  {asset_type}: {type_stats['enriched']}/{type_stats['total']} ({pct}%)")

    console.print("\n[bold]Enriching signals with prices...[/bold]")
    stats = enrich_signals_with_prices(
        since=since,
        limit=limit,
        dry_run=dry_run,
    )

    console.print(f"\n[green]Results:[/green]")
    console.print(f"  Signals processed: {stats['total_signals']}")
    console.print(f"  Enriched: {stats['enriched']}")
    console.print(f"  No ticker mapping: {stats['no_ticker']}")
    console.print(f"  No price data: {stats['no_price']}")
    if stats["errors"]:
        console.print(f"  [red]Errors: {stats['errors']}[/red]")

    return 0


def cmd_search_report(args: argparse.Namespace) -> int:
    """Generate monthly or yearly report with performance data."""
    from pathlib import Path

    from podstock.unified.report import (
        format_full_report,
        format_yearly_report,
        generate_monthly_report,
        generate_yearly_report,
        save_report,
    )

    # Check for year or month
    year_str = args.year if hasattr(args, "year") else None
    month_str = args.month if hasattr(args, "month") else None
    output_file = args.output if hasattr(args, "output") else None
    no_prices = args.no_prices if hasattr(args, "no_prices") else False
    limit = args.limit if hasattr(args, "limit") else 500

    # Yearly report
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            console.print(f"[red]Invalid year format: {year_str}. Use YYYY.[/red]")
            return 1

        # Use higher limit for yearly reports
        if limit == 500:
            limit = 5000

        console.print(f"\nGenerating yearly report for {year}...")

        if not no_prices:
            console.print("[dim]Fetching current prices from Yahoo Finance (this may take a while)...[/dim]\n")

        report = generate_yearly_report(
            year=year,
            fetch_current_prices=not no_prices,
            limit=limit,
        )

        output = format_yearly_report(report)

    # Monthly report
    else:
        if not month_str:
            # Default to current month
            from datetime import date

            today = date.today()
            year = today.year
            month = today.month
        else:
            try:
                parts = month_str.split("-")
                year = int(parts[0])
                month = int(parts[1])
            except (ValueError, IndexError):
                console.print(f"[red]Invalid month format: {month_str}. Use YYYY-MM.[/red]")
                return 1

        console.print(f"\nGenerating report for {year}-{month:02d}...")

        if not no_prices:
            console.print("[dim]Fetching current prices from Yahoo Finance...[/dim]\n")

        report = generate_monthly_report(
            year=year,
            month=month,
            fetch_current_prices=not no_prices,
            limit=limit,
        )

        output = format_full_report(report)

    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        save_report(output, output_path)
        console.print(f"[green]Report saved to: {output_path}[/green]\n")

    console.print(output)

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================


def cmd_guest_summary(args: argparse.Namespace) -> int:
    """Generate guest summary report."""
    from podstock.summary import SummaryGenerator

    config = get_config(args.data_dir)
    extracted_path = config.data_dir / "extracted"

    if not (extracted_path / "recommendations.json").exists():
        console.print("[red]✗[/red] No recommendations found. Run 'podstock extract rebuild-index' first.")
        return 1

    generator = SummaryGenerator(extracted_path)
    output_dir = config.data_dir / "reports" / "summaries"

    output_path = generator.save(
        output_dir=output_dir,
        filename=args.output if hasattr(args, "output") else None,
        podcast_filter=args.podcast if hasattr(args, "podcast") else None,
    )

    console.print(f"[green]✓[/green] Rapport sparad: {output_path}")
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="podstock",
        description="Track stock recommendations from Swedish podcasts",
    )

    parser.add_argument(
        "--data-dir",
        help="Override data directory",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Podcast commands
    podcast_parser = subparsers.add_parser("podcast", help="Manage podcasts")
    podcast_sub = podcast_parser.add_subparsers(dest="podcast_command")

    # podcast list
    podcast_sub.add_parser("list", help="List all podcasts")

    # podcast add
    add_parser = podcast_sub.add_parser("add", help="Add a podcast")
    add_parser.add_argument("name", help="Podcast name")
    add_parser.add_argument("url", help="RSS feed URL")
    add_parser.add_argument("--skip-validation", action="store_true", help="Skip RSS validation")

    # podcast remove
    remove_parser = podcast_sub.add_parser("remove", help="Remove a podcast")
    remove_parser.add_argument("id", help="Podcast ID")

    # podcast info
    info_parser = podcast_sub.add_parser("info", help="Show podcast info")
    info_parser.add_argument("id", help="Podcast ID")

    # List command (podcast lists for grouping)
    list_parser = subparsers.add_parser("list", help="Manage podcast lists")
    list_sub = list_parser.add_subparsers(dest="list_command")

    # list show
    list_show = list_sub.add_parser("show", help="Show all lists or a specific list")
    list_show.add_argument("list_id", nargs="?", help="Specific list ID to show")

    # list create
    list_create = list_sub.add_parser("create", help="Create a new list")
    list_create.add_argument("name", help="List name")
    list_create.add_argument(
        "--type", "-t",
        choices=["broad", "niche", "custom"],
        default="custom",
        help="List type (default: custom)"
    )
    list_create.add_argument("--description", "-d", help="List description")

    # list add
    list_add = list_sub.add_parser("add", help="Add a podcast to a list")
    list_add.add_argument("list_id", help="List ID")
    list_add.add_argument("podcast_id", help="Podcast ID to add")

    # list remove
    list_remove = list_sub.add_parser("remove", help="Remove a podcast from a list")
    list_remove.add_argument("list_id", help="List ID")
    list_remove.add_argument("podcast_id", help="Podcast ID to remove")

    # list delete
    list_delete = list_sub.add_parser("delete", help="Delete a list")
    list_delete.add_argument("list_id", help="List ID to delete")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync new podcast episodes")
    sync_parser.add_argument("--podcast", "-p", help="Specific podcast ID to sync")
    sync_parser.add_argument("--list", "-l", help="Sync all podcasts in a list")
    sync_parser.add_argument("--latest", "-n", type=int, default=1, help="Number of latest episodes per podcast (default: 1)")
    sync_parser.add_argument("--force", "-f", action="store_true", help="Force re-sync even if already processed")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without processing")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Generate summary reports")
    summary_sub = summary_parser.add_subparsers(dest="summary_command")

    # summary prepare
    summary_prepare = summary_sub.add_parser("prepare", help="Prepare summary data for LLM")
    summary_prepare.add_argument("--from", dest="start", required=True, help="Start date (YYYY-MM-DD)")
    summary_prepare.add_argument("--to", dest="end", required=True, help="End date (YYYY-MM-DD)")
    summary_prepare.add_argument("--type", "-t", choices=["broad", "detailed"], default="broad", help="Report type")
    summary_prepare.add_argument("--list", "-l", help="Override default list")
    summary_prepare.add_argument("--opencode", action="store_true", help="Export for Opencode/GLM-4.7 instead of Claude Code")

    # summary info
    summary_info = summary_sub.add_parser("info", help="Show available data for period")
    summary_info.add_argument("--from", dest="start", required=True, help="Start date (YYYY-MM-DD)")
    summary_info.add_argument("--to", dest="end", required=True, help="End date (YYYY-MM-DD)")
    summary_info.add_argument("--list", "-l", default="broad", help="List ID to check")

    # summary save
    summary_save = summary_sub.add_parser("save", help="Save a generated report")
    summary_save.add_argument("--input", "-i", help="Input file (reads from stdin if not provided)")
    summary_save.add_argument("--output", "-o", help="Output file path")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download episodes")
    download_parser.add_argument("--podcast", "-p", help="Specific podcast ID")
    download_parser.add_argument("--latest", "-n", type=int, help="Number of latest episodes")
    download_parser.add_argument("--force", "-f", action="store_true", help="Force re-download")

    # Transcribe command
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe episodes")
    transcribe_parser.add_argument("--podcast", "-p", help="Specific podcast ID")
    transcribe_parser.add_argument("--episode", "-e", help="Specific episode ID")
    transcribe_parser.add_argument("--model", "-m", help="Whisper model to use")
    transcribe_parser.add_argument("--force", "-f", action="store_true", help="Force re-transcribe")
    transcribe_parser.add_argument(
        "--source", "-s",
        choices=["whisper", "apple"],
        default="whisper",
        help="Transcript source (default: whisper)"
    )
    transcribe_parser.add_argument(
        "--list-apple",
        action="store_true",
        help="List available Apple Podcast transcripts"
    )
    transcribe_parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Exclude timestamps from Apple transcripts"
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze transcripts")
    analyze_parser.add_argument("episode", help="Episode ID to analyze")
    analyze_parser.add_argument("--input", "-i", help="Path to Claude response file")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("--output", "-o", help="Output filename")
    report_parser.add_argument("--podcast", "-p", help="Filter by podcast")

    # Status command
    subparsers.add_parser("status", help="Show processing status")

    # Extract command (AI-based recommendation extraction)
    extract_parser = subparsers.add_parser("extract", help="Extract recommendations from transcripts")
    extract_sub = extract_parser.add_subparsers(dest="extract_command")

    # extract process
    extract_process = extract_sub.add_parser("process", help="Process transcripts")
    extract_process.add_argument("--all", action="store_true", help="Process all pending")
    extract_process.add_argument("--file", type=str, help="Process specific file")
    extract_process.add_argument("--max", type=int, help="Max files to process")
    extract_process.add_argument("--delay", type=float, default=2.0, help="Delay between API calls")
    extract_process.add_argument("--podcast", type=str, help="Filter by podcast name")
    extract_process.add_argument("--model", type=str, default="claude-sonnet-4-20250514", help="LLM model: 'claude-sonnet-4-20250514' or 'ollama:llama3.3'")

    # extract search
    extract_search = extract_sub.add_parser("search", help="Search recommendations")
    extract_search.add_argument("--stock", type=str, help="Search by stock name")
    extract_search.add_argument("--recent", type=int, help="Recent N days")
    extract_search.add_argument("--speaker", type=str, help="Search by speaker")
    extract_search.add_argument("--podcast", type=str, help="Search by podcast")
    extract_search.add_argument("--action", choices=["buy", "sell", "hold", "watch", "avoid"])
    extract_search.add_argument("--top", type=int, help="Top N stocks by mentions")

    # extract stats
    extract_sub.add_parser("stats", help="Show extraction statistics")

    # extract rebuild-index
    extract_sub.add_parser("rebuild-index", help="Rebuild search index")

    # extract list
    extract_list = extract_sub.add_parser("list", help="List transcript files")
    extract_list.add_argument("--pending", action="store_true", help="Show only pending")

    # Guest summary command
    summary_parser = subparsers.add_parser("guest-summary", help="Generate guest summary report")
    summary_parser.add_argument("--podcast", help="Filter by podcast name")
    summary_parser.add_argument("--output", help="Custom output filename")
    summary_parser.add_argument("--days", type=int, help="Only include last N days")

    # Twitter command group
    twitter_parser = subparsers.add_parser("twitter", help="Manage Twitter/X data")
    twitter_sub = twitter_parser.add_subparsers(dest="twitter_command")

    # twitter add
    twitter_add = twitter_sub.add_parser("add", help="Add a Twitter source")
    twitter_add.add_argument("handle", help="Twitter handle (with or without @)")
    twitter_add.add_argument("--category", help="Category (analyst, fund_manager, podcast, etc.)")
    twitter_add.add_argument("--description", help="Description/notes")

    # twitter list
    twitter_sub.add_parser("list", help="List Twitter sources")

    # twitter remove
    twitter_remove = twitter_sub.add_parser("remove", help="Remove a Twitter source")
    twitter_remove.add_argument("id", help="Source ID to remove")

    # twitter collect
    twitter_collect = twitter_sub.add_parser("collect", help="Collect tweets from sources")
    twitter_collect.add_argument("--source", help="Specific source ID (username)")
    twitter_collect.add_argument("--max", type=int, default=10000, help="Max tweets per source")
    twitter_collect.add_argument("--full", action="store_true", help="Full collection (not incremental)")
    twitter_collect.add_argument("--all", action="store_true", help="Include inactive sources")
    twitter_collect.add_argument("--since", help="Start date (YYYY-MM-DD) - uses cost-effective Advanced Search")
    twitter_collect.add_argument("--until", help="End date (YYYY-MM-DD) - uses cost-effective Advanced Search")
    twitter_collect.add_argument("--include-replies", action="store_true", default=True, help="Include replies (default: True)")

    # twitter info
    twitter_info = twitter_sub.add_parser("info", help="Show detailed info for a source")
    twitter_info.add_argument("source", help="Twitter handle or source ID")

    # twitter coverage
    twitter_coverage = twitter_sub.add_parser("coverage", help="Analyze tweet coverage")
    twitter_coverage.add_argument("source", help="Twitter handle")
    twitter_coverage.add_argument("--json", action="store_true", help="Output as JSON")

    # twitter url
    twitter_url = twitter_sub.add_parser("url", help="Generate search URL")
    twitter_url.add_argument("source", help="Twitter handle")
    twitter_url.add_argument("--since", required=True, help="Start date (YYYY-MM-DD)")
    twitter_url.add_argument("--until", required=True, help="End date (YYYY-MM-DD)")

    # twitter search
    twitter_search = twitter_sub.add_parser("search", help="Search tweets")
    twitter_search.add_argument("--ticker", help="Search by ticker ($TSLA)")
    twitter_search.add_argument("--user", help="Search by source ID")
    twitter_search.add_argument("--recent", type=int, help="Last N days")
    twitter_search.add_argument("--top-tickers", type=int, help="Top N tickers")
    twitter_search.add_argument("--top-users", type=int, help="Top N users")
    twitter_search.add_argument("--with-tickers", action="store_true", help="Only tweets with tickers")
    twitter_search.add_argument("--limit", type=int, help="Max results to show")

    # twitter stats
    twitter_sub.add_parser("stats", help="Show Twitter statistics")

    # twitter rebuild-index
    twitter_sub.add_parser("rebuild-index", help="Rebuild search indexes")

    # twitter analyze
    twitter_analyze = twitter_sub.add_parser("analyze", help="Analyze tweets with LLM")
    twitter_analyze.add_argument("--source", required=True, help="Source ID to analyze")
    twitter_analyze.add_argument("--max", type=int, help="Max tweets to analyze")
    twitter_analyze.add_argument("--model", default="claude-sonnet-4-20250514", help="LLM model to use")

    # twitter report
    twitter_report = twitter_sub.add_parser("report", help="Generate analysis report")
    twitter_report.add_argument("--source", required=True, help="Source ID for report")
    twitter_report.add_argument("--output", "-o", action="store_true", help="Save to file instead of printing")

    # YouTube command group
    youtube_parser = subparsers.add_parser("youtube", help="Manage YouTube channels and transcripts")
    youtube_sub = youtube_parser.add_subparsers(dest="youtube_command")

    # youtube add
    youtube_add = youtube_sub.add_parser("add", help="Add a YouTube channel")
    youtube_add.add_argument("url", help="YouTube channel URL")
    youtube_add.add_argument("--category", help="Category (crypto, finance, tech, etc.)")
    youtube_add.add_argument("--description", help="Description/notes")
    youtube_add.add_argument("--language", default="en", help="Primary language (default: en)")

    # youtube list
    youtube_sub.add_parser("list", help="List YouTube channels")

    # youtube remove
    youtube_remove = youtube_sub.add_parser("remove", help="Remove a YouTube channel")
    youtube_remove.add_argument("id", help="Channel ID to remove")

    # youtube collect
    youtube_collect = youtube_sub.add_parser("collect", help="Collect transcripts from channels")
    youtube_collect.add_argument("--channel", help="Specific channel ID")
    youtube_collect.add_argument("--max", type=int, help="Max videos per channel")
    youtube_collect.add_argument("--all", action="store_true", help="Include inactive channels")

    # youtube stats
    youtube_sub.add_parser("stats", help="Show YouTube collection statistics")

    # Crypto command group
    crypto_parser = subparsers.add_parser("crypto", help="Crypto sentiment analysis")
    crypto_sub = crypto_parser.add_subparsers(dest="crypto_command")

    # crypto prepare-batch
    crypto_prepare = crypto_sub.add_parser("prepare-batch", help="Prepare batch for GLM analysis")
    crypto_prepare.add_argument("--channel", help="YouTube channel ID to analyze")
    crypto_prepare.add_argument("--source", default="youtube", choices=["youtube"], help="Source type")
    crypto_prepare.add_argument("--all", action="store_true", help="Include all channels")
    crypto_prepare.add_argument("--max", type=int, help="Max transcripts to include")

    # crypto search
    crypto_search = crypto_sub.add_parser("search", help="Search crypto sentiment data")
    crypto_search.add_argument("--asset", help="Filter by asset symbol (BTC, ETH, etc.)")
    crypto_search.add_argument("--recent", type=int, default=30, help="Last N days")

    # crypto predictions
    crypto_predictions = crypto_sub.add_parser("predictions", help="Manage price predictions")
    crypto_predictions.add_argument("--verify", action="store_true", help="Verify due predictions")

    # crypto report
    crypto_report = crypto_sub.add_parser("report", help="Generate sentiment report")
    crypto_report.add_argument("--source", required=True, help="Source ID for report")
    crypto_report.add_argument("--period", type=int, default=90, help="Days to analyze")

    # crypto bias
    crypto_bias = crypto_sub.add_parser("bias", help="Analyze source bias")
    crypto_bias.add_argument("--source", required=True, help="Source ID to analyze")
    crypto_bias.add_argument("--period", type=int, default=90, help="Days to analyze")

    # crypto stats
    crypto_sub.add_parser("stats", help="Show crypto analysis statistics")

    # Prices command group
    prices_parser = subparsers.add_parser("prices", help="Price tracking and verification")
    prices_sub = prices_parser.add_subparsers(dest="prices_command")

    # prices mapping
    prices_mapping = prices_sub.add_parser("mapping", help="Manage ticker mappings")
    mapping_sub = prices_mapping.add_subparsers(dest="mapping_command")

    mapping_add = mapping_sub.add_parser("add", help="Add a mapping")
    mapping_add.add_argument("name", help="Company name")
    mapping_add.add_argument("ticker", help="Stock ticker (e.g., EVO.ST)")

    mapping_sub.add_parser("list", help="List all mappings")

    mapping_search = mapping_sub.add_parser("search", help="Search mappings")
    mapping_search.add_argument("query", help="Search query")

    mapping_sub.add_parser("stats", help="Show mapping statistics")

    # prices verify
    prices_verify = prices_sub.add_parser("verify", help="Verify recommendations")
    prices_verify.add_argument("--all", action="store_true", help="Verify all due")
    prices_verify.add_argument("--today", action="store_true", help="Check current prices")
    prices_verify.add_argument("--id", help="Verify specific recommendation")

    # prices accuracy
    prices_accuracy = prices_sub.add_parser("accuracy", help="Show accuracy statistics")
    prices_accuracy.add_argument("--podcast", help="Filter by podcast")
    prices_accuracy.add_argument("--speaker", help="Filter by speaker")
    prices_accuracy.add_argument("--action", help="Filter by action type")

    # prices list
    prices_sub.add_parser("list", help="List tracked recommendations")

    # prices track
    prices_track = prices_sub.add_parser("track", help="Track a new recommendation")
    prices_track.add_argument("stock", help="Stock/asset name")
    prices_track.add_argument("action", choices=["buy", "sell", "hold", "watch", "avoid"])
    prices_track.add_argument("--date", help="Recommendation date (YYYY-MM-DD)")
    prices_track.add_argument("--source", help="Source name")
    prices_track.add_argument("--speaker", help="Speaker name")

    # prices import
    prices_import = prices_sub.add_parser("import", help="Import recommendations from extractions")
    prices_import.add_argument("--episode", help="Filter by episode ID")
    prices_import.add_argument("--stock", help="Filter by stock name")
    prices_import.add_argument("--podcast", help="Filter by podcast name")
    prices_import.add_argument("--since", help="Import since date (YYYY-MM-DD)")
    prices_import.add_argument(
        "--action",
        nargs="+",
        choices=["buy", "sell", "hold", "watch", "avoid"],
        help="Filter by action types",
    )
    prices_import.add_argument("--force", action="store_true", help="Re-import existing")
    prices_import.add_argument("--dry-run", action="store_true", help="Preview without importing")

    # Unified Search command
    search_parser = subparsers.add_parser("search", help="Search unified signals across all sources")
    search_sub = search_parser.add_subparsers(dest="search_command")

    # search (default - query)
    search_parser.add_argument("--asset", "-a", help="Filter by asset symbol (e.g., BTC, VOLVO)")
    search_parser.add_argument("--speaker", "-s", help="Filter by speaker name")
    search_parser.add_argument("--signal", choices=["bullish", "bearish", "neutral"], help="Filter by signal type")
    search_parser.add_argument("--source", choices=["podcast", "youtube", "twitter"], help="Filter by source type")
    search_parser.add_argument("--from", dest="start", help="Start date (YYYY-MM-DD)")
    search_parser.add_argument("--to", dest="end", help="End date (YYYY-MM-DD)")
    search_parser.add_argument("--limit", "-n", type=int, default=50, help="Max results (default: 50)")

    # search stats
    search_stats = search_sub.add_parser("stats", help="Show signal statistics")
    search_stats.add_argument("--from", dest="start", help="Start date (YYYY-MM-DD)")
    search_stats.add_argument("--to", dest="end", help="End date (YYYY-MM-DD)")

    # search import
    search_import = search_sub.add_parser("import", help="Import signals from all sources")
    search_import.add_argument("--source", choices=["podcast", "youtube", "twitter", "all"], default="all", help="Source to import")
    search_import.add_argument("--dry-run", action="store_true", help="Preview without importing")

    # search enrich-prices
    search_enrich = search_sub.add_parser("enrich-prices", help="Enrich signals with entry prices from Yahoo Finance")
    search_enrich.add_argument("--since", help="Only enrich signals from this date (YYYY-MM-DD)")
    search_enrich.add_argument("--limit", type=int, help="Maximum number of signals to process")
    search_enrich.add_argument("--dry-run", action="store_true", help="Preview without updating database")

    # search report
    search_report = search_sub.add_parser("report", help="Generate monthly/yearly report with performance data")
    search_report.add_argument("--month", "-m", help="Month to report (YYYY-MM)")
    search_report.add_argument("--year", "-y", help="Year to report (YYYY) - generates full year report")
    search_report.add_argument("--no-prices", action="store_true", help="Skip fetching current prices")
    search_report.add_argument("--output", "-o", help="Save report to file (e.g., report.txt)")
    search_report.add_argument("--limit", type=int, default=500, help="Maximum signals to include (default: 500, use higher for yearly)")

    # Database command group
    from podstock.db.cli import add_db_parser
    add_db_parser(subparsers)

    # Dashboard command group
    from podstock.dashboard.cli import add_dashboard_parser
    add_dashboard_parser(subparsers)

    # Filings command group
    from podstock.filings.cli import setup_filings_parser
    setup_filings_parser(subparsers)

    # Earnings command group
    from podstock.earnings.cli import setup_earnings_parser
    setup_earnings_parser(subparsers)

    # News command group
    from podstock.news.cli import setup_news_parser
    setup_news_parser(subparsers)

    return parser


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "podcast":
            if args.podcast_command == "list":
                sys.exit(cmd_podcast_list(args))
            elif args.podcast_command == "add":
                sys.exit(cmd_podcast_add(args))
            elif args.podcast_command == "remove":
                sys.exit(cmd_podcast_remove(args))
            elif args.podcast_command == "info":
                sys.exit(cmd_podcast_info(args))
            else:
                parser.parse_args(["podcast", "-h"])

        elif args.command == "list":
            sys.exit(cmd_list(args))

        elif args.command == "sync":
            sys.exit(cmd_sync(args))

        elif args.command == "summary":
            sys.exit(cmd_summary(args))

        elif args.command == "download":
            sys.exit(cmd_download(args))

        elif args.command == "transcribe":
            sys.exit(cmd_transcribe(args))

        elif args.command == "analyze":
            sys.exit(cmd_analyze(args))

        elif args.command == "report":
            sys.exit(cmd_report(args))

        elif args.command == "status":
            sys.exit(cmd_status(args))

        elif args.command == "extract":
            sys.exit(cmd_extract(args))

        elif args.command == "guest-summary":
            sys.exit(cmd_guest_summary(args))

        elif args.command == "twitter":
            sys.exit(cmd_twitter(args))

        elif args.command == "youtube":
            sys.exit(cmd_youtube(args))

        elif args.command == "crypto":
            sys.exit(cmd_crypto(args))

        elif args.command == "prices":
            sys.exit(cmd_prices(args))

        elif args.command == "search":
            sys.exit(cmd_search(args))

        elif args.command == "db":
            from podstock.db.cli import cmd_db
            sys.exit(cmd_db(args))

        elif args.command == "dashboard":
            from podstock.dashboard.cli import cmd_dashboard
            sys.exit(cmd_dashboard(args))

        elif args.command == "filings":
            from podstock.filings.cli import cmd_filings
            config = get_config(args.data_dir)
            sys.exit(cmd_filings(args, config))

        elif args.command == "earnings":
            from podstock.earnings.cli import cmd_earnings
            config = get_config(args.data_dir)
            sys.exit(cmd_earnings(args, config))

        elif args.command == "news":
            from podstock.news.cli import cmd_news
            config = get_config(args.data_dir)
            sys.exit(cmd_news(args, config))

        else:
            parser.print_help()
            sys.exit(0)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
