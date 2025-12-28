# Filings Module

Laddar ner och analyserar finansiella rapporter (årsredovisningar, kvartalsrapporter).

## Snabbstart

### 1. Lägg till bolag

```bash
# US bolag (via SEC EDGAR)
podstock filings company-add AAPL --market us

# Svenska bolag (via IR-sidor)
podstock filings list-swedish                    # Visa tillgängliga
podstock filings company-add evolution --market sweden
podstock filings company-add avanza --market sweden
```

### 2. Synka rapporter

```bash
# Synka alla bolag
podstock filings sync

# Synka specifikt bolag med begränsat antal
podstock filings sync --company evolution --limit 5
```

### 3. Lista nedladdade rapporter

```bash
podstock filings list
podstock filings list --company avanza
```

### 4. Analysera (kräver LLM API-nyckel)

```bash
podstock filings analyze --company evolution
```

## Kommandon

| Kommando | Beskrivning |
|----------|-------------|
| `company-add <id> --market <us\|sweden>` | Lägg till bolag att följa |
| `company-list` | Lista följda bolag |
| `list-swedish [--segment large-cap]` | Visa tillgängliga svenska bolag |
| `sync [--company <id>] [--limit N]` | Ladda ner nya rapporter |
| `list [--company <id>]` | Lista nedladdade rapporter |
| `analyze [--company <id>]` | Analysera rapporter med LLM |

## Filformat

### PDF-namngivning

Alla nedladdade PDFs följer formatet:
```
{company_id}_{year}_{type}[_q{quarter}][_{language}].pdf
```

**Exempel:**
- `evolution_2024_annual.pdf`
- `avanza_2024_quarterly_q2.pdf`
- `ericsson_2024_quarterly_q1_sv.pdf`

### Lagringsstruktur

```
data/filings/
├── companies.json           # Följda bolag (versionshanteras)
├── filings_state.json       # Sync-status (versionshanteras)
├── raw/                     # PDF-filer (INTE i git)
│   ├── evolution/
│   │   ├── evolution_2024_annual.pdf
│   │   └── evolution_2024_quarterly_q3.pdf
│   └── avanza/
│       └── avanza_2024_quarterly_q2.pdf
├── extracted/               # Nyckeltal JSON (versionshanteras)
│   └── evolution-annual-2024.json
└── analysis/                # LLM-analys JSON (versionshanteras)
    └── evolution-annual-2024.json
```

## Svenska bolag

Modulen stöder 25 Large Cap-bolag från Nasdaq Stockholm:

| Bolag | Ticker | IR-sida |
|-------|--------|---------|
| Evolution AB | EVO | evolution.com/investors |
| Avanza Bank | AZA | investors.avanza.se |
| Ericsson | ERIC B | ericsson.com/investors |
| H&M | HM B | hmgroup.com/investors |
| Volvo | VOLVO B | volvogroup.com/investors |
| ... | ... | ... |

### Lägg till nytt bolag

Om ett bolag saknas i registret, öppna `src/podstock/filings/swedish/ir_registry.py` och lägg till:

```python
"bolagsnamn": CompanyIRInfo(
    id="bolagsnamn",
    name="Bolagsnamn AB",
    ticker="TICKER",
    ir_url="https://bolag.se/investors/reports/",
    segment=MarketSegment.LARGE_CAP,
    report_patterns=["Annual Report", "Quarterly Report"],
),
```

## Felsökning

### "Company not in IR registry"

Bolaget finns inte i registret. Kör `podstock filings list-swedish` för att se tillgängliga bolag.

### Inga rapporter hittades

IR-sidans struktur kan ha ändrats. Kontrollera:
1. Att IR-URL:en är korrekt (besök sidan manuellt)
2. Att `report_patterns` matchar sidans rubriker
3. Kör med `--verbose` för mer loggning

### PDF-filer saknas

PDFs lagras inte i git. Kör `podstock filings sync` för att ladda ner dem igen.

## Arkitektur

```
src/podstock/filings/
├── models.py           # Pydantic-modeller (Filing, Company, etc.)
├── exceptions.py       # Fel-klasser
├── clients/
│   ├── base.py         # Abstrakt FilingsClient
│   ├── edgar.py        # SEC EDGAR (US)
│   └── swedish_ir.py   # Svenska IR-sidor
├── swedish/
│   ├── ir_registry.py  # Bolag → IR-URL mapping
│   └── ir_scraper.py   # HTML-scraping
├── pdf/
│   ├── parser.py       # PDF → Markdown (pymupdf4llm)
│   └── chunker.py      # Multi-pass chunking
└── analysis/
    └── analyzer.py     # LLM-analys
```
