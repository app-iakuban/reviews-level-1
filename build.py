#!/usr/bin/env python3
"""Сборка v2: мозаика лиц в hero + стена кружочков + аватар-ряд финала.

Данные: data/quotes_p{1,2,3}.json. Порядок: свежий выпуск сверху (p3 → p2 → p1).
Фото: assets/people/<key>.jpg (из фотоохоты); если фото нет — фолбэк на
assets/posters/<key>.jpg (кадр из Zoom). Числа-статистика — по data-stat.
Блоки «Как проверить академию» и FAQ «Отзывы и результаты» — из data/faq.json
(29.09.2026, этап 7 SERM: LLM-readiness), они же дают FAQPage в JSON-LD.

Запуск:  python3 build.py [--media local|kinescope]
  local     — data-video = media/pN/<file>.mp4 (локальный превью)
  kinescope — embed-ссылки из data/kinescope.json (после заливки видео)
"""
import json
import html
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
INDEX = HERE / "index.html"
PEOPLE = HERE / "assets" / "people"

MEDIA_MODE = "kinescope" if "--media" in sys.argv and "kinescope" in sys.argv else "local"

def dur_iso(d):
    m, s = d.split(":")
    return f"PT{int(m)}M{int(s)}S"


MADRID = ZoneInfo("Europe/Madrid")


def upload_iso(day):
    """uploadDate у VideoObject должен быть полным ISO 8601 с таймзоной.

    Одной даты Google не хватает: Search Console жалуется «missing a timezone»
    и «invalid datetime value» (письмо 08.08.2026). Берём полдень по Мадриду —
    смещение подставляется по дате (зимой +01:00, летом +02:00).
    """
    return datetime.fromisoformat(day).replace(hour=12, tzinfo=MADRID).isoformat(timespec="seconds")

MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def date_ru(day):
    """'2026-07-25' → '25 июля 2026'. Даты выпусков и дата проверки блока «Как проверить»."""
    y, m, d = (int(x) for x in day.split("-"))
    return f"{d} {MONTHS_RU[m - 1]} {y}"


def plural(n, one, few, many):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many

# Мозаика hero: 16 плиток, 4×4 на десктопе. Первые 12 — отобранные Алексеем лучшие отзывы
# (09.08.2026): на мобилке видны ровно они (CSS прячет .mtile:nth-child(n+13)), и по первому
# экрану кликают чаще всего. Последние 4 — добор до ровного ряда, микс потоков.
MOSAIC = [
    "p2_13_valeriya_pozhichkevich", "p1_01_mariya_silaeva", "p3_09_nursulu_tsupko", "p2_01_andrey_idrisov",
    "p3_12_olga_meerbach", "p2_10_mariya_gnitsevich", "p1_29_nadya_eliseeva", "p3_08_marina_belaya",
    "p2_18_tatyana_bogunova", "p1_27_yaromila_yulanova", "p2_03_veniamin_kozlovskiy", "p1_02_tamilla_buhmiller",
    "p3_04_irina_nakonechnaya", "p1_07_denis_boyko", "p2_14_polina_kartashova", "p3_06_nina_marabyan",
]
# Аватар-ряд в финале
AVATARS = MOSAIC[:16]


def load_cohorts():
    cohorts = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(DATA.glob("quotes_p*.json"))]
    cohorts.sort(key=lambda c: c["graduation"], reverse=True)
    return cohorts


def kinescope_map():
    f = DATA / "kinescope.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def key_of(cohort, item):
    return f'p{cohort["cohort"]}_{item["file"][:-4]}'


def face_src(key):
    """Путь к фото + ?v=mtime — кэш-бастинг: браузер Алексея показывал старые фото из кэша."""
    p = PEOPLE / f"{key}.jpg"
    if not p.exists():
        p = HERE / "assets" / "posters" / f"{key}.jpg"
        rel = f"assets/posters/{key}.jpg"
    else:
        rel = f"assets/people/{key}.jpg"
    return f"{rel}?v={int(p.stat().st_mtime)}"


def video_src(cohort, item, kmap):
    if MEDIA_MODE == "kinescope":
        key = key_of(cohort, item)
        if key not in kmap:
            raise SystemExit(f"нет kinescope-ссылки для {key}")
        return kmap[key]
    return f'media/p{cohort["cohort"]}/{item["file"]}'


def pcard(cohort, item, kmap):
    """Карточка стены: article → кнопка-фото, h3 имя, blockquote цитата, footer с датой выпуска в time.

    blockquote/footer/time — семантика типа «отзывы о компании» (skill seo-llm-readiness,
    page_type_rules §8, 29.09.2026); классы pquote/pdur сохранены, CSS не менялся.
    """
    key = key_of(cohort, item)
    name = html.escape(item["name"])
    quote = html.escape(item["quote"])
    src = html.escape(video_src(cohort, item, kmap))
    grad = cohort["graduation"]
    return (
        f'<article class="pcard reveal">\n'
        f'  <button class="pcircle" data-video="{src}" data-name="{name}" data-quote="«{quote}»" '
        f'aria-label="Видеоотзыв: {name}">'
        f'<img src="{face_src(key)}" alt="{name}" width="560" height="560" loading="lazy">'
        f'<span class="pplay" aria-hidden="true"></span>'
        f'</button>\n'
        f'  <h3>{name}</h3>\n'
        f'  <blockquote class="pquote">«{quote}»</blockquote>\n'
        f'  <footer class="pdur"><time datetime="{grad}">{date_ru(grad)}</time></footer>\n'
        f'</article>'
    )


def ccard(case, index, kmap):
    """Карточка кейса для карусели «Результаты выпускников».

    case: {key?, name, role, was, now, quote} — key указывает на карточку стены
    (фото + видео того же человека); без key фото берётся из photo (путь).
    «Было/стало» размечено dl: dt «До программы» / «После программы» скрыты визуально
    (.sr-only), но остаются в HTML — иначе парсер не понимает, какая строка «до», а какая «после».
    """
    name = html.escape(case["name"])
    role = html.escape(case.get("role", ""))
    was = html.escape(case["was"])
    now = html.escape(case["now"])
    quote = html.escape(case["quote"])
    key = case.get("key")
    if key:
        img = face_src(key)
        c, it = index[key]
        video = html.escape(video_src(c, it, kmap))
        vbtn = (
            f'\n  <button class="cvideo" data-video="{video}" data-name="{name}" '
            f'data-quote="«{html.escape(it["quote"])}»"><span class="ic" aria-hidden="true"></span>'
            f'Смотреть видеоотзыв</button>'
        )
    else:
        img = html.escape(case["photo"])
        vbtn = ""
    return (
        f'<article class="ccard">\n'
        f'  <div class="ccard-top">'
        f'<img src="{img}" alt="{name}" width="120" height="120" loading="lazy">'
        f'<div><h3 class="cname">{name}</h3><div class="crole">{role}</div></div></div>\n'
        f'  <dl class="cab">\n'
        f'    <div class="row was"><dt class="sr-only">До программы</dt><dd>{was}</dd></div>\n'
        f'    <div class="row now"><dt class="sr-only">После программы</dt><dd>{now}</dd></div>\n'
        f'  </dl>\n'
        f'  <q>{quote}</q>{vbtn}\n'
        f'</article>'
    )


BASE_URL = "https://iakuban.com/reviews/level-1"
PAGE_URL = BASE_URL + "/"   # канонический адрес статики — со слэшем
PUBLISHED = "2026-08-07"     # день публикации страницы («го» Алексея 07.08.2026)


def load_faq():
    f = DATA / "faq.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def fill(text, ctx):
    """Плейсхолдеры faq.json: {total}, {total_word}, {updated_time}. Без str.format — в HTML есть фигурные скобки CSS."""
    for k, v in ctx.items():
        text = text.replace("{" + k + "}", v)
    return text


def strip_tags(s):
    """Текст ответа для FAQPage: все теги снимаем, кроме <a href> (Google допускает ссылки в acceptedAnswer.text;
    без них в разметке висело бы «Ссылки: Яндекс.Карты, b17.ru…» без адресов). target/rel у ссылок убираем."""
    s = re.sub(r'<a\s+href="([^"]+)"[^>]*>', r'<a href="\1">', s)
    s = re.sub(r"<(?!a href=|/a>)[^>]+>", "", s)
    return html.unescape(s).replace("\xa0", " ")


def verify_html(faq, ctx):
    return "\n".join(
        f'<div class="vitem">\n  <dt>{html.escape(v["dt"])}</dt>\n  <dd>{fill(v["dd"], ctx)}</dd>\n</div>'
        for v in faq["verify"]
    )


def faq_html(faq, ctx):
    out = []
    for i, it in enumerate(faq["items"], 1):
        out.append(
            f'<details class="faq-item" id="faq-{i}">\n'
            f'  <summary><h3>{html.escape(it["q"])}</h3></summary>\n'
            f'  <div class="faq-body"><p>{fill(it["a"], ctx)}</p></div>\n'
            f'</details>'
        )
    return "\n".join(out)


def jsonld(ordered, kmap, faq, ctx):
    """@graph: CollectionPage + ItemList из VideoObject (без aggregateRating — решение Алексея №9)
    и FAQPage из data/faq.json (текст ответов = видимый текст без тегов)."""
    items = []
    for pos, (c, it) in enumerate(ordered, 1):
        key = key_of(c, it)
        video = {
            "@type": "VideoObject",
            "name": f'Видеоотзыв: {it["name"]}',
            "description": it["quote"],
            "thumbnailUrl": f"{BASE_URL}/assets/posters/{key}.jpg",
            "uploadDate": upload_iso(c["graduation"]),
            "duration": dur_iso(it["duration"]),
            "inLanguage": "ru",
        }
        if MEDIA_MODE == "kinescope" and key in kmap:
            video["embedUrl"] = kmap[key]
        items.append({"@type": "ListItem", "position": pos, "item": video})
    org = {
        "@type": "EducationalOrganization",
        "@id": "https://iakuban.com/#organization",
        "name": "Iakuban Coaching Academy",
        "alternateName": [
            "Академия коучинга Алексея Якубана",
            "Академия Алексея Якубана",
            "Академия Якубана",
            "IAKUBAN COACHING ACADEMY S.L.",
        ],
        "url": "https://iakuban.com",
        "logo": "https://iakuban.com/logo-512.png",
        # sameAs — ровно три профиля из BRANDCORE 6.3 (карточка Я.Бизнеса числовой формой)
        "sameAs": [
            "https://www.youtube.com/@iakuban",
            "https://t.me/iakuban",
            "https://yandex.ru/maps/org/86349660849/",
        ],
        "founder": {
            "@type": "Person",
            "@id": "https://iakuban.com/#person",
            "name": "Алексей Якубан",
            "alternateName": "Aleksei Iakuban",
            "description": "Основатель Iakuban Coaching Academy, коуч PCC ICF, 2 500+ часов коучинговой практики",
        },
    }
    page = {
        "@type": "CollectionPage",
        "@id": PAGE_URL + "#webpage",
        "name": "Отзывы об академии Алексея Якубана: видеоотзывы выпускников первой ступени (аккредитация ICF, Level 1)",
        "description": f"Отзывы выпускников об академии коучинга Алексея Якубана: {len(ordered)} видеоистории о программе подготовки коучей — записаны в день вручения сертификатов, без сценария.",
        "url": PAGE_URL,
        "inLanguage": "ru",
        "datePublished": PUBLISHED,
        "about": {"@id": "https://iakuban.com/#organization"},
        "publisher": org,
        "isPartOf": {"@type": "WebSite", "@id": "https://iakuban.com/#website", "name": "Iakuban Coaching Academy", "url": "https://iakuban.com"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(ordered), "itemListElement": items},
    }
    graph = [page]
    if faq:
        page["dateModified"] = faq["updated"]
        graph.append({
            "@type": "FAQPage",
            "@id": PAGE_URL + "#faq",
            "url": PAGE_URL + "#faq",
            "name": faq["faq_title"],
            "inLanguage": "ru",
            "isPartOf": {"@id": PAGE_URL + "#webpage"},
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": it["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(fill(it["a"], ctx))},
                }
                for it in faq["items"]
            ],
        })
    data = {"@context": "https://schema.org", "@graph": graph}
    return ('<script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            + "\n</script>")


def replace_block(src, start, end, content):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(src):
        raise SystemExit(f"в index.html нет блока {start} … {end}")
    # lambda: content подставляется литерально (в JSON-LD есть \" — строковая замена re.sub их съедает)
    return pattern.sub(lambda m: start + "\n" + content + "\n    " + end, src)


def main():
    cohorts = load_cohorts()
    kmap = kinescope_map()
    faq = load_faq()

    SKIP = {"p2_02_ekaterina_baltabaeva"}  # дубль: она есть в потоке 3, двойную карточку Алексей счёл ошибкой
    index = {}
    ordered = []
    for c in cohorts:
        for it in c["items"]:
            k = key_of(c, it)
            index[k] = (c, it)
            if k not in SKIP:
                ordered.append((c, it))

    mosaic_html = []
    for k in MOSAIC:
        c, it = index[k]
        name = html.escape(it["name"])
        src = html.escape(video_src(c, it, kmap))
        quote = html.escape(it["quote"])
        mosaic_html.append(
            f'<button class="mtile" data-video="{src}" data-name="{name}" data-quote="«{quote}»" '
            f'aria-label="Видеоотзыв: {name}">'
            f'<img src="{face_src(k)}" alt="{name}" width="560" height="560" '
            f'{"" if MOSAIC.index(k) < 8 else chr(108)+"oading=lazy "}>'
            f'<span class="mname" aria-hidden="true">{name}</span>'
            f'<span class="mplay" aria-hidden="true"></span>'
            f'</button>'
        )

    grid_html = "\n".join(pcard(c, it, kmap) for c, it in ordered)

    cases_file = DATA / "cases.json"
    cases = json.loads(cases_file.read_text(encoding="utf-8")) if cases_file.exists() else []
    cases_html = "\n".join(ccard(cs, index, kmap) for cs in cases)
    avatars_html = "\n".join(
        f'<img src="{face_src(k)}" alt="" width="52" height="52" loading="lazy">' for k in AVATARS
    )

    total = len(ordered)
    ctx = {
        "total": str(total),
        "total_word": plural(total, "видеоотзыв", "видеоотзыва", "видеоотзывов"),
        "updated_time": (f'<time datetime="{faq["updated"]}">{date_ru(faq["updated"])} года</time>' if faq else ""),
    }
    src = INDEX.read_text(encoding="utf-8")
    src = replace_block(src, "<!-- MOSAIC:START -->", "<!-- MOSAIC:END -->", "\n".join(mosaic_html))
    src = replace_block(src, "<!-- GRID:START -->", "<!-- GRID:END -->", grid_html)
    src = replace_block(src, "<!-- CASES:START -->", "<!-- CASES:END -->", cases_html)
    src = replace_block(src, "<!-- AVATARS:START -->", "<!-- AVATARS:END -->", avatars_html)
    if faq:
        src = replace_block(src, "<!-- VERIFY:START -->", "<!-- VERIFY:END -->", verify_html(faq, ctx))
        src = replace_block(src, "<!-- FAQ:START -->", "<!-- FAQ:END -->", faq_html(faq, ctx))
        src = re.sub(r'(id="verify-title"[^>]*>)[^<]*', lambda m: m.group(1) + html.escape(faq["verify_title"]), src)
        src = re.sub(r'(id="verify-intro"[^>]*>)[^<]*', lambda m: m.group(1) + html.escape(faq["verify_intro"]), src)
        src = re.sub(r'(id="faq-title"[^>]*>)[^<]*', lambda m: m.group(1) + html.escape(faq["faq_title"]), src)
        src = re.sub(r'(id="faq-intro"[^>]*>)[^<]*', lambda m: m.group(1) + html.escape(faq["faq_intro"]), src)
    src = replace_block(src, "<!-- JSONLD:START -->", "<!-- JSONLD:END -->", jsonld(ordered, kmap, faq, ctx))
    src = re.sub(r'(data-stat="total"[^>]*>)[^<]*', rf'\g<1>{total}', src)
    src = re.sub(r'(data-stat="cohorts"[^>]*>)[^<]*', rf'\g<1>{len(cohorts)}', src)
    src = re.sub(r"\d+ видеоистори", f"{total} видеоистори", src)  # meta/og description — живое число
    src = re.sub(r"\d+ видео выпускников", f"{total} видео выпускников", src)  # <title>
    INDEX.write_text(src, encoding="utf-8")

    n_photo = sum(1 for k in index if (PEOPLE / f"{k}.jpg").exists())
    print(f"ok: total={total}, mosaic={len(MOSAIC)}, фото={n_photo}, фолбэк-постер={total - n_photo}, "
          f"media={MEDIA_MODE}, faq={len(faq['items']) if faq else 0}, updated={faq['updated'] if faq else '-'}")


if __name__ == "__main__":
    main()
