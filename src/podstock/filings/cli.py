"""CLI commands for financial filings management.

This module provides CLI commands for:
- Managing tracked companies
- Syncing filings from SEC EDGAR
- Importing local PDFs
- Analyzing filings with LLM
- Extracting financial metrics
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from podstock.core.config import Config

console = Console()


def setup_filings_parser(subparsers) -> None:
    """Set up the filings subcommand parser.

    Args:
        subparsers: argparse subparsers object from main CLI.
    """
    filings_parser = subparsers.add_parser(
        "filings",
        help="Financial reports and analysis",
        description="Download, parse, and analyze financial filings (10-K, annual reports, etc.)",
    )
    filings_sub = filings_parser.add_subparsers(dest="filings_command", help="Filings commands")

    # === Company Management ===

    # podstock filings company-add <identifier>
    add_parser = filings_sub.add_parser("company-add", help="Add a company to track")
    add_parser.add_argument("identifier", help="Ticker symbol, CIK, or company name")
    add_parser.add_argument(
        "--market",
        choices=["us", "sweden", "europe", "other"],
        default="us",
        help="Market/region (default: us)",
    )
    add_parser.add_argument("--name", help="Override company name")
    add_parser.add_argument("--ticker", help="Override ticker symbol")

    # podstock filings company-list
    filings_sub.add_parser("company-list", help="List tracked companies")

    # podstock filings company-remove <company_id>
    remove_parser = filings_sub.add_parser("company-remove", help="Remove a company")
    remove_parser.add_argument("company_id", help="Company ID to remove")

    # === Filing Operations ===

    # podstock filings sync [--company <id>] [--type annual|quarterly] [--limit N]
    sync_parser = filings_sub.add_parser("sync", help="Sync filings from EDGAR")
    sync_parser.add_argument("--company", help="Specific company ID (default: all)")
    sync_parser.add_argument(
        "--type",
        choices=["annual", "quarterly", "all"],
        default="all",
        help="Filing type filter",
    )
    sync_parser.add_argument("--limit", type=int, default=3, help="Max filings per company")
    sync_parser.add_argument(
        "--include-presentations",
        action="store_true",
        help="Also download presentations linked to reports",
    )

    # podstock filings import <pdf_path>
    import_parser = filings_sub.add_parser("import", help="Import a local PDF")
    import_parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    import_parser.add_argument("--company", required=True, help="Company ID")
    import_parser.add_argument(
        "--type",
        choices=["annual", "quarterly", "interim"],
        required=True,
        help="Filing type",
    )
    import_parser.add_argument("--year", type=int, required=True, help="Fiscal year")
    import_parser.add_argument("--quarter", type=int, help="Quarter (1-4) for quarterly reports")

    # podstock filings list [--company <id>]
    list_parser = filings_sub.add_parser("list", help="List filings")
    list_parser.add_argument("--company", help="Filter by company ID")
    list_parser.add_argument("--analyzed", action="store_true", help="Show only analyzed")
    list_parser.add_argument("--pending", action="store_true", help="Show only pending analysis")

    # podstock filings list-swedish [--segment large_cap|mid_cap|small_cap]
    list_swedish = filings_sub.add_parser("list-swedish", help="List available Swedish companies")
    list_swedish.add_argument(
        "--segment",
        choices=["large_cap", "mid_cap", "small_cap", "first_north"],
        help="Filter by market segment",
    )
    list_swedish.add_argument("--search", help="Search by name or ticker")

    # === Analysis ===

    # podstock filings analyze [--filing <id>] [--company <id>]
    analyze_parser = filings_sub.add_parser("analyze", help="Analyze filings with LLM")
    analyze_parser.add_argument("--filing", help="Specific filing ID")
    analyze_parser.add_argument("--company", help="All filings for company")
    analyze_parser.add_argument("--max", type=int, default=5, help="Max filings to analyze")
    analyze_parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="LLM model to use",
    )

    # podstock filings extract <filing_id>
    extract_parser = filings_sub.add_parser("extract", help="Extract financial metrics")
    extract_parser.add_argument("filing_id", help="Filing ID to extract from")
    extract_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format",
    )

    # podstock filings show <filing_id>
    show_parser = filings_sub.add_parser("show", help="Show filing details and analysis")
    show_parser.add_argument("filing_id", help="Filing ID to show")

    # podstock filings status
    filings_sub.add_parser("status", help="Show filings module status and overview")

    # podstock filings validate-urls
    validate_parser = filings_sub.add_parser("validate-urls", help="Validate Swedish IR URLs")
    validate_parser.add_argument("--fix", action="store_true", help="Attempt to find new URLs for broken ones")


def cmd_filings(args: argparse.Namespace, config: Config) -> int:
    """Handle filings commands.

    Args:
        args: Parsed command line arguments.
        config: Application configuration.

    Returns:
        Exit code (0 for success).
    """
    command = args.filings_command

    if command == "company-add":
        return cmd_company_add(args, config)
    elif command == "company-list":
        return cmd_company_list(args, config)
    elif command == "company-remove":
        return cmd_company_remove(args, config)
    elif command == "sync":
        return cmd_sync(args, config)
    elif command == "import":
        return cmd_import(args, config)
    elif command == "list":
        return cmd_list(args, config)
    elif command == "list-swedish":
        return cmd_list_swedish(args, config)
    elif command == "analyze":
        return cmd_analyze(args, config)
    elif command == "extract":
        return cmd_extract(args, config)
    elif command == "show":
        return cmd_show(args, config)
    elif command == "status":
        return cmd_status(args, config)
    elif command == "validate-urls":
        return cmd_validate_urls(args, config)
    else:
        console.print("[yellow]Usage: podstock filings <command>[/yellow]")
        console.print("Commands: company-add, company-list, list-swedish, sync, list, analyze, status, validate-urls")
        return 1


def cmd_company_add(args: argparse.Namespace, config: Config) -> int:
    """Add a company to track."""
    from podstock.filings.models import Company, Market
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    market = Market(args.market)

    if market == Market.US:
        # Try to look up via EDGAR
        try:
            from podstock.filings.clients.edgar import EdgarClient

            client = EdgarClient()
            company = client.get_company(args.identifier)
            if company:
                if args.name:
                    company.name = args.name
                if args.ticker:
                    company.ticker = args.ticker

                storage.add_company(company)
                console.print(f"[green]Added US company:[/green] {company.name} ({company.ticker})")
                console.print(f"  ID: {company.id}")
                console.print(f"  CIK: {company.cik}")
                return 0
            else:
                console.print(f"[red]Company not found in EDGAR: {args.identifier}[/red]")
                return 1
        except ImportError:
            console.print("[yellow]edgartools not installed. Install with:[/yellow]")
            console.print("  pip install podstock[filings]")
            return 1

    elif market == Market.SWEDEN:
        # Try to look up in Swedish IR registry
        try:
            from podstock.filings.clients.swedish_ir import SwedishIRClient

            client = SwedishIRClient()
            company = client.get_company(args.identifier)
            if company:
                if args.name:
                    company.name = args.name
                if args.ticker:
                    company.ticker = args.ticker

                storage.add_company(company)
                console.print(f"[green]Added Swedish company:[/green] {company.name} ({company.ticker})")
                console.print(f"  ID: {company.id}")
                return 0
            else:
                console.print(f"[red]Company not found in Swedish registry: {args.identifier}[/red]")
                console.print("List available companies with: podstock filings list-swedish")
                return 1
        except ImportError as e:
            console.print(f"[yellow]Missing dependency: {e}[/yellow]")
            console.print("Install with: pip install beautifulsoup4 lxml")
            return 1

    else:
        # Manual company creation for other markets
        from podstock.filings.clients.pdf import PDFClient

        pdf_client = PDFClient(config.filings_raw_dir)
        company = pdf_client.create_company(
            name=args.name or args.identifier,
            ticker=args.ticker,
            market=market,
        )
        storage.add_company(company)
        console.print(f"[green]Added company:[/green] {company.name}")
        console.print(f"  ID: {company.id}")
        console.print(f"  Market: {company.market.value}")
        return 0


def cmd_company_list(args: argparse.Namespace, config: Config) -> int:
    """List tracked companies."""
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    companies = storage.list_companies()

    if not companies:
        console.print("[yellow]No companies tracked yet.[/yellow]")
        console.print("Add a company with: podstock filings company-add <ticker>")
        return 0

    table = Table(title="Tracked Companies")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Ticker", style="green")
    table.add_column("Market")
    table.add_column("Filings", justify="right")

    for company in companies:
        filings = storage.list_filings(company.id)
        table.add_row(
            company.id,
            company.name,
            company.ticker or "-",
            company.market.value.upper(),
            str(len(filings)),
        )

    console.print(table)
    return 0


def cmd_company_remove(args: argparse.Namespace, config: Config) -> int:
    """Remove a company."""
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    company = storage.get_company(args.company_id)

    if not company:
        console.print(f"[red]Company not found: {args.company_id}[/red]")
        return 1

    storage.remove_company(args.company_id)
    console.print(f"[green]Removed company:[/green] {company.name}")
    return 0


def cmd_sync(args: argparse.Namespace, config: Config) -> int:
    """Sync filings from sources (EDGAR for US, IR pages for Sweden)."""
    from podstock.filings.models import FilingType, Market
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)

    # Determine companies to sync
    if args.company:
        company = storage.get_company(args.company)
        if not company:
            console.print(f"[red]Company not found: {args.company}[/red]")
            return 1
        companies = [company]
    else:
        companies = storage.list_companies()

    if not companies:
        console.print("[yellow]No companies to sync.[/yellow]")
        console.print("Add a company with: podstock filings company-add <identifier>")
        return 0

    # Determine filing types
    filing_types = None
    if args.type == "annual":
        filing_types = [FilingType.ANNUAL_REPORT]
    elif args.type == "quarterly":
        filing_types = [FilingType.QUARTERLY_REPORT]

    total_added = 0

    # Group by market
    us_companies = [c for c in companies if c.market == Market.US]
    swedish_companies = [c for c in companies if c.market == Market.SWEDEN]

    # Sync US companies via EDGAR
    if us_companies:
        try:
            from podstock.filings.clients.edgar import EdgarClient
            client = EdgarClient()

            for company in us_companies:
                console.print(f"\n[bold]Syncing {company.name} (EDGAR)...[/bold]")
                try:
                    added = _sync_company(client, company, filing_types, args.limit, storage, config)
                    total_added += added
                except Exception as e:
                    console.print(f"  [red]Error syncing: {e}[/red]")

        except ImportError:
            console.print("[yellow]edgartools not installed. Install with:[/yellow]")
            console.print("  pip install podstock[filings]")

    # Sync Swedish companies via IR pages
    if swedish_companies:
        try:
            from podstock.filings.clients.swedish_ir import SwedishIRClient
            client = SwedishIRClient()

            include_presentations = getattr(args, 'include_presentations', False)

            for company in swedish_companies:
                console.print(f"\n[bold]Syncing {company.name} (IR page)...[/bold]")
                try:
                    added = _sync_company(
                        client, company, filing_types, args.limit, storage, config,
                        include_presentations=include_presentations,
                    )
                    total_added += added
                except Exception as e:
                    console.print(f"  [red]Error syncing: {e}[/red]")

        except ImportError as e:
            console.print(f"[yellow]Missing dependency for Swedish scraping: {e}[/yellow]")
            console.print("Install with: pip install beautifulsoup4 lxml")

    console.print(f"\n[bold]Synced {total_added} new filings[/bold]")
    return 0


def _sync_company(
    client,
    company,
    filing_types,
    limit,
    storage,
    config,
    include_presentations: bool = False,
) -> int:
    """Sync filings for a single company. Returns count of added filings."""
    from podstock.filings.clients.base import FilingsClient

    added = 0
    downloaded_filings = []  # Track downloaded filings for presentation matching

    try:
        # Get filings from client
        kwargs = {}
        if hasattr(company, 'cik') and company.cik:
            kwargs['cik'] = company.cik
        if hasattr(company, 'ticker') and company.ticker:
            kwargs['ticker'] = company.ticker

        filings = client.get_filings(
            company.id,
            filing_types=filing_types,
            limit=limit,
            **kwargs,
        )

        for filing in filings:
            existing = storage.get_filing(filing.id)
            if existing:
                console.print(f"  [dim]Already have: {filing.id}[/dim]")
                downloaded_filings.append(filing)
                continue

            # Download the filing
            try:
                local_path = client.download_filing(filing, config.filings_raw_dir / company.id)
                filing.local_path = str(local_path.relative_to(config.filings_raw_dir))
                storage.add_filing(filing)
                console.print(f"  [green]Added: {filing.id}[/green]")
                added += 1
                downloaded_filings.append(filing)
            except Exception as e:
                console.print(f"  [red]Failed to download {filing.id}: {e}[/red]")

    except Exception as e:
        console.print(f"  [red]Error getting filings: {e}[/red]")

    # Download presentations if requested (Swedish companies only)
    if include_presentations and hasattr(client, 'get_presentations'):
        _sync_presentations(client, company, downloaded_filings, storage, config)

    return added


def _sync_presentations(client, company, filings, storage, config) -> None:
    """Sync presentations for a company, linking to existing filings."""
    console.print(f"  [dim]Looking for presentations...[/dim]")

    try:
        presentations = client.get_presentations(company.id, limit=10)

        if not presentations:
            console.print(f"  [dim]No presentations found[/dim]")
            return

        linked_count = 0
        skipped_count = 0

        for pres, linked_filing_id in presentations:
            # Only download if we have an exact match
            if linked_filing_id is None:
                skipped_count += 1
                continue

            # Check if we already have this presentation
            pres_id = f"{company.id}-presentation-{pres.year}"
            if pres.quarter:
                pres_id += f"-q{pres.quarter}"

            existing = storage.get_presentation(pres_id)
            if existing:
                console.print(f"    [dim]Already have: {pres_id}[/dim]")
                continue

            # Download the presentation
            try:
                local_path = client.download_presentation(
                    pres,
                    storage.presentations_dir / company.id,
                    company.id,
                )
                relative_path = str(local_path.relative_to(storage.presentations_dir))

                # Save metadata
                storage.save_presentation_metadata(
                    company_id=company.id,
                    url=pres.url,
                    title=pres.title,
                    year=pres.year,
                    quarter=pres.quarter,
                    linked_filing_id=linked_filing_id,
                    local_path=relative_path,
                )

                console.print(f"    [green]Presentation: {pres_id} -> {linked_filing_id}[/green]")
                linked_count += 1

            except Exception as e:
                console.print(f"    [red]Failed to download presentation: {e}[/red]")

        if skipped_count > 0:
            console.print(f"    [yellow]Skipped {skipped_count} unlinked presentations[/yellow]")
        if linked_count > 0:
            console.print(f"    [bold]Downloaded {linked_count} presentations[/bold]")

    except Exception as e:
        console.print(f"  [red]Error syncing presentations: {e}[/red]")


def cmd_import(args: argparse.Namespace, config: Config) -> int:
    """Import a local PDF."""
    from podstock.filings.clients.pdf import PDFClient
    from podstock.filings.models import FilingType
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)

    # Check company exists
    company = storage.get_company(args.company)
    if not company:
        console.print(f"[red]Company not found: {args.company}[/red]")
        console.print("Add it first with: podstock filings company-add")
        return 1

    # Check PDF exists
    if not args.pdf_path.exists():
        console.print(f"[red]PDF not found: {args.pdf_path}[/red]")
        return 1

    # Map type string to enum
    type_map = {
        "annual": FilingType.ANNUAL_REPORT,
        "quarterly": FilingType.QUARTERLY_REPORT,
        "interim": FilingType.INTERIM_REPORT,
    }
    filing_type = type_map[args.type]

    try:
        pdf_client = PDFClient(config.filings_raw_dir)
        filing = pdf_client.import_pdf(
            pdf_path=args.pdf_path,
            company_id=args.company,
            filing_type=filing_type,
            fiscal_year=args.year,
            fiscal_quarter=args.quarter,
        )

        storage.add_filing(filing)
        console.print(f"[green]Imported filing:[/green] {filing.id}")
        console.print(f"  Type: {filing.filing_type.value}")
        console.print(f"  Pages: {filing.page_count}")
        console.print(f"  Language: {filing.language}")
        return 0

    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        return 1


def cmd_list(args: argparse.Namespace, config: Config) -> int:
    """List filings."""
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    filings = storage.list_filings(args.company if hasattr(args, "company") else None)

    if args.analyzed:
        filings = [f for f in filings if f.analyzed]
    elif args.pending:
        filings = [f for f in filings if not f.analyzed]

    if not filings:
        console.print("[yellow]No filings found.[/yellow]")
        return 0

    table = Table(title="Filings")
    table.add_column("ID", style="cyan")
    table.add_column("Company")
    table.add_column("Type")
    table.add_column("Year")
    table.add_column("Source")
    table.add_column("Analyzed", justify="center")

    for filing in filings:
        table.add_row(
            filing.id,
            filing.company_id,
            filing.filing_type.value,
            f"{filing.fiscal_year}" + (f" Q{filing.fiscal_quarter}" if filing.fiscal_quarter else ""),
            filing.source.value,
            "[green]Yes[/green]" if filing.analyzed else "[dim]No[/dim]",
        )

    console.print(table)
    return 0


def cmd_list_swedish(args: argparse.Namespace, config: Config) -> int:
    """List available Swedish companies from the IR registry."""
    try:
        from podstock.filings.swedish.ir_registry import IRRegistry, MarketSegment

        registry = IRRegistry()

        # Filter by segment if specified
        if args.segment:
            segment = MarketSegment(args.segment)
            companies = registry.list_by_segment(segment)
        else:
            companies = registry.list_all()

        # Search if specified
        if args.search:
            search_results = registry.search(args.search)
            companies = search_results

        if not companies:
            console.print("[yellow]No companies found.[/yellow]")
            return 0

        table = Table(title=f"Swedish Companies ({len(companies)} available)")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Ticker", style="green")
        table.add_column("Segment")
        table.add_column("IR URL")

        for company in sorted(companies, key=lambda c: c.name):
            # Truncate URL for display
            ir_url = company.ir_url
            if len(ir_url) > 40:
                ir_url = ir_url[:37] + "..."

            table.add_row(
                company.id,
                company.name[:35] + "..." if len(company.name) > 35 else company.name,
                company.ticker,
                company.segment.value.replace("_", " ").title(),
                ir_url,
            )

        console.print(table)
        console.print(f"\n[dim]Add a company with: podstock filings company-add <id> --market sweden[/dim]")
        return 0

    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        return 1


def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """Analyze filings with LLM."""
    from podstock.filings.analysis.analyzer import FilingAnalyzer
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)

    # Determine filings to analyze
    if args.filing:
        filing = storage.get_filing(args.filing)
        if not filing:
            console.print(f"[red]Filing not found: {args.filing}[/red]")
            return 1
        filings = [filing]
    elif args.company:
        filings = storage.list_filings(args.company)
        filings = [f for f in filings if not f.analyzed][:args.max]
    else:
        filings = [f for f in storage.list_filings() if not f.analyzed][:args.max]

    if not filings:
        console.print("[yellow]No filings to analyze.[/yellow]")
        return 0

    try:
        analyzer = FilingAnalyzer(model=args.model)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("Set ANTHROPIC_API_KEY environment variable")
        return 1
    except ImportError:
        console.print("[yellow]anthropic not installed. Install with:[/yellow]")
        console.print("  pip install podstock[filings]")
        return 1

    for filing in filings:
        console.print(f"\n[bold]Analyzing {filing.id}...[/bold]")

        # Get PDF path
        if not filing.local_path:
            console.print(f"  [red]No local file for {filing.id}[/red]")
            continue

        pdf_path = config.filings_raw_dir / filing.local_path
        if not pdf_path.exists():
            console.print(f"  [red]PDF not found: {pdf_path}[/red]")
            continue

        try:
            # Run analysis
            analysis = analyzer.analyze(filing, pdf_path)
            storage.save_analysis(analysis)

            # Also extract metrics
            console.print("  Extracting metrics...")
            metrics = analyzer.extract_metrics(filing, pdf_path)
            storage.save_metrics(metrics)

            console.print(f"  [green]Analysis complete[/green]")
            console.print(f"  Chunks processed: {analysis.chunks_processed}")
            console.print(f"  Tokens used: {analysis.total_tokens_used:,}")

            # Show summary
            console.print(f"\n  [bold]Executive Summary:[/bold]")
            console.print(f"  {analysis.executive_summary[:300]}...")

        except Exception as e:
            console.print(f"  [red]Analysis failed: {e}[/red]")

    return 0


def cmd_extract(args: argparse.Namespace, config: Config) -> int:
    """Extract financial metrics."""
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    metrics = storage.load_metrics(args.filing_id)

    if not metrics:
        console.print(f"[yellow]No metrics found for {args.filing_id}[/yellow]")
        console.print("Run analysis first: podstock filings analyze --filing " + args.filing_id)
        return 1

    if args.format == "json":
        console.print(metrics.model_dump_json(indent=2))
    else:
        table = Table(title=f"Financial Metrics: {args.filing_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        # Income Statement
        table.add_section()
        table.add_row("[bold]Income Statement[/bold]", "")
        if metrics.revenue:
            table.add_row("Revenue", f"{metrics.revenue:,.0f} {metrics.currency}")
        if metrics.gross_profit:
            table.add_row("Gross Profit", f"{metrics.gross_profit:,.0f}")
        if metrics.operating_income:
            table.add_row("Operating Income", f"{metrics.operating_income:,.0f}")
        if metrics.net_income:
            table.add_row("Net Income", f"{metrics.net_income:,.0f}")
        if metrics.eps:
            table.add_row("EPS", f"{metrics.eps:.2f}")

        # Balance Sheet
        table.add_section()
        table.add_row("[bold]Balance Sheet[/bold]", "")
        if metrics.total_assets:
            table.add_row("Total Assets", f"{metrics.total_assets:,.0f}")
        if metrics.total_equity:
            table.add_row("Total Equity", f"{metrics.total_equity:,.0f}")
        if metrics.total_debt:
            table.add_row("Total Debt", f"{metrics.total_debt:,.0f}")
        if metrics.cash_and_equivalents:
            table.add_row("Cash", f"{metrics.cash_and_equivalents:,.0f}")

        # Ratios
        if any([metrics.gross_margin, metrics.net_margin, metrics.roe]):
            table.add_section()
            table.add_row("[bold]Ratios[/bold]", "")
            if metrics.gross_margin:
                table.add_row("Gross Margin", f"{metrics.gross_margin:.1%}")
            if metrics.operating_margin:
                table.add_row("Operating Margin", f"{metrics.operating_margin:.1%}")
            if metrics.net_margin:
                table.add_row("Net Margin", f"{metrics.net_margin:.1%}")
            if metrics.roe:
                table.add_row("ROE", f"{metrics.roe:.1%}")

        console.print(table)

    return 0


def cmd_show(args: argparse.Namespace, config: Config) -> int:
    """Show filing details and analysis."""
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    filing = storage.get_filing(args.filing_id)

    if not filing:
        console.print(f"[red]Filing not found: {args.filing_id}[/red]")
        return 1

    console.print(f"\n[bold]Filing: {filing.id}[/bold]")
    console.print(f"Company: {filing.company_id}")
    console.print(f"Type: {filing.filing_type.value}")
    console.print(f"Fiscal Year: {filing.fiscal_year}" + (f" Q{filing.fiscal_quarter}" if filing.fiscal_quarter else ""))
    console.print(f"Filing Date: {filing.filing_date.strftime('%Y-%m-%d')}")
    console.print(f"Source: {filing.source.value}")
    console.print(f"Pages: {filing.page_count or 'Unknown'}")
    console.print(f"Analyzed: {'Yes' if filing.analyzed else 'No'}")

    # Show analysis if available
    analysis = storage.load_analysis(args.filing_id)
    if analysis:
        console.print(f"\n[bold]Analysis[/bold]")
        console.print(f"[bold]Executive Summary:[/bold]")
        console.print(analysis.executive_summary)

        console.print(f"\n[bold]Key Highlights:[/bold]")
        for highlight in analysis.key_highlights:
            console.print(f"  - {highlight}")

        if analysis.risks_mentioned:
            console.print(f"\n[bold]Risks:[/bold]")
            for risk in analysis.risks_mentioned[:5]:
                console.print(f"  - {risk}")

        console.print(f"\n[bold]Management Tone:[/bold] {analysis.management_tone.value}")

    return 0


def cmd_status(args: argparse.Namespace, config: Config) -> int:
    """Show filings module status and overview."""
    from podstock.filings.models import Market
    from podstock.filings.storage import FilingsStorage

    storage = FilingsStorage(config)
    companies = storage.list_companies()
    filings = storage.list_filings()

    # Count by market
    us_count = len([c for c in companies if c.market == Market.US])
    sweden_count = len([c for c in companies if c.market == Market.SWEDEN])
    other_count = len(companies) - us_count - sweden_count

    # Count analyzed
    analyzed_count = len([f for f in filings if f.analyzed])
    pending_count = len(filings) - analyzed_count

    # Calculate storage size
    storage_size = 0
    pdf_count = 0
    if config.filings_raw_dir.exists():
        for pdf_file in config.filings_raw_dir.rglob("*.pdf"):
            storage_size += pdf_file.stat().st_size
            pdf_count += 1

    # Get last sync time
    state = storage.load_state()
    last_sync = state.last_sync if state else None

    # Print status
    console.print("\n[bold]Filings Status[/bold]")
    console.print("─" * 40)

    # Companies
    company_parts = []
    if us_count:
        company_parts.append(f"{us_count} US")
    if sweden_count:
        company_parts.append(f"{sweden_count} Sweden")
    if other_count:
        company_parts.append(f"{other_count} other")

    console.print(f"Companies tracked: [cyan]{len(companies)}[/cyan]" +
                  (f" ({', '.join(company_parts)})" if company_parts else ""))

    # Filings
    console.print(f"Total filings: [cyan]{len(filings)}[/cyan]")
    console.print(f"  Analyzed: [green]{analyzed_count}[/green]")
    console.print(f"  Pending: [yellow]{pending_count}[/yellow]")

    # Storage
    if storage_size > 1024 * 1024:
        size_str = f"{storage_size / (1024 * 1024):.1f} MB"
    elif storage_size > 1024:
        size_str = f"{storage_size / 1024:.1f} KB"
    else:
        size_str = f"{storage_size} bytes"

    console.print(f"Storage: [cyan]{size_str}[/cyan] ({pdf_count} PDFs)")

    # Last sync
    if last_sync:
        console.print(f"Last sync: [dim]{last_sync.strftime('%Y-%m-%d %H:%M')}[/dim]")
    else:
        console.print("Last sync: [dim]Never[/dim]")

    # Quick actions
    console.print("\n[dim]Quick actions:[/dim]")
    if not companies:
        console.print("  podstock filings company-add AAPL --market us")
        console.print("  podstock filings list-swedish")
    elif pending_count > 0:
        console.print(f"  podstock filings analyze  # Analyze {pending_count} pending filings")
    else:
        console.print("  podstock filings sync  # Check for new reports")

    return 0


def cmd_validate_urls(args: argparse.Namespace, config: Config) -> int:
    """Validate Swedish IR URLs."""
    import requests

    try:
        from podstock.filings.swedish.ir_registry import IRRegistry
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        return 1

    registry = IRRegistry()
    companies = registry.list_all()

    console.print(f"\n[bold]Validating {len(companies)} Swedish company IR URLs...[/bold]\n")

    valid_count = 0
    broken_count = 0
    broken_companies = []

    session = requests.Session()
    session.headers.update({"User-Agent": "PodStock/1.0 (URL Validator)"})

    for company in sorted(companies, key=lambda c: c.name):
        try:
            response = session.head(company.ir_url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                console.print(f"  [green]\u2713[/green] {company.id}: OK")
                valid_count += 1
            elif response.status_code in (301, 302, 307, 308):
                new_url = response.headers.get("Location", "?")
                console.print(f"  [yellow]\u2192[/yellow] {company.id}: Redirect -> {new_url}")
                valid_count += 1
            else:
                console.print(f"  [red]\u2717[/red] {company.id}: HTTP {response.status_code}")
                broken_count += 1
                broken_companies.append(company)

        except requests.exceptions.Timeout:
            console.print(f"  [red]\u2717[/red] {company.id}: Timeout")
            broken_count += 1
            broken_companies.append(company)
        except requests.exceptions.RequestException as e:
            console.print(f"  [red]\u2717[/red] {company.id}: {e.__class__.__name__}")
            broken_count += 1
            broken_companies.append(company)

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Valid: [green]{valid_count}[/green]")
    console.print(f"  Broken: [red]{broken_count}[/red]")

    if broken_companies:
        console.print(f"\n[bold]Broken URLs:[/bold]")
        for company in broken_companies:
            console.print(f"  {company.id}: {company.ir_url}")

        if args.fix:
            console.print(f"\n[bold]Attempting to find new URLs...[/bold]")
            for company in broken_companies:
                # Try common IR page patterns
                base_domain = company.ir_url.split("/")[2]
                suggestions = _suggest_ir_urls(base_domain, company.name, session)
                if suggestions:
                    console.print(f"\n  [yellow]{company.id}[/yellow]:")
                    for url in suggestions[:3]:
                        console.print(f"    {url}")
                else:
                    console.print(f"\n  [dim]{company.id}: No suggestions found[/dim]")

    return 0 if broken_count == 0 else 1


def _suggest_ir_urls(domain: str, company_name: str, session: requests.Session) -> list[str]:
    """Try to find working IR URLs for a company."""
    # Common IR URL patterns
    patterns = [
        f"https://{domain}/investors/",
        f"https://{domain}/en/investors/",
        f"https://{domain}/investor-relations/",
        f"https://{domain}/ir/",
        f"https://investors.{domain}/",
        f"https://{domain}/investors/reports/",
        f"https://{domain}/en/investors/reports/",
    ]

    valid_urls = []
    for url in patterns:
        try:
            response = session.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                valid_urls.append(url)
        except requests.exceptions.RequestException:
            continue

    return valid_urls
