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
