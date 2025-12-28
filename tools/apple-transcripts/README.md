# Apple Podcast Transcript Extraction

PodStock kan extrahera transkript direkt från Apple Podcasts-appen.

## Användning

### Lista tillgängliga transkript

```bash
podstock transcribe --list-apple
```

Visar alla transkript i Apple Podcasts-databasen och vilka som är cachade lokalt.

### Extrahera transkript

```bash
# Extrahera alla cachade transkript för konfigurerade podcasts
podstock transcribe --source apple

# Extrahera endast för en specifik podcast
podstock transcribe --source apple -p borspodden

# Utan timestamps
podstock transcribe --source apple --no-timestamps

# Tvinga om-extraktion
podstock transcribe --source apple --force
```

## Hur det fungerar

1. Apple Podcasts lagrar metadata om transkript i en SQLite-databas
2. TTML-filer (Timed Text Markup Language) cachas lokalt när användaren visar transkriptet i appen
3. PodStock läser databasen och extraherar cachade TTML-filer
4. Transkripten konverteras till PodStock-format med timestamps

## TTML Cache-plats

```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML/
```

## SQLite-databas

```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite
```

## Viktigt

- **Transkript måste visas i Apple Podcasts först** för att cachas lokalt
- Endast transkript för konfigurerade podcasts importeras
- Timestamps inkluderas som standard (format: `[MM:SS]` eller `[HH:MM:SS]`)

## Referens

Originalimplementation (Node.js):
https://github.com/mattdanielmurphy/apple-podcast-transcript-extractor

PodStock använder en ren Python-implementation som inte kräver Node.js.
