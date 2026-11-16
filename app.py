"""
dream-atlas - Suche und Karte ueber 22.096 Traumberichte.

Alles Teure ist vorberechnet: Embeddings, Kartenkoordinaten und Cluster
liegen als Dateien bereit. Zur Laufzeit wird nur die Eingabe kodiert
und einmal gegen die Matrix multipliziert.
"""

import json

import gradio as gr
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sentence_transformers import SentenceTransformer

MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Wie viele Punkte die Karte zeigt. Alle 22k zu uebertragen laesst den
# Browser haengen - eine Stichprobe sieht praktisch gleich aus.
KARTE_PUNKTE = 7000

FARBEN = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860",
    "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD", "#B07AA1", "#76B7B2",
]

# --- einmalig beim Start laden ------------------------------------------

df = pd.read_parquet("dreams.parquet")
E = np.load("embeddings.npy")
XY = np.load("atlas_xy.npy")
cluster = np.load("clusters.npy")
namen = {int(k): v for k, v in json.load(open("cluster_names.json")).items()}

model = SentenceTransformer(MODELL)

rng = np.random.default_rng(0)
HINTERGRUND = rng.choice(len(df), size=min(KARTE_PUNKTE, len(df)), replace=False)

print(f"{len(df)} Traeume geladen, {E.shape[1]} Dimensionen")


def kuerzen(t, n=110):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + "…"


# --- Karte ---------------------------------------------------------------

def karte(markieren=None):
    fig = go.Figure()

    # Hintergrund: eine einzige Spur, Farbe pro Punkt - viel leichter
    # als zwoelf getrennte Spuren.
    idx = HINTERGRUND
    fig.add_trace(go.Scattergl(
        x=XY[idx, 0], y=XY[idx, 1],
        mode="markers",
        marker=dict(
            size=3.5,
            opacity=0.55,
            color=[FARBEN[c % len(FARBEN)] for c in cluster[idx]],
        ),
        text=[kuerzen(t) for t in df.iloc[idx]["dreams"]],
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
    ))

    # Regionen beschriften, statt eine lange Legende zu zeigen
    for c in sorted(namen):
        m = cluster == c
        fig.add_annotation(
            x=float(np.median(XY[m, 0])), y=float(np.median(XY[m, 1])),
            text=namen[c],
            showarrow=False,
            font=dict(size=11, color="#222"),
            bgcolor="rgba(255,255,255,0.82)",
            bordercolor="rgba(0,0,0,0.15)",
            borderwidth=1, borderpad=3,
        )

    if markieren is not None and len(markieren):
        t = np.asarray(markieren, dtype=int)
        fig.add_trace(go.Scattergl(
            x=XY[t, 0], y=XY[t, 1],
            mode="markers",
            marker=dict(size=16, color="#111", symbol="circle-open",
                        line=dict(width=3)),
            text=[kuerzen(x) for x in df.iloc[t]["dreams"]],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, fixedrange=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FAFAFA",
        hoverlabel=dict(bgcolor="white", font_size=12),
        dragmode="pan",
    )
    return fig


# --- Suche ---------------------------------------------------------------

def suche(text, min_woerter, anzahl):
    if not text or not text.strip():
        return "Gib links einen Traum ein – auf Deutsch oder Englisch.", karte()

    q = model.encode([text], normalize_embeddings=True)
    sims = (E @ q.T).ravel()

    # Kurze Berichte abwerten statt loeschen: sie liefern duenne Vektoren
    # und landen sonst oben, ohne inhaltlich zu passen.
    lang_genug = df["word_count"].to_numpy() >= min_woerter
    sims = np.where(lang_genug, sims, -1.0)

    top = np.argsort(-sims)[: int(anzahl)]

    teile = []
    for rang, i in enumerate(top, start=1):
        z = df.iloc[int(i)]
        jahr = ""
        try:
            if not pd.isna(z["year"]):
                jahr = f", {int(z['year'])}"
        except (KeyError, TypeError, ValueError):
            pass
        teile.append(
            f"**{rang}.** &nbsp;Ähnlichkeit {sims[i]:.3f} &nbsp;·&nbsp; "
            f"*{z['series']}{jahr}*\n\n{z['dreams']}"
        )

    return "\n\n---\n\n".join(teile), karte(top)


# --- Oberflaeche ---------------------------------------------------------

BEISPIELE = [
    "Ich wurde durch ein dunkles Haus verfolgt",
    "My teeth were falling out one by one",
    "Ich konnte fliegen und bin über die Dächer geschwebt",
    "I was late for an exam and could not find the room",
]

CSS = """
.schmal { max-width: 1200px; margin: auto; }
footer { display: none !important; }
"""

with gr.Blocks(title="dream-atlas", theme=gr.themes.Soft(), css=CSS) as demo:
    with gr.Column(elem_classes="schmal"):
        gr.Markdown(
            "# dream-atlas\n"
            "### Beschreib einen Traum – und finde die Träume von Fremden, die ihm ähneln.\n"
            "22.096 echte Berichte aus dem **DreamBank**-Korpus. Das Archiv ist englisch, "
            "die Suche versteht trotzdem Deutsch: beides landet im selben Bedeutungsraum. Echte Berichte aus einem Forschungsarchiv – manche enthalten Gewalt oder sexuelle Übergriffe."
        )

        with gr.Row():
            with gr.Column(scale=2):
                eingabe = gr.Textbox(
                    label="Dein Traum",
                    placeholder="Ich war in einem Haus und jemand folgte mir…",
                    lines=6,
                )
                with gr.Row():
                    min_woerter = gr.Slider(0, 60, value=20, step=5,
                                            label="Mindestlänge der Treffer (Wörter)")
                    anzahl = gr.Slider(3, 10, value=5, step=1, label="Treffer")
                knopf = gr.Button("Suchen", variant="primary", size="lg")
                gr.Examples(BEISPIELE, inputs=eingabe, label="Beispiele")

            with gr.Column(scale=3):
                treffer = gr.Markdown(
                    "Gib links einen Traum ein – auf Deutsch oder Englisch.",
                    label="Ähnliche Träume",
                )

        gr.Markdown(
            "### Der Atlas\n"
            "Jeder Punkt ist ein Traum. Ziehen zum Verschieben, Scrollen zum Zoomen. "
            "Deine Treffer werden eingekreist. Ziehen zum Verschieben, Scrollen zum Zoomen."
        )
        plot = gr.Plot(label="")

        gr.Markdown(
            "---\n"
            "Daten: Domhoff, G. W., & Schneider, A. (2008), "
            "[DreamBank](https://dreambank.net/). &nbsp;·&nbsp; "
            "Code: [github.com/Gunnny/dream-atlas](https://github.com/Gunnny/dream-atlas)"
        )

    knopf.click(suche, [eingabe, min_woerter, anzahl], [treffer, plot])
    eingabe.submit(suche, [eingabe, min_woerter, anzahl], [treffer, plot])
    demo.load(karte, None, plot)


if __name__ == "__main__":
    demo.launch()
