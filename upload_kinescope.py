#!/usr/bin/env python3
"""Заливка всех роликов лендинга в Kinescope + сборка data/kinescope.json (key → embed_link).

Идемпотентен: перед заливкой читает список видео воркспейса; ролик с тайтлом=key
не заливается повторно, ссылка берётся из существующего. Запуск повторно безопасен.

Токен: ~/.config/iakuban/secrets/kinescope-token (права токена должны включать Upload files!)
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TOKEN = (Path.home() / ".config/iakuban/secrets/kinescope-token").read_text().strip()
PARENT_ID = "192aea8b-a47d-45d4-83e5-5fd38c52d289"  # проект "My project"
VIDEOS_DIR = Path.home() / "Desktop" / "Отзывы выпускников Level 1"


def api(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def existing_videos():
    """title → video dict, по всем страницам."""
    out, page = {}, 1
    while True:
        d = api(f"https://api.kinescope.io/v1/videos?per_page=100&page={page}")
        for v in d["data"]:
            out[v["title"]] = v
        if page * 100 >= d["meta"]["pagination"]["total"]:
            return out
        page += 1


def cohort_folder(cohort_num):
    hits = [p for p in VIDEOS_DIR.iterdir() if p.is_dir() and p.name.startswith(f"{cohort_num} поток")]
    assert len(hits) == 1, f"папка потока {cohort_num}: {hits}"
    return hits[0]


def upload(path, title):
    """curl-ом (стриминг с диска), возвращает data-объект ответа."""
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://uploader.kinescope.io/v2/video",
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", f"X-Parent-ID: {PARENT_ID}",
         "-H", f"X-Video-Title: {title}",
         "-H", "Content-Type: video/mp4",
         "--data-binary", f"@{path}"],
        capture_output=True, text=True, timeout=1800)
    resp = json.loads(r.stdout)
    if "error" in resp:
        raise RuntimeError(f"{title}: {resp['error']}")
    return resp["data"]


def main():
    cohorts = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(DATA.glob("quotes_p*.json"))]
    have = existing_videos()
    kmap_links = {}   # key -> embed_link
    todo = []
    for c in cohorts:
        folder = cohort_folder(c["cohort"])
        for it in c["items"]:
            key = f'p{c["cohort"]}_{it["file"][:-4]}'
            if key in have:
                kmap_links[key] = have[key]["embed_link"]
            else:
                todo.append((key, folder / it["file"]))

    print(f"всего {sum(len(c['items']) for c in cohorts)}, уже в кинескопе {len(kmap_links)}, заливаем {len(todo)}", flush=True)

    for i, (key, path) in enumerate(todo, 1):
        assert path.exists(), f"нет файла {path}"
        for attempt in (1, 2):
            try:
                d = upload(path, key)
                kmap_links[key] = d["embed_link"]
                print(f"[{i}/{len(todo)}] {key} ok", flush=True)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"[{i}/{len(todo)}] {key} FAIL: {e}", flush=True)
                else:
                    print(f"[{i}/{len(todo)}] {key} retry: {e}", flush=True)
                    time.sleep(5)

    out = DATA / "kinescope.json"
    out.write_text(json.dumps(dict(sorted(kmap_links.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"kinescope.json: {len(kmap_links)} ссылок", flush=True)

    missing = [f'p{c["cohort"]}_{it["file"][:-4]}' for c in cohorts for it in c["items"]
               if f'p{c["cohort"]}_{it["file"][:-4]}' not in kmap_links]
    if missing:
        print("НЕ ЗАЛИТО:", ", ".join(missing), flush=True)
        sys.exit(1)
    print("ГОТОВО: все ролики в Kinescope", flush=True)


if __name__ == "__main__":
    main()
