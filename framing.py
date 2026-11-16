"""
Entfernt Rahmenformeln am Anfang von Traumberichten.

Eine Rahmenformel spricht ueber den Traum, statt ihn zu erzaehlen:

    "I dreamed that I was walking"   ->  "I was walking"
    "Last night I had a bizarre dream. First of all, ..."  ->  "First of all, ..."

Hintergrund: Die erste Hauptkomponente der Satz-Embeddings trennt Berichte mit
Rahmenformel von solchen ohne - ein Artefakt unterschiedlicher Erhebungs-
anweisungen in den Teilsammlungen, kein inhaltliches Merkmal.

Leitprinzip: lieber eine Formel uebersehen als Inhalt zerstoeren.
"""

import re

# Fuellwoerter, die zwischen "I had" und "dream" stehen duerfen, ohne dass
# Information verloren geht. Steht dort etwas anderes ("sex dream",
# "flying dream"), greift das Muster absichtlich NICHT - dieses Wort ist Thema.
LEER = (
    r"(?:a|an|the|some|some sort of|kind of|sort of|really|very|quite|"
    r"bizarre|odd|strange|weird|funny|vivid|long|short|good|bad|"
    r"nice|awful|terrible|crazy|wild|interesting|recurring)"
)

RAHMEN = re.compile(
    r"^\s*(?:"

    # (A) "I dreamed ..." / "Last night I dreamt that ..."
    #     Benannte Gruppe, weil hier der Inhalt DIREKT folgt - im Englischen
    #     darf "that" weggelassen werden ("I dreamed I was flying").
    #     Deshalb wird hier nie der ganze Satz geloescht.
    r"(?P<direkt>"
    r"(?:last night|one night|the other night|first)?[,\s]*"
    r"i (?:dreamed|dreamt)\b(?:\s+(?:once again|again|last night))?"
    r"(?:\s+(?:that|about|of|where))?"
    r")"

    # (B) "I had a bizarre dream ..." - nur mit inhaltsleeren Fuellwoertern
    rf"|(?:last night|one night|the other night|first)?[,\s]*"
    rf"i had\s+(?:{LEER}\s+){{0,4}}dreams?\b"
    r"(?:\s+(?:that|about|where|in which))?"

    # (C) Metasaetze ueber den Traum
    r"|(?:my|the)\s+(?:last\s+)?dream\b(?:\s+of\s+last\s+night)?\s*"
    r"(?:was|is|took place|could be called)(?:\s+(?:about|that))?"
    r"|another dream i had was(?:\s+that)?"
    r"|this is a dream[^.]*\."

    # (D) Erinnerungs-Floskeln
    r"|all i remember is"
    r"|i can only (?:recall|remember)"
    r"|i don'?t remember[^,.]*[,.]"

    r")[\s,:]*",
    flags=re.IGNORECASE,
)

# Endet die Formel auf einen Komplementierer, geht der Satz inhaltlich weiter.
KOMPLEMENT = re.compile(r"\b(?:that|about|of|where|in which)[\s,:]*$", re.IGNORECASE)


def entrahmen(text, max_runden=3):
    """Entfernt bis zu `max_runden` aufeinanderfolgende Rahmenformeln.

    Zwei Faelle:
      - Formel vom Typ (A), oder Formel endet auf "that/about/of/where"
        -> nur die Formel entfernen, der Rest des Satzes ist Inhalt
      - sonst
        -> bis zum Satzende entfernen, der ganze Satz war Verpackung
    """
    t = str(text).strip()

    for _ in range(max_runden):
        m = RAHMEN.match(t)
        if not m:
            break

        if m.group("direkt") or KOMPLEMENT.search(m.group(0)):
            t = t[m.end():].strip()
        else:
            punkt = t.find(".", m.start())
            t = (t[punkt + 1:] if punkt != -1 else "").strip()

    return t


# --------------------------------------------------------------------------
# Selbsttest: python framing.py
# --------------------------------------------------------------------------

FAELLE = [
    # (Eingabe, erwarteter Anfang der Ausgabe)
    ("I dreamed that I was walking through a dark house.",
     "I was walking through a dark house."),

    ("I dreamed I was to be married to the boy I go with (20) when he arrived.",
     "I was to be married to the boy"),

    ("I dreamt I was at a social ball where I met a very beautiful girl.",
     "I was at a social ball"),

    ("Last night I had a bizarre dream . First of all, this was after everybody left",
     "First of all,"),

    ("My dream of last night could be called a series of scenes. First I was in a big field",
     "First I was in a big field"),

    # Darf NICHT veraendert werden - "sex" ist Thema, nicht Fuellwort
    ("First I had some sort of sex dream or something. I can't remember most of it.",
     "First I had some sort of sex dream"),

    # Darf NICHT veraendert werden - luzider Traum, "dream" ist Inhalt
    ("I was dreaming inside my dream and it felt strange",
     "I was dreaming inside my dream"),
]


if __name__ == "__main__":
    fehler = 0
    for eingabe, erwartet in FAELLE:
        ergebnis = entrahmen(eingabe)
        ok = ergebnis.startswith(erwartet)
        fehler += not ok
        print(f"[{'ok ' if ok else 'FEHL'}] {ergebnis[:70]!r}")
        if not ok:
            print(f"        erwartet: {erwartet!r}")

    print(f"\n{len(FAELLE) - fehler}/{len(FAELLE)} bestanden")
