# Improvement Rules

Regler för automatisk självförbättring under orchestration-körning.

## Princip

Orchestration-skillen övervakar alla steg för kända problem. Vid upptäckt:

1. **Försök fixa automatiskt** om problemet är känt och säkert att fixa
2. **Logga förbättringen** för slutrapporten
3. **Fortsätt körningen** efter fix

## Automatiskt Fixbara Problem

### 1. Sökvägsfel i Skills

**Symptom:** FileNotFoundError eller "No such file or directory"

**Detection:**
```python
if "No such file or directory" in error_msg:
    path_match = re.search(r"'([^']+)'", error_msg)
    if path_match:
        bad_path = path_match.group(1)
```

**Fix:**
```python
def fix_path_in_skill(skill_file, bad_path, correct_path):
    content = skill_file.read_text()
    if bad_path in content:
        new_content = content.replace(bad_path, correct_path)
        skill_file.write_text(new_content)
        return True
    return False
```

**Kända sökvägsändringar:**
| Gammalt | Nytt |
|---------|------|
| `data/podcasts/raw/*/transcripts/` | `data/transcripts/*/` |
| `data/extracted/glm-batch/` | `data/podcasts/analyses-v2/` |

### 2. Saknade Podcast Mappings

**Symptom:** "Podcast not in mapping" eller okänt Apple Podcast-namn

**Detection:**
```python
if "not in mapping" in error_msg or "Unknown podcast" in error_msg:
    podcast_name = extract_podcast_name(error_msg)
```

**Fix:**
```python
def add_podcast_mapping(apple_name, suggested_id):
    mapping_file = Path("data/podcast_mapping.json")
    mapping = json.loads(mapping_file.read_text())

    # Generera ID från namn om inget föreslås
    if not suggested_id:
        suggested_id = apple_name.lower().replace(" ", "").replace("-", "")

    mapping["apple_to_id"][apple_name] = suggested_id
    mapping_file.write_text(json.dumps(mapping, indent=2, ensure_ascii=False))
    return suggested_id
```

### 3. Script-syntaxfel

**Symptom:** Script returnerar fel pga ändrad syntax eller deprecated funktioner

**Detection:**
```python
deprecated_patterns = [
    ("from podstock.db import Session", "from podstock.db.engine import get_session"),
    ("session = Session()", "session = get_session()"),
]

for old, new in deprecated_patterns:
    if old in script_content:
        # Found deprecated pattern
```

**Fix:**
```python
def fix_deprecated_code(file_path, old_pattern, new_pattern):
    content = file_path.read_text()
    if old_pattern in content:
        new_content = content.replace(old_pattern, new_pattern)
        file_path.write_text(new_content)
        return True
    return False
```

### 4. Timeout-värden

**Symptom:** Konsekvent timeout på samma steg

**Detection:**
```python
# Om samma steg timeout:ar 3 gånger i rad
if step_name in timeout_history:
    timeout_history[step_name] += 1
    if timeout_history[step_name] >= 3:
        # Timeout är för kort
```

**Fix:**
```python
def increase_timeout(skill_file, step_name, multiplier=1.5):
    content = skill_file.read_text()

    # Hitta timeout-värde för steget
    pattern = rf"{step_name}.*timeout.*=.*(\d+)"
    match = re.search(pattern, content)

    if match:
        old_value = int(match.group(1))
        new_value = int(old_value * multiplier)
        new_content = content.replace(
            match.group(0),
            match.group(0).replace(str(old_value), str(new_value))
        )
        skill_file.write_text(new_content)
        return old_value, new_value
    return None
```

## Ej Automatiskt Fixbara Problem

Dessa problem loggas för manuell åtgärd:

| Problem | Anledning |
|---------|-----------|
| Ny podcast utan tydligt ID | Behöver mänskligt beslut om namngivning |
| API-fel (Yahoo, etc.) | Extern tjänst - kan inte fixas lokalt |
| Korrupt fil | Behöver manuell undersökning |
| Git merge-konflikt | Behöver mänskligt beslut |
| Okänd feltyp | Kan inte förutsägas |

## Förbättringslogg

Alla automatiska förbättringar sparas:

```python
improvements = []

def log_improvement(skill_name, problem, fix_description):
    improvements.append({
        "timestamp": datetime.now().isoformat(),
        "skill": skill_name,
        "problem": problem,
        "fix": fix_description
    })
```

I slutrapporten:
```
SJÄLVFÖRBÄTTRINGAR
──────────────────
• analyze/SKILL.md: Uppdaterade sökväg data/extracted → data/podcasts/analyses-v2
• podcast_mapping.json: La till "Nya Podcasten" → "nyapodcasten"
• podcast-download/SKILL.md: Ökade timeout från 10 till 15 minuter
```

## Säkerhetsgränser

**Aldrig fixa automatiskt:**
- Ändringar som påverkar databasschema
- Borttagning av filer eller data
- Ändringar i .env eller credentials
- Git force push eller history rewrite

**Max antal automatiska fixar per körning:** 10

Om gränsen nås, pausa och rapportera till användaren.
