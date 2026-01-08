#!/usr/bin/env python3
"""
Generera alla podcast runner-scripts.

Skapar ett script per podcast, och chunks för stora podcasts (>100 avsnitt).
"""

from pathlib import Path

# Konfiguration
CHUNK_SIZE = 50
LARGE_PODCAST_THRESHOLD = 100

# Podcast-inventering (från vår kartläggning)
PODCASTS = {
    # Stora (>100, behöver chunks)
    "kortochlang": 536,
    "sparpodden": 442,
    "fillorkill": 400,
    "marketmakers": 337,
    "analyspodden": 335,
    "marknaden": 315,
    "borspodden": 257,
    "aktiepodden": 244,
    "kvalitetsaktiepodden": 179,
    "borsmaklarna": 118,
    "ettrikareliv": 108,

    # Medelstora (50-100)
    "montrosepodden": 87,
    "avanzapodden": 72,
    "globalgains": 70,
    "gotttjot": 61,

    # Små (<50)
    "smaspararpodden": 48,
    "borsensfinest": 37,
    "kvalitetforpengarna": 36,
    "veckanstrade": 35,
    "bullochbjorn": 33,
    "borsmagasinet": 29,
    "igborssnack": 25,
}

RUNNER_TEMPLATE = '''#!/usr/bin/env python3
"""
Re-analys runner för {podcast_display}{chunk_display}.

Kör med: python3 scripts/reanalyze/podcasts/{filename}
"""

import sys
from pathlib import Path

# Lägg till parent för import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reanalyze.runner import run_podcast

if __name__ == "__main__":
    run_podcast("{podcast_id}"{chunk_arg})
'''


def generate_runners():
    """Generera alla runner-scripts."""

    output_dir = Path(__file__).parent / "podcasts"
    output_dir.mkdir(exist_ok=True)

    generated = []

    for podcast_id, episode_count in PODCASTS.items():
        if episode_count > LARGE_PODCAST_THRESHOLD:
            # Generera chunk-runners
            num_chunks = (episode_count + CHUNK_SIZE - 1) // CHUNK_SIZE

            for chunk_idx in range(num_chunks):
                start = chunk_idx * CHUNK_SIZE
                end = min(start + CHUNK_SIZE, episode_count)

                filename = f"run_{podcast_id}_chunk{chunk_idx + 1}.py"
                chunk_display = f" (chunk {chunk_idx + 1}/{num_chunks}: {start}-{end})"
                chunk_arg = f", chunk=({start}, {end})"

                content = RUNNER_TEMPLATE.format(
                    podcast_display=podcast_id.replace("_", " ").title(),
                    chunk_display=chunk_display,
                    filename=filename,
                    podcast_id=podcast_id,
                    chunk_arg=chunk_arg
                )

                output_file = output_dir / filename
                output_file.write_text(content)
                output_file.chmod(0o755)
                generated.append(filename)

        else:
            # Generera vanlig runner
            filename = f"run_{podcast_id}.py"

            content = RUNNER_TEMPLATE.format(
                podcast_display=podcast_id.replace("_", " ").title(),
                chunk_display="",
                filename=filename,
                podcast_id=podcast_id,
                chunk_arg=""
            )

            output_file = output_dir / filename
            output_file.write_text(content)
            output_file.chmod(0o755)
            generated.append(filename)

    return generated


def main():
    print("🚀 Genererar podcast runners...")
    print()

    generated = generate_runners()

    # Gruppera output
    chunks = [f for f in generated if "chunk" in f]
    regular = [f for f in generated if "chunk" not in f]

    print(f"📁 Genererade {len(regular)} vanliga runners:")
    for f in sorted(regular):
        print(f"  - {f}")

    print()
    print(f"📁 Genererade {len(chunks)} chunk-runners (för stora podcasts):")

    # Gruppera chunks per podcast
    current_podcast = None
    for f in sorted(chunks):
        podcast = f.replace("run_", "").split("_chunk")[0]
        if podcast != current_podcast:
            current_podcast = podcast
            print(f"  {podcast}:")
        print(f"    - {f}")

    print()
    print(f"✅ Totalt: {len(generated)} runner-scripts")
    print()
    print("Kör med:")
    print("  python3 scripts/reanalyze/podcasts/run_<podcast>.py")


if __name__ == "__main__":
    main()
