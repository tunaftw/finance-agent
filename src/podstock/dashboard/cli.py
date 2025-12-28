"""CLI commands for dashboard operations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()


def cmd_dashboard_generate(args: argparse.Namespace) -> int:
    """Generate the dashboard."""
    from podstock.db.engine import DEFAULT_DB_PATH

    from .generator import DashboardGenerator

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH

    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        console.print("Run 'podstock db init' and 'podstock db load' first")
        return 1

    # Default output directory
    output_dir = Path(args.output) if args.output else db_path.parent / "dashboard"

    try:
        generator = DashboardGenerator(db_path, output_dir)

        with console.status("Generating dashboard..."):
            result = generator.generate(full_rebuild=args.full)

        console.print(f"[green]✓[/green] Dashboard generated: {result.output_path}")
        console.print(f"  Analyses: {result.analyses_count}")
        console.print(f"  Recommendations: {result.recommendations_count}")
        console.print(f"  Watchlist items: {result.watchlist_count}")

        if args.open:
            _open_in_browser(result.output_path)

        return 0

    except Exception as e:
        console.print(f"[red]✗[/red] Error generating dashboard: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cmd_dashboard_open(args: argparse.Namespace) -> int:
    """Open the dashboard in the default browser."""
    from podstock.db.engine import DEFAULT_DB_PATH

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    output_dir = Path(args.output) if args.output else db_path.parent / "dashboard"
    index_path = output_dir / "index.html"

    if not index_path.exists():
        console.print(f"[yellow]Dashboard not found:[/yellow] {index_path}")
        console.print("Run 'podstock dashboard generate' first")
        return 1

    _open_in_browser(index_path)
    return 0


def _open_in_browser(path: Path) -> None:
    """Open a file in the default browser."""
    url = f"file://{path.absolute()}"
    console.print(f"Opening: {url}")

    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        subprocess.run(["start", str(path)], shell=True, check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Route dashboard subcommands."""
    if args.dashboard_command == "generate":
        return cmd_dashboard_generate(args)
    elif args.dashboard_command == "open":
        return cmd_dashboard_open(args)
    else:
        console.print("Use 'podstock dashboard --help' for usage")
        return 1


def add_dashboard_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add dashboard command group to CLI."""
    dashboard_parser = subparsers.add_parser("dashboard", help="Generate and view analysis dashboard")
    dashboard_parser.add_argument("--db", help="Database file path")
    dashboard_parser.add_argument("--output", "-o", help="Output directory for dashboard")
    dashboard_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    dashboard_sub = dashboard_parser.add_subparsers(dest="dashboard_command")

    # dashboard generate
    generate_parser = dashboard_sub.add_parser("generate", help="Generate dashboard from database")
    generate_parser.add_argument("--full", action="store_true", help="Full rebuild (regenerate all data)")
    generate_parser.add_argument("--open", action="store_true", help="Open in browser after generating")

    # dashboard open
    dashboard_sub.add_parser("open", help="Open dashboard in browser")
