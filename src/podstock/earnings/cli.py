"""CLI commands for earnings call transcript management.

This module provides CLI commands for:
- Syncing transcripts from Inderes.fi
- Listing and viewing transcripts
- Analyzing transcripts with LLM
- Interactive Q&A on transcripts

Example usage:
    podstock earnings sync --company Nordea     # Download Nordea transcripts
    podstock earnings list                      # View collected transcripts
    podstock earnings show nordea-earnings-2024-q3   # Show transcript details
    podstock earnings analyze nordea-earnings-2024-q3  # Analyze with LLM
    podstock earnings ask nordea-earnings-2024-q3      # Interactive Q&A
    podstock earnings search "Hacksaw"          # Search for available transcripts
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from podstock.core.config import Config

console = Console()


def setup_earnings_parser(subparsers) -> None:
    """Set up the earnings subcommand parser.

    Args:
        subparsers: argparse subparsers object from main CLI.
    """
    earnings_parser = subparsers.add_parser(
        "earnings",
        help="Earnings call transcripts",
        description="Collect, analyze, and query earnings call transcripts",
    )
    earnings_sub = earnings_parser.add_subparsers(
        dest="earnings_command",
        help="Earnings commands",
    )

    # === Sync Command ===
    # podstock earnings sync [--company <id>] [--limit N]
    sync_parser = earnings_sub.add_parser(
        "sync",
        help="Sync transcripts from Inderes",
        description="Fetch and store earnings call transcripts from Inderes.fi. "
        "Downloads new transcripts not already in the local database.",
    )
    sync_parser.add_argument(
        "--company",
        metavar="NAME",
        help="Company name to sync (e.g., 'Nordea', 'Hacksaw'). "
        "Omit to sync latest transcripts from all companies.",
    )
    sync_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum transcripts to fetch (default: 10)",
    )

    # === List Command ===
    # podstock earnings list [--company <id>]
    list_parser = earnings_sub.add_parser(
        "list",
        help="List collected transcripts",
        description="Display all downloaded transcripts with metadata including "
        "company name, period, word count, language, and analysis status.",
    )
    list_parser.add_argument(
        "--company",
        metavar="ID",
        help="Filter results by company ID (e.g., 'nordea', 'hacksaw')",
    )

    # === Show Command ===
    # podstock earnings show <transcript_id>
    show_parser = earnings_sub.add_parser(
        "show",
        help="Show transcript details",
        description="Display transcript metadata, speakers, and any available "
        "LLM analysis. Use --full to see the complete transcript text.",
    )
    show_parser.add_argument(
        "transcript_id",
        metavar="ID",
        help="Transcript ID to display (use 'list' command to find IDs)",
    )
    show_parser.add_argument(
        "--full",
        action="store_true",
        help="Include full transcript text in output (may be very long)",
    )

    # === Analyze Command ===
    # podstock earnings analyze <transcript_id> [--model <model>]
    analyze_parser = earnings_sub.add_parser(
        "analyze",
        help="Analyze transcript with LLM",
        description="Run LLM analysis on earnings transcripts. Extracts executive "
        "summary, bullish/bearish takeaways, management tone, and key signals. "
        "Only analyzes transcripts not previously analyzed.",
    )
    analyze_parser.add_argument(
        "transcript_id",
        nargs="?",
        metavar="ID",
        help="Specific transcript ID to analyze. "
        "Omit and use --company to analyze all transcripts for a company.",
    )
    analyze_parser.add_argument(
        "--company",
        metavar="ID",
        help="Analyze all unanalyzed transcripts for a company",
    )
    analyze_parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        metavar="MODEL",
        help="LLM model for analysis (default: claude-sonnet-4-20250514). "
        "Requires ANTHROPIC_API_KEY environment variable.",
    )

    # === Ask Command ===
    # podstock earnings ask <transcript_id> [question]
    ask_parser = earnings_sub.add_parser(
        "ask",
        help="Interactive Q&A on transcript",
        description="Ask questions about a specific earnings call transcript. "
        "Supports single-question mode or interactive conversation. "
        "Type 'exit' or 'quit' to end interactive session.",
    )
    ask_parser.add_argument(
        "transcript_id",
        metavar="ID",
        help="Transcript ID to query (use 'list' command to find IDs)",
    )
    ask_parser.add_argument(
        "question",
        nargs="?",
        metavar="QUESTION",
        help="Question to ask. Omit to enter interactive mode.",
    )

    # === Search Command ===
    # podstock earnings search <query>
    search_parser = earnings_sub.add_parser(
        "search",
        help="Search Inderes for transcripts",
        description="Search Inderes.fi for available earnings call transcripts. "
        "Shows results with links. Use 'sync --company' to download found transcripts.",
    )
    search_parser.add_argument(
        "query",
        metavar="COMPANY",
        help="Company name to search for (e.g., 'Nordea', 'Hacksaw')",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum search results to display (default: 10)",
    )


def cmd_earnings(args: argparse.Namespace, config: Config) -> int:
    """Handle earnings subcommands.

    Args:
        args: Parsed arguments.
        config: Application configuration.

    Returns:
        Exit code.
    """
    if not args.earnings_command:
        console.print("[yellow]Usage: podstock earnings <command>[/yellow]")
        console.print("Commands: sync, list, show, analyze, ask, search")
        return 1

    if args.earnings_command == "sync":
        return _cmd_sync(args, config)
    elif args.earnings_command == "list":
        return _cmd_list(args, config)
    elif args.earnings_command == "show":
        return _cmd_show(args, config)
    elif args.earnings_command == "analyze":
        return _cmd_analyze(args, config)
    elif args.earnings_command == "ask":
        return _cmd_ask(args, config)
    elif args.earnings_command == "search":
        return _cmd_search(args, config)
    else:
        console.print(f"[red]Unknown command: {args.earnings_command}[/red]")
        return 1


def _cmd_sync(args: argparse.Namespace, config: Config) -> int:
    """Sync transcripts from Inderes.

    Args:
        args: Parsed arguments with company and limit.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.playwright_scraper import PlaywrightInderesScraper
    from podstock.earnings.storage import EarningsStorage

    storage = EarningsStorage(config)
    scraper = PlaywrightInderesScraper()

    console.print("[bold]Syncing transcripts from Inderes...[/bold]")

    # Find available transcripts
    with console.status("Searching for transcripts..."):
        if args.company:
            listings = scraper.find_transcripts(
                company_name=args.company,
                limit=args.limit,
            )
        else:
            listings = scraper.find_transcripts(limit=args.limit)

    if not listings:
        console.print("[yellow]No transcripts found.[/yellow]")
        if args.company:
            console.print(
                f"Try searching Inderes directly for '{args.company}' "
                "or check company name spelling."
            )
        return 0

    console.print(f"Found {len(listings)} transcript(s)")

    # Fetch and save each transcript
    new_count = 0
    skip_count = 0

    for listing in listings:
        # Generate expected ID to check if already exists
        company_id = scraper._slugify(listing.company_name)
        year = listing.year or 2024
        quarter = listing.quarter or 1
        transcript_id = f"{company_id}-earnings-{year}-q{quarter}"

        if storage.transcript_exists(transcript_id):
            console.print(f"  [dim]Skipping {transcript_id} (already exists)[/dim]")
            skip_count += 1
            continue

        with console.status(f"Fetching: {listing.title[:50]}..."):
            transcript = scraper.fetch_transcript(listing, company_id=company_id)

        if transcript:
            path = storage.save_transcript(transcript)
            console.print(
                f"  [green]✓[/green] {transcript.id} "
                f"({transcript.word_count} words)"
            )
            new_count += 1
        else:
            console.print(f"  [red]✗[/red] Failed to fetch: {listing.title[:50]}")

    storage.update_last_sync()

    console.print()
    console.print(f"[green]Synced {new_count} new transcript(s)[/green]")
    if skip_count:
        console.print(f"[dim]Skipped {skip_count} existing transcript(s)[/dim]")

    return 0


def _cmd_list(args: argparse.Namespace, config: Config) -> int:
    """List collected transcripts.

    Args:
        args: Parsed arguments with optional company filter.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.storage import EarningsStorage

    storage = EarningsStorage(config)
    transcripts = storage.list_transcripts(company_id=args.company)

    if not transcripts:
        console.print("[yellow]No transcripts collected yet.[/yellow]")
        console.print("Run: podstock earnings sync")
        return 0

    table = Table(title="Collected Transcripts")
    table.add_column("ID", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("Period")
    table.add_column("Words", justify="right")
    table.add_column("Lang")
    table.add_column("Analyzed", justify="center")

    for t in transcripts:
        period = f"Q{t.fiscal_quarter} {t.fiscal_year}"
        analyzed = "✓" if storage.is_analyzed(t.id) else ""
        table.add_row(
            t.id,
            t.company_name[:30],
            period,
            str(t.word_count),
            t.language.upper(),
            analyzed,
        )

    console.print(table)
    return 0


def _cmd_show(args: argparse.Namespace, config: Config) -> int:
    """Show transcript details.

    Args:
        args: Parsed arguments with transcript_id and optional --full.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.storage import EarningsStorage

    storage = EarningsStorage(config)
    transcript = storage.get_transcript(args.transcript_id)

    if not transcript:
        console.print(f"[red]Transcript not found: {args.transcript_id}[/red]")
        return 1

    # Header info
    console.print()
    console.print(f"[bold cyan]{transcript.company_name}[/bold cyan]")
    console.print(f"[dim]Q{transcript.fiscal_quarter} {transcript.fiscal_year} Earnings Call[/dim]")
    console.print()

    # Metadata table
    table = Table(show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column()

    table.add_row("ID:", transcript.id)
    table.add_row("Date:", transcript.call_date.strftime("%Y-%m-%d"))
    table.add_row("Language:", transcript.language.upper())
    table.add_row("Words:", str(transcript.word_count))
    table.add_row("Source:", transcript.source)

    if transcript.linked_filing_id:
        table.add_row("Linked Filing:", transcript.linked_filing_id)
    if transcript.linked_presentation_id:
        table.add_row("Linked Presentation:", transcript.linked_presentation_id)

    if transcript.speakers:
        speakers_str = ", ".join(
            f"{s.name}" + (f" ({s.role})" if s.role else "")
            for s in transcript.speakers[:5]
        )
        if len(transcript.speakers) > 5:
            speakers_str += f" (+{len(transcript.speakers) - 5} more)"
        table.add_row("Speakers:", speakers_str)

    console.print(table)
    console.print()

    # Show analysis if available
    analysis = storage.load_analysis(args.transcript_id)
    if analysis:
        console.print("[bold green]Analysis Available[/bold green]")
        console.print()
        console.print("[bold]Executive Summary:[/bold]")
        console.print(analysis.executive_summary)
        console.print()

        if analysis.key_takeaways_bullish:
            console.print("[bold green]Bullish Takeaways:[/bold green]")
            for takeaway in analysis.key_takeaways_bullish[:5]:
                console.print(f"  [green]↑[/green] {takeaway}")
            console.print()

        if analysis.key_takeaways_bearish:
            console.print("[bold red]Bearish Takeaways:[/bold red]")
            for takeaway in analysis.key_takeaways_bearish[:5]:
                console.print(f"  [red]↓[/red] {takeaway}")
            console.print()

    # Show full text if requested
    if args.full:
        console.print()
        console.print("[bold]Full Transcript:[/bold]")
        console.print("-" * 60)
        console.print(transcript.full_text)

    return 0


def _cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """Analyze transcript with LLM.

    Args:
        args: Parsed arguments with transcript_id or --company.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.storage import EarningsStorage

    storage = EarningsStorage(config)

    # Determine which transcripts to analyze
    if args.transcript_id:
        transcript = storage.get_transcript(args.transcript_id)
        if not transcript:
            console.print(f"[red]Transcript not found: {args.transcript_id}[/red]")
            return 1
        transcripts = [transcript]
    elif args.company:
        transcripts = storage.list_transcripts(company_id=args.company)
        if not transcripts:
            console.print(f"[red]No transcripts found for company: {args.company}[/red]")
            return 1
    else:
        console.print("[red]Specify a transcript_id or --company[/red]")
        return 1

    # Filter to unanalyzed only
    unanalyzed = [t for t in transcripts if not storage.is_analyzed(t.id)]

    if not unanalyzed:
        console.print("[yellow]All specified transcripts are already analyzed.[/yellow]")
        return 0

    console.print(f"Analyzing {len(unanalyzed)} transcript(s) with {args.model}...")

    try:
        from podstock.earnings.analyzer import TranscriptAnalyzer
    except ImportError:
        console.print(
            "[yellow]Analyzer not yet implemented. "
            "This will be available once LLM integration is complete.[/yellow]"
        )
        return 1

    analyzer = TranscriptAnalyzer(model=args.model)

    for transcript in unanalyzed:
        with console.status(f"Analyzing {transcript.id}..."):
            try:
                analysis = analyzer.analyze(transcript)
                storage.save_analysis(analysis)
                console.print(f"  [green]✓[/green] {transcript.id}")
            except Exception as e:
                console.print(f"  [red]✗[/red] {transcript.id}: {e}")

    return 0


def _cmd_ask(args: argparse.Namespace, config: Config) -> int:
    """Interactive Q&A on transcript.

    Args:
        args: Parsed arguments with transcript_id and optional question.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.storage import EarningsStorage

    storage = EarningsStorage(config)
    transcript = storage.get_transcript(args.transcript_id)

    if not transcript:
        console.print(f"[red]Transcript not found: {args.transcript_id}[/red]")
        return 1

    console.print(f"[bold]{transcript.company_name} Q{transcript.fiscal_quarter} {transcript.fiscal_year}[/bold]")
    console.print(f"[dim]{transcript.word_count} words[/dim]")
    console.print()

    try:
        from podstock.earnings.analyzer import TranscriptAnalyzer
    except ImportError:
        console.print(
            "[yellow]Analyzer not yet implemented. "
            "This will be available once LLM integration is complete.[/yellow]"
        )
        return 1

    analyzer = TranscriptAnalyzer()

    if args.question:
        # Single question mode
        with console.status("Thinking..."):
            answer = analyzer.ask(transcript, args.question)
        console.print()
        console.print(Panel(answer, title="Answer"))
    else:
        # Interactive mode
        console.print("Ask questions about this transcript. Type 'exit' to quit.")
        console.print()

        while True:
            try:
                question = console.input("[bold cyan]You:[/bold cyan] ")
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            if question.lower() in ["exit", "quit", "q"]:
                break

            if not question.strip():
                continue

            with console.status("Thinking..."):
                answer = analyzer.ask(transcript, question)

            console.print()
            console.print(f"[bold green]Assistant:[/bold green] {answer}")
            console.print()

    return 0


def _cmd_search(args: argparse.Namespace, config: Config) -> int:
    """Search Inderes for transcripts.

    Args:
        args: Parsed arguments with query and limit.
        config: Application configuration.

    Returns:
        Exit code.
    """
    from podstock.earnings.playwright_scraper import PlaywrightInderesScraper

    scraper = PlaywrightInderesScraper()

    with console.status(f"Searching for '{args.query}'..."):
        listings = scraper.find_transcripts(
            company_name=args.query,
            limit=args.limit,
        )

    if not listings:
        console.print(f"[yellow]No transcripts found for '{args.query}'[/yellow]")
        return 0

    table = Table(title=f"Search Results: {args.query}")
    table.add_column("Title", style="cyan")
    table.add_column("Company")
    table.add_column("Period")
    table.add_column("URL", style="dim")

    for listing in listings:
        period = ""
        if listing.quarter and listing.year:
            period = f"Q{listing.quarter} {listing.year}"
        elif listing.year:
            period = str(listing.year)

        # Truncate URL for display
        url_display = listing.url
        if len(url_display) > 50:
            url_display = "..." + url_display[-47:]

        table.add_row(
            listing.title[:50],
            listing.company_name[:25],
            period,
            url_display,
        )

    console.print(table)
    console.print()
    console.print(
        f"[dim]To download these, run: "
        f"podstock earnings sync --company '{args.query}'[/dim]"
    )

    return 0
