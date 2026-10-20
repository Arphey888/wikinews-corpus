#!/usr/bin/env python3
"""Сжимает файлы в формат .zst (Zstandard) без установки программы zstd.

Для каждого файла рядом создаётся файл с добавленным суффиксом .zst
(articles.csv -> articles.csv.zst). Исходные файлы не изменяются и не удаляются.
После сжатия файл распаковывается "на лету" и сверяется по SHA-256 с исходным.

Установка (один раз):
    python -m pip install zstandard

Примеры:
    python tools/compress_zst.py D:/out/articles.csv D:/out/categories.csv D:/out/article_categories.csv
    python tools/compress_zst.py D:/out/articles.csv --level 19      # быстрее, файл чуть больше

--level N     уровень сжатия 1..22 (по умолчанию 22, как `zstd --ultra -22`)
--threads N   число потоков; 0 = один поток (по умолчанию, лучшее сжатие),
              -1 = по числу ядер (быстрее, размер может чуть вырасти)
"""
import argparse
import hashlib
import os
import sys
import time

try:
    import zstandard
except ImportError:
    sys.exit("Не найден модуль zstandard. Установите: python -m pip install zstandard")

CHUNK = 1 << 20  # 1 МБ


def human(n):
    return f"{n / 1e6:.1f} МБ" if n >= 1e6 else f"{n / 1e3:.0f} КБ"


def sha256_of_stream(reader):
    h = hashlib.sha256()
    while True:
        chunk = reader.read(CHUNK)
        if not chunk:
            return h.hexdigest()
        h.update(chunk)


def compress_file(src, level, threads):
    dst = src + ".zst"
    size = os.path.getsize(src)
    cctx = zstandard.ZstdCompressor(level=level, threads=threads)
    h = hashlib.sha256()
    done, next_report, t0 = 0, 0.1, time.time()
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        with cctx.stream_writer(fout, size=size) as w:
            while True:
                chunk = fin.read(CHUNK)
                if not chunk:
                    break
                h.update(chunk)
                w.write(chunk)
                done += len(chunk)
                if size and done / size >= next_report:
                    print(f"  {src}: {done / size:5.0%}  ({time.time() - t0:.0f} с)", flush=True)
                    next_report += 0.1

    # проверка: распаковываем и сравниваем хеш с исходным
    with open(dst, "rb") as f:
        back = sha256_of_stream(zstandard.ZstdDecompressor().stream_reader(f))
    if back != h.hexdigest():
        os.remove(dst)
        sys.exit(f"ОШИБКА: проверка {dst} не прошла, файл удалён")

    out = os.path.getsize(dst)
    ratio = size / out if out else 0
    print(f"OK  {dst}: {human(size)} -> {human(out)} "
          f"(в {ratio:.1f} раза меньше), {time.time() - t0:.0f} с")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="файлы для сжатия")
    ap.add_argument("--level", type=int, default=22, choices=range(1, 23), metavar="1..22")
    ap.add_argument("--threads", type=int, default=0)
    args = ap.parse_args()
    for f in args.files:
        if not os.path.isfile(f):
            sys.exit(f"Файл не найден: {f}")
    for f in args.files:
        compress_file(f, args.level, args.threads)


if __name__ == "__main__":
    main()
