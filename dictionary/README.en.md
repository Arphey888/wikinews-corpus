🌐 [Read in Russian](README.md)

<div align="center">

# 📰 Russian Wikinews Frequency Dictionary v2

**Lemma and part-of-speech frequencies from the Russian Wikinews corpus**

![pymorphy3](https://img.shields.io/badge/pymorphy3-2.0.6-3776AB)
![CSV](https://img.shields.io/badge/format-CSV%20%2B%20Zstandard-brightgreen)
![v2](https://img.shields.io/badge/version-v2-blue)

</div>

The dictionary was built from the `articles.csv` table of the [Arphey888/ruwikinews-corpus](https://huggingface.co/datasets/Arphey888/ruwikinews-corpus) dataset. According to the dataset card, the source is the [Russian Wikinews](https://ru.wikinews.org/) Wikimedia dump dated 1 September 2026. The dictionary contains 1,282,848 lemma–part-of-speech pairs and counts 327,945,204 tokens across 1,473,531 articles.

---

## 📑 Contents

1. [Files](#-files)
2. [Columns](#-columns)
3. [Processing and provenance](#-processing-and-provenance)
4. [Reading the dictionary](#-reading-the-dictionary)

---

## 🗂 Files

| File | Contents |
|---|---|
| [`lemmas.csv.zst`](lemmas.csv.zst) | Zstandard-compressed UTF-8 CSV frequency table, sorted by descending frequency. |
| [`stats.json`](stats.json) | Processing settings, lemmatizer version, and run statistics. |

Archive SHA-256: `8b118afab349dd8ea1f13f3ac1efedf6cc71003adfdd0a9d606d5690610b1970`.

Uncompressed `lemmas.csv` SHA-256: `f96dc3d8b9e9a3b942d87496156e5efc74fa016209f5d2f9146848c7bd6692b4`.

---

## 📋 Columns

| Column | Meaning |
|---|---|
| `lemma` | Lowercase base form, with «ё» normalized to «е». |
| `pos` | pymorphy3 part-of-speech tag, such as `NOUN`, `ADJF`, or `VERB`. `PROPN` marks proper nouns. `NONE` marks an undetermined part of speech. |
| `freq` | Number of occurrences of the lemma–part-of-speech pair in the processed corpus. |
| `known` | `1` if at least one word form for the pair appears in the pymorphy3 dictionary, otherwise `0`. |

---

## 🧭 Processing and provenance

The `build_dictionary.py` script tokenizes sequences of Russian letters, allows hyphens within words, and selects the most likely analysis from pymorphy3 2.0.6 without using context. The `name_filter.py` module marks known proper nouns and uses a heuristic to discard sentences with signs of non-Russian text. Part-of-speech ambiguity affects the counts.

The dictionary contains derived frequency data. The original Russian Wikinews text is available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) unless a page states otherwise. Credit Russian Wikinews and the original article authors, link to the license, and indicate any changes when reusing the data. The corpus includes articles marked `origin_type = external_import`, which may be subject to terms from external sources. See the dataset card for details on article provenance.

---

## 🚀 Reading the dictionary

With `pandas` and `zstandard` installed:

```python
import pandas as pd

df = pd.read_csv("lemmas.csv.zst", keep_default_na=False)
```
