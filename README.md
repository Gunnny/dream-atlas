# dream-atlas

An interactive atlas of dream reports — find the dreams of strangers that resemble your own.

> **Status:** work in progress. Retrieval and evaluation are done (M0–M2); the web interface is next.

<!-- TODO: screenshot or GIF of the app goes here, above everything else, once M4 is built -->

---

## What this is

A semantic search engine over 22,096 real dream reports from the [DreamBank](https://dreambank.net/) corpus.
You describe a dream — in English **or German** — and get back the dreams from the archive that are
closest in meaning, not in wording.

The interesting part is not that it works. It is **by how much**, and where it fails.

---

## Results

Precision@5 over a hand-built evaluation set of 20 queries:

| Method | P@5 | vs. baseline |
|---|---|---|
| TF-IDF (lexical baseline) | 0.360 | — |
| Multilingual sentence embeddings | **0.560** | **+20 points (+56 %)** |
| Embeddings + minimum-length filter | 0.580 | +22 points (+61 %) |

In plain terms: the lexical baseline returns 1.8 useful results out of 5, the embedding model 2.8.

### Why embeddings win

TF-IDF compares strings, not meaning. Two concrete failures from the same query:

- **Synonyms.** Changing *"chased"* to *"pursued"* in the query drops the top similarity
  from 0.413 to 0.293, and none of the five chase dreams found by the first query appear
  in the results of the second.
- **Language.** A German query returns dreams that merely *mention Germany* — the method
  matches on country names, not on content.

The embedding model handles both, because it maps all languages into one shared vector space.

### Why the length filter is not the improvement it looks like

Requiring at least 20 words per report raises mean P@5 by only 0.02 — but that average hides
two real and opposing effects. The filter changes the result list for **9 of 20 queries**:
it helps 5 and hurts 4.

The pattern is systematic:

| | queries helped | queries hurt |
|---|---|---|
| Relevant documents shorter than 20 words | 1 of 5 queries | **5 of 5 queries** |

Every query the filter damaged has short relevant reports that the filter discards by construction
— for example *"My last dream was about my grandfather. He had passed away about two years ago."*
(14 words) for the *deceased relative* query.

Across the whole gold set, **11.3 % of all relevant documents are shorter than 20 words.**

A hard length cutoff therefore trades away true positives to suppress noisy short matches.
It is not a free improvement, and this evaluation cannot show that it is an improvement at all.

### Cross-lingual retrieval works — on average
 
Every report in the archive is in English. Query it in German and the results are, in aggregate,
just as good:
 
| Query language | Queries | P@5 |
|---|---|---|
| German | 8 | 0.550 |
| English | 12 | 0.567 |
 
Those are different queries on different topics, so the set also contains three **matched pairs**:
the same dream described in both languages, everything else held constant.
 
| Pair | German | English | shared results |
|---|---|---|---|
| teeth falling out | 1.0 | 1.0 | 3 of 5 |
| flying over a city | 0.6 | 0.8 | 4 of 5 |
| late for an exam | **0.8** | **0.2** | **0 of 5** |
 
Two pairs behave as hoped. The third does not — the result lists are completely disjoint.
 
The cause is not the language itself but the **word choice that translation forces**. In
`...could not find the room`, the English *room* dominated the query: four of five results were
hotel rooms, dorm rooms and student rooms, and none involved an exam. In the German version
*Prüfung* dominated instead. *Room* is a dense, high-frequency setting word in an English dream
corpus; *Raum* is not its exact equivalent.
 
Translated query pairs are therefore only partly controlled, since translation involves lexical
decisions and those decisions drive retrieval. The aggregate figures hold, but per-query variance
is large.

## Method

```
OFFLINE (once)
  DreamBank  →  clean  →  embed all reports  →  matrix on disk

AT QUERY TIME
  user text  →  one embedding  →  dot product against the matrix  →  top-k
```

The expensive step runs once; each search is a single matrix–vector product over 22,096 rows.

- **Embedding model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions,
  L2-normalised, so cosine similarity reduces to a dot product.
- **Baseline:** scikit-learn `TfidfVectorizer`, English stop words, `min_df=2`, 24,119-term vocabulary.
  The document–term matrix has 539 M cells but only 0.22 % are non-zero (9.5 MB sparse vs. 4.3 GB dense).

---

## Data

Dream reports come from **DreamBank**, via the `DReAMy-lib/DreamBank-dreams-en` dataset on the
Hugging Face Hub. Columns: `series`, `description`, `dreams`, `gender`, `year`.

Cleaning:

| Step | Rows |
|---|---|
| Raw | 22,415 |
| Removed reports with fewer than 5 words | 22,347 |
| Removed exact duplicate texts | **22,096** |

Reports under 5 words are not dreams but **titles** — `'Packing.'`, `'Unknown.'`,
`'Matthew's Graduation'`. In some series the title is stored inside the text field, and where
no narrative followed, only the title remains.

Everything above 5 words was kept. Short reports like *"I was in a hospital."* are genuine but
thin; rather than deleting them, a `word_count` column is retained so each use case can filter
for itself. Deleting rows is irreversible; filtering is not.

**Known issues not yet addressed:**
- Titles are glued to the start of the text in some series (`'Blisters On My Face  I have blisters...'`)
- Bracketed waking-life notes are mixed into the text (`'[Note: I got sunburn yesterday on my face.]'`)

---

## Evaluation

There is no ground truth for "which of 22,096 dreams match this query". It had to be built.

**Pooling.** For each of 20 queries, the top-5 results of all three methods were collected and
merged, giving 213 unique (query, document) pairs to judge — 97 of which were marked relevant.

**Criterion**, fixed in writing before judging:

> **Relevant** if the central event of the query actually occurs in the dream.
> Setting alone is not enough — a castle without a dragon does not match *"a dragon over a castle"*.
> The event need not fill the whole dream; if it clearly occurs and the dream then moves on, it counts.

**Blinding.** The judging table contained no column identifying which method produced which result,
and rows were shuffled within each query. Knowing the source would have biased the judgement toward
the method built most recently.

**Agreement.** 41 of the 213 pairs were judged independently by two annotators:
**95.1 % agreement, Cohen's κ = 0.897.** The remaining 172 were labelled by a language model
following the same written criterion. Two borderline cases were discussed afterwards and unified in
the gold standard; κ is reported from the independent pass and was not recomputed after that revision.

**Query set.** 20 queries, 8 German and 12 English, including three matched German/English pairs
that describe the same dream in both languages. Three queries (`gaming`, `dragons`, `math`) were
included as expected-hard cases for a corpus collected largely before 2000.

The full gold standard is in [`judgements_final.csv`](judgements_final.csv).

---

## Limitations
 
- **Concrete settings outrank abstract events.** Given a query with several components, the model
  latches onto the physical scene rather than onto what happens in it. Two independent cases from
  the evaluation:
  | Query | What comes back | What is missing |
  |---|---|---|
  | *being chased through a **dark house*** | dark, threatening houses | the chase, in most results |
  | *late for an exam, could not find the **room*** | hotel and dorm rooms | the exam, in all five results |
  TF-IDF does not share this failure: it insists on *chased* and on *exam*. Each method wins where
  the other loses, which is the strongest argument for the hybrid retrieval listed under next steps.
- **Most labels are not human.** 172 of 213 relevance judgements come from a language model;
  the κ above is what makes them usable, not a guarantee that they are right.
- **20 queries is small.** Differences of a few points are not meaningful at this sample size.
- **The corpus is historical.** Many reports date from the mid-20th century, so modern topics are
  sparsely covered.
- **English archive.** German queries work through cross-lingual embeddings, but every stored
  report is in English.

---

## Next steps

- [ ] Web interface (Gradio) and public deployment
- [ ] Per-language evaluation breakdown
- [ ] Emotion annotation following the Hall & Van de Castle scheme
- [ ] Hybrid retrieval: combine the lexical and semantic scores, since each wins where the other loses

---

## Reproducing

```bash
pip install -r requirements.txt
```

See [`notebooks/01_explore_data.ipynb`](notebooks/) — it runs top to bottom and recreates the cleaned
dataset, both indexes and the evaluation.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Gunnny/dream-atlas/blob/main/notebooks/01_explore_data.ipynb)

Raw data is not committed; the notebook downloads it.

---

## References

- Domhoff, G. W., & Schneider, A. (2008). Studying dream content using the archive and search engine
  on DreamBank.net. *Consciousness and Cognition*, 17(4), 1238–1247.
  [doi:10.1016/j.concog.2008.06.010](https://doi.org/10.1016/j.concog.2008.06.010)
- Bertolini, L., et al. (2024). Automatic Annotation of Dream Report's Emotional Content with Large
  Language Models. [ACL Anthology](https://aclanthology.org/2024.clpsych-1.7/)
- [DReAMy](https://github.com/lorenzoscottb/DReAMy) — library and models for dream report analysis

---

## License

Code in this repository is MIT licensed. **This does not cover the DreamBank data**, which has its
own terms — see DreamBank for conditions of use.
