#!/usr/bin/env python3
"""Вырезает из большого дампа небольшой корректный XML-фрагмент.

Работает одинаково в Windows (cmd), Linux и macOS, понимает .xml и .xml.bz2.
Заголовок (<mediawiki>, <siteinfo>) сохраняется, в конце ставится </mediawiki>,
поэтому все теги в результате закрыты.

Примеры:
    python tools/make_sample.py dump.xml.bz2 data/sample.xml --pages 50
    python tools/make_sample.py dump.xml.bz2 data/sample.xml --title "Обводном канале снесли" --title "Лёвочкин"
    python tools/make_sample.py dump.xml.bz2 data/sample.xml --pages 30 --title "Лёвочкин"

--pages N    взять первые N страниц с ns = 0 (по умолчанию 0)
--title S    добавить страницу, в заголовке которой есть подстрока S (можно несколько раз)
"""
import argparse
import bz2
import sys


def open_text(path):
    if str(path).endswith(".bz2"):
        return bz2.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--pages", type=int, default=0)
    ap.add_argument("--title", action="append", default=[])
    args = ap.parse_args()
    if not args.pages and not args.title:
        ap.error("укажите --pages и/или --title")

    wanted = [t.lower() for t in args.title]
    found_titles = set()
    taken = 0
    header, page, in_page = [], [], False

    with open_text(args.src) as fin, open(args.dst, "w", encoding="utf-8", newline="") as fout:
        for line in fin:
            if not in_page:
                if "<page>" in line:
                    in_page, page = True, [line]
                elif not header or "</siteinfo>" not in "".join(header):
                    header.append(line)
                continue
            page.append(line)
            if "</page>" in line:
                in_page = False
                block = "".join(page)
                if header:
                    fout.write("".join(header))
                    header = []
                    fout.write("")  # заголовок записан один раз
                title = block.split("<title>", 1)[1].split("</title>", 1)[0]
                is_ns0 = "<ns>0</ns>" in block
                match = [w for w in wanted if w in title.lower()]
                take = bool(match) or (is_ns0 and taken < args.pages)
                if take:
                    fout.write(block)
                    if match:
                        found_titles.update(match)
                    else:
                        taken += 1
                done_pages = taken >= args.pages
                if done_pages and len(found_titles) == len(wanted):
                    break
        fout.write("</mediawiki>\n")

    missing = [t for t in wanted if t not in found_titles]
    print(f"Готово: {args.dst}. Первых страниц: {taken}, найдено по заголовку: {sorted(found_titles)}")
    if missing:
        print("Не найдено (просмотрен весь файл или до нужного числа страниц):", missing, file=sys.stderr)


if __name__ == "__main__":
    main()
