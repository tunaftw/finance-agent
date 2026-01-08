---
name: download-reports
description: Download annual and quarterly reports for a company efficiently
---

# Download Financial Reports

## When to Use

Use when user asks to:
- Download annual reports for a company
- Download quarterly/interim reports
- Get financial filings from investor relations

## Process

### Step 1: Create Output Directory

```bash
mkdir -p data/filings/raw/{company-slug}
```

### Step 2: Find Investor Relations Page

Use ONE WebSearch:
```
"{company name}" investor relations reports presentations
```

Look for URLs like:
- `company.com/investors/reports`
- `company.com/ir/financial-reports`

### Step 3: Extract ALL PDF Links (The Key Step)

Use ONE WebFetch on the investor relations page:
```
Prompt: "Extract all PDF download links for annual reports and quarterly/interim reports.
         For each, list: year, report type (annual/Q1/Q2/Q3/Q4), and full URL path.
         Focus on official company reports, not press releases."
```

This single call gets ALL links - do NOT search for individual years.

### Step 4: Download with Parallel Curl

```bash
cd data/filings/raw/{company-slug}

# Download in parallel
curl -L -o "annual-2024.pdf" "URL1" &
curl -L -o "annual-2023.pdf" "URL2" &
curl -L -o "quarterly-2024-q3.pdf" "URL3" &
# ... add all files
wait
```

Key flags:
- `-L`: Follow redirects (essential)
- `-o`: Specify output filename
- `&` and `wait`: Parallel downloads

### Step 5: Verify Downloads

```bash
file *.pdf  # Should say "PDF document"
ls -lh *.pdf  # Check sizes (real PDFs are usually >100KB)
```

If files are ~60KB and `file` shows HTML, the URL returned a redirect page.

**Unicode URL fix:** If a URL with special characters (å, ä, ö, etc.) returns 404:
- Try the decomposed Unicode form instead of precomposed
- Example: `å` can be encoded as:
  - `%C3%A5` (precomposed) - may fail
  - `a%CC%8A` (decomposed: a + combining ring) - often works
- Open the working URL in browser, copy from address bar to get correct encoding

### Step 6: Fallback Sources (if needed)

If primary source fails:

1. **annualreports.com**:
   ```
   WebFetch: https://www.annualreports.com/Company/{company-slug}
   ```

2. **Cision** (Nordic companies):
   ```
   WebSearch: site:mb.cision.com "{company}" annual report PDF
   ```

## Naming Convention

- Annual reports: `annual-YYYY.pdf`
- Quarterly reports: `quarterly-YYYY-qN.pdf`

## What NOT to Do

1. **Don't use Chrome/browser** - Disconnections, cookie popups, slow
2. **Don't search for each year separately** - Use WebFetch to get ALL links at once
3. **Don't guess URLs** - They often return HTML redirect pages
4. **Don't download without -L flag** - Many PDFs are behind redirects

## Efficiency Target

- 1 WebSearch (find IR page)
- 1 WebFetch (extract all links)
- 1-3 Bash commands (parallel downloads + verify)
- **Total: 4-6 tool calls**
