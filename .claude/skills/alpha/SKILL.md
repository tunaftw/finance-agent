---
name: alpha
description: Aggregera all tillgänglig data om ett bolag för att beräkna fair value med Bull/Base/Bear scenarios. Brutalt objektiv - fokuserar på pris vs värde.
---

# Alpha Extractor

Sammanställ ALL tillgänglig data om ett bolag och beräkna ett motiverat fair value.

## Quick Start

Invokera med bolagsnamn eller ticker + valfri kontext:

```
/alpha Betsson "överväger att öka position"
/alpha EVO "har i portfölj, vill uppdatera"
/alpha INVE-B "nytt case, känner inte bolaget"
```

## Kärnprinciper

- **Objektiv, inte yes-sayer** - aktivt leta efter bear-case och risker
- **Pris är allt** - fantastiskt bolag till fel pris = dålig investering
- **Konsekvent metodik** - samma ramverk oavsett bransch
- **Ärlig om begränsningar** - flagga saknad data, tvinga inte fram slutsatser

## Implementation

Se `references/workflow.md` för fullständig implementation.
