# Automatisk nedladdning av Apple Podcasts-transkript

## Bakgrund

Apple Podcasts lagrar transkript som TTML-filer (Timed Text Markup Language). Normalt cachas dessa endast när användaren öppnar transkriptet i Apple Podcasts-appen. Detta dokument beskriver hur du automatiskt kan ladda ner transkript utan att manuellt klicka igenom varje avsnitt.

## Metod

Vi använder verktyget [apple-podcast-transcript-downloader](https://github.com/dado3212/apple-podcast-transcript-downloader) som:
1. Använder Apples privata `AppleMediaServices.framework` för autentisering
2. Hämtar transkript direkt från Apples CDN (`podcasts.itunes.apple.com`)
3. Sparar TTML-filerna lokalt

## Krav

- **macOS 15.5 eller senare** (verktyget använder privata frameworks som ändras mellan versioner)
- Apple Podcasts installerad och inloggad med Apple ID
- Podcasten måste vara prenumererad i Apple Podcasts

## Installation

### 1. Klona FetchTranscript-verktyget

```bash
cd /tmp
git clone https://github.com/dado3212/apple-podcast-transcript-downloader
```

Binären `FetchTranscript` följer med färdigkompilerad.

### 2. Verifiera installation

```bash
/tmp/apple-podcast-transcript-downloader/FetchTranscript --help
```

## Användning

### Vårt wrapper-skript

Vi har ett Python-skript som automatiserar hela processen:

```bash
# Se vilka transkript som saknas (dry run)
python scripts/download_apple_transcripts.py --podcast "Fill or Kill" --dry-run

# Ladda ner alla saknade transkript för en podcast
python scripts/download_apple_transcripts.py --podcast "Fill or Kill"

# Ladda ner max 50 transkript med 1 sekunds fördröjning
python scripts/download_apple_transcripts.py --podcast "Börspodden" --max 50 --delay 1.0

# Ladda ner för ALLA podcasts
python scripts/download_apple_transcripts.py --all
```

### Skriptets funktioner

- Läser Apple Podcasts SQLite-databas för att hitta avsnitt med transkript
- Filtrerar bort redan cachade transkript
- Laddar ner saknade transkript med FetchTranscript
- Kopierar till rätt plats i Apple Podcasts cache (för integration med podstock)
- Visar progress och resultat

### Efter nedladdning

När transkripten är nedladdade, extrahera dem till projektformatet:

```bash
podstock transcribe --source apple --podcast fillorkill
```

## Tekniska detaljer

### Apple Podcasts databasstruktur

Databasen finns på:
```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite
```

Relevanta tabeller:
- `ZMTEPISODE` - Avsnittsinformation
- `ZMTPODCAST` - Podcastinformation

Transkript-ID finns i kolumnen `ZTRANSCRIPTIDENTIFIER` med formatet:
```
PodcastContent211/v4/xx/xx/xx/uuid/transcript_EPISODEID.ttml
```

### TTML Cache-struktur

Cachade transkript sparas på:
```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML/
```

Filnamnsformat (duplicerat av Apple):
```
transcript_1000741696914.ttml-1000741696914.ttml
```

### API-endpoint

FetchTranscript anropar:
```
https://amp-api.podcasts.apple.com/v1/catalog/us/podcast-episodes/{EPISODE_ID}/transcripts
```

Svaret innehåller `ttmlAssetUrls` med signerade CDN-URL:er.

## Felsökning

### "FetchTranscript tool not found"
```bash
cd /tmp && git clone https://github.com/dado3212/apple-podcast-transcript-downloader
```

### "Unauthorized" eller autentiseringsfel
- Kontrollera att du är inloggad i Apple Podcasts
- macOS-versionen kan vara inkompatibel (testat på 15.5+)
- Prova att köra med `--cache-bearer-token` för att cacha autentisering

### Inga transkript tillgängliga
- Inte alla podcasts har transkript (endast de med engelska/svenska transkript från Apple)
- Podcasten måste vara prenumererad i Apple Podcasts-appen

## Källor

- [apple-podcast-transcript-downloader](https://github.com/dado3212/apple-podcast-transcript-downloader)
- [Blog post: Downloading arbitrary Apple Podcast episode transcripts](https://blog.alexbeals.com/posts/downloading-arbitrary-apple-podcast-episode-transcripts)
- [Apple Podcast Transcript Viewer](https://blog.alexbeals.com/posts/apple-podcast-transcript-viewer)
