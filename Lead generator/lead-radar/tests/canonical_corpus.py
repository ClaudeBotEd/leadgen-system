"""Canonical post corpus voor regression-tests.

Elke post heeft `expected`-dict met velden:
- classifier_kind: 'lead' | 'promo' | 'info' | 'unknown'
- classifier_keep: bool (is_potential_lead)
- intent: 'hot' | 'warm' | 'cold'  (na scoring met juiste niche)
- score_min, score_max: inclusieve score-range
- city: detected city (None = niet verwacht)
- niche: welke niche-keywords te gebruiken in scoring

Aanpassen alleen na bewust onderbouwd besluit — deze suite vangt regressies.
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# HOT leads (≥80) — duidelijke koop-intentie + locatie + urgentie/defect
# ─────────────────────────────────────────────────────────────────────────────

HOT_POSTS: list[dict] = [
    {
        "id": "hot_cv_kapot_utrecht_spoed",
        "title": "CV-ketel kapot Utrecht, zoek monteur",
        "text": "Mijn cv-ketel is kapot, geen warm water meer. Heeft iemand een goede monteur in Utrecht die deze week kan komen? Spoed.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 90,
            "score_max": 100,
            "city": "utrecht",
        },
    },
    {
        "id": "hot_warmtepomp_amsterdam_spoed",
        "title": "Warmtepomp installateur gezocht in Amsterdam",
        "text": "Wie kan met spoed een warmtepomp installeren in Amsterdam? Heb een tussenwoning van 110m2 en wil zo snel mogelijk overstappen. Offerte nodig.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "amsterdam",
        },
    },
    {
        "id": "hot_airco_lekt_eindhoven",
        "title": "Airco lekt water, monteur gezocht Eindhoven",
        "text": "Onze airco lekt water bij de unit en geeft foutmelding F12. Iemand een goede installateur in Eindhoven die dringend kan komen kijken?",
        "niche": "airco",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "eindhoven",
        },
    },
    {
        "id": "hot_geen_warm_water_asap",
        "title": "Geen warm water meer — asap monteur Rotterdam",
        "text": "Onze combiketel doet het niet meer, geen warm water. Met spoed een monteur nodig in Rotterdam, vandaag het liefst.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 90,
            "score_max": 100,
            "city": "rotterdam",
        },
    },
    {
        "id": "hot_cv_storing_antwerpen",
        "title": "CV-ketel storing Antwerpen, valt steeds uit",
        "text": "Mijn cv valt steeds uit met foutmelding, geen verwarming. Wie kent een goede technieker in Antwerpen die snel kan? Heel dringend.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "antwerpen",
        },
    },
    {
        "id": "hot_warmtepomp_laten_plaatsen_eindhoven",
        "title": "Warmtepomp laten plaatsen in Eindhoven, offerte gewenst",
        "text": "Ik wil een warmtepomp laten plaatsen in mijn rijtjeshuis in Eindhoven. Binnen 2 weken graag een offerte van een installateur. Bouwjaar 1985, 120m2.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "eindhoven",
        },
    },
    {
        "id": "hot_zonnepanelen_dringend_groningen",
        "title": "Zonnepanelen installateur dringend gezocht Groningen",
        "text": "Wij zoeken met spoed een installateur voor zonnepanelen op ons dak in Groningen. Wil deze maand nog beginnen. Offerte nodig, woning van 140m2.",
        "niche": "zonnepanelen",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "groningen",
        },
    },
    {
        "id": "hot_airco_kapot_deze_week_breda",
        "title": "Airco kapot deze week monteur nodig Breda",
        "text": "Onze airco is defect, werkt niet meer. Heel warm hier. Wie kan deze week een monteur sturen in Breda?",
        "niche": "airco",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "breda",
        },
    },
    {
        "id": "hot_cv_vervangen_binnen_2_weken",
        "title": "CV-ketel vervangen binnen 2 weken Tilburg",
        "text": "CV moet vervangen worden, lekkage in oude ketel. Zoek installatiebedrijf in Tilburg dat binnen 2 weken kan plaatsen. Budget rond 3000 euro.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 90,
            "score_max": 100,
            "city": "tilburg",
        },
    },
    {
        "id": "hot_offerte_warmtepomp_gent",
        "title": "Offerte warmtepomp Gent — al 2 offertes vergelijken",
        "text": "Ik heb al 2 offertes binnen voor een warmtepomp in Gent en wil een derde mening. Tweede offerte was 12k euro, eerste 9k. Iemand een goede installateur die deze maand kan?",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 85,
            "score_max": 100,
            "city": "gent",
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# WARM leads (60-79) — duidelijke intentie maar minder urgentie/details
# ─────────────────────────────────────────────────────────────────────────────

WARM_POSTS: list[dict] = [
    {
        "id": "warm_zoek_installateur_tilburg",
        "title": "Op zoek naar warmtepomp installateur in Tilburg",
        "text": "Wie kent een goede warmtepomp installateur in Tilburg? Wil binnenkort offerte vergelijken voor onze woning.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 70,
            "score_max": 100,
            "city": "tilburg",
        },
    },
    {
        "id": "warm_zonnepanelen_offerte_haarlem",
        "title": "Zonnepanelen voor woning in Haarlem, wie kan offerte maken",
        "text": "Wij hebben een rijtjeshuis in Haarlem met dak op het zuiden. Wie kan een offerte maken voor zonnepanelen?",
        "niche": "zonnepanelen",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "warm",
            "score_min": 60,
            "score_max": 85,
            "city": "haarlem",
        },
    },
    {
        "id": "warm_cv_vervangen_offerte",
        "title": "CV moet vervangen, wie maakt offerte in Apeldoorn",
        "text": "Onze cv-ketel is 18 jaar oud en aan vervanging toe. Wie kan een offerte maken in Apeldoorn? Geen haast maar wel binnen een paar weken.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "warm",
            "score_min": 60,
            "score_max": 100,
            "city": "apeldoorn",
        },
    },
    {
        "id": "warm_airco_installeren_leuven",
        "title": "Airco laten installeren in slaapkamer, Leuven",
        "text": "Ik wil een airco laten installeren in onze slaapkamer in Leuven. Wie kent een goede installateur? Offerte gewenst.",
        "niche": "airco",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "warm",
            "score_min": 60,
            "score_max": 100,
            "city": "leuven",
        },
    },
    {
        "id": "warm_renovatie_aannemer_brugge",
        "title": "Renovatie woning Brugge, wie kent goede aannemer",
        "text": "Wij gaan een woning renoveren in Brugge. Wie kent een goede aannemer? Bouwjaar 1972, 150m2, alles moet aangepakt worden.",
        "niche": "renovatie",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "warm",
            "score_min": 60,
            "score_max": 100,
            "city": "brugge",
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH-only (COLD) — moet INFO worden, niet LEAD
# ─────────────────────────────────────────────────────────────────────────────

RESEARCH_POSTS: list[dict] = [
    {
        "id": "research_welke_warmtepomp_kiezen",
        "title": "Welke warmtepomp moet ik kiezen voor mijn woning",
        "text": "Ik twijfel tussen Daikin en LG voor een lucht-water warmtepomp. Wat raden jullie aan? Welke is het beste qua prijs/kwaliteit?",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "research_advies_welk_merk_airco",
        "title": "Advies welk merk airco kopen",
        "text": "Welke airco zou je aanraden? Twijfel tussen Mitsubishi en Daikin. Vergelijking gezocht, wat zijn voor- en nadelen?",
        "niche": "airco",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "research_review_warmtepomp",
        "title": "Review warmtepomp Atag — ervaringen",
        "text": "Heeft iemand ervaring met de Atag warmtepomp? Ben aan het oriënteren, wil graag weten wat voor- en nadelen zijn. Hoe werkt hij in de winter?",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "research_zonnepanelen_aankoop_overwegen",
        "title": "Overweeg zonnepanelen — informatie gezocht",
        "text": "Wij zijn aan het oriënteren over zonnepanelen. Wat is het verschil tussen monokristal en polykristal? Voor- en nadelen van een omvormer per paneel?",
        "niche": "zonnepanelen",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# INFO-only (COLD) — pure kennisvragen
# ─────────────────────────────────────────────────────────────────────────────

INFO_POSTS: list[dict] = [
    {
        "id": "info_wat_is_warmtepomp",
        "title": "Wat is een warmtepomp",
        "text": "Hoe werkt een warmtepomp eigenlijk? Iemand die het kan uitleggen?",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "info_verschil_split_cassette",
        "title": "Wat is het verschil tussen split en cassette airco",
        "text": "Ik wil graag begrijpen wat het verschil is tussen split airco en cassette airco. Iemand die uitleg kan geven?",
        "niche": "airco",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DISCUSSION (COLD) — meningsvragen, forum-gebruikers zoeken geen monteur
# ─────────────────────────────────────────────────────────────────────────────

DISCUSSION_POSTS: list[dict] = [
    {
        "id": "discussion_jullie_ervaring_warmtepomp",
        "title": "Wat zijn jullie ervaringen met warmtepomp deze winter",
        "text": "Benieuwd naar jullie ervaringen met warmtepomp deze winter. Hoe presteert hij bij -5 graden? Wat vinden jullie van de COP-waardes?",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "discussion_meningen_zonnepanelen_2026",
        "title": "Meningen over zonnepanelen in 2026 met salderingsregeling weg",
        "text": "Wat denken jullie over zonnepanelen nu de salderingsregeling verdwijnt? Loont het nog? Hoe ervaren jullie de terugverdientijd?",
        "niche": "zonnepanelen",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
    {
        "id": "discussion_iemand_ervaring_met_X",
        "title": "Iemand ervaring met Atag One thermostaat",
        "text": "Iemand ervaring met de Atag One slimme thermostaat? Werkt hij goed met andere systemen? Wat denken jullie?",
        "niche": "cv",
        "expected": {
            "classifier_kind": "info",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 60,
            "city": None,
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# PROMO (COLD) — bedrijfs-/verkoop-/vacature-advertenties
# ─────────────────────────────────────────────────────────────────────────────

PROMO_POSTS: list[dict] = [
    {
        "id": "promo_wij_plaatsen_warmtepompen",
        "title": "Wij plaatsen warmtepompen door heel Nederland",
        "text": "Wij installeren warmtepompen al 15 jaar. Onze monteurs zijn gecertificeerd. Bel ons voor een gratis offerte. Werken in heel Nederland.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        "id": "promo_te_koop_warmtepomp",
        "title": "Te koop nieuwe warmtepomp Daikin Altherma vanaf 4500 euro",
        "text": "Aangeboden: nieuwe Daikin Altherma warmtepomp, fabrieksnieuw, incl. btw. Vanaf 4500 euro. Bel naar +31612345678.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        "id": "promo_vacature_monteur",
        "title": "Vacature CV-monteur Amsterdam — leuk team!",
        "text": "Wij zoeken een ervaren cv-monteur in Amsterdam. Fulltime dienstverband, leuk team, goed salaris. Werken bij ons betekent veel afwisseling. Aanmelden via website.",
        "niche": "cv",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        "id": "promo_korting_zonnepanelen",
        "title": "20% korting op zonnepanelen — actie deze maand",
        "text": "Aanbiedingsprijs zonnepanelen: 20% korting deze maand. Onze installateurs plaatsen door heel NL. Bespaar tot 3000 euro. Bel ons voor scherpe prijs.",
        "niche": "zonnepanelen",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    # ─── FB-groups patterns (post-Apify-integratie, 2026-05-17 corpus uitbreiding) ───
    {
        # CTA-closer met URL — "Bekijk de quickscan via: https://..." pattern.
        "id": "promo_fb_quickscan_cta",
        "title": "Herkent u dit?",
        "text": (
            "De ene installateur adviseert hybride, de andere zegt all-electric.\n"
            "Bij Klimaat Techniek Nederland kijken wij onafhankelijk mee met uw situatie.\n"
            "Met onze Warmtepomp Quickscan beoordelen wij onder andere:\n"
            "* Of uw woning geschikt is voor een warmtepomp\n"
            "* Welk type warmtepomp het beste past\n\n"
            "Bekijk de Warmtepomp Quickscan via: https://www.voorbeeld.nl/quickscan/"
        ),
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        # Sale opener — "Nu verkrijgbaar: ..." commercial ad.
        "id": "promo_fb_sale_opener",
        "title": "Ultiem comfort met energiebesparing",
        "text": (
            "Nu verkrijgbaar: hoogwaardige Inverter airconditioners\n"
            "Grote besparing op elektriciteitsverbruik\n"
            "Speciale prijs: slechts 1000 euro inclusief montage."
        ),
        "niche": "airco",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        # "Wij regelen ..." service-doer pronoun (broader dan bestaande "wij installeren").
        "id": "promo_fb_wij_regelen",
        "title": "Buitenkraan laten plaatsen?",
        "text": (
            "Met dit weer is een buitenkraan geen luxe maar een must.\n"
            "Wij regelen het snel en vakkundig voor je.\n"
            "Tuin sproeien, auto wassen, zwembad vullen — geen gedoe meer."
        ),
        "niche": "renovatie",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        # Freelancer self-ad — aankondigt eigen beschikbaarheid.
        "id": "promo_fb_freelancer_available",
        "title": "Hallo allemaal",
        "text": (
            "Mijn man is weer beschikbaar voor nieuwe klussen in omgeving Apeldoorn.\n"
            "Hij is allround vakman en helpt met schilderwerk, plafonds, laminaat en timmerwerk."
        ),
        "niche": "renovatie",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        # Checkmark-bullet service-lijst (3+ regels) — installer-ad format.
        "id": "promo_fb_checkmark_bullets",
        "title": "Geen commissies, geen tussenpersonen",
        "text": (
            "Waarom betalen voor een platform? Bij ons is het simpel.\n"
            "✅ Geen commissies voor de vakman\n"
            "✅ Geen tussenpersonen tussen jou en de klusser\n"
            "✅ Gewoon rechtstreeks contact tussen partijen\n"
        ),
        "niche": "renovatie",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        # FALSE-POSITIVE GUARD — consumer die zelf zoekt en "interesse? stuur" als
        # uitnodiging gebruikt MAG NIET geflipt worden naar promo.  Regressie-test
        # voor de patroon-keuze (we hebben "interesse?" bewust niet opgenomen in
        # sale_opener).
        "id": "lead_fb_consumer_invites_response",
        "title": "Op zoek naar iemand voor dakwerken",
        "text": (
            "Dag iedereen,\n"
            "Ik ben op zoek naar iemand voor dakwerken in Willebroek. Het volledige dak "
            "moet worden afgebroken en vervangen.\n"
            "Heeft u interesse? Stuur gerust een bericht.\n"
            "Alvast bedankt."
        ),
        "niche": "renovatie",
        # score-range is bewust ruim: deze test verifieert primair dat de
        # classifier NIET promo-flipt op "interesse? stuur"; exacte score is
        # secundair en afhankelijk van renovatie-keyword coverage.
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "cold",
            "score_min": 0,
            "score_max": 80,
            "city": None,
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# EDGE cases — empty, mixed signals, allcaps, off-topic, postcode-only
# ─────────────────────────────────────────────────────────────────────────────

EDGE_POSTS: list[dict] = [
    {
        "id": "edge_empty",
        "title": "",
        "text": "",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "unknown",
            "classifier_keep": True,
            "intent": "cold",
            "score_min": 0,
            "score_max": 30,
            "city": None,
        },
    },
    {
        "id": "edge_offtopic",
        "title": "Beste fietsenmaker Amsterdam",
        "text": "Wie kent een goede fietsenmaker in Amsterdam? Mijn fiets is kapot en ik heb 'm dringend nodig.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "cold",
            "score_min": 0,
            "score_max": 70,
            "city": "amsterdam",
        },
    },
    {
        "id": "edge_mixed_research_then_buy",
        "title": "Eerst gekeken naar verschillende merken, nu wil ik een installateur",
        "text": "Ik heb verschillende warmtepompen vergeleken (Daikin, Atag) en wil nu een installateur in Utrecht die kan plaatsen. Binnen 3 weken graag. Offerte nodig.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 70,
            "score_max": 100,
            "city": "utrecht",
        },
    },
    {
        "id": "edge_allcaps_promo",
        "title": "NIEUWE WARMTEPOMP MET GARANTIE — 5 JAAR ERVARING",
        "text": "Onze installateurs plaatsen warmtepompen door heel Nederland. Met garantie, gecertificeerd. Bel ons.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "promo",
            "classifier_keep": False,
            "intent": "cold",
            "score_min": 0,
            "score_max": 100,
            "city": None,
        },
    },
    {
        "id": "edge_postcode_only",
        "title": "Warmtepomp installateur gezocht 1234 AB",
        "text": "Zoek installateur voor warmtepomp in 1234 AB. Wil binnenkort offerte vergelijken.",
        "niche": "warmtepomp",
        "expected": {
            "classifier_kind": "lead",
            "classifier_keep": True,
            "intent": "hot",
            "score_min": 60,
            "score_max": 100,
            "city": "nl-postcode",
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Compositie
# ─────────────────────────────────────────────────────────────────────────────

ALL_POSTS: list[dict] = (
    HOT_POSTS
    + WARM_POSTS
    + RESEARCH_POSTS
    + INFO_POSTS
    + DISCUSSION_POSTS
    + PROMO_POSTS
    + EDGE_POSTS
)


def post_by_id(post_id: str) -> dict:
    for p in ALL_POSTS:
        if p["id"] == post_id:
            return p
    raise KeyError(f"Unknown post id: {post_id}")
