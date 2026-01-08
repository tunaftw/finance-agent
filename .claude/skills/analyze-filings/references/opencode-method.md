# OpenCode/GLM-4.7 Method

Analysera filings med OpenCode CLI och GLM-4.7-modellen i en separat terminal.

## Fordelar
- Gratis (ingar i OpenCode)
- Bra for batch-korning
- Kor i bakgrunden
- **Automatisk PDF-extraktion** - scriptet extraherar PDF till markdown automatiskt

## Nackdelar
- Kraver separat terminal
- Langsammare (~5-10 min/filing)
- Mindre flexibel prompt-tuning

## Forutsattningar

1. OpenCode installerat: `/Users/pontus/.opencode/bin/opencode`
2. GLM-4.7 modell tillganglig: `opencode/glm-4.7-free`
3. pymupdf4llm installerat (for PDF-extraktion)

## Enskild analys

Kor i terminal. Bade PDF och MD accepteras (PDF extraheras automatiskt):

```bash
# Med PDF (extraheras automatiskt)
python scripts/filings_glm_driver.py \
  data/filings/raw/hove/annual-2024.pdf

# Eller med redan extraherad markdown
python scripts/filings_glm_driver.py \
  data/filings/extracted/getinge/getinge_annual_report_2024.md
```

Output:
```
  Extracting annual-2024.pdf...
  Extracted: annual-2024.md (450,000 chars)
  Analyserar: annual-2024.md (45,000 ord) [forsok 1/3]
   Extraherar sektioner...
   - CEO Letter: 1,850 ord
   - MD&A: 8,500 ord
   - Risk Factors: 4,200 ord
  Analys klar! Tokens: 15,000 in / 4,500 out
  Sparade: data/filings/analysis/hove/annual-2024.json
```

## Batch-korning

Drivern hittar automatiskt alla oanalyserade filings fran bade `raw/` (PDFs) och `extracted/` (MDs).

### Lista oanalyserade

```bash
python scripts/filings_glm_driver.py --list
```

Output:
```
PENDING FILINGS:
==================================================
  [PDF] hove/annual-2024
  [PDF] hove/quarterly-2025-h1
  [MD] getinge/quarterly-2025-q3
==================================================
Total: 3 filings
```

`[PDF]` = Behover extraheras forst, `[MD]` = Redan extraherad

### Automatisk batch

```bash
# Analysera alla oanalyserade filings for ett bolag (PDFs extraheras automatiskt)
python scripts/filings_glm_driver.py --batch hove

# Analysera alla oanalyserade filings (alla bolag)
python scripts/filings_glm_driver.py --batch-all
```

## Driver Script

`scripts/filings_glm_driver.py` gor foljande:

1. **Extraherar PDF till markdown** (om input ar PDF)
2. Laser filingen (markdown)
3. Extraherar relevanta sektioner med section finders
4. Bygger prompt med sektion-innehall
5. Anropar `opencode run --format json -m opencode/glm-4.7-free`
6. Parsear och validerar JSON-respons
7. Sparar till `data/filings/analysis/{company}/{filing_id}.json`

## Prompt-struktur

Drivern bygger en prompt som inkluderar:

```
Analysera denna finansiella rapport.

BOLAG: {company_name}
RAKNESKAPSPERIOD: {fiscal_period}
DOKUMENTTYP: {document_type}

CEO LETTER:
{ceo_section}

MD&A:
{mda_section}

RISK FACTORS:
{risk_section}

GUIDANCE:
{guidance_section}

SEGMENTS:
{segment_section}

Extrahera foljande i JSON-format:
[Schema beskrivning...]
```

## Felhantering

### Timeout
Om analysen tar for lang tid (>300s), forsoker scriptet automatiskt igen (max 3 ganger).

```
⚠️  Timeout efter 300 sekunder - forsoker igen...
```

### JSON-parsning misslyckades
Om GLM returnerar ogiltig JSON, forsoker scriptet igen.

```
⚠️  Kunde inte parsa JSON-respons - forsoker igen...
```

### Valideringsfel
Om JSON saknar obligatoriska falt:

```
⚠️  Validation error: ceo_letter missing field: tone - forsoker igen...
```

### Sektion saknas
Om en sektion inte hittas i dokumentet:

```
⚠️  Sektion 'risk_factors' hittades inte - hoppar over
```

## Output-format

Analyserna sparas i `data/filings/analysis/{company}/{filing_id}.json`.

Se [output-schema.md](output-schema.md) for fullstandigt schema.

## Tips

- Kor batch-analysen over natten for manga filings
- Kolla output-filerna regelbundet for progress
- Vid upprepade fel pa samma filing, kolla dokumentets format
- GLM-4.7 ar bra pa svenska finanstermer
- For mycket stora filings (>100k ord), overvag att dela upp i sektioner
