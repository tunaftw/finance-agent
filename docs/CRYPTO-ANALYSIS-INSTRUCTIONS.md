# Crypto Sentiment Analysis - GLM-4.7 Batch Instructions

## Syfte

Analysera TechnicalRoundup YouTube-transkript för att extrahera crypto sentiment och price calls.

---

## Batch-info

| Fält | Värde |
|------|-------|
| **Kanal** | TechnicalRoundup |
| **Totalt transkript** | 268 |
| **Redan analyserade** | 40 |
| **Kvarstår** | **228** |
| **Uppdaterad** | 2025-12-26 20:56 |

---

## Automatiserad körning (REKOMMENDERAT)

Använd batch-runnern för helautomatiserad analys:

```bash
cd /Users/pontus/Developer/podcast-transcriber
python3 scripts/crypto_batch_runner.py

# Kör i bakgrunden:
nohup python3 scripts/crypto_batch_runner.py > crypto_batch.log 2>&1 &

# Följ progress:
tail -f crypto_batch.log
```

**Scriptet hanterar:**
- ✅ Automatisk fortsättning genom alla transkript
- ✅ Progress-tracking och resumability
- ✅ Retry vid fel (3 försök)
- ✅ Completion-log uppdatering
- ✅ Datum-lookup från `video-dates.txt`

---

## 👥 Hosts

| Host | Aliases |
|------|---------|
| **Cred** | CryptoCred, CC |
| **Duck** | Don, DonAlt, CryptoDonAlt |

**Tips för speaker-identifiering:**
- Lyssna efter namn i dialogen (t.ex. "What do you think, Don?")
- `>>` markerar talarbyte i transkriptet
- Cred är vanligtvis main host
- Duck = Don = DonAlt (samma person)

**VIKTIGT:** Varje mention MÅSTE ha korrekt `speaker`-fält!

---

## Manuell körning (alternativ)

Om du vill köra manuellt istället för batch-runnern:

### 1. Läs completion-log

```
Läs: data/crypto/technicalroundup-analysis/completion-log.json
```

Kontrollera vilka som redan finns i `completed`-arrayen.

### 2. Välj nästa transkript

Välj transkript från **Kvarvarande transkript** nedan som INTE finns i `completed`.

### 3. För varje transkript

1. Läs transkriptfilen
2. Slå upp datum i **Datum-tabellen**
3. Analysera med sentiment-prompten
4. Spara JSON
5. Uppdatera completion-log

---

## ⚠️ KRITISKT: Datum-tabell

**Använd ALLTID denna tabell för att sätta `date`-fältet.**
**GISSA ALDRIG datum!**

| Video ID | Publish Date |
|----------|--------------|
| K4XV1bEovtY | 2025-09-19 |
| F6Azi0j8A70 | 2025-07-18 |
| 6aP4PFdQies | 2025-07-11 |
| 5AXq0EWfRTU | 2025-07-04 |
| M_tWnQEGrf0 | 2025-06-27 |
| 2unMRdT0n8A | 2025-06-23 |
| UtWAUsxyOd4 | 2025-06-20 |
| qYzLy0WZL-E | 2025-06-13 |
| BEgs6dMi3SM | 2025-05-24 |
| r8QeR1Oksc0 | 2025-05-16 |
| cFY7x7Ki1Q4 | 2025-05-09 |
| GRXxCTSFqfs | 2025-03-14 |
| FO7jissnJMg | 2025-02-28 |
| sMZzb-UZTRs | 2025-02-21 |
| D9iM4JNqOr4 | 2025-02-14 |
| vT_ndxr0WJE | 2025-01-31 |
| qIuYh-zdJUA | 2025-01-24 |
| bqcec4PNHfU | 2025-01-17 |
| a3fi2YYfPy4 | 2025-01-10 |
| r5sc0PN7Dm4 | 2024-12-13 |
| FU_k-qWWUY0 | 2024-11-30 |
| leCgjHaAcYU | 2024-11-22 |
| ezk0H_VBcKE | 2024-11-15 |
| C0Nd2pGO9_0 | 2024-11-08 |
| IhonU0vEFQE | 2024-11-01 |
| LTMr8u8ESIs | 2024-10-25 |
| 6u6qdiOTNJU | 2024-10-21 |
| xr-JA8GChyY | 2024-10-20 |
| lj-eSGfgBrs | 2024-10-14 |
| uT8TW61zYlo | 2024-10-11 |
| N-5ZupdUAhw | 2024-10-07 |
| H57Q3Neqmjg | 2024-10-05 |
| owi_umOKYCU | 2024-09-30 |
| eN0uF64mX_8 | 2024-09-27 |
| qHJ-vfFyeAY | 2024-08-26 |
| byuCzFoYhEY | 2024-08-25 |
| lE0o8DPn9So | 2024-08-19 |
| QQ43xYvyXVM | 2024-08-16 |
| 0yxcjmGlYJ4 | 2024-08-02 |
| fksyqhZsM3Q | 2024-07-29 |
| A3PgcaeT5CM | 2024-07-12 |
| y1Rt_cuuec0 | 2024-07-08 |
| K2bDfWLzLuc | 2024-07-07 |
| Oa838KLBIVE | 2024-07-02 |
| q_GrjHSHTfY | 2024-06-30 |
| a-W8uJy5Fo0 | 2024-06-24 |
| bZHq3bqtbRc | 2024-06-21 |
| 5a1OPVDwITU | 2024-06-17 |
| ID_fe5OlRKc | 2024-06-14 |
| CIeM7TwMEu8 | 2024-06-10 |
| LIzYdtB_COs | 2024-06-03 |
| v1RgLyfaNu4 | 2024-05-31 |
| AwZUag5IUlc | 2024-05-10 |
| _fldUuoLkxU | 2024-05-06 |
| NcRCyHwZqT8 | 2024-05-03 |
| WXDLLhNahnc | 2024-05-02 |
| pKxijSCbXKo | 2024-04-26 |
| Tz9zwU4e6E0 | 2024-04-25 |
| o7QebRXGOEs | 2024-04-22 |
| 3MpgVzmhdsU | 2024-04-19 |
| OXk1z6Q5qyY | 2024-04-19 |
| AqCrNJly5wc | 2024-04-15 |
| 6aWnt0UnmNo | 2024-04-12 |
| VTatv54HsiA | 2024-03-25 |
| SwsEm3b4tgA | 2024-03-22 |
| OdV3ZcHGKGQ | 2024-03-21 |
| 1VKTTRZchXM | 2024-03-18 |
| j1LLsbFE2gc | 2024-03-16 |
| 9hxlYYkJjjU | 2024-03-11 |
| 3p1uG2AqmEo | 2024-03-04 |
| 1uJAsc24FMU | 2024-03-01 |
| b1dznYafbMQ | 2024-02-29 |
| 50KqhtGdyg0 | 2024-02-26 |
| 1XHQqVebiFM | 2024-02-16 |
| ycEHxpNzh4U | 2024-02-12 |
| ykxcRwQ-f38 | 2024-02-09 |
| 0NK8s4B9q7g | 2024-02-05 |
| E0eOrwR-qz4 | 2024-01-29 |
| nPx2vGJm9mY | 2024-01-26 |
| Kmoh6O_AlAU | 2024-01-22 |
| 0prCQNIDUZc | 2024-01-19 |
| dAvlgePWdo8 | 2024-01-15 |
| pajPzKs07Jo | 2024-01-12 |
| BYbqt3MYbWw | 2024-01-08 |
| IXBztsQ7VUE | 2024-01-01 |
| Z4ixXCbOOag | 2023-12-29 |
| 77n30Tmt_8k | 2023-12-22 |
| TgvxVmGSjUE | 2023-12-18 |
| Ev1PyYkiy3I | 2023-12-08 |
| j3ksAhH84Hc | 2023-12-04 |
| YPRqcEG_BD8 | 2023-12-01 |
| pEDGS1-E5aU | 2023-11-27 |
| Gd1ShaGF8q4 | 2023-11-24 |
| Qh5mhC_H8Js | 2023-11-20 |
| n9N0mfn90kI | 2023-11-17 |
| 9rWPohSjXc0 | 2023-11-13 |
| TtewAAMKC0g | 2023-11-03 |
| 6fL4NXkQmjU | 2023-10-30 |
| oCcFkjkoEcw | 2023-10-27 |
| zLH3z7OD85Y | 2023-10-23 |
| tnpQw2sHgRE | 2023-10-20 |
| K6NdLUSAuus | 2023-10-16 |
| PhJUvzeYjaw | 2023-10-13 |
| N5hWyCJ1GnQ | 2023-10-06 |
| yId__-pwTFs | 2023-10-02 |
| Rcha4X6S9Oo | 2023-09-29 |
| CwUOqfi7Te4 | 2023-09-25 |
| UX2yBqfTwss | 2023-09-22 |
| qFkozqJL35A | 2023-09-18 |
| 35K2Z8M0XIQ | 2023-09-15 |
| aVbDdPU1nTM | 2023-09-11 |
| HCQhWn1cyLw | 2023-09-04 |
| fkgWMe0l8JQ | 2023-09-03 |
| OBVMukF7FpI | 2023-08-28 |
| YCv56-NYfA8 | 2023-08-21 |
| V_x2B01BY0w | 2023-08-18 |
| 6t8M8PUPDRc | 2023-08-14 |
| mYs4YY2GZSE | 2023-08-11 |
| Zs4Ub-cezNc | 2023-08-07 |
| KZEWFew1WLI | 2023-08-04 |
| ESYDt_HTb-0 | 2023-07-31 |
| PgKuv1LR6Sc | 2023-07-28 |
| 9vIB6-6FdS0 | 2023-07-24 |
| yeRFHsZBuzM | 2023-07-21 |
| dl6L5sB0UNw | 2023-07-17 |
| r1gdz-uGtng | 2023-07-14 |
| 0_F6GnODfTs | 2023-07-10 |
| Jfa8XdnJW14 | 2023-07-07 |
| cAOw_PYWENI | 2023-06-30 |
| fETlVC7sc94 | 2023-06-26 |
| PeTikyV9YcM | 2023-06-23 |
| X2T6GTbrD0U | 2023-06-19 |
| YFmi6D-89Uo | 2023-06-16 |
| cix8Lqu4j98 | 2023-06-09 |
| f9JFM_8wyVM | 2023-06-05 |
| F4pN7s1E3ZA | 2023-06-02 |
| 386SL5xvkJA | 2023-05-29 |
| ydSGgeRqxNg | 2023-05-26 |
| oZfODoV1IjE | 2023-05-19 |
| cfxvfE4uZqM | 2023-05-18 |
| bBktTndLQiA | 2023-05-15 |
| txoDEvxUpdg | 2023-05-12 |
| yuR8stPKA8U | 2023-05-08 |
| Yw8WsbbHDVg | 2023-05-07 |
| 7ttuJSuYH8o | 2023-05-01 |
| w70bwQZst0U | 2023-03-31 |
| efGdobDdmb0 | 2023-03-27 |
| bRszhzDrwXU | 2023-03-23 |
| 4jHeq5Pi2es | 2023-03-17 |
| haATrBsJGxg | 2023-03-13 |
| SsEls5EMbCs | 2023-03-11 |
| sd2LbMSHQQw | 2023-03-09 |
| jrNS9D6vR4U | 2023-03-06 |
| YPxU_fmawns | 2023-03-03 |
| Q6bUoyRrWHE | 2023-03-02 |
| VcAv4RIPoSI | 2023-02-27 |
| eJhGS6PxiC0 | 2023-02-24 |
| 8RrCP-c6PPc | 2023-02-23 |
| l5Hxvge-Sqs | 2023-02-20 |
| D0bCxI8paxQ | 2023-02-17 |
| aBkN7VYyDlU | 2023-02-16 |
| _3swjrJqppA | 2023-02-13 |
| zJvkP852ci0 | 2023-02-06 |
| 2S24m20Gwgw | 2023-02-03 |
| WiIfoVo0pqI | 2023-02-02 |
| QwXGY9tLUKA | 2023-01-30 |
| ZNV9gs7oGaw | 2023-01-27 |
| pQq3OJU8mMk | 2023-01-23 |
| y0MNc0TJUo0 | 2023-01-21 |
| Iuytsq564EM | 2023-01-16 |
| wLkSrrVk9dQ | 2023-01-13 |
| mEohR_Ne0Js | 2023-01-09 |
| fvvy4YuGkIM | 2023-01-06 |
| fOZCxSiwOB8 | 2023-01-02 |
| HUM0l97eSjQ | 2022-12-30 |
| 2tSsv289jy8 | 2022-12-19 |
| ZxAbeWbmUZQ | 2022-12-16 |
| O7aWc1DQNyU | 2022-12-12 |
| n1IobhCfDVY | 2022-12-09 |
| NK5HOKIEgOk | 2022-12-05 |
| u2DmLIODDtY | 2022-12-02 |
| LUDUtPs158Y | 2022-11-28 |
| od8-ZG5uAAs | 2022-11-25 |
| s7yBXQgUXqM | 2022-11-21 |
| xcAC1ChGugc | 2022-11-18 |
| uBHh6jyHex8 | 2022-11-14 |
| HLrugtov50s | 2022-11-07 |
| dZgKYR9p06I | 2022-11-04 |
| XQ5CvgqhFWA | 2022-10-31 |
| VQhuNKo2-7I | 2022-10-28 |
| 41eDaeg2yws | 2022-10-24 |
| YPy9Tr-p0a0 | 2022-10-21 |
| z5vFyv-RCmk | 2022-10-17 |
| ILOK2YsULdA | 2022-10-14 |
| fx7uVl8uTS4 | 2022-10-10 |
| 1w1RIgsbzq8 | 2022-10-07 |
| Embzkepcse4 | 2022-10-03 |
| T15WJ_IS1fs | 2022-09-30 |
| 5VwX4HPWN3Q | 2022-09-26 |
| Z1NqFMpwSyA | 2022-09-23 |
| sZEM4uNgyyg | 2022-09-19 |
| vN20GXb0LxE | 2022-09-16 |
| 8LjqUBropVs | 2022-09-12 |
| My-Uvwe2bKM | 2022-09-09 |
| oAQfhhapgTw | 2022-09-05 |
| UOhlnCX0vco | 2022-09-02 |
| kCHzdT5DE6k | 2022-08-16 |
| w5OwhEqc-cE | 2022-07-29 |
| bFTaTjJ-ZpI | 2022-07-28 |
| pdFJeuoVYRQ | 2022-07-25 |
| cKnIUZcwrNk | 2022-07-18 |
| lRt6dwi76fY | 2022-07-11 |
| cezOYKSghpY | 2022-07-08 |
| ccvTFKS053M | 2022-07-04 |
| VyctpBj0qaU | 2022-07-01 |
| N0KdP70eV60 | 2022-06-20 |
| p676VSfHhHI | 2022-06-17 |
| p2hIpwHmzvo | 2022-06-13 |
| lrZSAyLmehw | 2022-06-10 |
| eRIMQItHrw4 | 2022-06-06 |
| 6uxmjHz-Qcw | 2022-06-05 |
| JH66-RTNSNI | 2022-05-30 |
| xYJAakTe6w8 | 2022-05-27 |
| 4c1H15sa3x0 | 2022-05-23 |
| SoWcqjF87kc | 2022-05-20 |
| JsNxLtLQu6A | 2022-05-16 |
| AgrmIT33ETs | 2022-05-14 |
| y-PmC72NMmI | 2022-05-09 |
| Mv0Z3OPCx2I | 2022-05-06 |
| lTS7hibdyj0 | 2022-04-30 |
| E4C5vXow0qs | 2022-04-25 |
| XEBYKAke4s0 | 2022-04-18 |
| q_W78DNQAFU | 2022-04-15 |
| 30OkajZzXBQ | 2022-04-11 |
| zf24LM8rIcY | 2022-04-08 |
| IGFhYUvXt_M | 2022-04-05 |
| Z3aSVTysaoQ | 2022-03-27 |
| hXJ35Hr75Ro | 2022-03-24 |
| iJ9KbE1REzw | 2022-03-22 |
| wPupX6yU_q4 | 2022-03-18 |
| vB1D2tr8EqQ | 2022-03-16 |
| jhnolqJgmJw | 2022-03-14 |
| G1JTFhYrvHY | 2022-03-09 |
| ze2pqhZD3Ww | 2022-03-07 |
| IZc_HuQbtvs | 2022-02-28 |
| WNsjStfdROc | 2022-02-26 |
| LTzkwIgjJNs | 2022-02-21 |
| vctox2ZWujQ | 2022-02-14 |
| eSKJrN07RmQ | 2022-02-07 |
| iTds5baQgBA | 2022-01-21 |
| H2EBMz3oji0 | 2022-01-14 |
| mO3-_CD6p8A | 2021-08-13 |
| pm1jO77IXfA | 2021-08-06 |
| 0C5avyDWnow | 2021-07-23 |
| W1_51FGJr0c | 2021-07-09 |
| nwhJHPisV88 | 2021-06-24 |
| tyG0j0TtRFc | 2021-06-18 |
| k5cnyHVOOC8 | 2021-04-16 |
| AOKlz1pJf38 | 2021-04-09 |
| P2nLgate9Nw | 2021-04-02 |
| gVdIXegS_-0 | 2021-03-26 |
| B_Ne4GGLyPY | 2021-03-19 |
| aPjYN669qb0 | 2021-03-11 |
| FkbfkXXWnyc | 2021-03-06 |
| cPmgqNEoL7E | 2020-11-01 |
| CUXvurlwzEQ | 2020-10-26 |
| 7DYlvBHVy_k | 2020-09-02 |
| -ds7GO4SrLg | 2020-08-25 |

---

## Kvarvarande transkript (228 st)

Analysera dessa i ordning. Hoppa över om redan i `completed`:

1. `data/youtube/transcripts/technicalroundup/-ds7GO4SrLg.txt` (2020-08-25)
2. `data/youtube/transcripts/technicalroundup/0C5avyDWnow.txt` (2021-07-23)
3. `data/youtube/transcripts/technicalroundup/0NK8s4B9q7g.txt` (2024-02-05)
4. `data/youtube/transcripts/technicalroundup/0_F6GnODfTs.txt` (2023-07-10)
5. `data/youtube/transcripts/technicalroundup/0prCQNIDUZc.txt` (2024-01-19)
6. `data/youtube/transcripts/technicalroundup/1VKTTRZchXM.txt` (2024-03-18)
7. `data/youtube/transcripts/technicalroundup/1XHQqVebiFM.txt` (2024-02-16)
8. `data/youtube/transcripts/technicalroundup/1uJAsc24FMU.txt` (2024-03-01)
9. `data/youtube/transcripts/technicalroundup/1w1RIgsbzq8.txt` (2022-10-07)
10. `data/youtube/transcripts/technicalroundup/2S24m20Gwgw.txt` (2023-02-03)
11. `data/youtube/transcripts/technicalroundup/2tSsv289jy8.txt` (2022-12-19)
12. `data/youtube/transcripts/technicalroundup/30OkajZzXBQ.txt` (2022-04-11)
13. `data/youtube/transcripts/technicalroundup/35K2Z8M0XIQ.txt` (2023-09-15)
14. `data/youtube/transcripts/technicalroundup/386SL5xvkJA.txt` (2023-05-29)
15. `data/youtube/transcripts/technicalroundup/3MpgVzmhdsU.txt` (2024-04-19)
16. `data/youtube/transcripts/technicalroundup/3p1uG2AqmEo.txt` (2024-03-04)
17. `data/youtube/transcripts/technicalroundup/41eDaeg2yws.txt` (2022-10-24)
18. `data/youtube/transcripts/technicalroundup/4c1H15sa3x0.txt` (2022-05-23)
19. `data/youtube/transcripts/technicalroundup/4jHeq5Pi2es.txt` (2023-03-17)
20. `data/youtube/transcripts/technicalroundup/50KqhtGdyg0.txt` (2024-02-26)
21. `data/youtube/transcripts/technicalroundup/5VwX4HPWN3Q.txt` (2022-09-26)
22. `data/youtube/transcripts/technicalroundup/5a1OPVDwITU.txt` (2024-06-17)
23. `data/youtube/transcripts/technicalroundup/6aWnt0UnmNo.txt` (2024-04-12)
24. `data/youtube/transcripts/technicalroundup/6fL4NXkQmjU.txt` (2023-10-30)
25. `data/youtube/transcripts/technicalroundup/6t8M8PUPDRc.txt` (2023-08-14)
26. `data/youtube/transcripts/technicalroundup/6uxmjHz-Qcw.txt` (2022-06-05)
27. `data/youtube/transcripts/technicalroundup/77n30Tmt_8k.txt` (2023-12-22)
28. `data/youtube/transcripts/technicalroundup/7DYlvBHVy_k.txt` (2020-09-02)
29. `data/youtube/transcripts/technicalroundup/7ttuJSuYH8o.txt` (2023-05-01)
30. `data/youtube/transcripts/technicalroundup/8LjqUBropVs.txt` (2022-09-12)
31. `data/youtube/transcripts/technicalroundup/8RrCP-c6PPc.txt` (2023-02-23)
32. `data/youtube/transcripts/technicalroundup/9hxlYYkJjjU.txt` (2024-03-11)
33. `data/youtube/transcripts/technicalroundup/9rWPohSjXc0.txt` (2023-11-13)
34. `data/youtube/transcripts/technicalroundup/9vIB6-6FdS0.txt` (2023-07-24)
35. `data/youtube/transcripts/technicalroundup/A3PgcaeT5CM.txt` (2024-07-12)
36. `data/youtube/transcripts/technicalroundup/AOKlz1pJf38.txt` (2021-04-09)
37. `data/youtube/transcripts/technicalroundup/AgrmIT33ETs.txt` (2022-05-14)
38. `data/youtube/transcripts/technicalroundup/AqCrNJly5wc.txt` (2024-04-15)
39. `data/youtube/transcripts/technicalroundup/AwZUag5IUlc.txt` (2024-05-10)
40. `data/youtube/transcripts/technicalroundup/BYbqt3MYbWw.txt` (2024-01-08)
41. `data/youtube/transcripts/technicalroundup/B_Ne4GGLyPY.txt` (2021-03-19)
42. `data/youtube/transcripts/technicalroundup/CIeM7TwMEu8.txt` (2024-06-10)
43. `data/youtube/transcripts/technicalroundup/CUXvurlwzEQ.txt` (2020-10-26)
44. `data/youtube/transcripts/technicalroundup/CwUOqfi7Te4.txt` (2023-09-25)
45. `data/youtube/transcripts/technicalroundup/D0bCxI8paxQ.txt` (2023-02-17)
46. `data/youtube/transcripts/technicalroundup/E0eOrwR-qz4.txt` (2024-01-29)
47. `data/youtube/transcripts/technicalroundup/E4C5vXow0qs.txt` (2022-04-25)
48. `data/youtube/transcripts/technicalroundup/ESYDt_HTb-0.txt` (2023-07-31)
49. `data/youtube/transcripts/technicalroundup/Embzkepcse4.txt` (2022-10-03)
50. `data/youtube/transcripts/technicalroundup/Ev1PyYkiy3I.txt` (2023-12-08)
51. `data/youtube/transcripts/technicalroundup/F4pN7s1E3ZA.txt` (2023-06-02)
52. `data/youtube/transcripts/technicalroundup/FkbfkXXWnyc.txt` (2021-03-06)
53. `data/youtube/transcripts/technicalroundup/G1JTFhYrvHY.txt` (2022-03-09)
54. `data/youtube/transcripts/technicalroundup/Gd1ShaGF8q4.txt` (2023-11-24)
55. `data/youtube/transcripts/technicalroundup/H2EBMz3oji0.txt` (2022-01-14)
56. `data/youtube/transcripts/technicalroundup/HCQhWn1cyLw.txt` (2023-09-04)
57. `data/youtube/transcripts/technicalroundup/HLrugtov50s.txt` (2022-11-07)
58. `data/youtube/transcripts/technicalroundup/HUM0l97eSjQ.txt` (2022-12-30)
59. `data/youtube/transcripts/technicalroundup/ID_fe5OlRKc.txt` (2024-06-14)
60. `data/youtube/transcripts/technicalroundup/IGFhYUvXt_M.txt` (2022-04-05)
61. `data/youtube/transcripts/technicalroundup/ILOK2YsULdA.txt` (2022-10-14)
62. `data/youtube/transcripts/technicalroundup/IXBztsQ7VUE.txt` (2024-01-01)
63. `data/youtube/transcripts/technicalroundup/IZc_HuQbtvs.txt` (2022-02-28)
64. `data/youtube/transcripts/technicalroundup/Iuytsq564EM.txt` (2023-01-16)
65. `data/youtube/transcripts/technicalroundup/JH66-RTNSNI.txt` (2022-05-30)
66. `data/youtube/transcripts/technicalroundup/Jfa8XdnJW14.txt` (2023-07-07)
67. `data/youtube/transcripts/technicalroundup/JsNxLtLQu6A.txt` (2022-05-16)
68. `data/youtube/transcripts/technicalroundup/K2bDfWLzLuc.txt` (2024-07-07)
69. `data/youtube/transcripts/technicalroundup/K6NdLUSAuus.txt` (2023-10-16)
70. `data/youtube/transcripts/technicalroundup/KZEWFew1WLI.txt` (2023-08-04)
71. `data/youtube/transcripts/technicalroundup/Kmoh6O_AlAU.txt` (2024-01-22)
72. `data/youtube/transcripts/technicalroundup/LIzYdtB_COs.txt` (2024-06-03)
73. `data/youtube/transcripts/technicalroundup/LTzkwIgjJNs.txt` (2022-02-21)
74. `data/youtube/transcripts/technicalroundup/LUDUtPs158Y.txt` (2022-11-28)
75. `data/youtube/transcripts/technicalroundup/Mv0Z3OPCx2I.txt` (2022-05-06)
76. `data/youtube/transcripts/technicalroundup/My-Uvwe2bKM.txt` (2022-09-09)
77. `data/youtube/transcripts/technicalroundup/N0KdP70eV60.txt` (2022-06-20)
78. `data/youtube/transcripts/technicalroundup/N5hWyCJ1GnQ.txt` (2023-10-06)
79. `data/youtube/transcripts/technicalroundup/NK5HOKIEgOk.txt` (2022-12-05)
80. `data/youtube/transcripts/technicalroundup/NcRCyHwZqT8.txt` (2024-05-03)
81. `data/youtube/transcripts/technicalroundup/O7aWc1DQNyU.txt` (2022-12-12)
82. `data/youtube/transcripts/technicalroundup/OBVMukF7FpI.txt` (2023-08-28)
83. `data/youtube/transcripts/technicalroundup/OXk1z6Q5qyY.txt` (2024-04-19)
84. `data/youtube/transcripts/technicalroundup/Oa838KLBIVE.txt` (2024-07-02)
85. `data/youtube/transcripts/technicalroundup/OdV3ZcHGKGQ.txt` (2024-03-21)
86. `data/youtube/transcripts/technicalroundup/P2nLgate9Nw.txt` (2021-04-02)
87. `data/youtube/transcripts/technicalroundup/PeTikyV9YcM.txt` (2023-06-23)
88. `data/youtube/transcripts/technicalroundup/PgKuv1LR6Sc.txt` (2023-07-28)
89. `data/youtube/transcripts/technicalroundup/PhJUvzeYjaw.txt` (2023-10-13)
90. `data/youtube/transcripts/technicalroundup/Q6bUoyRrWHE.txt` (2023-03-02)
91. `data/youtube/transcripts/technicalroundup/Qh5mhC_H8Js.txt` (2023-11-20)
92. `data/youtube/transcripts/technicalroundup/QwXGY9tLUKA.txt` (2023-01-30)
93. `data/youtube/transcripts/technicalroundup/Rcha4X6S9Oo.txt` (2023-09-29)
94. `data/youtube/transcripts/technicalroundup/SoWcqjF87kc.txt` (2022-05-20)
95. `data/youtube/transcripts/technicalroundup/SsEls5EMbCs.txt` (2023-03-11)
96. `data/youtube/transcripts/technicalroundup/SwsEm3b4tgA.txt` (2024-03-22)
97. `data/youtube/transcripts/technicalroundup/T15WJ_IS1fs.txt` (2022-09-30)
98. `data/youtube/transcripts/technicalroundup/TgvxVmGSjUE.txt` (2023-12-18)
99. `data/youtube/transcripts/technicalroundup/TtewAAMKC0g.txt` (2023-11-03)
100. `data/youtube/transcripts/technicalroundup/Tz9zwU4e6E0.txt` (2024-04-25)
101. `data/youtube/transcripts/technicalroundup/UOhlnCX0vco.txt` (2022-09-02)
102. `data/youtube/transcripts/technicalroundup/UX2yBqfTwss.txt` (2023-09-22)
103. `data/youtube/transcripts/technicalroundup/VQhuNKo2-7I.txt` (2022-10-28)
104. `data/youtube/transcripts/technicalroundup/VTatv54HsiA.txt` (2024-03-25)
105. `data/youtube/transcripts/technicalroundup/V_x2B01BY0w.txt` (2023-08-18)
106. `data/youtube/transcripts/technicalroundup/VcAv4RIPoSI.txt` (2023-02-27)
107. `data/youtube/transcripts/technicalroundup/VyctpBj0qaU.txt` (2022-07-01)
108. `data/youtube/transcripts/technicalroundup/W1_51FGJr0c.txt` (2021-07-09)
109. `data/youtube/transcripts/technicalroundup/WNsjStfdROc.txt` (2022-02-26)
110. `data/youtube/transcripts/technicalroundup/WXDLLhNahnc.txt` (2024-05-02)
111. `data/youtube/transcripts/technicalroundup/WiIfoVo0pqI.txt` (2023-02-02)
112. `data/youtube/transcripts/technicalroundup/X2T6GTbrD0U.txt` (2023-06-19)
113. `data/youtube/transcripts/technicalroundup/XEBYKAke4s0.txt` (2022-04-18)
114. `data/youtube/transcripts/technicalroundup/XQ5CvgqhFWA.txt` (2022-10-31)
115. `data/youtube/transcripts/technicalroundup/YCv56-NYfA8.txt` (2023-08-21)
116. `data/youtube/transcripts/technicalroundup/YFmi6D-89Uo.txt` (2023-06-16)
117. `data/youtube/transcripts/technicalroundup/YPRqcEG_BD8.txt` (2023-12-01)
118. `data/youtube/transcripts/technicalroundup/YPxU_fmawns.txt` (2023-03-03)
119. `data/youtube/transcripts/technicalroundup/YPy9Tr-p0a0.txt` (2022-10-21)
120. `data/youtube/transcripts/technicalroundup/Yw8WsbbHDVg.txt` (2023-05-07)
121. `data/youtube/transcripts/technicalroundup/Z1NqFMpwSyA.txt` (2022-09-23)
122. `data/youtube/transcripts/technicalroundup/Z3aSVTysaoQ.txt` (2022-03-27)
123. `data/youtube/transcripts/technicalroundup/Z4ixXCbOOag.txt` (2023-12-29)
124. `data/youtube/transcripts/technicalroundup/ZNV9gs7oGaw.txt` (2023-01-27)
125. `data/youtube/transcripts/technicalroundup/Zs4Ub-cezNc.txt` (2023-08-07)
126. `data/youtube/transcripts/technicalroundup/ZxAbeWbmUZQ.txt` (2022-12-16)
127. `data/youtube/transcripts/technicalroundup/_3swjrJqppA.txt` (2023-02-13)
128. `data/youtube/transcripts/technicalroundup/_fldUuoLkxU.txt` (2024-05-06)
129. `data/youtube/transcripts/technicalroundup/a-W8uJy5Fo0.txt` (2024-06-24)
130. `data/youtube/transcripts/technicalroundup/aBkN7VYyDlU.txt` (2023-02-16)
131. `data/youtube/transcripts/technicalroundup/aPjYN669qb0.txt` (2021-03-11)
132. `data/youtube/transcripts/technicalroundup/aVbDdPU1nTM.txt` (2023-09-11)
133. `data/youtube/transcripts/technicalroundup/b1dznYafbMQ.txt` (2024-02-29)
134. `data/youtube/transcripts/technicalroundup/bBktTndLQiA.txt` (2023-05-15)
135. `data/youtube/transcripts/technicalroundup/bFTaTjJ-ZpI.txt` (2022-07-28)
136. `data/youtube/transcripts/technicalroundup/bRszhzDrwXU.txt` (2023-03-23)
137. `data/youtube/transcripts/technicalroundup/bZHq3bqtbRc.txt` (2024-06-21)
138. `data/youtube/transcripts/technicalroundup/cAOw_PYWENI.txt` (2023-06-30)
139. `data/youtube/transcripts/technicalroundup/cKnIUZcwrNk.txt` (2022-07-18)
140. `data/youtube/transcripts/technicalroundup/cPmgqNEoL7E.txt` (2020-11-01)
141. `data/youtube/transcripts/technicalroundup/ccvTFKS053M.txt` (2022-07-04)
142. `data/youtube/transcripts/technicalroundup/cezOYKSghpY.txt` (2022-07-08)
143. `data/youtube/transcripts/technicalroundup/cfxvfE4uZqM.txt` (2023-05-18)
144. `data/youtube/transcripts/technicalroundup/cix8Lqu4j98.txt` (2023-06-09)
145. `data/youtube/transcripts/technicalroundup/dAvlgePWdo8.txt` (2024-01-15)
146. `data/youtube/transcripts/technicalroundup/dZgKYR9p06I.txt` (2022-11-04)
147. `data/youtube/transcripts/technicalroundup/dl6L5sB0UNw.txt` (2023-07-17)
148. `data/youtube/transcripts/technicalroundup/eJhGS6PxiC0.txt` (2023-02-24)
149. `data/youtube/transcripts/technicalroundup/eRIMQItHrw4.txt` (2022-06-06)
150. `data/youtube/transcripts/technicalroundup/eSKJrN07RmQ.txt` (2022-02-07)
151. `data/youtube/transcripts/technicalroundup/efGdobDdmb0.txt` (2023-03-27)
152. `data/youtube/transcripts/technicalroundup/f9JFM_8wyVM.txt` (2023-06-05)
153. `data/youtube/transcripts/technicalroundup/fETlVC7sc94.txt` (2023-06-26)
154. `data/youtube/transcripts/technicalroundup/fOZCxSiwOB8.txt` (2023-01-02)
155. `data/youtube/transcripts/technicalroundup/fkgWMe0l8JQ.txt` (2023-09-03)
156. `data/youtube/transcripts/technicalroundup/fvvy4YuGkIM.txt` (2023-01-06)
157. `data/youtube/transcripts/technicalroundup/fx7uVl8uTS4.txt` (2022-10-10)
158. `data/youtube/transcripts/technicalroundup/gVdIXegS_-0.txt` (2021-03-26)
159. `data/youtube/transcripts/technicalroundup/hXJ35Hr75Ro.txt` (2022-03-24)
160. `data/youtube/transcripts/technicalroundup/haATrBsJGxg.txt` (2023-03-13)
161. `data/youtube/transcripts/technicalroundup/iJ9KbE1REzw.txt` (2022-03-22)
162. `data/youtube/transcripts/technicalroundup/iTds5baQgBA.txt` (2022-01-21)
163. `data/youtube/transcripts/technicalroundup/j1LLsbFE2gc.txt` (2024-03-16)
164. `data/youtube/transcripts/technicalroundup/j3ksAhH84Hc.txt` (2023-12-04)
165. `data/youtube/transcripts/technicalroundup/jhnolqJgmJw.txt` (2022-03-14)
166. `data/youtube/transcripts/technicalroundup/jrNS9D6vR4U.txt` (2023-03-06)
167. `data/youtube/transcripts/technicalroundup/k5cnyHVOOC8.txt` (2021-04-16)
168. `data/youtube/transcripts/technicalroundup/kCHzdT5DE6k.txt` (2022-08-16)
169. `data/youtube/transcripts/technicalroundup/l5Hxvge-Sqs.txt` (2023-02-20)
170. `data/youtube/transcripts/technicalroundup/lRt6dwi76fY.txt` (2022-07-11)
171. `data/youtube/transcripts/technicalroundup/lTS7hibdyj0.txt` (2022-04-30)
172. `data/youtube/transcripts/technicalroundup/lrZSAyLmehw.txt` (2022-06-10)
173. `data/youtube/transcripts/technicalroundup/mEohR_Ne0Js.txt` (2023-01-09)
174. `data/youtube/transcripts/technicalroundup/mO3-_CD6p8A.txt` (2021-08-13)
175. `data/youtube/transcripts/technicalroundup/mYs4YY2GZSE.txt` (2023-08-11)
176. `data/youtube/transcripts/technicalroundup/n1IobhCfDVY.txt` (2022-12-09)
177. `data/youtube/transcripts/technicalroundup/n9N0mfn90kI.txt` (2023-11-17)
178. `data/youtube/transcripts/technicalroundup/nPx2vGJm9mY.txt` (2024-01-26)
179. `data/youtube/transcripts/technicalroundup/nwhJHPisV88.txt` (2021-06-24)
180. `data/youtube/transcripts/technicalroundup/o7QebRXGOEs.txt` (2024-04-22)
181. `data/youtube/transcripts/technicalroundup/oAQfhhapgTw.txt` (2022-09-05)
182. `data/youtube/transcripts/technicalroundup/oCcFkjkoEcw.txt` (2023-10-27)
183. `data/youtube/transcripts/technicalroundup/oZfODoV1IjE.txt` (2023-05-19)
184. `data/youtube/transcripts/technicalroundup/od8-ZG5uAAs.txt` (2022-11-25)
185. `data/youtube/transcripts/technicalroundup/p2hIpwHmzvo.txt` (2022-06-13)
186. `data/youtube/transcripts/technicalroundup/p676VSfHhHI.txt` (2022-06-17)
187. `data/youtube/transcripts/technicalroundup/pEDGS1-E5aU.txt` (2023-11-27)
188. `data/youtube/transcripts/technicalroundup/pKxijSCbXKo.txt` (2024-04-26)
189. `data/youtube/transcripts/technicalroundup/pQq3OJU8mMk.txt` (2023-01-23)
190. `data/youtube/transcripts/technicalroundup/pajPzKs07Jo.txt` (2024-01-12)
191. `data/youtube/transcripts/technicalroundup/pdFJeuoVYRQ.txt` (2022-07-25)
192. `data/youtube/transcripts/technicalroundup/pm1jO77IXfA.txt` (2021-08-06)
193. `data/youtube/transcripts/technicalroundup/qFkozqJL35A.txt` (2023-09-18)
194. `data/youtube/transcripts/technicalroundup/q_GrjHSHTfY.txt` (2024-06-30)
195. `data/youtube/transcripts/technicalroundup/q_W78DNQAFU.txt` (2022-04-15)
196. `data/youtube/transcripts/technicalroundup/r1gdz-uGtng.txt` (2023-07-14)
197. `data/youtube/transcripts/technicalroundup/s7yBXQgUXqM.txt` (2022-11-21)
198. `data/youtube/transcripts/technicalroundup/sZEM4uNgyyg.txt` (2022-09-19)
199. `data/youtube/transcripts/technicalroundup/sd2LbMSHQQw.txt` (2023-03-09)
200. `data/youtube/transcripts/technicalroundup/tnpQw2sHgRE.txt` (2023-10-20)
201. `data/youtube/transcripts/technicalroundup/txoDEvxUpdg.txt` (2023-05-12)
202. `data/youtube/transcripts/technicalroundup/tyG0j0TtRFc.txt` (2021-06-18)
203. `data/youtube/transcripts/technicalroundup/u2DmLIODDtY.txt` (2022-12-02)
204. `data/youtube/transcripts/technicalroundup/uBHh6jyHex8.txt` (2022-11-14)
205. `data/youtube/transcripts/technicalroundup/v1RgLyfaNu4.txt` (2024-05-31)
206. `data/youtube/transcripts/technicalroundup/vB1D2tr8EqQ.txt` (2022-03-16)
207. `data/youtube/transcripts/technicalroundup/vN20GXb0LxE.txt` (2022-09-16)
208. `data/youtube/transcripts/technicalroundup/vctox2ZWujQ.txt` (2022-02-14)
209. `data/youtube/transcripts/technicalroundup/w5OwhEqc-cE.txt` (2022-07-29)
210. `data/youtube/transcripts/technicalroundup/w70bwQZst0U.txt` (2023-03-31)
211. `data/youtube/transcripts/technicalroundup/wLkSrrVk9dQ.txt` (2023-01-13)
212. `data/youtube/transcripts/technicalroundup/wPupX6yU_q4.txt` (2022-03-18)
213. `data/youtube/transcripts/technicalroundup/xYJAakTe6w8.txt` (2022-05-27)
214. `data/youtube/transcripts/technicalroundup/xcAC1ChGugc.txt` (2022-11-18)
215. `data/youtube/transcripts/technicalroundup/y-PmC72NMmI.txt` (2022-05-09)
216. `data/youtube/transcripts/technicalroundup/y0MNc0TJUo0.txt` (2023-01-21)
217. `data/youtube/transcripts/technicalroundup/y1Rt_cuuec0.txt` (2024-07-08)
218. `data/youtube/transcripts/technicalroundup/yId__-pwTFs.txt` (2023-10-02)
219. `data/youtube/transcripts/technicalroundup/ycEHxpNzh4U.txt` (2024-02-12)
220. `data/youtube/transcripts/technicalroundup/ydSGgeRqxNg.txt` (2023-05-26)
221. `data/youtube/transcripts/technicalroundup/yeRFHsZBuzM.txt` (2023-07-21)
222. `data/youtube/transcripts/technicalroundup/ykxcRwQ-f38.txt` (2024-02-09)
223. `data/youtube/transcripts/technicalroundup/yuR8stPKA8U.txt` (2023-05-08)
224. `data/youtube/transcripts/technicalroundup/z5vFyv-RCmk.txt` (2022-10-17)
225. `data/youtube/transcripts/technicalroundup/zJvkP852ci0.txt` (2023-02-06)
226. `data/youtube/transcripts/technicalroundup/zLH3z7OD85Y.txt` (2023-10-23)
227. `data/youtube/transcripts/technicalroundup/ze2pqhZD3Ww.txt` (2022-03-07)
228. `data/youtube/transcripts/technicalroundup/zf24LM8rIcY.txt` (2022-04-08)

---

## Analysera ett transkript

### Steg 1: Läs transkriptet + HÄMTA DATUM

1. Läs hela innehållet i transkriptfilen
2. ⚠️ **KRITISKT:** Slå upp datum i Datum-tabellen (använd video_id från filnamnet)
3. **GISSA ALDRIG datum**

### Steg 2: Analysera med följande prompt

```
You are an expert at analyzing cryptocurrency content and extracting sentiment.

Your task is to carefully analyze transcripts from crypto podcasts/videos and identify:
1. SPECIFIC crypto asset mentions (BTC, ETH, SOL, etc.)
2. The sentiment expressed (very_bullish/bullish/neutral/bearish/very_bearish)
3. Any price predictions or targets
4. The reasoning behind their views
5. Risk factors or catalysts mentioned

## IMPORTANT GUIDELINES:

### Be CONSERVATIVE with sentiment classification:
- "Could go up" or "might be interesting" = neutral (NOT bullish)
- "I'm buying more" or "accumulating" = bullish
- "DCA every week" or "adding to position" = bullish
- "Time to take profits" or "I'm selling some" = bearish
- "Don't touch this" or "stay away" = bearish
- Strong conviction language like "definitely going to moon" = very_bullish
- Panic language like "this is going to zero" = very_bearish

### Capture EXACT quotes:
- Include the actual words spoken that support your sentiment classification
- Quotes should be 1-3 sentences, max 150 words
- Include any price targets or timeline mentioned

### Note speaker knowledge:
- Set market_cap_awareness=true if they mention market cap, fully diluted valuation, tokenomics
- List specific catalysts (ETF approval, halving, upgrade, regulation, etc.)
- List risk factors they mention (regulation, competition, technical issues, etc.)

### Speaker Identification (CRITICAL):
- Each mention MUST have the correct speaker if identifiable
- Look for names mentioned in dialogue (e.g., "What do you think, Don?")
- The ">>" marker in transcripts indicates a speaker change
- Use the host information provided (Cred, Duck)
- If unsure, set speaker to "Unknown" rather than guessing

### Recommendation Classification (CRITICAL for accuracy tracking):

1. **recommendation_type** (required):
   - "active_position": Speaker states they own/are long/short
   - "entry_signal": Speaker recommends buying here
   - "exit_signal": Speaker recommends selling
   - "price_call": Price prediction without entry recommendation
   - "commentary": General sentiment, no actionable advice

2. **invalidation_price** (if mentioned):
   - The price level that would invalidate their thesis
   - "Bullish unless 108k breaks" → invalidation_price: 108000
   - If not mentioned, set to null

3. **is_new_position** (required):
   - true: This is a NEW call/trade/position
   - false: Repeating previous stance

### CRYPTO-SPECIFIC TERMINOLOGY:
Bullish: "moon", "accumulating", "DCA", "buying the dip", "undervalued", "bottom is in"
Bearish: "dead cat bounce", "exit liquidity", "top signal", "overextended", "distribution"
Neutral: "consolidation", "ranging", "wait and see", "choppy", "sideways"

## OUTPUT FORMAT:
Return ONLY valid JSON matching the schema. No markdown, no explanation.
```

### Steg 3: Spara JSON

Filnamn: `data/crypto/technicalroundup-analysis/[video_id].json`

Exempel: `K4XV1bEovtY.txt` → `K4XV1bEovtY.json`

### Steg 4: Uppdatera completion-log

Efter varje sparat transkript:

1. Läs `data/crypto/technicalroundup-analysis/completion-log.json`
2. Lägg till `[video_id].txt` i `completed`-arrayen
3. Öka `total_processed` med 1
4. Uppdatera `last_updated`
5. Spara filen

---

## JSON-schema

```json
{
  "source_id": "K4XV1bEovtY",
  "source_type": "youtube",
  "channel_or_podcast": "TechnicalRoundup",
  "date": "2025-09-19",
  "speakers": ["Cred", "Duck"],
  "main_topics": ["Bitcoin analysis", "Alt season"],
  "assets_discussed": ["BTC", "ETH", "SOL"],
  "mentions": [
    {
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin",
      "sentiment": "bullish",
      "confidence": "high",
      "speaker": "Duck",
      "timestamp": null,
      "quote": "Exact quote (max 500 chars)",
      "reasoning": "Why this sentiment",
      "price_prediction": "Going to 150k",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "market_cap_awareness": false,
      "mentioned_catalysts": ["ETF inflows"],
      "risk_factors_mentioned": ["regulation"],
      "recommendation_type": "active_position",
      "invalidation_price": 90000,
      "is_new_position": true
    }
  ],
  "overall_market_sentiment": "bullish",
  "bitcoin_dominance_view": "stable",
  "alt_season_prediction": false,
  "summary": "3-5 sentence summary",
  "key_takeaways": ["Key point 1", "Key point 2"],
  "transcript_word_count": 5000,
  "has_timestamps": true,
  "model_used": "glm-4.7"
}
```

### Schema-regler

| Fält | Värden |
|------|--------|
| sentiment | `very_bullish` \| `bullish` \| `neutral` \| `bearish` \| `very_bearish` |
| confidence | `high` \| `medium` \| `low` \| `speculative` |
| asset_type | `coin` \| `token` \| `stablecoin` \| `nft` \| `defi` |
| recommendation_type | `active_position` \| `entry_signal` \| `exit_signal` \| `price_call` \| `commentary` |
| bitcoin_dominance_view | `increasing` \| `decreasing` \| `stable` \| `not_discussed` |

---

## Completion-log format

```json
{
  "completed": ["K4XV1bEovtY.txt", "F6Azi0j8A70.txt"],
  "failed": [],
  "last_updated": "2025-12-26T21:30:00",
  "total_processed": 42,
  "notes": "40 analyzed by Claude Code, remaining for GLM-4.7"
}
```

---

## Vanliga fel att undvika

1. **Fel datum** - Använd ALLTID datum-tabellen, gissa aldrig
2. **Fel speaker** - Cred ≠ Duck, identifiera korrekt
3. **Osäker sentiment** - Var konservativ, använd "neutral" vid tveksamhet
4. **JSON-syntaxfel** - Validera JSON innan sparning
5. **Glömd completion-log** - Uppdatera ALLTID efter varje transkript

---

## Checklista per transkript (manuell körning)

- [ ] Läst transkriptet
- [ ] Slagit upp datum i tabellen
- [ ] Analyserat med prompt
- [ ] Genererat valid JSON
- [ ] Sparat till technicalroundup-analysis/
- [ ] Uppdaterat completion-log.json
