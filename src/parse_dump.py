#!/usr/bin/env python3
"""Парсер XML-дампа Русских Викиновостей -> три CSV (облегчённая схема v0.1-lite).

Выход:
    articles.csv            page_id, title, date, origin_type, origin_name, text_plain
    categories.csv          category_id, name
    article_categories.csv  page_id, category_id

Запуск:
    python src/parse_dump.py data/sample.xml -o output/
    python src/parse_dump.py ruwikinews-...-pages-articles.xml.bz2 -o output/

Только стандартная библиотека Python 3.9+.
"""
import argparse
import bz2
import csv
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

SCHEMA_VERSION = "0.1-lite"

ARTICLE_FIELDS = ["page_id", "title", "date", "origin_type", "origin_name", "text_plain"]

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

# Шаблоны, которые несут служебную информацию и удаляются из текста
# после того, как из них всё нужное извлечено.
SERVICE_TEMPLATES = ("дата", "тема", "категории")
SERVICE_PREFIXES = ("загружено ботом", "эксклюзивное интервью")

SOURCES_RE = re.compile(r"^[ \t]*(=+)[ \t]*Источники[ \t]*\1[ \t]*$",
                        re.IGNORECASE | re.MULTILINE)
CATEGORY_LINK_RE = re.compile(r"\[\[\s*Категория\s*:\s*([^\]|]+?)\s*(?:\|[^\]]*)?\]\]",
                              re.IGNORECASE)


# ---------------------------------------------------------------- шаблоны

def find_templates(text):
    """Находит шаблоны верхнего уровня {{...}} с учётом вложенности.

    Возвращает список (name, args, start, end). name нормализован
    (strip). args это список строк, разделённых по | на верхнем уровне
    (вложенные {{ }} и [[ ]] не разрываются).
    """
    result = []
    i, n = 0, len(text)
    while i < n - 1:
        if text[i:i + 2] == "{{":
            depth, j = 1, i + 2
            while j < n - 1 and depth:
                two = text[j:j + 2]
                if two == "{{":
                    depth += 1
                    j += 2
                elif two == "}}":
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if depth == 0:
                inner = text[i + 2:j - 2]
                parts = split_top_level(inner)
                result.append((parts[0].strip(), [p.strip() for p in parts[1:]], i, j))
                i = j
                continue
        i += 1
    return result


def split_top_level(s):
    """Делит строку по | вне вложенных {{ }} и [[ ]]."""
    parts, buf, curly, square, i = [], [], 0, 0, 0
    while i < len(s):
        two = s[i:i + 2]
        if two == "{{":
            curly += 1; buf.append(two); i += 2; continue
        if two == "}}":
            curly -= 1; buf.append(two); i += 2; continue
        if two == "[[":
            square += 1; buf.append(two); i += 2; continue
        if two == "]]":
            square -= 1; buf.append(two); i += 2; continue
        if s[i] == "|" and curly == 0 and square == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(s[i])
        i += 1
    parts.append("".join(buf))
    return parts


def norm_name(name):
    return re.sub(r"\s+", " ", name).strip().lower()


def is_service(name):
    n = norm_name(name)
    return n in SERVICE_TEMPLATES or n.startswith(SERVICE_PREFIXES)


# ---------------------------------------------------------------- правила

def parse_date(raw):
    """'15 февраля 2011' -> date(2011, 2, 15); иначе None."""
    m = re.fullmatch(r"\s*(\d{1,2})\s+([А-Яа-яЁё]+)\s+(\d{4})\s*(?:г\.?|года)?\s*", raw)
    if not m:
        return None
    month = MONTHS.get(m.group(2).lower())
    if not month:
        return None
    try:
        return date(int(m.group(3)), month, int(m.group(1)))
    except ValueError:
        return None


def clean_cat(name):
    return re.sub(r"\s+", " ", name).strip()


def extract_metadata(wikitext):
    """Извлекает дату, происхождение и категории из полного wikitext."""
    templates = find_templates(wikitext)

    # --- дата: берётся первый шаблон {{дата|...}}; не нормализуется: пусто
    date_iso = None
    for name, args, _, _ in templates:
        if norm_name(name) == "дата":
            d = parse_date(args[0]) if args else None
            date_iso = d.isoformat() if d else None
            break

    # --- происхождение
    origin_type, origin_name = "unknown", None
    bot = [t for t in templates if norm_name(t[0]).startswith("загружено ботом")]
    interview = [t for t in templates if norm_name(t[0]).startswith("эксклюзивное интервью")]
    if bot:
        origin_type = "external_import"
        # {{Загружено ботом в архив|NewsBots|Канонер}}: источник во 2-м параметре
        if len(bot[0][1]) >= 2 and bot[0][1][1]:
            origin_name = bot[0][1][1]
    elif interview:
        origin_type, origin_name = "wikinews_original", "Русские Викиновости"

    # --- категории (имена, без повторов, в порядке появления)
    cats = []
    for name, args, _, _ in templates:
        if norm_name(name) in ("тема", "категории"):
            for a in args:
                if "=" in a:       # именованные параметры не категории
                    continue
                c = clean_cat(a)
                if c:
                    cats.append(c)
    for m in CATEGORY_LINK_RE.finditer(wikitext):
        c = clean_cat(m.group(1))
        if c:
            cats.append(c)

    return {
        "date": date_iso,
        "origin_type": origin_type, "origin_name": origin_name,
        "categories": list(dict.fromkeys(cats)),
    }


# ---------------------------------------------------------------- очистка

def build_wikitext(wikitext, origin_name=None):
    """Отсекает «Источники», убирает служебные шаблоны и категории.

    Шаблон внешнего источника ({{Канонер|...}}), имя которого совпало с
    origin_name, тоже считается служебным и удаляется.
    """
    m = SOURCES_RE.search(wikitext)
    body = wikitext[:m.start()] if m else wikitext

    # служебные шаблоны вырезаем с конца, чтобы не сбить индексы
    for name, _, s, e in reversed(find_templates(body)):
        if is_service(name) or (origin_name and norm_name(name) == norm_name(origin_name)):
            body = body[:s] + body[e:]
    body = CATEGORY_LINK_RE.sub("", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def to_plain(wikitext):
    t = wikitext
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<ref[^>/]*>.*?</ref>|<ref[^>]*/>", "", t, flags=re.S | re.I)
    # оставшиеся шаблоны удаляются целиком
    for _, _, s, e in reversed(find_templates(t)):
        t = t[:s] + t[e:]
    # файлы и изображения
    t = re.sub(r"\[\[\s*(?:Файл|File|Изображение|Image)\s*:[^\]]*\]\]", "", t, flags=re.I)
    # внутренние ссылки
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    # внешние ссылки [url текст] и [url]
    t = re.sub(r"\[(?:https?:)?//\S+\s+([^\]]+)\]", r"\1", t)
    t = re.sub(r"\[(?:https?:)?//\S+\]", "", t)
    # заголовки, курсив/жирный, html-теги
    t = re.sub(r"^=+\s*(.*?)\s*=+\s*$", r"\1", t, flags=re.M)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ---------------------------------------------------------------- XML

def local(tag):
    return tag.rsplit("}", 1)[-1]


def iter_pages(path):
    """Потоково отдаёт словари страниц; память не растёт."""
    opener = bz2.open if str(path).endswith(".bz2") else open
    with opener(path, "rb") as f:
        for _, elem in ET.iterparse(f, events=("end",)):
            if local(elem.tag) != "page":
                continue
            page = {"redirect": False, "text": ""}
            for ch in elem.iter():
                tag = local(ch.tag)
                if tag == "title":
                    page["title"] = ch.text or ""
                elif tag == "ns":
                    page["ns"] = (ch.text or "").strip()
                elif tag == "redirect":
                    page["redirect"] = True
                elif tag == "text":
                    page["text"] = ch.text or ""
            # <page><id> это первый прямой потомок id, не revision/contributor id
            for ch in elem:
                if local(ch.tag) == "id":
                    page["id"] = (ch.text or "").strip()
                    break
            elem.clear()
            yield page


def process_page(page):
    """Возвращает (строка articles, список имён категорий)."""
    wikitext = page["text"]
    meta = extract_metadata(wikitext)
    body = build_wikitext(wikitext, meta["origin_name"])
    row = {
        "page_id": page["id"],
        "title": page["title"],
        "date": meta["date"],
        "origin_type": meta["origin_type"],
        "origin_name": meta["origin_name"],
        "text_plain": to_plain(body),
    }
    return row, meta["categories"]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def run(src, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(sys.maxsize)
    links = set()          # (page_id, category_name)
    stats = {"seen": 0, "written": 0, "skipped_ns": 0, "skipped_redirect": 0}

    with open(out / "articles.csv", "w", encoding="utf-8", newline="") as fa:
        w = csv.DictWriter(fa, fieldnames=ARTICLE_FIELDS)
        w.writeheader()
        for page in iter_pages(src):
            stats["seen"] += 1
            if page.get("ns") != "0":
                stats["skipped_ns"] += 1
                continue
            if page["redirect"] or page["text"].lstrip().upper().startswith("#REDIRECT") \
                    or page["text"].lstrip().startswith("#перенаправление"):
                stats["skipped_redirect"] += 1
                continue
            row, cats = process_page(page)
            w.writerow({k: fmt(v) for k, v in row.items()})
            for name in cats:
                links.add((int(row["page_id"]), name))
            stats["written"] += 1

    names = sorted({n for _, n in links})
    ids = {n: i for i, n in enumerate(names, start=1)}   # детерминированно
    with open(out / "categories.csv", "w", encoding="utf-8", newline="") as fc:
        w = csv.writer(fc)
        w.writerow(["category_id", "name"])
        for n in names:
            w.writerow([ids[n], n])
    with open(out / "article_categories.csv", "w", encoding="utf-8", newline="") as fl:
        w = csv.writer(fl)
        w.writerow(["page_id", "category_id"])
        for pid, n in sorted(links, key=lambda x: (x[0], ids[x[1]])):
            w.writerow([pid, ids[n]])
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml", help="путь к XML или XML.bz2")
    ap.add_argument("-o", "--out", default="output", help="папка для CSV")
    args = ap.parse_args()
    stats = run(args.xml, args.out)
    print(f"Схема v{SCHEMA_VERSION}. Готово: {stats}")


if __name__ == "__main__":
    main()
