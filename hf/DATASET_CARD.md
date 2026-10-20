---
language:
- ru
# Проверьте лицензию на странице дампа/вики перед публикацией (см. раздел License ниже).
license: cc-by-2.5
pretty_name: Russian Wikinews corpus (ruwikinews)
tags:
- wikinews
- news
- russian
- corpus
configs:
- config_name: articles
  data_files: articles.csv.zst
  default: true
- config_name: categories
  data_files: categories.csv.zst
- config_name: article_categories
  data_files: article_categories.csv.zst
---

# Russian Wikinews corpus

A corpus of articles from Russian Wikinews, extracted from the official Wikimedia XML dump into three linked tables. Plain text only: wiki markup, service templates and categories are stripped from the article text.

Корпус статей Русских Викиновостей, извлечённый из официального XML-дампа Wikimedia в три связанные таблицы. В тексте статей нет вики-разметки, служебных шаблонов и категорий.

- **Code and documentation:** https://github.com/Arphey888/wikinews-corpus
- **Source dump:** `ruwikinews-<YYYYMMDD>-pages-articles.xml` from https://dumps.wikimedia.org/ruwikinews/
- **Schema version:** `v0.1-lite` (printed by the parser)
- **Parser commit:** `<git rev-parse HEAD>`

## Files

All files are CSV (UTF-8) compressed with Zstandard (`--ultra -22`).

| File | One row is | Fields |
|---|---|---|
| `articles.csv.zst` | one article | `page_id`, `title`, `date`, `origin_type`, `origin_name`, `text_plain` |
| `categories.csv.zst` | one unique category | `category_id`, `name` |
| `article_categories.csv.zst` | an article–category link | `page_id`, `category_id` |

### Fields of `articles`

| Field | Description |
|---|---|
| `page_id` | page id from the dump (`<page><id>`), not a revision id |
| `title` | article title |
| `date` | event date `YYYY-MM-DD` from the `{{дата}}` template; empty if the template is missing or the date format is not recognized |
| `origin_type` | `external_import` (uploaded by a bot from an external source), `wikinews_original` (original interview), or `unknown` |
| `origin_name` | name of the external source for `external_import`; `Русские Викиновости` for `wikinews_original`; otherwise empty |
| `text_plain` | readable text without wiki markup; the "Sources" section is cut off |

## Usage

```bash
python -m pip install pandas zstandard huggingface_hub
```

```python
import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "<hf-username>/<dataset-name>"
path = hf_hub_download(REPO, "articles.csv.zst", repo_type="dataset")
articles = pd.read_csv(path, keep_default_na=False)   # .zst is detected automatically
print(articles.head())
```

Or with the `datasets` library:

```python
from datasets import load_dataset

articles = load_dataset("<hf-username>/<dataset-name>", "articles", split="train")
```

A complete example (joining articles with categories) is in the GitHub repository: `examples/load_from_hf.py`.

## How it was made

The dump was processed by `src/parse_dump.py` from the GitHub repository above, and each CSV was compressed with `zstd --ultra -22`. The parser reads the XML as a stream; only main-namespace pages (`ns = 0`) are kept, redirects are skipped.

## Known limitations

- Articles whose date could not be normalized have an empty `date`; the raw value is not stored.
- Sections named "Ссылки" ("Links") instead of "Источники" ("Sources") are not cut off and remain in `text_plain`.
- Wiki tables and HTML entities are not cleaned in `text_plain`.
- Some `text_plain` values may start with a stray `]]` (a nested link in an image caption).
- Parsing quality flags are not included in this lightweight schema.

## License

Wikinews content is published under a Creative Commons Attribution license (CC BY 2.5 at the time of writing; please verify on the project's pages before publishing). Articles with `origin_type = external_import` were uploaded from external sources and may carry their own terms; check them before reusing. When reusing, credit Wikinews and the authors of the articles.

## Citation

```bibtex
@misc{wikinews_ru_corpus,
  title        = {Russian Wikinews corpus},
  author       = {<your name>},
  year         = {2026},
  howpublished = {\url{https://huggingface.co/datasets/<hf-username>/<dataset-name>}}
}
```
