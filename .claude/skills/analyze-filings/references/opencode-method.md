# OpenCode/GLM-4.7 Method

Analysera filings med OpenCode CLI och GLM-4.7-modellen i en separat terminal.

## Fordelar
- Gratis (ingar i OpenCode)
- Bra for batch-korning
- Kor i bakgrunden

## Nackdelar
- Kraver separat terminal
- Langsammare (~5-10 min/filing)
- Mindre flexibel prompt-tuning

## Forutsattningar

1. OpenCode installerat: `/Users/pontus/.opencode/bin/opencode`
2. GLM-4.7 modell tillganglig: `opencode/glm-4.7-free`

## Enskild analys

Kor i terminal:

```bash
python scripts/filings_glm_driver.py \
  data/filings/extracted/getinge/getinge_annual_report_2024.md
```

Output:
```
📝 Analyserar: getinge_annual_report_2024.md (45,000 ord) [forsok 1/3]
   Extraherar sektioner...
   - CEO Letter: 1,850 ord
   - MD&A: 8,500 ord
   - Risk Factors: 4,200 ord
✅ Analys klar! Tokens: 15,000 in / 4,500 out
💾 Sparade: data/filings/analysis/getinge/getinge_annual_report_2024.json
```

## Batch-korning

### Automatisk batch

```bash
# Analysera alla oanalyserade filings for ett bolag
python scripts/filings_glm_driver.py --batch getinge

# Analysera alla oanalyserade filings
python scripts/filings_glm_driver.py --batch-all
```

### Manuell batch

```bash
# Hitta oanalyserade
for f in data/filings/extracted/getinge/*.md; do
  base=$(basename "$f" .md)
  if [[ ! -f "data/filings/analysis/getinge/${base}.json" ]]; then
    echo "Analyserar: $f"
    python scripts/filings_glm_driver.py "$f"
  fi
done
```

## Driver Script

`scripts/filings_glm_driver.py` gor foljande:

1. Laser filingen
2. Extraherar relevanta sektioner med section finders
3. Bygger prompt med sektion-innehall
4. Anropar `opencode run --format json -m opencode/glm-4.7-free`
5. Parsear och validerar JSON-respons
6. Sparar till `data/filings/analysis/{company}/{filing_id}.json`

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
