# FB Primary — Plan A: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship de data-foundation voor het FB-primary tijdperk: doctrine v0.2 gemerged, inventory-pool met intent-strength operationeel, decay-windows per niche × intent-strength, region-utility voor NL plaatsen.

**Architecture:** Data-only foundation. Geen behavior changes in bestaande pipeline — Plan B doet de wiring naar de approval-flow. Inventory leeft naast `lead_log.csv` (event-log) als "warme voorraad". `pcs.py` blijft ongewijzigd; nieuwe module `consumer/inventory.py` orkestreert inventory-CRUD en roept `pcs.append_transition` aan voor EXPIRED-transities. Nightly sweep via launchd.

**Tech Stack:** Python 3, pytest, PyYAML, CSV (geen DB), launchd (macOS) voor nightly sweep.

**Bron-spec:** `lead-radar/docs/superpowers/specs/2026-05-19-facebook-primary-source-design.md`

---

## File Structure

| Bestand | Actie | Verantwoordelijkheid |
|---------|-------|---------------------|
| `lead-radar/specs/doctrine/trust-provenance-moderation.md` | Modify | Doctrine v0.1 → v0.2 (sectie-wijzigingen + appendix-additions + changelog) |
| `lead-radar/utils/regions.py` | Create | NL plaats → (provincie, plaats) canonical lowercase mapping |
| `lead-radar/consumer/inventory.py` | Create | INVENTORY_FIELDS, ensure_inventory_csv, append_inventory_row, compute_expires_at, sweep_expired_inventory |
| `lead-radar/config.yaml` | Modify | Add `inventory:` section met decay_windows per niche × intent-strength |
| `lead-radar/run_inventory_sweep.py` | Create | CLI entry-point voor nightly expire-sweep, met `--dry-run` |
| `lead-radar/com.leadradar.inventory_sweep.plist` | Create | launchd plist voor 03:00 nightly sweep |
| `lead-radar/tests/test_regions.py` | Create | Unit tests voor region-utility |
| `lead-radar/tests/test_inventory.py` | Create | Unit tests voor INVENTORY_FIELDS, ensure_csv, append, compute_expires_at |
| `lead-radar/tests/test_inventory_sweep.py` | Create | Unit tests voor sweep_expired_inventory + CLI dry-run |

---

## Pre-flight check

- [ ] **Verify werkdirectory en tools beschikbaar**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 --version  # Expected: Python 3.10+
pytest --version   # Expected: pytest 7+
git status         # Should be on a clean branch
```

- [ ] **Maak een nieuwe branch vanaf main**

```bash
git checkout main
git pull
git checkout -b feat/fb-primary-a-foundation
```

---

## Task 1: Doctrine v0.2 bump (markdown only)

**Files:**
- Modify: `lead-radar/specs/doctrine/trust-provenance-moderation.md`

- [ ] **Step 1.1: Update frontmatter**

Vervang `version: v0.1` en `date: 2026-05-18` met `version: v0.2` en `date: 2026-05-19`. Voeg `supersedes: v0.1` toe.

```yaml
---
title: Trust, Provenance, and Moderation Doctrine
version: v0.2
date: 2026-05-19
status: frozen
namespace: doctrine
owner: lead-radar
supersedes: v0.1
---
```

- [ ] **Step 1.2: Voeg §00.0 toe — Moderation-filosofie**

Direct na het kopje `## 00. First principles` een nieuwe subsectie invoegen vóór `### 00.1`:

```markdown
### 00.0 Moderation-filosofie

Lead-radar's moderation-laag optimaliseert voor **commerciële bruikbaarheid + trust preservation**, niet voor perfecte waarheid-classificatie.

De vijand is duidelijke garbage en trust erosion — niet imperfecte categorisatie. Twee asymmetrieën:

1. **False-positives binnen de WARM-band zijn aanvaardbaar.** Een installateur die af en toe een minder scherpe WARM-lead krijgt, leert het systeem te lezen. Een installateur die geen volume krijgt, vertrekt.
2. **False-negatives die bruikbaar volume onderdrukken zijn niet aanvaardbaar.** Conservatieve filtering die echte intent weggooit kost het systeem zijn levensvatbaarheid.

Trust komt uit slimme provenance op de delivery-laag (citaat + bron + reviewer-attestation waar nodig), niet uit zware approval-bureaucratie. Multi-step approval, verplichte ≥N-karakter attestation, tweede-reviewer-gates: nee.

```

- [ ] **Step 1.3: Update §00.2 (vijf-dingen-regel)**

Aan het einde van de bestaande §00.2 sectie de volgende alinea toevoegen:

```markdown

**Resolvable URL — twee modaliteiten (v0.2):**

- (a) **Publicly resolvable:** elke lezer kan de URL openen en de oorspronkelijke post zien. Default voor Reddit, publieke FB-groepen, Marketplace, fora.
- (b) **Member-resolvable:** URL alleen toegankelijk voor leden van een specifieke community (typisch closed Facebook groups). Toegestaan onder verplichte compenserende discipline — zie §00.2.b.

```

- [ ] **Step 1.4: Voeg §00.2.b toe**

Direct na §00.2 een nieuwe subsectie:

```markdown
### 00.2.b Closed-group provenance (member-resolvable URLs)

Voor leads waarvan de bron-URL alleen voor groepsleden zichtbaar is (typisch closed Facebook groups), gelden drie compenserende disciplines:

1. **Verplichte archive-bundle bij approval** — uitgebreid in §01.3. HTML-DOM + screenshot + SHA-256 hashes. Ontbrekende bundle = fail-closed in delivery (A32).

2. **Group provenance metadata in delivery** — installateur ziet expliciet de groep-naam, ledenaantal, en een member-only disclaimer. Geen marketing-camouflage. Archive-snapshot beschikbaar op verzoek binnen 24u.

3. **Reviewer-attestation** — vrije tekst (non-empty) door de reviewer toegevoegd: "Gezien in groep X, OP is actieve groepslid." Boilerplate-detectie via weekly review-rapport, geen UI-frictie.

Alleen samen vormen deze drie disciplines een geldige provenance-modaliteit. Eén ontbreekt = lead mag NIET DELIVERED worden.

```

- [ ] **Step 1.5: Update §01.3 (archive-obligation)**

Aan het einde van §01.3 toevoegen:

```markdown

**v0.2 uitbreiding voor closed-group leads:** archive-capture bevat zowel HTML-DOM (`data/archives/<lead_id>.html`) als screenshot (`data/archives/<lead_id>.png`). SHA-256 hashes van beide worden opgenomen in `data/archives/archive_manifest.csv`. Ontbreekt één van de drie (html, png, manifest-entry) → fail-closed in delivery.

```

- [ ] **Step 1.6: Update §02.2 (uncertainty rendering)**

Aan het einde van §02.2 toevoegen:

```markdown

**v0.2 — intent-strength als geldige categorie:**

HOT en WARM zijn beide eerste-klas inventory-categorieën, niet "high quality" vs "low quality". Een WARM-lead is een lead in een eerdere koper-fase met andere conversie-economie, niet een verzwakte HOT. Demo-tool en delivery tonen beide expliciet; copy mag WARM niet presenteren als "minder waardevol".

```

- [ ] **Step 1.7: Update §02.3 (vocabulary) — vocab-lint source-class-aware**

Aan het einde van §02.3 toevoegen:

```markdown

**v0.2 — source-class-aware vocab-lint:**

Delivery-content voor leads met `source_class = burner_closed` mag NIET de termen "publieke bron", "publicly available", "openbare post" gebruiken. Dispatcher-lint (`consumer/output/dispatcher.py`) krijgt source-class-bewustzijn — zie Plan B implementatie.

```

- [ ] **Step 1.8: Voeg A32 toe aan Appendix A**

Onderaan Appendix A, na het laatste item (A31), invoegen:

```markdown
### A32 — Closed-group lead delivered zonder volledige archive-bundle

Een lead met `source_class = burner_closed` mag NOOIT DELIVERED worden als één van de archive-bundle items ontbreekt: HTML-DOM, screenshot, manifest-entry met SHA-256 hashes. Fail-closed — geen runtime override.

```

- [ ] **Step 1.9: Update Appendix B.1 — canonical terms**

In de B.1 canonical-terms lijst toevoegen:

```markdown
- **verifiable public intent** — homeowner's eigen sentence in een publicly resolvable bron (Reddit, publieke FB-groep, Marketplace, forum, page-comment). Default verifieerbaarheid-modaliteit.
- **verifiable member-witnessed intent** (v0.2) — homeowner's eigen sentence in een member-resolvable bron (closed Facebook group). Sub-categorie van verifiable intent met verplichte archive-bundle + reviewer-attestation per §00.2.b.

```

- [ ] **Step 1.10: Voeg changelog toe onderaan document**

Onderaan het hele document (na het laatste appendix-item):

```markdown
---

## Changelog

### v0.2 — 2026-05-19

Member-resolvable URL toegevoegd als geldige provenance-modaliteit voor closed Facebook groups. Drie compenserende disciplines: verplichte archive-bundle (HTML + screenshot + hash), group provenance metadata in delivery, reviewer-attestation.

Toegevoegd: §00.0 Moderation-filosofie (commerciële bruikbaarheid + trust preservation als optimaliseringsdoelen, niet perfecte waarheid). §00.2.b Closed-group provenance. §01.3 screenshot-uitbreiding. §02.2 intent-strength HOT/WARM als gelijkwaardige delivery-categorieën. §02.3 source-class-aware vocab-lint. A32 fail-closed bij missing archive-bundle. B.1 verifiable member-witnessed intent.

Geen breuk in §00.5 accountable reviewer pattern.

### v0.1 — 2026-05-18

Initiële frozen versie. Constitutionele rules, 31 anti-patterns (A1-A31), 19 canonical terms + 15 banned terms.
```

- [ ] **Step 1.11: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/specs/doctrine/trust-provenance-moderation.md
git commit -m "doctrine: bump v0.1 to v0.2 (closed-group provenance + moderation philosophy)"
```

---

## Task 2: Region utility (NL plaats → provincie + plaats)

**Files:**
- Create: `lead-radar/utils/regions.py`
- Create: `lead-radar/tests/test_regions.py`

- [ ] **Step 2.1: Schrijf falende test**

Maak `lead-radar/tests/test_regions.py`:

```python
"""Unit tests for lead-radar/utils/regions.py."""
from __future__ import annotations

import pytest

from utils.regions import normalize_region, UnknownPlaceError


class TestNormalizeRegion:
    def test_amersfoort_to_utrecht(self):
        assert normalize_region("Amersfoort") == ("utrecht", "amersfoort")

    def test_capitalization_irrelevant(self):
        assert normalize_region("AMERSFOORT") == ("utrecht", "amersfoort")
        assert normalize_region("amersfoort") == ("utrecht", "amersfoort")

    def test_whitespace_trimmed(self):
        assert normalize_region("  Amersfoort  ") == ("utrecht", "amersfoort")

    def test_den_haag_canonical(self):
        assert normalize_region("Den Haag") == ("zuid-holland", "den haag")
        assert normalize_region("'s-Gravenhage") == ("zuid-holland", "den haag")

    def test_groningen_city(self):
        assert normalize_region("Groningen") == ("groningen", "groningen")

    def test_unknown_place_raises(self):
        with pytest.raises(UnknownPlaceError):
            normalize_region("Atlantis")

    def test_empty_string_raises(self):
        with pytest.raises(UnknownPlaceError):
            normalize_region("")
```

- [ ] **Step 2.2: Run test om falen te verifiëren**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
pytest tests/test_regions.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'utils.regions'".

- [ ] **Step 2.3: Implementeer regions.py**

Maak `lead-radar/utils/regions.py`:

```python
"""NL plaats -> (provincie, plaats) canonical lowercase normalization.

Plan A foundation utility. Used by inventory pool for region indexing
and by demo-tool for scope filtering. NL-only in v1 (BE komt later).
"""
from __future__ import annotations


class UnknownPlaceError(ValueError):
    """Plaats kon niet worden gevonden in de NL-mapping."""


_PLACE_TO_PROVINCE: dict[str, tuple[str, str]] = {
    # Noord-Holland
    "amsterdam": ("noord-holland", "amsterdam"),
    "haarlem": ("noord-holland", "haarlem"),
    "alkmaar": ("noord-holland", "alkmaar"),
    "zaanstad": ("noord-holland", "zaanstad"),
    "hilversum": ("noord-holland", "hilversum"),
    # Zuid-Holland
    "rotterdam": ("zuid-holland", "rotterdam"),
    "den haag": ("zuid-holland", "den haag"),
    "'s-gravenhage": ("zuid-holland", "den haag"),
    "the hague": ("zuid-holland", "den haag"),
    "leiden": ("zuid-holland", "leiden"),
    "delft": ("zuid-holland", "delft"),
    "dordrecht": ("zuid-holland", "dordrecht"),
    "gouda": ("zuid-holland", "gouda"),
    # Utrecht
    "utrecht": ("utrecht", "utrecht"),
    "amersfoort": ("utrecht", "amersfoort"),
    "nieuwegein": ("utrecht", "nieuwegein"),
    "veenendaal": ("utrecht", "veenendaal"),
    # Noord-Brabant
    "eindhoven": ("noord-brabant", "eindhoven"),
    "tilburg": ("noord-brabant", "tilburg"),
    "breda": ("noord-brabant", "breda"),
    "den bosch": ("noord-brabant", "den bosch"),
    "'s-hertogenbosch": ("noord-brabant", "den bosch"),
    "helmond": ("noord-brabant", "helmond"),
    # Gelderland
    "arnhem": ("gelderland", "arnhem"),
    "nijmegen": ("gelderland", "nijmegen"),
    "apeldoorn": ("gelderland", "apeldoorn"),
    "ede": ("gelderland", "ede"),
    # Overijssel
    "enschede": ("overijssel", "enschede"),
    "zwolle": ("overijssel", "zwolle"),
    "deventer": ("overijssel", "deventer"),
    "hengelo": ("overijssel", "hengelo"),
    # Limburg
    "maastricht": ("limburg", "maastricht"),
    "venlo": ("limburg", "venlo"),
    "heerlen": ("limburg", "heerlen"),
    "sittard": ("limburg", "sittard"),
    # Groningen
    "groningen": ("groningen", "groningen"),
    # Friesland
    "leeuwarden": ("friesland", "leeuwarden"),
    "drachten": ("friesland", "drachten"),
    # Drenthe
    "assen": ("drenthe", "assen"),
    "emmen": ("drenthe", "emmen"),
    # Flevoland
    "almere": ("flevoland", "almere"),
    "lelystad": ("flevoland", "lelystad"),
    # Zeeland
    "middelburg": ("zeeland", "middelburg"),
    "vlissingen": ("zeeland", "vlissingen"),
}


def normalize_region(place: str) -> tuple[str, str]:
    """Resolve een plaats-string naar (provincie, plaats) canonical lowercase.

    Raises UnknownPlaceError als de plaats niet bekend is.
    """
    if not place:
        raise UnknownPlaceError("Empty place name")
    key = place.strip().lower()
    if key in _PLACE_TO_PROVINCE:
        return _PLACE_TO_PROVINCE[key]
    raise UnknownPlaceError(f"Unknown place: {place!r}")
```

- [ ] **Step 2.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_regions.py -v
```

Expected: 7 passed.

- [ ] **Step 2.5: Commit**

```bash
git add lead-radar/utils/regions.py lead-radar/tests/test_regions.py
git commit -m "feat(utils): NL plaats to (provincie, plaats) normalization"
```

---

## Task 3: Inventory module — CSV schema + ensure-helpers

**Files:**
- Create: `lead-radar/consumer/inventory.py`
- Create: `lead-radar/tests/test_inventory.py`

- [ ] **Step 3.1: Schrijf falende test**

Maak `lead-radar/tests/test_inventory.py`:

```python
"""Unit tests for lead-radar/consumer/inventory.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.inventory import INVENTORY_FIELDS, ensure_inventory_csv


class TestInventorySchema:
    def test_fields_in_correct_order(self):
        assert INVENTORY_FIELDS == [
            "lead_id",
            "niche",
            "region_nl",
            "intent_strength",
            "captured_at",
            "approved_at",
            "expires_at",
            "source_class",
            "reviewer_attestation",
            "delivered_to",
            "demo_used_at",
            "still_warm_checked_at",
        ]


class TestEnsureInventoryCSV:
    def test_creates_csv_with_header(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        result = ensure_inventory_csv(csv_path)
        assert result == csv_path
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert content.startswith(",".join(INVENTORY_FIELDS))

    def test_idempotent_on_existing_file(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        ensure_inventory_csv(csv_path)
        with csv_path.open("a", encoding="utf-8") as f:
            f.write("lead-1,warmtepomp,utrecht|amersfoort,HOT,,,,,,,,,\n")
        ensure_inventory_csv(csv_path)
        content = csv_path.read_text(encoding="utf-8")
        assert "lead-1,warmtepomp" in content
```

- [ ] **Step 3.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'consumer.inventory'".

- [ ] **Step 3.3: Implementeer inventory.py — schema + ensure-helpers**

Maak `lead-radar/consumer/inventory.py`:

```python
"""Inventory pool — warme voorraad van APPROVED leads die nog niet DELIVERED zijn.

Plan A foundation module. Houdt CSV-schema, append-helpers en
expire-sweep functies. Wordt gebruikt door Plan B's approval-flow
(console writes inventory rows) en door de nightly sweep CLI.

Inventory is geen vervanging van pcs.py's event-log; het is een
parallelle "warme voorraad" view. EXPIRED-transities worden via
pcs.append_transition naar lead_log.csv geschreven (single source
of truth voor state changes).
"""
from __future__ import annotations

import csv
from pathlib import Path


INVENTORY_FIELDS: list[str] = [
    "lead_id",
    "niche",
    "region_nl",
    "intent_strength",
    "captured_at",
    "approved_at",
    "expires_at",
    "source_class",
    "reviewer_attestation",
    "delivered_to",
    "demo_used_at",
    "still_warm_checked_at",
]


def ensure_inventory_csv(path: str | Path) -> Path:
    """Maakt lead_inventory.csv aan met de juiste header indien afwezig.

    Idempotent: bestaande bestanden worden niet aangeraakt.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
            writer.writeheader()
    return path
```

- [ ] **Step 3.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory.py -v
```

Expected: 3 passed.

- [ ] **Step 3.5: Commit**

```bash
git add lead-radar/consumer/inventory.py lead-radar/tests/test_inventory.py
git commit -m "feat(inventory): CSV schema + ensure_inventory_csv"
```

---

## Task 4: Inventory append_inventory_row

**Files:**
- Modify: `lead-radar/consumer/inventory.py`
- Modify: `lead-radar/tests/test_inventory.py`

- [ ] **Step 4.1: Schrijf falende test**

Voeg toe aan `lead-radar/tests/test_inventory.py`:

```python
from consumer.inventory import append_inventory_row


class TestAppendInventoryRow:
    def test_writes_all_fields(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        append_inventory_row(
            csv_path,
            lead_id="lead-abc",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at="2026-05-19T08:00:00+00:00",
            approved_at="2026-05-19T09:00:00+00:00",
            expires_at="2026-06-02T08:00:00+00:00",
            source_class="burner_closed",
            reviewer_attestation="Gezien in groep X",
        )
        content = csv_path.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert len(lines) == 2
        row = lines[1].split(",")
        assert row[0] == "lead-abc"
        assert row[1] == "warmtepomp"
        assert row[2] == "utrecht|amersfoort"
        assert row[3] == "HOT"
        assert row[7] == "burner_closed"
        assert row[8] == "Gezien in groep X"

    def test_default_optional_fields_empty(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        append_inventory_row(
            csv_path,
            lead_id="lead-xyz",
            niche="isolatie",
            region_nl="zuid-holland|rotterdam",
            intent_strength="WARM",
            captured_at="2026-05-19T08:00:00+00:00",
            approved_at="2026-05-19T09:00:00+00:00",
            expires_at="2026-06-30T08:00:00+00:00",
            source_class="apify_public",
        )
        content = csv_path.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        row = lines[1].split(",")
        assert row[8] == ""
        assert row[9] == ""
        assert row[10] == ""
        assert row[11] == ""

    def test_invalid_intent_strength_raises(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        with pytest.raises(ValueError, match="intent_strength"):
            append_inventory_row(
                csv_path,
                lead_id="lead-z",
                niche="warmtepomp",
                region_nl="utrecht|utrecht",
                intent_strength="LUKEWARM",
                captured_at="2026-05-19T08:00:00+00:00",
                approved_at="2026-05-19T09:00:00+00:00",
                expires_at="2026-06-02T08:00:00+00:00",
                source_class="apify_public",
            )

    def test_invalid_source_class_raises(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        with pytest.raises(ValueError, match="source_class"):
            append_inventory_row(
                csv_path,
                lead_id="lead-z",
                niche="warmtepomp",
                region_nl="utrecht|utrecht",
                intent_strength="HOT",
                captured_at="2026-05-19T08:00:00+00:00",
                approved_at="2026-05-19T09:00:00+00:00",
                expires_at="2026-06-02T08:00:00+00:00",
                source_class="reddit",
            )
```

- [ ] **Step 4.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory.py::TestAppendInventoryRow -v
```

Expected: FAIL with "ImportError: cannot import name 'append_inventory_row'".

- [ ] **Step 4.3: Implementeer append_inventory_row**

Voeg toe aan `lead-radar/consumer/inventory.py`:

```python
VALID_INTENT_STRENGTHS = frozenset({"HOT", "WARM"})
VALID_SOURCE_CLASSES = frozenset({"apify_public", "burner_closed", "paste"})


def append_inventory_row(
    path: str | Path,
    *,
    lead_id: str,
    niche: str,
    region_nl: str,
    intent_strength: str,
    captured_at: str,
    approved_at: str,
    expires_at: str,
    source_class: str,
    reviewer_attestation: str = "",
    delivered_to: str = "",
    demo_used_at: str = "",
    still_warm_checked_at: str = "",
) -> Path:
    """Append een row aan lead_inventory.csv.

    Valideert intent_strength en source_class tegen toegestane waarden.
    """
    if intent_strength not in VALID_INTENT_STRENGTHS:
        raise ValueError(
            f"intent_strength must be one of {sorted(VALID_INTENT_STRENGTHS)}, "
            f"got {intent_strength!r}"
        )
    if source_class not in VALID_SOURCE_CLASSES:
        raise ValueError(
            f"source_class must be one of {sorted(VALID_SOURCE_CLASSES)}, "
            f"got {source_class!r}"
        )

    path = ensure_inventory_csv(path)
    with Path(path).open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
        writer.writerow({
            "lead_id": lead_id,
            "niche": niche,
            "region_nl": region_nl,
            "intent_strength": intent_strength,
            "captured_at": captured_at,
            "approved_at": approved_at,
            "expires_at": expires_at,
            "source_class": source_class,
            "reviewer_attestation": reviewer_attestation,
            "delivered_to": delivered_to,
            "demo_used_at": demo_used_at,
            "still_warm_checked_at": still_warm_checked_at,
        })
    return Path(path)
```

- [ ] **Step 4.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory.py -v
```

Expected: 7 passed.

- [ ] **Step 4.5: Commit**

```bash
git add lead-radar/consumer/inventory.py lead-radar/tests/test_inventory.py
git commit -m "feat(inventory): append_inventory_row with intent/source-class validation"
```

---

## Task 5: Config inventory.decay_windows section

**Files:**
- Modify: `lead-radar/config.yaml`
- Modify: `lead-radar/consumer/inventory.py`
- Modify: `lead-radar/tests/test_inventory.py`

- [ ] **Step 5.1: Schrijf falende test**

Voeg toe aan `lead-radar/tests/test_inventory.py`:

```python
from consumer.inventory import load_decay_windows


class TestDecayWindowsConfig:
    def test_loads_windows_from_yaml(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            """
inventory:
  decay_windows:
    warmtepomp:
      HOT: 14
      WARM: 28
    isolatie:
      HOT: 21
      WARM: 42
""",
            encoding="utf-8",
        )
        windows = load_decay_windows(cfg)
        assert windows["warmtepomp"]["HOT"] == 14
        assert windows["warmtepomp"]["WARM"] == 28
        assert windows["isolatie"]["HOT"] == 21
        assert windows["isolatie"]["WARM"] == 42

    def test_missing_inventory_section_raises(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("scrapers:\n  - foo\n", encoding="utf-8")
        with pytest.raises(KeyError, match="inventory"):
            load_decay_windows(cfg)
```

- [ ] **Step 5.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory.py::TestDecayWindowsConfig -v
```

Expected: FAIL with "ImportError: cannot import name 'load_decay_windows'".

- [ ] **Step 5.3: Implementeer load_decay_windows**

Voeg toe aan `lead-radar/consumer/inventory.py`:

```python
import yaml


def load_decay_windows(config_path: str | Path) -> dict[str, dict[str, int]]:
    """Laad decay-windows uit config.yaml.

    Schema: inventory.decay_windows.<niche>.<HOT|WARM> = aantal dagen.

    Raises KeyError als de inventory sectie ontbreekt.
    """
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "inventory" not in data:
        raise KeyError("config.yaml missing 'inventory' section")
    return data["inventory"].get("decay_windows", {})
```

- [ ] **Step 5.4: Voeg inventory-sectie toe aan `lead-radar/config.yaml`**

Append onderaan `lead-radar/config.yaml`:

```yaml

# Inventory pool decay-windows per niche x intent-strength (Plan A foundation, 2026-05-19).
# HOT: acute koop-intent verliest waarde snel.
# WARM: orientatie-fase, krijgt meer ruimte.
# Aanpasbaar zonder code-deploy.
inventory:
  decay_windows:
    warmtepomp:
      HOT: 14
      WARM: 28
    airco:
      HOT: 14
      WARM: 28
    zonnepanelen:
      HOT: 14
      WARM: 28
    laadpaal:
      HOT: 14
      WARM: 28
    isolatie:
      HOT: 21
      WARM: 42
    ventilatie:
      HOT: 21
      WARM: 42
    kozijnen:
      HOT: 21
      WARM: 42
    dakwerk:
      HOT: 10
      WARM: 21
    renovatie:
      HOT: 7
      WARM: 14
    cv:
      HOT: 7
      WARM: 14
```

- [ ] **Step 5.5: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory.py -v
```

Expected: 9 passed.

- [ ] **Step 5.6: Commit**

```bash
git add lead-radar/consumer/inventory.py lead-radar/tests/test_inventory.py lead-radar/config.yaml
git commit -m "feat(config): inventory.decay_windows per niche x intent-strength"
```

---

## Task 6: compute_expires_at

**Files:**
- Modify: `lead-radar/consumer/inventory.py`
- Modify: `lead-radar/tests/test_inventory.py`

- [ ] **Step 6.1: Schrijf falende test**

Voeg toe aan `lead-radar/tests/test_inventory.py`:

```python
from datetime import datetime, timezone

from consumer.inventory import compute_expires_at


class TestComputeExpiresAt:
    def test_warmtepomp_hot_14_days(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(captured, "warmtepomp", "HOT", windows)
        assert result == datetime(2026, 6, 2, 8, 0, 0, tzinfo=timezone.utc)

    def test_isolatie_warm_42_days(self):
        windows = {"isolatie": {"HOT": 21, "WARM": 42}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(captured, "isolatie", "WARM", windows)
        assert result == datetime(2026, 6, 30, 8, 0, 0, tzinfo=timezone.utc)

    def test_unknown_niche_raises(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(KeyError, match="niche"):
            compute_expires_at(captured, "tovenarij", "HOT", windows)

    def test_unknown_intent_strength_raises(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(KeyError, match="intent_strength"):
            compute_expires_at(captured, "warmtepomp", "TEPID", windows)
```

- [ ] **Step 6.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory.py::TestComputeExpiresAt -v
```

Expected: FAIL with "ImportError: cannot import name 'compute_expires_at'".

- [ ] **Step 6.3: Implementeer compute_expires_at**

Voeg toe aan `lead-radar/consumer/inventory.py`:

```python
from datetime import datetime, timedelta


def compute_expires_at(
    captured_at: datetime,
    niche: str,
    intent_strength: str,
    decay_windows: dict[str, dict[str, int]],
) -> datetime:
    """Bereken expires_at als captured_at + decay_windows[niche][intent_strength] dagen.

    Raises KeyError als niche of intent_strength niet in decay_windows zitten.
    """
    if niche not in decay_windows:
        raise KeyError(f"niche {niche!r} not in decay_windows")
    niche_windows = decay_windows[niche]
    if intent_strength not in niche_windows:
        raise KeyError(
            f"intent_strength {intent_strength!r} not in decay_windows[{niche!r}]"
        )
    days = niche_windows[intent_strength]
    return captured_at + timedelta(days=days)
```

- [ ] **Step 6.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory.py -v
```

Expected: 13 passed.

- [ ] **Step 6.5: Commit**

```bash
git add lead-radar/consumer/inventory.py lead-radar/tests/test_inventory.py
git commit -m "feat(inventory): compute_expires_at(captured, niche, intent, windows)"
```

---

## Task 7: sweep_expired_inventory

**Files:**
- Modify: `lead-radar/consumer/inventory.py`
- Create: `lead-radar/tests/test_inventory_sweep.py`

- [ ] **Step 7.1: Schrijf falende test**

Maak `lead-radar/tests/test_inventory_sweep.py`:

```python
"""Unit tests for sweep_expired_inventory."""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from consumer.inventory import (
    append_inventory_row,
    sweep_expired_inventory,
)


@pytest.fixture
def inventory_with_rows(tmp_path: Path) -> tuple[Path, Path]:
    """Fixture: inventory met 1 overdue rij en 1 nog-binnen-window rij.
    Returns (inventory_path, lead_log_path).
    """
    inventory_path = tmp_path / "data" / "lead_inventory.csv"
    lead_log_path = tmp_path / "data" / "lead_log.csv"

    now = datetime.now(timezone.utc)
    overdue = (now - timedelta(days=1)).isoformat(timespec="seconds")
    fresh = (now + timedelta(days=14)).isoformat(timespec="seconds")

    append_inventory_row(
        inventory_path,
        lead_id="lead-overdue",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at=(now - timedelta(days=15)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(days=14)).isoformat(timespec="seconds"),
        expires_at=overdue,
        source_class="apify_public",
    )
    append_inventory_row(
        inventory_path,
        lead_id="lead-fresh",
        niche="warmtepomp",
        region_nl="utrecht|utrecht",
        intent_strength="HOT",
        captured_at=now.isoformat(timespec="seconds"),
        approved_at=now.isoformat(timespec="seconds"),
        expires_at=fresh,
        source_class="apify_public",
    )
    return inventory_path, lead_log_path


class TestSweepExpiredInventory:
    def test_writes_expired_transition_for_overdue(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        expired_ids = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert expired_ids == ["lead-overdue"]
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["lead_id"] == "lead-overdue"
        assert rows[0]["to_state"] == "EXPIRED"
        assert rows[0]["actor"] == "cron"

    def test_idempotent_skip_already_expired(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        result = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert result == []
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1

    def test_skips_already_delivered(self, tmp_path: Path):
        inventory_path = tmp_path / "data" / "lead_inventory.csv"
        lead_log_path = tmp_path / "data" / "lead_log.csv"
        now = datetime.now(timezone.utc)
        overdue = (now - timedelta(days=1)).isoformat(timespec="seconds")
        append_inventory_row(
            inventory_path,
            lead_id="lead-delivered",
            niche="warmtepomp",
            region_nl="utrecht|utrecht",
            intent_strength="HOT",
            captured_at=(now - timedelta(days=15)).isoformat(timespec="seconds"),
            approved_at=(now - timedelta(days=14)).isoformat(timespec="seconds"),
            expires_at=overdue,
            source_class="apify_public",
            delivered_to="installer-7",
        )
        result = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert result == []
```

- [ ] **Step 7.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory_sweep.py -v
```

Expected: FAIL with "ImportError: cannot import name 'sweep_expired_inventory'".

- [ ] **Step 7.3: Implementeer sweep_expired_inventory**

Voeg toe aan `lead-radar/consumer/inventory.py`:

```python
from datetime import datetime as _dt
from datetime import timezone as _tz

import pcs


def sweep_expired_inventory(
    *,
    inventory_path: str | Path,
    lead_log_path: str | Path,
    actor: str = "cron",
    now: datetime | None = None,
) -> list[str]:
    """Vind leads met expires_at < now en die nog niet DELIVERED zijn.

    Schrijft per overdue lead een EXPIRED-transitie naar lead_log_path
    via pcs.append_transition. Idempotent: als er al een EXPIRED-rij
    bestaat voor dit lead_id, wordt 'm overgeslagen.

    Returns: lijst van expired lead_ids (in volgorde).
    """
    now = now or _dt.now(_tz.utc)
    inventory_path = Path(inventory_path)
    lead_log_path = Path(lead_log_path)

    if not inventory_path.exists():
        return []

    already_expired: set[str] = set()
    if lead_log_path.exists():
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("to_state") == "EXPIRED":
                    already_expired.add(row["lead_id"])

    expired_now: list[str] = []
    with inventory_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lead_id = row["lead_id"]
            if lead_id in already_expired:
                continue
            if row.get("delivered_to"):
                continue
            expires_at_str = row.get("expires_at", "")
            if not expires_at_str:
                continue
            try:
                expires_at = _dt.fromisoformat(expires_at_str)
            except ValueError:
                continue
            if expires_at < now:
                expired_now.append(lead_id)

    for lead_id in expired_now:
        pcs.append_transition(
            lead_id,
            from_state="APPROVED",
            to_state="EXPIRED",
            actor=actor,
            reason="inventory_sweep:decay_window_passed",
            log_path=lead_log_path,
        )

    return expired_now
```

- [ ] **Step 7.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory_sweep.py -v
```

Expected: 3 passed.

- [ ] **Step 7.5: Run hele inventory test-suite voor regressies**

```bash
pytest tests/test_inventory.py tests/test_inventory_sweep.py -v
```

Expected: 16 passed.

- [ ] **Step 7.6: Commit**

```bash
git add lead-radar/consumer/inventory.py lead-radar/tests/test_inventory_sweep.py
git commit -m "feat(inventory): sweep_expired_inventory with pcs integration"
```

---

## Task 8: CLI wrapper run_inventory_sweep.py

**Files:**
- Create: `lead-radar/run_inventory_sweep.py`
- Modify: `lead-radar/tests/test_inventory_sweep.py`

- [ ] **Step 8.1: Schrijf falende test**

Voeg toe aan `lead-radar/tests/test_inventory_sweep.py`:

```python
import subprocess
import sys


class TestCLI:
    def test_dry_run_exits_zero(self, inventory_with_rows: tuple[Path, Path]):
        inventory_path, lead_log_path = inventory_with_rows
        result = subprocess.run(
            [
                sys.executable,
                "run_inventory_sweep.py",
                "--inventory", str(inventory_path),
                "--lead-log", str(lead_log_path),
                "--dry-run",
            ],
            cwd="/Users/claudebot/Lead generator/lead-radar",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "DRY-RUN" in result.stdout
        assert "lead-overdue" in result.stdout
        if lead_log_path.exists():
            with lead_log_path.open("r", encoding="utf-8") as f:
                content = f.read()
            assert "EXPIRED" not in content

    def test_actual_run_writes_to_lead_log(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        result = subprocess.run(
            [
                sys.executable,
                "run_inventory_sweep.py",
                "--inventory", str(inventory_path),
                "--lead-log", str(lead_log_path),
            ],
            cwd="/Users/claudebot/Lead generator/lead-radar",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "1 expired" in result.stdout
        with lead_log_path.open("r", encoding="utf-8") as f:
            content = f.read()
        assert "lead-overdue" in content
        assert "EXPIRED" in content
```

- [ ] **Step 8.2: Run test om falen te verifiëren**

```bash
pytest tests/test_inventory_sweep.py::TestCLI -v
```

Expected: FAIL (FileNotFoundError voor run_inventory_sweep.py).

- [ ] **Step 8.3: Implementeer CLI**

Maak `lead-radar/run_inventory_sweep.py`:

```python
"""CLI wrapper voor sweep_expired_inventory.

Usage:
    python3 run_inventory_sweep.py [--inventory PATH] [--lead-log PATH] [--dry-run]

Default paden: data/lead_inventory.csv en data/lead_log.csv (relatief aan
het lead-radar/ project root).

Voor automation via launchd: zie com.leadradar.inventory_sweep.plist.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from consumer.inventory import sweep_expired_inventory


def _dry_run_preview(inventory_path: Path, lead_log_path: Path) -> list[str]:
    """Zonder schrijven: welke lead_ids zouden expired worden."""
    now = datetime.now(timezone.utc)
    if not inventory_path.exists():
        return []

    already_expired: set[str] = set()
    if lead_log_path.exists():
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("to_state") == "EXPIRED":
                    already_expired.add(row["lead_id"])

    candidates: list[str] = []
    with inventory_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lead_id = row["lead_id"]
            if lead_id in already_expired:
                continue
            if row.get("delivered_to"):
                continue
            expires_at_str = row.get("expires_at", "")
            if not expires_at_str:
                continue
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                continue
            if expires_at < now:
                candidates.append(lead_id)
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        default="data/lead_inventory.csv",
        help="Path naar inventory CSV (default: data/lead_inventory.csv)",
    )
    parser.add_argument(
        "--lead-log",
        default="data/lead_log.csv",
        help="Path naar lead_log CSV (default: data/lead_log.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon wat geexpired zou worden zonder te schrijven",
    )
    args = parser.parse_args(argv)

    inventory_path = Path(args.inventory)
    lead_log_path = Path(args.lead_log)

    if args.dry_run:
        candidates = _dry_run_preview(inventory_path, lead_log_path)
        print(f"DRY-RUN: {len(candidates)} expired candidates")
        for lead_id in candidates:
            print(f"  - {lead_id}")
        return 0

    expired = sweep_expired_inventory(
        inventory_path=inventory_path,
        lead_log_path=lead_log_path,
        actor="cron",
    )
    print(f"Sweep complete: {len(expired)} expired")
    for lead_id in expired:
        print(f"  - {lead_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 8.4: Run test om te verifiëren dat het slaagt**

```bash
pytest tests/test_inventory_sweep.py -v
```

Expected: 5 passed.

- [ ] **Step 8.5: Handmatige smoke-test**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 run_inventory_sweep.py --dry-run --inventory /tmp/nonexistent.csv --lead-log /tmp/nonexistent_log.csv
```

Expected output:
```
DRY-RUN: 0 expired candidates
```

- [ ] **Step 8.6: Commit**

```bash
git add lead-radar/run_inventory_sweep.py lead-radar/tests/test_inventory_sweep.py
git commit -m "feat(cli): run_inventory_sweep.py with --dry-run"
```

---

## Task 9: launchd plist voor nightly sweep

**Files:**
- Create: `lead-radar/com.leadradar.inventory_sweep.plist`

- [ ] **Step 9.1: Maak plist**

Maak `lead-radar/com.leadradar.inventory_sweep.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.leadradar.inventory_sweep</string>

    <key>WorkingDirectory</key>
    <string>/Users/claudebot/Lead generator/lead-radar</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>python3</string>
        <string>/Users/claudebot/Lead generator/lead-radar/run_inventory_sweep.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/claudebot/Lead generator/lead-radar/logs/inventory_sweep.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/claudebot/Lead generator/lead-radar/logs/inventory_sweep.err</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

- [ ] **Step 9.2: Handmatige install-instructies (operator-actie, niet automation)**

> Kopieer plist naar `~/Library/LaunchAgents/` en laad met launchctl:
>
> ```bash
> cp "/Users/claudebot/Lead generator/lead-radar/com.leadradar.inventory_sweep.plist" \
>    ~/Library/LaunchAgents/
> launchctl load -w ~/Library/LaunchAgents/com.leadradar.inventory_sweep.plist
> launchctl list | grep leadradar.inventory
> ```
>
> Voor smoke-test handmatige trigger:
>
> ```bash
> launchctl start com.leadradar.inventory_sweep
> tail -f "/Users/claudebot/Lead generator/lead-radar/logs/inventory_sweep.log"
> ```

- [ ] **Step 9.3: Commit**

```bash
git add lead-radar/com.leadradar.inventory_sweep.plist
git commit -m "feat(launchd): nightly inventory sweep at 03:00"
```

---

## Task 10: Final integration smoke-test

**Files:** geen wijzigingen

- [ ] **Step 10.1: Run hele test-suite voor Plan A modules**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
pytest tests/test_regions.py tests/test_inventory.py tests/test_inventory_sweep.py -v
```

Expected: 21 passed (7 regions + 13 inventory + 5 sweep — verifieer aantal).

- [ ] **Step 10.2: Run full regression suite**

```bash
pytest -v --tb=short 2>&1 | tail -30
```

Expected: bestaande tests blijven slagen (pre-Plan-A baseline was 1054 passed, 3 skipped).

- [ ] **Step 10.3: Handmatige inventory write + sweep flow**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"

mkdir -p /tmp/plan-a-smoke
rm -f /tmp/plan-a-smoke/*.csv

python3 -c "
import sys
sys.path.insert(0, '.')
from datetime import datetime, timezone, timedelta
from consumer.inventory import append_inventory_row

now = datetime.now(timezone.utc)
append_inventory_row(
    '/tmp/plan-a-smoke/lead_inventory.csv',
    lead_id='smoke-test-1',
    niche='warmtepomp',
    region_nl='utrecht|amersfoort',
    intent_strength='HOT',
    captured_at=(now - timedelta(days=20)).isoformat(timespec='seconds'),
    approved_at=(now - timedelta(days=19)).isoformat(timespec='seconds'),
    expires_at=(now - timedelta(days=1)).isoformat(timespec='seconds'),
    source_class='apify_public',
)
print('Wrote test row')
"

python3 run_inventory_sweep.py \
  --inventory /tmp/plan-a-smoke/lead_inventory.csv \
  --lead-log /tmp/plan-a-smoke/lead_log.csv \
  --dry-run

python3 run_inventory_sweep.py \
  --inventory /tmp/plan-a-smoke/lead_inventory.csv \
  --lead-log /tmp/plan-a-smoke/lead_log.csv

cat /tmp/plan-a-smoke/lead_log.csv
```

Expected: dry-run toont "1 expired candidates" + "smoke-test-1". Echte run toont "1 expired" en lead_log.csv bevat een EXPIRED-rij.

- [ ] **Step 10.4: Push branch en open PR**

```bash
cd "/Users/claudebot/Lead generator"
git push -u origin feat/fb-primary-a-foundation

gh pr create --title "Plan A: FB-primary foundation (doctrine v0.2 + inventory + decay)" --body "$(cat <<'EOF'
## Summary

Plan A implementatie uit docs/superpowers/plans/2026-05-19-fb-primary-a-foundation.md.

- Doctrine v0.2: 00.0 moderation-filosofie, 00.2.b closed-group provenance, 01.3 screenshot-uitbreiding, 02.2 HOT/WARM categorieen, A32 fail-closed, B.1 verifiable member-witnessed intent
- Region utility (~40 NL plaatsen)
- Inventory module: 12-veld CSV, append met validatie, decay-window calc
- Config: inventory.decay_windows per niche x intent-strength
- CLI run_inventory_sweep.py met --dry-run
- launchd plist voor 03:00 nightly sweep

## Test plan

- [ ] pytest tests/test_regions.py tests/test_inventory.py tests/test_inventory_sweep.py -v (21 passed)
- [ ] Full regression suite blijft groen
- [ ] Handmatige smoke-test inventory write + sweep flow
- [ ] launchd plist install op Sem's Mac
EOF
)"
```

---

## Self-Review (Plan author)

**Spec coverage check** — heeft elke spec-sectie een task die het implementeert?

| Spec-sectie | Plan-task |
|-------------|-----------|
| §0 Context | n/a (informatief) |
| §1 Strategische intentie | n/a (informatief) |
| §2 Architectuur — Apify+burner dual-path | **Plan C** (burner runner) |
| §3 Burner setup/warming/recovery | **Plan C** |
| §4 Closed-group provenance — archive-bundle | **Plan B** (delivery + archive-screenshot wiring) |
| §4 Closed-group — reviewer attestation | **Plan B** (console attestation veld) |
| §4 Vocab-lint source-class-aware | **Plan B** (dispatcher.py extension) |
| §5 Review throughput — pre-screen LLM | **Plan B** |
| §5 Console /inventory/review | **Plan B** |
| §6 Inventory CSV schema | **Task 3, 4** ✓ |
| §6.2 Decay-windows | **Task 5, 6** ✓ |
| §6.3 Still-warm recheck | n/a (spec zegt initieel uit) |
| §7 Demo-tool | **Plan D** |
| §8 Doctrine v0.2 | **Task 1** ✓ |
| §9 Testing-strategie | per-task tests + Task 10 ✓ |
| §10 Non-goals | n/a (informatief) |
| §11.1 Decided | n/a (informatief) |
| §12 DoD item 1 (doctrine merged) | **Task 1** ✓ |
| §12 DoD item 7 (inventory operationeel) | **Tasks 3-9** ✓ |

**Placeholder scan:** geen TBD / TODO / fill-in-later. Elke code-step heeft volledige code. Elke test heeft volledige test-code.

**Type consistency:** INVENTORY_FIELDS, VALID_INTENT_STRENGTHS, VALID_SOURCE_CLASSES, compute_expires_at, sweep_expired_inventory consistent gebruikt tussen tasks. pcs.append_transition signature geverifieerd via Read van lead-radar/pcs.py.

**Geen gaps gevonden.**

---

## Execution Handoff

Plan complete en opgeslagen naar `lead-radar/docs/superpowers/plans/2026-05-19-fb-primary-a-foundation.md`.

Twee uitvoerings-opties:

**1. Subagent-Driven (aanbevolen)** — Ik dispatch een fresh subagent per task, review tussen tasks, snelle iteratie

**2. Inline Execution** — Voer tasks uit in deze sessie via executing-plans, batch-uitvoering met checkpoints voor review

Welke aanpak?
