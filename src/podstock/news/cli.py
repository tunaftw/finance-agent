"""CLI commands for news aggregation.

This module provides CLI commands for:
- Syncing news from RSS feeds
- Listing and filtering news items
- Managing feed configurations
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from podstock.news.default_feeds import SOURCE_NAMES, get_default_feeds
from podstock.news.feeds import FeedManager
from podstock.news.matcher import create_matcher_if_available
from podstock.news.models import NewsPriority, NewsType
from podstock.news.storage import NewsStorage

if TYPE_CHECKING:
    from argparse import Namespace

    from podstock.core.config import Config

console = Console()


def setup_news_parser(subparsers) -> None:
    """Set up the news subcommand parser.

    Args:
        subparsers: argparse subparsers object from main CLI.
    """
    news_parser = subparsers.add_parser(
        "news",
        help="Stock market news aggregation",
        description="Fetch and manage news from Nasdaq Nordic and financial media",
    )
    news_sub = news_parser.add_subparsers(dest="news_command", help="News commands")

    # === Sync ===

    # podstock news sync [--feed <feed_id>]
    sync_parser = news_sub.add_parser("sync", help="Fetch news from RSS feeds")
    sync_parser.add_argument("--feed", help="Sync specific feed by ID")

    # === List/View ===

    # podstock news list [--hours N] [--company <id>] [--followed] [--type regulatory|editorial]
    list_parser = news_sub.add_parser("list", help="List recent news")
    list_parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours to look back (default: 24)",
    )
    list_parser.add_argument("--company", help="Filter by company ID")
    list_parser.add_argument(
        "--followed",
        action="store_true",
        help="Only show news for followed companies",
    )
    list_parser.add_argument(
        "--type",
        choices=["regulatory", "editorial", "press_release"],
        help="Filter by news type",
    )
    list_parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Filter by priority",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum items to show (default: 50)",
    )

    # === Feed Management ===

    # podstock news feed-list
    news_sub.add_parser("feed-list", help="List configured feeds")

    # podstock news feed-add <url> --type <type>
    feed_add = news_sub.add_parser("feed-add", help="Add a custom feed")
    feed_add.add_argument("url", help="RSS feed URL")
    feed_add.add_argument(
        "--type",
        choices=["regulatory", "editorial", "press_release"],
        required=True,
        help="Type of news from this feed",
    )
    feed_add.add_argument("--name", help="Feed name (optional)")

    # podstock news feed-enable/disable <feed_id>
    feed_enable = news_sub.add_parser("feed-enable", help="Enable a feed")
    feed_enable.add_argument("feed_id", help="Feed ID to enable")

    feed_disable = news_sub.add_parser("feed-disable", help="Disable a feed")
    feed_disable.add_argument("feed_id", help="Feed ID to disable")

    # podstock news feed-remove <feed_id>
    feed_remove = news_sub.add_parser("feed-remove", help="Remove a feed")
    feed_remove.add_argument("feed_id", help="Feed ID to remove")

    # === Status ===

    # podstock news status
    news_sub.add_parser("status", help="Show news aggregation status")

    # === Init ===

    # podstock news init
    news_sub.add_parser("init", help="Initialize with default feeds")


def cmd_news(args: Namespace, config: Config) -> int:
    """Handle news subcommands.

    Args:
        args: Parsed command-line arguments.
        config: Application configuration.

    Returns:
        Exit code (0 for success).
    """
    storage = NewsStorage(config)
    matcher = create_matcher_if_available()

    command = args.news_command

    if command == "init":
        _handle_init(storage)
    elif command == "sync":
        _handle_sync(args, storage, matcher)
    elif command == "list":
        _handle_list(args, storage)
    elif command == "feed-list":
        _handle_feed_list(storage)
    elif command == "feed-add":
        _handle_feed_add(args, storage)
    elif command == "feed-enable":
        _handle_feed_enable(args, storage, enable=True)
    elif command == "feed-disable":
        _handle_feed_enable(args, storage, enable=False)
    elif command == "feed-remove":
        _handle_feed_remove(args, storage)
    elif command == "status":
        _handle_status(storage)
    else:
        console.print("[yellow]Use --help to see available commands[/yellow]")

    return 0


def _handle_init(storage: NewsStorage) -> None:
    """Initialize with default feeds."""
    default_feeds = get_default_feeds()
    existing = {f.id for f in storage.list_feeds()}

    added = 0
    for feed in default_feeds:
        if feed.id not in existing:
            storage.add_feed(feed)
            console.print(f"[green]Added feed:[/green] {feed.name}")
            added += 1

    if added == 0:
        console.print("[yellow]All default feeds already configured[/yellow]")
    else:
        console.print(f"\n[green]Added {added} default feeds[/green]")
        console.print("Run [bold]podstock news sync[/bold] to fetch news")


def _handle_sync(args, storage: NewsStorage, matcher) -> None:
    """Sync news from feeds."""
    feeds = storage.list_feeds()

    if not feeds:
        console.print("[yellow]No feeds configured. Run 'podstock news init' first.[/yellow]")
        return

    manager = FeedManager(storage, matcher)

    if args.feed:
        # Sync specific feed
        try:
            new_count = manager.sync_by_id(args.feed)
            console.print(f"[green]Synced {args.feed}:[/green] {new_count} new items")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
    else:
        # Sync all active feeds
        with console.status("[bold blue]Syncing feeds..."):
            total = 0
            for feed in feeds:
                if feed.active:
                    new_count = manager.sync_feed(feed)
                    if new_count > 0:
                        console.print(f"  {feed.name}: {new_count} new")
                    total += new_count

        console.print(f"\n[green]Total:[/green] {total} new items")


def _handle_list(args, storage: NewsStorage) -> None:
    """List recent news items."""
    items = storage.get_recent_items(
        hours=args.hours,
        company_id=args.company,
        followed_only=args.followed,
    )

    # Apply type filter
    if args.type:
        news_type = NewsType(args.type)
        items = [i for i in items if i.news_type == news_type]

    # Apply priority filter
    if args.priority:
        priority = NewsPriority(args.priority)
        items = [i for i in items if i.priority == priority]

    # Apply limit
    items = items[:args.limit]

    if not items:
        console.print("[yellow]No news items found matching criteria[/yellow]")
        return

    # Display as table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Time", style="dim", width=16)
    table.add_column("Priority", width=8)
    table.add_column("Source", width=12)
    table.add_column("Title", no_wrap=False)
    table.add_column("Companies", width=15)

    for item in items:
        # Format time
        time_str = item.published_at.strftime("%Y-%m-%d %H:%M")

        # Format priority with color
        priority_colors = {
            NewsPriority.HIGH: "[red]HIGH[/red]",
            NewsPriority.MEDIUM: "[yellow]MED[/yellow]",
            NewsPriority.LOW: "[dim]LOW[/dim]",
        }
        priority_str = priority_colors.get(item.priority, str(item.priority.value))

        # Format source
        source_name = SOURCE_NAMES.get(item.source, item.source.value)
        source_str = source_name[:12]

        # Format companies
        if item.companies:
            company_strs = []
            for m in item.companies[:2]:
                ticker = m.ticker or m.company_id
                if m.is_followed:
                    company_strs.append(f"[bold]{ticker}[/bold]")
                else:
                    company_strs.append(ticker)
            companies_str = ", ".join(company_strs)
            if len(item.companies) > 2:
                companies_str += f" +{len(item.companies) - 2}"
        else:
            companies_str = "[dim]-[/dim]"

        # Truncate title
        title = item.title
        if len(title) > 60:
            title = title[:57] + "..."

        table.add_row(time_str, priority_str, source_str, title, companies_str)

    console.print(table)
    console.print(f"\n[dim]Showing {len(items)} items from last {args.hours}h[/dim]")


def _handle_feed_list(storage: NewsStorage) -> None:
    """List configured feeds."""
    feeds = storage.list_feeds()

    if not feeds:
        console.print("[yellow]No feeds configured. Run 'podstock news init' first.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Active")
    table.add_column("Last Polled")
    table.add_column("Items")

    for feed in feeds:
        active_str = "[green]Yes[/green]" if feed.active else "[red]No[/red]"
        last_polled = (
            feed.last_polled.strftime("%Y-%m-%d %H:%M") if feed.last_polled else "-"
        )

        table.add_row(
            feed.id,
            feed.name,
            feed.news_type.value,
            active_str,
            last_polled,
            str(feed.last_item_count),
        )

    console.print(table)


def _handle_feed_add(args, storage: NewsStorage) -> None:
    """Add a custom feed."""
    from podstock.news.models import FeedConfig, NewsSource, NewsType

    # Generate ID from URL
    from urllib.parse import urlparse
    parsed = urlparse(args.url)
    feed_id = parsed.netloc.replace(".", "-").replace("www-", "")

    name = args.name or f"Custom: {parsed.netloc}"
    news_type = NewsType(args.type)

    feed = FeedConfig(
        id=feed_id,
        name=name,
        url=args.url,
        news_type=news_type,
        source=NewsSource.OTHER,
    )

    try:
        storage.add_feed(feed)
        console.print(f"[green]Added feed:[/green] {feed.id}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


def _handle_feed_enable(args, storage: NewsStorage, enable: bool) -> None:
    """Enable or disable a feed."""
    feed = storage.get_feed(args.feed_id)
    if not feed:
        console.print(f"[red]Feed not found:[/red] {args.feed_id}")
        return

    feed.active = enable
    storage.update_feed(feed)

    status = "enabled" if enable else "disabled"
    console.print(f"[green]Feed {status}:[/green] {feed.name}")


def _handle_feed_remove(args, storage: NewsStorage) -> None:
    """Remove a feed."""
    feed = storage.get_feed(args.feed_id)
    if not feed:
        console.print(f"[red]Feed not found:[/red] {args.feed_id}")
        return

    storage.remove_feed(args.feed_id)
    console.print(f"[green]Removed feed:[/green] {feed.name}")


def _handle_status(storage: NewsStorage) -> None:
    """Show news aggregation status."""
    stats = storage.get_stats()
    feeds = storage.list_feeds()

    console.print("\n[bold]News Aggregation Status[/bold]\n")

    # Overall stats
    console.print(f"Active feeds: {stats['feeds_active']}/{stats['feeds_total']}")
    console.print(f"Items (last 7 days): {stats['items_last_7_days']}")
    console.print(f"Dedup IDs tracked: {stats['recent_ids_tracked']}")

    if stats['last_updated']:
        console.print(f"Last updated: {stats['last_updated']}")

    # Per-feed status
    if feeds:
        console.print("\n[bold]Feed Status:[/bold]")
        for feed in feeds:
            status = "[green]●[/green]" if feed.active else "[red]○[/red]"
            last = feed.last_polled.strftime("%H:%M") if feed.last_polled else "never"
            console.print(f"  {status} {feed.name}: {feed.last_item_count} items (last: {last})")
