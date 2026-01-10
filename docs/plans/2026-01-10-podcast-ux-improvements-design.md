# Design: Podcast UX Improvements

**Datum:** 2026-01-10
**Status:** Godkänd
**Scope:** Frontend-endast (ingen backend-ändring)

## Bakgrund

Dashboard ska delas med investeringsgrupp. Huvudfokus är podcast-analyser. Nuvarande UX har begränsningar:
- Endast single-select för podcasts
- Manuella datumfält istället för presets
- Inbox är default-vy (borde vara Podcasts)

## Ändringar

### 1. Multi-select podcast dropdown

**Nuvarande:** Single-select dropdown
**Nytt:** Dropdown med checkboxes + valda visas som chips under

```
┌──────────────────────────────────┐
│ ▼ Välj podcasts...               │
├──────────────────────────────────┤
│ 🔍 Filtrera...                   │
├──────────────────────────────────┤
│ ☑ Börspodden (142)               │
│ ☐ Avanzapodden (89)              │
│ ☑ Sparpodden (67)                │
│ ...                              │
├──────────────────────────────────┤
│ [Välj alla] [Rensa]              │
└──────────────────────────────────┘
[Börspodden ×] [Sparpodden ×]      <- Chips för valda
```

**Funktioner:**
- Sökfält i dropdown för filtrering
- Episodräknare per podcast `(142)`
- Sorterat på antal episoder (mest först)
- Chips med × för snabb borttagning
- "Välj alla" / "Rensa" knappar

**State:**
```javascript
podcastFilters: {
    sources: [],  // Array istället för string
    // ...
}
```

### 2. Datumpresets

**Nuvarande:** Två separata datumfält (från/till)
**Nytt:** Preset-knappar + valfria custom-fält

```
Period: [7d] [30d] [90d] [YTD] [Alla]    Eller: [Från ___] [Till ___]
```

**Preset-värden:**
| Knapp | Filter |
|-------|--------|
| 7d | Senaste 7 dagarna |
| 30d | Senaste 30 dagarna |
| 90d | Senaste 90 dagarna |
| YTD | Från 1 januari i år |
| Alla | Inget datumfilter (default) |

**Beteende:**
- Preset och custom är ömsesidigt uteslutande
- Klick på preset → markeras aktiv, custom rensas
- Input i custom → preset avmarkeras

**State:**
```javascript
podcastFilters: {
    datePreset: '',      // '7d', '30d', '90d', 'ytd', ''
    dateFrom: '',        // Custom, används om datePreset är tom
    dateTo: '',
    // ...
}
```

### 3. Snabbfilter

**Ny rad med preset-kombinationer:**

```
[🔥 High Conviction] [📈 Endast KÖP] [🎯 Med kursmål] [Rensa filter]
```

| Knapp | Sätter filter |
|-------|---------------|
| 🔥 High Conviction | `confidence: 'high'`, `datePreset: '30d'` |
| 📈 Endast KÖP | `action: 'buy'` |
| 🎯 Med kursmål | `hasPriceTarget: true` |
| Rensa filter | Återställer alla filter |

**Beteende:**
- Snabbfilter **behåller** podcast-val (sources)
- Snabbfilter **ersätter** övriga filter (datum, action, confidence, sökning)

### 4. Navigation

**Ändringar:**
| Före | Efter |
|------|-------|
| Default-vy: `inbox` | Default-vy: `podcast` |
| Flik-namn: "Inbox" | Flik-namn: "Alla tips" |
| Flik-namn: "Podcast" | Flik-namn: "Podcasts" |
| Header: "X recommendations" | Header: "X avsnitt" |

### 5. Ny filter-panel layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Podcasts                          Period                                │
│ ┌──────────────────────────┐      [7d] [30d] [90d] [YTD] [Alla]        │
│ │ ▼ Välj podcasts...       │                                           │
│ └──────────────────────────┘      Eller: [Från ___] [Till ___]         │
│ [Börspodden ×] [Sparpodden ×]                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ [🔍 Sök bolag...________________________]   Ägarskap: [▼ Alla]         │
├─────────────────────────────────────────────────────────────────────────┤
│ Snabbfilter:                                                            │
│ [🔥 High Conviction] [📈 Endast KÖP] [🎯 Med kursmål] [Rensa filter]   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Filer som påverkas

```
src/podstock/dashboard/
├── templates/
│   ├── index.html      # Navbar, filter-panel HTML
│   └── assets/
│       ├── app.js      # Filter-logik, multi-select state
│       └── styles.css  # Chip-styling
```

## Implementation

### Steg 1: State-ändringar (app.js)
- Ändra `podcastFilters.source` (string) → `podcastFilters.sources` (array)
- Lägg till `podcastFilters.datePreset`
- Lägg till `podcastFilters.action`, `podcastFilters.confidence`
- Uppdatera `filteredPodcastEpisodes` computed property

### Steg 2: Multi-select komponent (index.html)
- Ersätt single-select med custom dropdown
- Lägg till checkbox-lista
- Lägg till chip-rendering under dropdown

### Steg 3: Datumpresets (index.html + app.js)
- Lägg till preset-knappar
- Implementera preset → datum konvertering i filter-logik

### Steg 4: Snabbfilter (index.html + app.js)
- Lägg till snabbfilter-rad
- Implementera preset-applicering med podcast-bevarande

### Steg 5: Navigation (index.html + app.js)
- Ändra default `view: 'podcast'`
- Uppdatera navbar labels

## Framtida förbättringar (ej i scope)

- **Signalstyrka-score:** Lyfta fram starkare rekommendationer (nästa iteration)
- **Sparade filter:** Personliga filter-kombinationer i localStorage
- **Podcast-kort:** Visuell discovery av podcasts
