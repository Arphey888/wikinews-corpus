#!/usr/bin/env python3
"""Пример: как обратиться к набору данных Russian Wikinews на Hugging Face.

Установка (один раз):
    python -m pip install pandas zstandard huggingface_hub

Запуск (подставьте имя вашего набора на Hugging Face):
    python examples/load_from_hf.py --repo <hf-username>/<dataset-name>

Проверка без интернета, на локальных файлах .csv.zst:
    python examples/load_from_hf.py --local-dir D:/wikinews_zst

Что делает скрипт: скачивает три файла (при повторном запуске берёт их из
локального кэша), читает их в pandas, печатает размеры и показывает два
примера работы: самые частые категории и поиск статьи по слову в заголовке.
Для набора, который не помещается в память, см. закомментированный пример
чтения кусками (chunksize) в конце файла.
"""
import argparse
import os

import pandas as pd

FILES = {
    "articles": "articles.csv.zst",
    "categories": "categories.csv.zst",
    "article_categories": "article_categories.csv.zst",
}


def get_paths(repo, local_dir):
    """Возвращает словарь имя -> путь к файлу (локальный или из кэша HF)."""
    if local_dir:
        return {k: os.path.join(local_dir, v) for k, v in FILES.items()}
    from huggingface_hub import hf_hub_download
    return {k: hf_hub_download(repo_id=repo, filename=v, repo_type="dataset")
            for k, v in FILES.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="<hf-username>/<dataset-name>",
                    help="имя набора на Hugging Face, например user/ruwikinews-corpus")
    ap.add_argument("--local-dir", help="папка с локальными файлами .csv.zst (вместо загрузки)")
    args = ap.parse_args()

    paths = get_paths(args.repo, args.local_dir)

    # pandas сам распознаёт .zst по расширению (нужен пакет zstandard)
    articles = pd.read_csv(paths["articles"], dtype={"page_id": "int64"},
                           keep_default_na=False)
    categories = pd.read_csv(paths["categories"])
    links = pd.read_csv(paths["article_categories"])

    print(f"Статей: {len(articles):,}; категорий: {len(categories):,}; связей: {len(links):,}")
    print("Поля articles:", ", ".join(articles.columns))

    # Пример 1: самые частые категории
    top = (links.merge(categories, on="category_id")
                .groupby("name").size().sort_values(ascending=False).head(10))
    print("\nСамые частые категории:")
    print(top.to_string())

    # Пример 2: статьи по слову в заголовке и категории одной статьи
    found = articles[articles["title"].str.contains("космос", case=False, na=False)]
    print(f"\nСтатей со словом «космос» в заголовке: {len(found)}")
    if len(found):
        row = found.iloc[0]
        cats = links[links["page_id"] == row["page_id"]].merge(categories, on="category_id")
        print("Заголовок:", row["title"])
        print("Дата:", row["date"] or "не указана")
        print("Категории:", ", ".join(cats["name"]))
        print("Начало текста:", row["text_plain"][:200].replace("\n", " "), "...")

    # Альтернатива: загрузка через библиотеку datasets
    #   from datasets import load_dataset
    #   ds = load_dataset(args.repo, "articles", split="train")
    #
    # Чтение большого файла кусками, чтобы не держать всё в памяти:
    #   for chunk in pd.read_csv(paths["articles"], chunksize=50_000, keep_default_na=False):
    #       ...  # обработка chunk


if __name__ == "__main__":
    main()
