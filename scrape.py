#!/usr/bin/env python3
"""Collects public listing titles + links from open sources. Respects robots.txt.
Sources: emploi-public.ma (list pages), stage.ma (open offers, embedded page data),
dreamjob.ma and alwadifa-maroc.com (their public RSS feeds).
Only title, organisation, dates and the link are kept. Applying happens on the source site."""
import re, json, html, sys, time, datetime, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = {"User-Agent": "Mozilla/5.0 (compatible; FursaTalabaBot/1.0; +https://wwwhamiddd136-cloud.github.io/fursa-talaba/)"}
TODAY = datetime.date.today()
DELAY = 1.2


def get(u, tries=2):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf8", "replace")
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


FR_M = {m: i + 1 for i, m in enumerate("janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split())}
AR_M = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "ماي": 5, "مايو": 5, "يونيو": 6, "يونيه": 6,
        "يوليوز": 7, "يوليو": 7, "غشت": 8, "أغسطس": 8, "شتنبر": 9, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10,
        "نونبر": 11, "نوفمبر": 11, "دجنبر": 12, "ديسمبر": 12}


def date_fr(s):
    m = re.search(r"(\d{1,2}) ([a-zéûô]+) (\d{4})", (s or "").lower())
    if m and m.group(2) in FR_M:
        return "%s-%02d-%02d" % (m.group(3), FR_M[m.group(2)], int(m.group(1)))


def date_ar(s):
    m = re.search(r"(\d{1,2})\s+(" + "|".join(AR_M) + r")\s+(\d{4})", s or "")
    if m:
        return "%s-%02d-%02d" % (m.group(3), AR_M[m.group(2)], int(m.group(1)))


# city keywords (French / Arabic) -> Arabic label
CITIES = [
    ("الدار البيضاء", ["casablanca", "casa ", "الدار البيضاء", "البيضاء"]), ("الرباط", ["rabat", "الرباط"]), ("سلا", ["salé", "sale ", "سلا"]),
    ("مراكش", ["marrakech", "مراكش"]), ("فاس", ["fès", "fes ", "fès", "فاس"]), ("مكناس", ["meknès", "meknes", "مكناس"]),
    ("طنجة", ["tanger", "طنجة"]), ("أكادير", ["agadir", "أكادير", "اكادير"]), ("وجدة", ["oujda", "وجدة"]),
    ("تطوان", ["tétouan", "tetouan", "تطوان"]), ("القنيطرة", ["kénitra", "kenitra", "القنيطرة"]), ("تمارة", ["témara", "temara", "تمارة"]),
    ("المحمدية", ["mohammedia", "المحمدية"]), ("الجديدة", ["el jadida", "الجديدة"]), ("بني ملال", ["béni mellal", "beni mellal", "بني ملال"]),
    ("خريبكة", ["khouribga", "خريبكة"]), ("الناظور", ["nador", "الناظور"]), ("آسفي", ["safi", "آسفي"]), ("تازة", ["taza", "تازة"]),
    ("العيون", ["laâyoune", "laayoune", "العيون"]), ("الداخلة", ["dakhla", "الداخلة"]), ("ورزازات", ["ouarzazate", "ورزازات"]),
    ("برشيد", ["berrechid", "برشيد"]), ("سطات", ["settat", "سطات"]), ("الحسيمة", ["al hoceima", "الحسيمة"]),
    ("تارودانت", ["taroudant", "تارودانت"]), ("إنزكان", ["inezgane", "إنزكان"]), ("الصويرة", ["essaouira", "الصويرة"]),
    ("بركان", ["berkane", "بركان"]), ("تيزنيت", ["tiznit", "تيزنيت"]), ("خنيفرة", ["khénifra", "khenifra", "خنيفرة"]),
]


_AR = "\u0621-\u064A"


def _key_re(k):
    k = k.strip()
    if re.search("[" + _AR + "]", k):
        return re.compile("(?<![" + _AR + "])(?:ال|بال|لل|[وبلفك])?" + re.escape(k) + "(?![" + _AR + "])")
    return re.compile(r"(?<![a-zà-ÿ])" + re.escape(k) + r"(?![a-zà-ÿ])")


_CITY_RE = [(ar, [_key_re(k) for k in keys]) for ar, keys in CITIES]


def find_cities(text):
    t = (text or "").lower()
    return [ar for ar, res in _CITY_RE if any(r.search(t) for r in res)]


GRADES = [("Administrateur", "متصرف"), ("Technicien", "تقني"), ("Ingénieur d'Etat", "مهندس دولة"), ("Ingénieur d’Etat", "مهندس دولة"),
          ("Ingénieur", "مهندس"), ("Médecin", "طبيب"), ("Rédacteur", "محرر"), ("Assistant administratif", "مساعد إداري"),
          ("Assistant technique", "مساعد تقني"), ("Architecte", "مهندس معماري"), ("Infirmier", "ممرض"), ("Professeur", "أستاذ"),
          ("Pharmacien", "صيدلي"), ("Vétérinaire", "طبيب بيطري"), ("Juriste", "قانوني"), ("Conseiller", "مستشار"), ("Cadre", "إطار"),
          ("Agent", "عون"), ("Adjoint", "مساعد"), ("Secrétaire", "كاتب")]
ORD = {"1er": "الأولى", "1ère": "الأولى", "2ème": "الثانية", "3ème": "الثالثة", "4ème": "الرابعة", "5ème": "الخامسة"}


def title_ar(fr):
    for k, v in GRADES:
        if fr.lower().startswith(k.lower()):
            g = re.search(r"(\d(?:er|ère|ème)) grade", fr)
            e = re.search(r"[EÉé]chelle\s*(\d+)", fr)
            s = v
            if g:
                s += " من الدرجة " + ORD.get(g.group(1), g.group(1))
            if e:
                s += " - السلم " + e.group(1)
            return s
    return ""


MODE = {"sur site": "حضوري", "hybride": "مختلط", "télétravail": "عن بعد", "teletravail": "عن بعد"}
KIND = {"stage pfe": "تدريب نهاية الدراسة", "pré-embauche": "تدريب ما قبل التوظيف", "pre-embauche": "تدريب ما قبل التوظيف",
        "stage opérationnel": "تدريب عملي", "stage operationnel": "تدريب عملي"}
DUR = {"1 mois": "شهر واحد", "1 à 3 mois": "من شهر إلى 3 أشهر", "3 à 6 mois": "من 3 إلى 6 أشهر", "plus de 6 mois": "أكثر من 6 أشهر"}


def pay_ar(p):
    m = re.search(r"([\d\s\u202f\u00a0]+)\s*Dh", p or "")
    return (re.sub(r"\D", "", m.group(1)) + " درهم / شهر") if m else ""


# ---------- sources ----------
def _ep_page(p):
    time.sleep(DELAY)
    return get("https://www.emploi-public.ma/fr/concours-liste?page=%d" % p)


def src_emploi_public():
    from concurrent.futures import ThreadPoolExecutor
    first = get("https://www.emploi-public.ma/fr/concours-liste?page=1")
    tot = re.search(r"([\d\.\s]+) R[ée]sultats", first)
    n = int(re.sub(r"\D", "", tot.group(1))) if tot else 360
    import os
    pages = min(int(os.environ.get("EP_MAX_PAGES", "80")), n // 18 + 2)
    with ThreadPoolExecutor(4) as ex:
        htmls = [first] + list(ex.map(_ep_page, range(2, pages + 1)))
    out, seen = [], set()
    for h in htmls:
        for b in h.split("<!-- Item -->")[1:]:
            m = re.search(r'href="(/fr/concours/details/[^"]+)"', b)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            t = re.search(r'card-title">(.*?)</h2>', b, re.S)
            o = re.search(r'card-text">(.*?)</div>', b, re.S)
            foot = clean(b.split("card-footer")[-1])
            title = clean(t.group(1)) if t else ""
            title = re.sub(r"^Avis de (?:concours de recrutement|recrutement) (?:de |d['’])?", "", title) or title
            posts = re.search(r"(\d+) poste", foot)
            dl = re.search(r"Limite de dépôt : (.*?)(?: - \d|Date du|$)", foot)
            ex_ = re.search(r"Date du concours : (.*)$", foot)
            out.append(dict(type="concours", title=title, title_ar=title_ar(title), org=clean(o.group(1)) if o else "",
                            cities=[], posts=int(posts.group(1)) if posts else None, deadline=date_fr(dl.group(1)) if dl else None,
                            exam=date_fr(ex_.group(1)) if ex_ else None, source="emploi-public.ma",
                            url="https://www.emploi-public.ma" + m.group(1)))
    return out


def src_stage_ma():
    out, p = [], 1
    while p <= 12:
        h = get("https://stage.ma/offres-stage?page=%d" % p)
        m = re.search(r'<script data-page="app" type="application/json">(.*?)</script>', h, re.S)
        data = json.loads(m.group(1))["props"]["offers"]["data"]
        act = [x for x in data if not x.get("isExpired")]
        for x in act:
            md = (x.get("workMode") or "").lower()
            city = x.get("city") or ""
            cities = find_cities(city)
            out.append(dict(type="stage", title=x["title"], title_ar="", org=(x.get("company") or {}).get("name", ""),
                            cities=cities, mode=MODE.get(md, ""), kind=KIND.get((x.get("offerType") or "").lower(), ""),
                            duration=DUR.get((x.get("duration") or "").lower(), ""), pay=pay_ar(x.get("stipend")),
                            published=(x.get("publishedAt") or "")[:10], source="stage.ma",
                            url="https://stage.ma" + x["url"].split("?")[0]))
        if not act and p > 2:
            break
        p += 1
        time.sleep(DELAY)
    return out


def rss(url):
    root = ET.fromstring(get(url).encode("utf8"))
    for it in root.iter("item"):
        yield (clean(it.findtext("title")), (it.findtext("link") or "").strip(), clean(it.findtext("description")),
               it.findtext("pubDate"), [clean(c.text) for c in it.findall("category")])


def pub_date(s):
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except Exception:
        return None


def src_alwadifa():
    out = []
    for t, link, desc, pd, cats in rss("https://alwadifa-maroc.com/rss"):
        out.append(dict(type="concours", title=t, title_ar="", org="", cities=find_cities(t + " " + desc), posts=None,
                        deadline=date_ar(t), exam=None, published=pub_date(pd), source="alwadifa-maroc.com", url=link, lang="ar"))
    return out


def src_dreamjob(pages=4):
    out = []
    for p in range(1, pages + 1):
        try:
            items = list(rss("https://www.dreamjob.ma/feed/" + ("?paged=%d" % p if p > 1 else "")))
        except Exception:
            break
        for t, link, desc, pd, cats in items:
            path = link.split("dreamjob.ma/")[-1].split("/")[0]
            typ = {"stage": "stage", "emploi": "emploi", "emploi-public": "concours", "alwadifa": "concours"}.get(path)
            if not typ:
                continue
            out.append(dict(type=typ, title=t, title_ar="", org="", cities=find_cities(t + " " + " ".join(cats)),
                            published=pub_date(pd), deadline=date_fr(t), source="dreamjob.ma", url=link,
                            kind=("تدريب" if typ == "stage" else "")))
        time.sleep(DELAY)
    return out


SOURCES = [("emploi-public.ma", src_emploi_public), ("stage.ma", src_stage_ma),
           ("alwadifa-maroc.com", src_alwadifa), ("dreamjob.ma", src_dreamjob)]


def alive(x):
    if x.get("deadline"):
        return x["deadline"] >= TODAY.isoformat()
    pub = x.get("published")
    if pub:
        return (TODAY - datetime.date.fromisoformat(pub)).days <= 30
    return True


if __name__ == "__main__":
    try:
        old = json.load(open("data.json", encoding="utf8"))
    except Exception:
        old = {"items": [], "sources": {}}
    items, status = [], {}
    for name, fn in SOURCES:
        try:
            got = fn()
            status[name] = {"ok": True, "count": len(got)}
        except Exception as e:
            got = [x for x in old.get("items", []) if x.get("source") == name]
            status[name] = {"ok": False, "count": len(got), "error": str(e)[:120]}
            print("FAILED", name, e, file=sys.stderr)
        items += got
    seen, final = set(), []
    for x in items:
        if x["url"] in seen or not alive(x):
            continue
        seen.add(x["url"])
        final.append(x)
    final.sort(key=lambda x: x.get("published") or "0000", reverse=True)
    json.dump({"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": status, "items": final},
              open("data.json", "w", encoding="utf8"), ensure_ascii=False, indent=0)
    print(len(final), status)
