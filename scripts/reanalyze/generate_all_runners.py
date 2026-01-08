#!/usr/bin/env python3
"""
Genererar runner-scripts för alla podcasts.
Stora podcasts (>50 avsnitt) delas upp i chunks.
"""

from pathlib import Path

# Podcast-data (från inventering)
PODCASTS = {
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
    "montrosepodden": 87,
    "avanzapodden": 72,
    "globalgains": 70,
    "gotttjot": 61,
    "smaspararpodden": 48,
    "borsensfinest": 37,
    "kvalitetforpengarna": 36,
    "veckanstrade": 35,
    "bullochbjorn": 33,
    "borsmagasinet": 29,
    "igborssnack": 25,
}

CHUNK_SIZE = 50
OUTPUT_DIR = Path(__file__).parent / "podcasts"

TEMPLATE = '''#!/usr/bin/env python3
"""
Runner för {podcast_name}{chunk_info}.
Genererad automatiskt - kör med: python3 {filename}
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="{podcast_id}",
        chunk={chunk_value}
    )
    runner.run()
'''


def generate_runner(podcast_id: str, chunk: tuple = None):
    """Generera en runner-fil."""
    if chunk:
        start, end = chunk
        chunk_num = (start // CHUNK_SIZE) + 1
        filename = f"run_{podcast_id}_chunk{chunk_num}.py"
        chunk_info = f" (chunk {chunk_num}: avsnitt {start+1}-{end})"
        chunk_value = f"({start}, {end})"
    else:
        filename = f"run_{podcast_id}.py"
        chunk_info = ""
        chunk_value = "None"

    content = TEMPLATE.format(
        podcast_name=podcast_id.replace("_", " ").title(),
        chunk_info=chunk_info,
        filename=filename,
        podcast_id=podcast_id,
        chunk_value=chunk_value,
    )

    output_file = OUTPUT_DIR / filename
    output_file.write_text(content)
    return filename


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = []

    for podcast, count in PODCASTS.items():
        if count == 0:
            continue

        if count > CHUNK_SIZE:
            # Dela upp i chunks
            for start in range(0, count, CHUNK_SIZE):
                end = min(start + CHUNK_SIZE, count)
                filename = generate_runner(podcast, chunk=(start, end))
                generated.append(filename)
        else:
            # En enda runner
            filename = generate_runner(podcast)
            generated.append(filename)

    print(f"✅ Genererade {len(generated)} runner-scripts i {OUTPUT_DIR}/")
    print()

    # Gruppera efter storlek
    small = [f for f in generated if "chunk" not in f]
    chunked = [f for f in generated if "chunk" in f]

    print(f"📦 Små podcasts (<50 avsnitt): {len(small)} scripts")
    for f in sorted(small):
        print(f"   {f}")

    print()
    print(f"📦 Stora podcasts (chunked): {len(chunked)} scripts")

    # Gruppera chunks per podcast
    current_podcast = None
    for f in sorted(chunked):
        podcast = f.replace("run_", "").split("_chunk")[0]
        if podcast != current_podcast:
            print(f"\n   {podcast}:")
            current_podcast = podcast
        print(f"      {f}")


if __name__ == "__main__":
    main()
