"""CLI commands for database operations."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def cmd_db_init(args: argparse.Namespace) -> int:
    """Initialize the database schema."""
    from podstock.db.engine import get_engine, init_db, DEFAULT_DB_PATH

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if db_path.exists() and not args.force:
        console.print(f"[yellow]Database already exists:[/yellow] {db_path}")
        console.print("Use --force to recreate")
        return 1

    try:
        engine = get_engine(db_path, echo=args.verbose)

        with console.status("Initializing database..."):
            init_db(engine, force=args.force)

        console.print(f"[green]✓[/green] Database initialized: {db_path}")
        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize database: {e}")
        return 1


def cmd_db_status(args: argparse.Namespace) -> int:
    """Show database status and statistics."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.models import (
        Source, Content, Analysis, Security, Recommendation, Mention
    )

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        console.print("Run 'podstock db init' to create it")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            stats = {
                "sources": session.query(Source).count(),
                "content": session.query(Content).count(),
                "analyses": session.query(Analysis).count(),
                "securities": session.query(Security).count(),
                "recommendations": session.query(Recommendation).count(),
                "mentions": session.query(Mention).count(),
            }

            # Get unmatched recommendations
            unmatched = session.query(Recommendation).filter(
                Recommendation.security_id.is_(None)
            ).count()

        console.print(f"\n[bold]Database:[/bold] {db_path}")
        console.print(f"[bold]Size:[/bold] {db_path.stat().st_size / 1024:.1f} KB\n")

        table = Table(title="Database Statistics")
        table.add_column("Table", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for name, count in stats.items():
            table.add_row(name, str(count))

        console.print(table)

        if unmatched > 0:
            console.print(f"\n[yellow]⚠ {unmatched} recommendations without matched security[/yellow]")

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_db_seed_securities(args: argparse.Namespace) -> int:
    """Seed securities from ticker_mapping.json."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.ticker_lookup import seed_from_ticker_mapping

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        console.print("Run 'podstock db init' first")
        return 1

    # Default mapping file
    mapping_path = Path(args.mapping) if args.mapping else (
        Path(__file__).parent.parent.parent.parent / "data" / "prices" / "ticker_mapping.json"
    )

    if not mapping_path.exists():
        console.print(f"[red]✗[/red] Mapping file not found: {mapping_path}")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            with console.status("Seeding securities..."):
                result = seed_from_ticker_mapping(session, mapping_path)

        console.print(f"[green]✓[/green] Seeded {result['securities_created']} securities")
        console.print(f"[green]✓[/green] Added {result['aliases_created']} aliases")

        if result['securities_updated'] > 0:
            console.print(f"[dim]Updated {result['securities_updated']} existing securities[/dim]")

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_db_load(args: argparse.Namespace) -> int:
    """Load data from JSON files into database."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.loader import PodcastLoader, TwitterLoader, YouTubeLoader, LoadResult

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        console.print("Run 'podstock db init' first")
        return 1

    # Determine loader type and data directory
    load_type = getattr(args, "type", None) or "podcast"

    if load_type == "twitter":
        loader = TwitterLoader()
        default_dir = Path(__file__).parent.parent.parent.parent / "data" / "twitter" / "analyses"
    elif load_type == "youtube":
        loader = YouTubeLoader()
        # Support channel-specific directories
        channel = getattr(args, "channel", None) or "technicalroundup"
        default_dir = Path(__file__).parent.parent.parent.parent / "data" / "crypto" / f"{channel}-analysis"
    else:
        loader = PodcastLoader()
        default_dir = Path(__file__).parent.parent.parent.parent / "data" / "extracted"

    data_dir = Path(args.data_dir) if args.data_dir else default_dir

    try:
        engine = get_engine(db_path)

        # Find JSON files
        if args.file:
            files = [Path(args.file)]
        elif load_type == "twitter":
            # Only load tweet-analyses files for Twitter
            files = sorted(data_dir.glob("*-tweet-analyses.json"))
        elif load_type == "youtube":
            # Load all JSON files except completion-log.json
            files = sorted(f for f in data_dir.glob("*.json") if f.name != "completion-log.json")
        else:
            pattern = f"{args.source}-*.json" if args.source else "*.json"
            files = sorted(data_dir.glob(pattern))

        if not files:
            console.print(f"[yellow]No JSON files found in:[/yellow] {data_dir}")
            return 0

        console.print(f"Found {len(files)} files to process")

        results = {"loaded": 0, "skipped": 0, "failed": 0}

        for json_path in files:
            try:
                # Use separate session for each file to avoid rollback issues
                with get_session(engine) as session:
                    result = loader.load(json_path, session)

                    if result.status == "success":
                        results["loaded"] += 1
                        if args.verbose:
                            console.print(f"[green]✓[/green] {json_path.name}")
                    elif result.status == "skipped":
                        results["skipped"] += 1
                        if args.verbose:
                            console.print(f"[dim]○ {json_path.name} (unchanged)[/dim]")
                    else:
                        results["failed"] += 1
                        console.print(f"[red]✗[/red] {json_path.name}: {result.error}")

            except Exception as e:
                results["failed"] += 1
                console.print(f"[red]✗[/red] {json_path.name}: {e}")

        console.print(f"\n[green]Loaded:[/green] {results['loaded']}")
        console.print(f"[dim]Skipped:[/dim] {results['skipped']}")
        if results["failed"] > 0:
            console.print(f"[red]Failed:[/red] {results['failed']}")

        return 0 if results["failed"] == 0 else 1

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_db_search(args: argparse.Namespace) -> int:
    """Search recommendations in database."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.queries import search_recommendations

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            results = search_recommendations(
                session,
                stock=args.stock,
                ticker=args.ticker,
                action=args.action,
                since=args.since,
                speaker=args.speaker,
                limit=args.limit or 20,
            )

        if not results:
            console.print("[yellow]No recommendations found[/yellow]")
            return 0

        table = Table(title=f"Recommendations ({len(results)} results)")
        table.add_column("Date", style="dim")
        table.add_column("Stock", style="cyan")
        table.add_column("Action", style="green")
        table.add_column("Speaker")
        table.add_column("Source")

        for rec in results:
            action_style = {
                "buy": "green",
                "sell": "red",
                "hold": "yellow",
                "watch": "blue",
                "avoid": "red dim",
            }.get(rec.action, "")

            table.add_row(
                rec.date,
                rec.stock_name,
                f"[{action_style}]{rec.action}[/{action_style}]",
                rec.speaker or "-",
                rec.source_name,
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_db_pending(args: argparse.Namespace) -> int:
    """Manage pending (unmatched) securities."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.models import PendingSecurity, Security

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            if args.pending_command == "list":
                pending = session.query(PendingSecurity).filter_by(
                    status="pending"
                ).order_by(PendingSecurity.occurrence_count.desc()).limit(50).all()

                if not pending:
                    console.print("[green]No pending securities[/green]")
                    return 0

                table = Table(title="Pending Securities")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="cyan")
                table.add_column("Ticker")
                table.add_column("Count", justify="right")
                table.add_column("Source")

                for p in pending:
                    table.add_row(
                        str(p.id),
                        p.raw_name,
                        p.raw_ticker or "-",
                        str(p.occurrence_count),
                        p.source or "-",
                    )

                console.print(table)

            elif args.pending_command == "resolve":
                pending = session.query(PendingSecurity).get(args.id)
                if not pending:
                    console.print(f"[red]Pending security not found:[/red] {args.id}")
                    return 1

                security = session.query(Security).get(args.security_id)
                if not security:
                    console.print(f"[red]Security not found:[/red] {args.security_id}")
                    return 1

                pending.status = "resolved"
                pending.resolved_security_id = security.id
                session.commit()

                console.print(f"[green]✓[/green] Resolved '{pending.raw_name}' -> {security.name} ({security.ticker})")

            elif args.pending_command == "reject":
                pending = session.query(PendingSecurity).get(args.id)
                if not pending:
                    console.print(f"[red]Pending security not found:[/red] {args.id}")
                    return 1

                pending.status = "rejected"
                session.commit()

                console.print(f"[green]✓[/green] Rejected '{pending.raw_name}'")

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_db_trust(args: argparse.Namespace) -> int:
    """Manage trust ratings for sources."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.models import Source

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            if args.trust_command == "set":
                source = session.query(Source).filter_by(id=args.source_id).first()
                if not source:
                    console.print(f"[red]Source not found:[/red] {args.source_id}")
                    return 1

                if args.rating < -1 or args.rating > 3:
                    console.print("[red]Rating must be between -1 and 3[/red]")
                    console.print("  -1: Unreliable (verified misleading)")
                    console.print("   0: Neutral (unknown track record)")
                    console.print("   1: Positive (somewhat reliable)")
                    console.print("   2: Very positive (consistently reliable)")
                    console.print("   3: GOAT (exceptional track record)")
                    return 1

                old_rating = source.trust_rating if source.trust_rating is not None else 0
                source.trust_rating = args.rating
                if args.notes:
                    source.trust_notes = args.notes
                session.commit()

                console.print(f"[green]✓[/green] Updated {source.name}: {old_rating} → {args.rating}")
                if args.notes:
                    console.print(f"  Notes: {args.notes}")

            elif args.trust_command == "show":
                if args.source_id:
                    sources = session.query(Source).filter_by(id=args.source_id).all()
                else:
                    sources = session.query(Source).order_by(
                        Source.trust_rating.desc(), Source.name
                    ).all()

                if not sources:
                    console.print("[yellow]No sources found[/yellow]")
                    return 0

                table = Table(title="Source Trust Ratings")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="cyan")
                table.add_column("Type")
                table.add_column("Trust", justify="center")
                table.add_column("Notes", max_width=40)

                for s in sources:
                    rating = s.trust_rating if s.trust_rating is not None else 0
                    # Display: -1=⚠️, 0=⚪, 1=⭐, 2=⭐⭐, 3=👑
                    display = {
                        -1: "⚠️ Unreliable",
                        0: "⚪ Neutral",
                        1: "⭐ Positive",
                        2: "⭐⭐ Very positive",
                        3: "👑 GOAT",
                    }.get(rating, f"? ({rating})")
                    rating_style = {
                        3: "green bold",
                        2: "green",
                        1: "cyan",
                        0: "dim",
                        -1: "red",
                    }.get(rating, "")

                    table.add_row(
                        s.id,
                        s.name,
                        s.type,
                        f"[{rating_style}]{display}[/{rating_style}]",
                        (s.trust_notes or "-")[:40],
                    )

                console.print(table)

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return 1


def cmd_db_migrate(args: argparse.Namespace) -> int:
    """Run database migrations."""
    from podstock.db.engine import get_engine, DEFAULT_DB_PATH
    import sqlite3

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        return 1

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        migrations_run = 0

        # Migration 1: Add trust_rating and trust_notes to sources
        cursor.execute("PRAGMA table_info(sources)")
        columns = [col[1] for col in cursor.fetchall()]

        if "trust_rating" not in columns:
            console.print("  Adding trust_rating column to sources...")
            cursor.execute("ALTER TABLE sources ADD COLUMN trust_rating INTEGER DEFAULT 3")
            migrations_run += 1

        if "trust_notes" not in columns:
            console.print("  Adding trust_notes column to sources...")
            cursor.execute("ALTER TABLE sources ADD COLUMN trust_notes TEXT")
            migrations_run += 1

        conn.commit()
        conn.close()

        if migrations_run > 0:
            console.print(f"[green]✓[/green] Ran {migrations_run} migration(s)")
        else:
            console.print("[dim]Database is up to date[/dim]")

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Migration error: {e}")
        return 1


def cmd_db_performance(args: argparse.Namespace) -> int:
    """Calculate performance for recommendations."""
    from podstock.db.engine import get_engine, get_session, DEFAULT_DB_PATH
    from podstock.db.performance import update_all_performance, import_prices_from_tracker, fetch_prices_from_yahoo

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        return 1

    try:
        engine = get_engine(db_path)

        with get_session(engine) as session:
            if args.perf_command == "update":
                with console.status("Updating performance data..."):
                    result = update_all_performance(
                        session,
                        limit=args.limit,
                        force=args.force,
                    )

                console.print(f"[green]Updated:[/green] {result['updated']}")
                console.print(f"[dim]Skipped:[/dim] {result['skipped']}")
                if result['failed'] > 0:
                    console.print(f"[red]Failed:[/red] {result['failed']}")

            elif args.perf_command == "import-prices":
                with console.status("Importing prices from tracker..."):
                    result = import_prices_from_tracker(session)

                console.print(f"[green]Imported:[/green] {result['imported']} price records")
                console.print(f"[dim]Skipped:[/dim] {result['skipped']}")

            elif args.perf_command == "fetch-prices":
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Fetching prices...", total=100)

                    def update_progress(current, total, ticker):
                        progress.update(task, completed=int(current / total * 100),
                                       description=f"Fetching {ticker}...")

                    result = fetch_prices_from_yahoo(session, progress_callback=update_progress)

                console.print(f"\n[green]Securities processed:[/green] {result['securities_processed']}")
                console.print(f"[green]Price records fetched:[/green] {result['fetched']}")
                console.print(f"[dim]Skipped:[/dim] {result['skipped']}")
                if result['failed'] > 0:
                    console.print(f"[yellow]Failed:[/yellow] {result['failed']}")

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_db(args: argparse.Namespace) -> int:
    """Route db subcommands."""
    if args.db_command == "init":
        return cmd_db_init(args)
    elif args.db_command == "status":
        return cmd_db_status(args)
    elif args.db_command == "seed-securities":
        return cmd_db_seed_securities(args)
    elif args.db_command == "load":
        return cmd_db_load(args)
    elif args.db_command == "search":
        return cmd_db_search(args)
    elif args.db_command == "pending":
        return cmd_db_pending(args)
    elif args.db_command == "performance":
        return cmd_db_performance(args)
    elif args.db_command == "trust":
        return cmd_db_trust(args)
    elif args.db_command == "migrate":
        return cmd_db_migrate(args)
    else:
        console.print("Use 'podstock db --help' for usage")
        return 1


def add_db_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add db command group to CLI."""
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_parser.add_argument("--db", help="Database file path")
    db_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    db_sub = db_parser.add_subparsers(dest="db_command")

    # db init
    init_parser = db_sub.add_parser("init", help="Initialize database schema")
    init_parser.add_argument("--force", action="store_true", help="Drop and recreate all tables")

    # db status
    db_sub.add_parser("status", help="Show database statistics")

    # db seed-securities
    seed_parser = db_sub.add_parser("seed-securities", help="Seed securities from ticker mapping")
    seed_parser.add_argument("--mapping", help="Path to ticker_mapping.json")

    # db load
    load_parser = db_sub.add_parser("load", help="Load JSON data into database")
    load_parser.add_argument("--source", help="Filter by source ID (e.g., fillorkill)")
    load_parser.add_argument("--type", choices=["podcast", "twitter", "youtube"], default="podcast",
                            help="Data type to load (default: podcast)")
    load_parser.add_argument("--channel", help="YouTube channel name (default: technicalroundup)")
    load_parser.add_argument("--file", help="Load specific file")
    load_parser.add_argument("--data-dir", help="Data directory path")

    # db search
    search_parser = db_sub.add_parser("search", help="Search recommendations")
    search_parser.add_argument("stock", nargs="?", help="Stock name to search")
    search_parser.add_argument("--ticker", help="Search by ticker")
    search_parser.add_argument("--action", choices=["buy", "sell", "hold", "watch", "avoid"])
    search_parser.add_argument("--since", help="Since date (YYYY-MM-DD)")
    search_parser.add_argument("--speaker", help="Filter by speaker")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # db pending
    pending_parser = db_sub.add_parser("pending", help="Manage pending securities")
    pending_sub = pending_parser.add_subparsers(dest="pending_command")

    pending_sub.add_parser("list", help="List pending securities")

    resolve_parser = pending_sub.add_parser("resolve", help="Resolve a pending security")
    resolve_parser.add_argument("id", type=int, help="Pending security ID")
    resolve_parser.add_argument("--security-id", type=int, required=True, help="Security ID to map to")

    reject_parser = pending_sub.add_parser("reject", help="Reject a pending security")
    reject_parser.add_argument("id", type=int, help="Pending security ID")

    # db performance
    perf_parser = db_sub.add_parser("performance", help="Calculate recommendation performance")
    perf_sub = perf_parser.add_subparsers(dest="perf_command")

    perf_update = perf_sub.add_parser("update", help="Update performance calculations")
    perf_update.add_argument("--limit", type=int, help="Max recommendations to process")
    perf_update.add_argument("--force", action="store_true", help="Recalculate all")

    perf_sub.add_parser("import-prices", help="Import prices from price tracker files")
    perf_sub.add_parser("fetch-prices", help="Fetch historical prices from Yahoo Finance")

    # db trust
    trust_parser = db_sub.add_parser("trust", help="Manage source trust ratings")
    trust_sub = trust_parser.add_subparsers(dest="trust_command")

    trust_show = trust_sub.add_parser("show", help="Show trust ratings")
    trust_show.add_argument("source_id", nargs="?", help="Specific source ID")

    trust_set = trust_sub.add_parser("set", help="Set trust rating for a source")
    trust_set.add_argument("source_id", help="Source ID")
    trust_set.add_argument("rating", type=int, help="Trust rating (-1 to 3: -1=unreliable, 0=neutral, 1=positive, 2=very positive, 3=GOAT)")
    trust_set.add_argument("--notes", help="Notes explaining the rating")

    # db migrate
    db_sub.add_parser("migrate", help="Run database migrations")
