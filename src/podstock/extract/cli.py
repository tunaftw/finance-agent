"""Kommandoradsgränssnitt för PodStock extraction pipeline."""

import argparse
import os
import sys
from pathlib import Path


def main():
    """Huvudfunktion för CLI."""
    parser = argparse.ArgumentParser(description="PodStock Transcript Extraction")
    subparsers = parser.add_subparsers(dest="command", help="Kommandon")

    # Process command
    process_parser = subparsers.add_parser("process", help="Processa transkript")
    process_parser.add_argument(
        "--all", action="store_true", help="Processa alla väntande"
    )
    process_parser.add_argument("--file", type=str, help="Processa en specifik fil")
    process_parser.add_argument("--max", type=int, help="Max antal filer")
    process_parser.add_argument(
        "--delay", type=float, default=2.0, help="Sekunder mellan anrop"
    )
    process_parser.add_argument(
        "--podcast", type=str, help="Filtrera på podcast-namn (t.ex. 'borspodden')"
    )
    process_parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="LLM-modell: 'claude-sonnet-4-20250514' eller 'ollama:llama3.3'",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Sök i extraherad data")
    search_parser.add_argument("--stock", type=str, help="Sök på aktienamn")
    search_parser.add_argument("--recent", type=int, help="Senaste X dagar")
    search_parser.add_argument("--speaker", type=str, help="Sök på talare")
    search_parser.add_argument("--podcast", type=str, help="Sök på podcast")
    search_parser.add_argument("--sector", type=str, help="Sök på sektor")
    search_parser.add_argument(
        "--action",
        type=str,
        choices=["buy", "sell", "hold", "watch", "avoid"],
        help="Filtrera på action",
    )
    search_parser.add_argument(
        "--top", type=int, help="Visa top N mest omnämnda aktier"
    )

    # Rebuild index
    subparsers.add_parser("rebuild-index", help="Bygg om index från extraherade filer")

    # Stats
    subparsers.add_parser("stats", help="Visa statistik")

    # List files
    list_parser = subparsers.add_parser("list", help="Lista transkript-filer")
    list_parser.add_argument(
        "--pending", action="store_true", help="Visa endast väntande"
    )

    args = parser.parse_args()

    # Sökvägar
    base_dir = Path(__file__).parent.parent.parent.parent / "data"
    transcripts_dir = base_dir / "transcripts"
    extracted_dir = base_dir / "extracted"
    processing_dir = base_dir / "processing"

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if args.command == "process":
        is_ollama = args.model.startswith("ollama:")

        if not is_ollama and not api_key:
            print("Fel: ANTHROPIC_API_KEY saknas i miljövariabler")
            print("Sätt den med: export ANTHROPIC_API_KEY=din-nyckel")
            print("\nEller använd lokal modell: --model ollama:llama3.3")
            sys.exit(1)

        from .batch_runner import BatchRunner
        from .process_transcript import TranscriptProcessor

        if args.file:
            # Processa en fil
            print(f"Processar: {args.file}")
            processor = TranscriptProcessor(api_key, model=args.model)
            filepath = Path(args.file)
            if not filepath.exists():
                print(f"Fel: Filen finns inte: {filepath}")
                sys.exit(1)

            analysis = processor.process_transcript(filepath)
            output_file = processor.save_analysis(analysis, extracted_dir)
            print(f"Klar! {len(analysis.recommendations)} rekommendationer extraherade.")
            print(f"Sparad till: {output_file}")
        else:
            # Batch
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

    elif args.command == "search":
        from .search import RecommendationSearch

        try:
            search = RecommendationSearch(extracted_dir)
        except FileNotFoundError as e:
            print(f"Fel: {e}")
            print("Kör 'process' för att extrahera data först.")
            sys.exit(1)

        results = []

        if args.top:
            top_stocks = search.get_top_stocks(args.top)
            print(f"\nTop {args.top} mest omnämnda aktier:\n")
            for i, stock in enumerate(top_stocks, 1):
                latest = stock.get("latest_recommendation", {})
                latest_action = latest.get("action", "?") if latest else "?"
                print(
                    f"  {i}. {stock['name']} ({stock['mention_count']} omnämnanden, "
                    f"senast: {latest_action})"
                )
            return

        if args.stock:
            results = search.get_recommendations_for_stock(args.stock, args.action)
        elif args.recent:
            results = search.get_recent_recommendations(args.recent, args.action)
        elif args.speaker:
            results = search.search_by_speaker(args.speaker)
        elif args.podcast:
            results = search.search_by_podcast(args.podcast)
        elif args.sector:
            results = search.search_by_sector(args.sector)
        elif args.action:
            results = [r for r in search.recommendations if r["action"] == args.action]

        if results:
            print(f"\nHittade {len(results)} rekommendationer:\n")
            for r in results[:20]:  # Begränsa till 20
                print(f"  [{r['date']}] {r['stock']} - {r['action'].upper()}")
                print(f"    Podcast: {r['podcast']}")
                print(f"    Speaker: {r.get('speaker', 'Okänd')}")
                if r.get("reasoning"):
                    reasoning = r["reasoning"][:100]
                    if len(r["reasoning"]) > 100:
                        reasoning += "..."
                    print(f"    Reasoning: {reasoning}")
                print()

            if len(results) > 20:
                print(f"  ... och {len(results) - 20} till")
        else:
            print("Inga resultat hittades.")

    elif args.command == "rebuild-index":
        from .build_index import save_index

        try:
            save_index(extracted_dir)
        except ValueError as e:
            print(f"Fel: {e}")
            print("Kör 'process' för att extrahera data först.")
            sys.exit(1)

    elif args.command == "stats":
        from .search import RecommendationSearch

        try:
            search = RecommendationSearch(extracted_dir)
        except FileNotFoundError as e:
            print(f"Fel: {e}")
            print("Kör 'process' för att extrahera data först.")
            sys.exit(1)

        stats = search.get_stats()

        print("\n📊 PodStock Statistik")
        print("=" * 40)
        print(f"Totalt antal avsnitt:      {stats['total_episodes']}")
        print(f"Totalt rekommendationer:   {stats['total_recommendations']}")
        print(f"Unika aktier:              {stats['unique_stocks']}")
        print("\nPer action:")
        for action, count in stats["recommendations_by_action"].items():
            print(f"  {action}: {count}")
        print("\nPer podcast:")
        for podcast, count in stats["recommendations_by_podcast"].items():
            print(f"  {podcast}: {count}")
        print(f"\nSenast uppdaterat: {stats['last_updated']}")

    elif args.command == "list":
        from .batch_runner import BatchRunner

        # Skapa en temporär runner för att hitta filer
        runner = BatchRunner(
            api_key="dummy",  # Behövs inte för att lista
            transcripts_dir=transcripts_dir,
            output_dir=extracted_dir,
            processing_dir=processing_dir,
        )

        files = runner.find_transcripts()
        completed = runner.get_completed()

        if args.pending:
            files = [f for f in files if f.name not in completed]
            print(f"\nVäntande transkript ({len(files)} filer):\n")
        else:
            print(f"\nAlla transkript ({len(files)} filer):\n")

        for f in files[:50]:  # Begränsa till 50
            status = "✓" if f.name in completed else "○"
            print(f"  {status} {f.parent.name}/{f.name}")

        if len(files) > 50:
            print(f"\n  ... och {len(files) - 50} till")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
