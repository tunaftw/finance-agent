# PodStock Rapporterings-Instruktioner

## Obligatoriskt format för rekommendationer

**Alla köp- och säljrekommendationer MÅSTE inkludera:**

1. **Direktcitat** från transkriptet (blockquote-format)
2. **Motivering** i egen sammanfattning
3. **Confidence-nivå** (high/medium/low/speculative)
4. **Timestamp** om tillgänglig

---

## Standardformat per rekommendation

```markdown
### **[Aktienamn]** - [ACTION] ([Confidence])
*[Talare] | [Podcast] | [Datum]*

> "[Exakt citat från transkriptet, max 100 ord]"

**Motivering:** [Sammanfattning av argumentet, 1-3 meningar]

**Sektor:** [tech/finans/fastigheter/etc] | **Marknad:** [sweden/us/europe]
```

---

## Exempel

### **Novo Nordisk** - BUY (Medium)
*Peter Hedlund | Börsens Finest | 2025-12-17*

> "det finns ju inte många som är såhär lite hosade nu, när kursen är såhär pressad så tycker jag ändå att det är en sån enorm marknad...nu tycker jag att mer köp än sälj"

**Motivering:** Enorm marknad inom viktminskning och diabetes. Nya applikationsområden kommer (hjärt- och kärlsjukdomar). Kursen pressad nu ger bra ingångsläge.

**Sektor:** pharma | **Marknad:** europe

---

### **Truecaller** - AVOID (High)
*John | Börsens Finest | 2025-12-17*

> "När bolagsledningen börjar hetsa mot blankarna och leta rapporter och försöka kommentera, då är ju blankarna alltid rätt...De har ju torskat 600 miljoner, vilket är 10% av bolagsvärdet, på bara återköpa alldeles för dyra aktier"

**Motivering:** Vinstvarning efter Google-algoritmändring. Ledningen jagat blankare som haft rätt. 600M förlorat på återköp. Carnegie sänkte riktkurs från 60 till 40.

**Sektor:** tech | **Marknad:** sweden

---

## Tabellformat (för översikter)

Om utrymmet är begränsat, använd tabell MEN behåll citatkolumn:

| Aktie | Action | Talare | Citat (förkortad) | Motivering |
|-------|--------|--------|-------------------|------------|
| Novo Nordisk | BUY | Peter H | "...kursen är såhär pressad...enorm marknad" | Kursen pressad, stor marknadspotential |

---

## Varför citat är viktiga

1. **Verifierbarhet** - Läsaren kan bedöma själv om analysen stämmer
2. **Kontext** - Visar talarens ton och övertygelse
3. **Transparens** - Undviker att lägga ord i munnen på talare
4. **Nyans** - Citat fångar osäkerhet och nyanser som sammanfattningar missar

---

## Checklista före publicering

- [ ] Varje BUY/SELL-rekommendation har direktcitat
- [ ] Citat är korrekt formaterade som blockquote (`>`)
- [ ] Talare och podcast är identifierade
- [ ] Confidence-nivå är angiven
- [ ] Timestamp finns om tillgänglig i transkriptet
