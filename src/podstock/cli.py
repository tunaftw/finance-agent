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

    sources_file = config.data_dir / "twitter_sources.json"

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

    sources_file = config.data_dir / "twitter_sources.json"
    state_file = config.data_dir / "twitter_state.json"

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

    sources_file = config.data_dir / "twitter_sources.json"

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
    """
    from podstock.twitter.manager import load_twitter_sources
    from podstock.twitter.state import TwitterState

    sources_file = config.data_dir / "twitter_sources.json"
    state_file = config.data_dir / "twitter_state.json"

    sources = load_twitter_sources(sources_file)
    state = TwitterState(state_file)

    if not sources:
        console.print("[yellow]No Twitter sources configured.[/yellow]")
        return 0

    # Filter if specific source requested
    if args.source:
        sources = [s for s in sources if s.id == args.source]
        if not sources:
            console.print(f"[red]✗[/red] Source not found: {args.source}")
            return 1

    # Filter to active only by default
    if not args.all:
        sources = [s for s in sources if s.active]

    max_tweets = args.max or 500
    incremental = not args.full

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

    console.print(f"\n[bold]Twitter API Collection[/bold]")
    console.print(f"Sources: {len(sources)}")
    console.print(f"Mode: {'Full' if args.full else 'Incremental'}")
    console.print(f"Max tweets per source: {max_tweets}")
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
    if errors > 0:
        console.print(f"  Errors: [red]{errors}[/red]")

    return 0 if errors == 0 else 1


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

    sources_file = config.data_dir / "twitter_sources.json"
    state_file = config.data_dir / "twitter_state.json"

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
        output_dir = config.data_dir / "twitter" / "analyses"
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
    analyses_file = config.data_dir / "twitter" / "analyses" / f"{source_id}-tweet-analyses.json"

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
    twitter_collect = twitter_sub.add_parser("collect", help="Show collection plan")
    twitter_collect.add_argument("--source", help="Specific source ID")
    twitter_collect.add_argument("--max", type=int, help="Max tweets per source")
    twitter_collect.add_argument("--full", action="store_true", help="Full collection (not incremental)")
    twitter_collect.add_argument("--all", action="store_true", help="Include inactive sources")

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

        elif args.command == "extract":
            sys.exit(cmd_extract(args))

        elif args.command == "guest-summary":
            sys.exit(cmd_guest_summary(args))

        elif args.command == "twitter":
            sys.exit(cmd_twitter(args))

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
