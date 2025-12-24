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
# Main Entry Point
# =============================================================================


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
