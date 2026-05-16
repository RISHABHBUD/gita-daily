"""
Generate gita_v8.json — all 700 Bhagavad Gita shlokas in V8 mega-combo format.

Sources per field:
  sanskrit          — vedicscriptures.github.io (slok field)
  transliteration   — gita/gita GitHub (cleaner diacritics)
  word_meanings     — gita/gita GitHub
  hindi             — Ramsukhdas via vedicscriptures (rams.ht)
  hindi_commentary  — Ramsukhdas via DharmicData/IIT Kanpur (rams.hc)
  english           — Mukundananda via holy-bhagavad-gita.org (scraped)
  commentary_en     — Mukundananda via holy-bhagavad-gita.org (scraped)
  purport_snippet   — Prabhupada via vedabase.io (scraped)
  lesson            — auto-generated from Mukundananda commentary (first 2 sentences)
  social_hooks      — auto-generated from lesson + chapter theme

Run:
  python generate_gita_v8.py              # full run
  python generate_gita_v8.py --resume     # resume from existing gita_v8.json
  python generate_gita_v8.py --test       # only fetch BG_02_47 as a test

Output: gita_v8.json (700 entries)

NOTE: This script scrapes 3 websites (Mukundananda, vedabase, DharmicData).
      It uses a 1.5s delay between verses to be polite. Total time ~30 min.
      Use --resume to continue if interrupted.
"""

import json
import re
import sys
import time
import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────

CHAPTER_VERSES = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29, 6: 47, 7: 30, 8: 28,
    9: 34, 10: 42, 11: 55, 12: 20, 13: 35, 14: 27, 15: 20,
    16: 24, 17: 28, 18: 78
}

CHAPTER_TITLES = {
    1:  "Arjuna Vishada Yoga",       2:  "Sankhya Yoga",
    3:  "Karma Yoga",                4:  "Jnana Karma Sanyasa Yoga",
    5:  "Karma Sanyasa Yoga",        6:  "Atma Samyama Yoga",
    7:  "Jnana Vijnana Yoga",        8:  "Aksara Brahma Yoga",
    9:  "Raja Vidya Raja Guhya Yoga",10: "Vibhuti Yoga",
    11: "Vishwarupa Darshana Yoga",  12: "Bhakti Yoga",
    13: "Kshetra Kshetrajna Vibhaga Yoga", 14: "Gunatraya Vibhaga Yoga",
    15: "Purushottama Yoga",         16: "Daivasura Sampad Vibhaga Yoga",
    17: "Shraddhatraya Vibhaga Yoga",18: "Moksha Sanyasa Yoga",
}

CHAPTER_CATEGORIES = {
    1: "arjuna_vishada",    2: "sankhya_yoga",       3: "karma_yoga",
    4: "jnana_yoga",        5: "karma_sanyasa_yoga", 6: "dhyana_yoga",
    7: "jnana_vijnana_yoga",8: "aksara_brahma_yoga", 9: "raja_vidya_yoga",
    10: "vibhuti_yoga",     11: "vishwarupa_yoga",   12: "bhakti_yoga",
    13: "kshetra_yoga",     14: "gunatraya_yoga",    15: "purushottama_yoga",
    16: "daivasura_yoga",   17: "shraddhatraya_yoga",18: "moksha_yoga",
}

# Chapter-level social hook templates (filled with verse-specific content at runtime)
CHAPTER_HOOKS = {
    1:  "Kya aap bhi kabhi itne overwhelmed hue ki kuch karna hi mushkil laga?",
    2:  "Gita ka sabse bada gyaan — aaj ke liye ek shlok",
    3:  "Karm karo bina fal ki chinta ke — Gita ka rahasya",
    4:  "Gyaan aur karm ka sangam — Gita Chapter 4",
    5:  "Karm karo ya tyaag karo? Gita deti hai seedha jawab",
    6:  "Mann ko kabu karna hai? Gita bataati hai kaise",
    7:  "Ishwar ko jaanna hai? Gita Chapter 7 mein hai jawab",
    8:  "Mrityu ke baad kya? Gita ka sabse gehri baat",
    9:  "Bhakti ka rahasya — Gita Chapter 9",
    10: "Ishwar ki shakti har jagah hai — Gita Chapter 10",
    11: "Vishwaroop darshan — Arjun ne jo dekha woh aap bhi samjhein",
    12: "Sachchi bhakti kaisi hoti hai? Gita Chapter 12",
    13: "Sharir aur aatma ka fark — Gita Chapter 13",
    14: "Teen gunas jo aapki zindagi control karte hain",
    15: "Purushottam kaun hai? Gita Chapter 15",
    16: "Daivi aur aasuri swabhav — aap kahan hain?",
    17: "Shraddha ke teen roop — Gita Chapter 17",
    18: "Gita ka antim sandesh — moksha ka raasta",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitaBot/1.0)"}

# ── Data loaders (called once at startup) ─────────────────────────────────────

def load_gita_github_data():
    """Load gita/gita GitHub dataset for transliteration + word_meanings."""
    print("Loading gita/gita GitHub dataset...")
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/gita/gita/master/data/verse.json",
            timeout=30
        )
        if r.status_code == 200:
            verses = r.json()
            # Index by (chapter, verse)
            index = {}
            for v in verses:
                key = (v.get("chapter_number"), v.get("verse_number"))
                index[key] = v
            print(f"  Loaded {len(index)} verses from gita/gita")
            return index
    except Exception as e:
        print(f"  gita/gita load failed: {e}")
    return {}


def load_dharmic_data():
    """Load DharmicData (IIT Kanpur) for Ramsukhdas Hindi commentary — all 18 chapters."""
    print("Loading DharmicData (IIT Kanpur / Ramsukhdas)...")
    index = {}
    base = "https://raw.githubusercontent.com/bhavykhatri/DharmicData/main/SrimadBhagvadGita"
    for ch in range(1, 19):
        try:
            url = f"{base}/bhagavad_gita_chapter_{ch}.json"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                verses = data.get("BhagavadGitaChapter", data) if isinstance(data, dict) else data
                for v in verses:
                    key = (v.get("chapter"), v.get("verse"))
                    index[key] = v
                print(f"  ch{ch}: {len([v for v in verses])} verses", end="\r")
            else:
                print(f"  ch{ch}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  DharmicData ch{ch} failed: {e}")
    print(f"  Loaded {len(index)} verses from DharmicData        ")
    return index

# ── Per-verse scrapers ─────────────────────────────────────────────────────────

def scrape_mukundananda(chapter, verse):
    """Scrape English translation + commentary from holy-bhagavad-gita.org."""
    try:
        url = f"https://www.holy-bhagavad-gita.org/chapter/{chapter}/verse/{verse}"
        r = requests.get(url, timeout=15, headers=HEADERS)
        if r.status_code != 200:
            return "", ""
        soup = BeautifulSoup(r.text, "html.parser")
        trans_el = soup.find(class_="bg-verse-translation")
        comm_el  = soup.find(class_="bg-verse-commentary")
        trans = trans_el.get_text(strip=True) if trans_el else ""
        comm  = comm_el.get_text(strip=True)  if comm_el  else ""
        # Remove "BG X.Y:" prefix
        trans = re.sub(r'^BG\s*\d+\.\d+:\s*', '', trans).strip()
        return trans, comm
    except Exception:
        return "", ""


def scrape_vedabase(chapter, verse):
    """Scrape Prabhupada purport from vedabase.io."""
    try:
        url = f"https://vedabase.io/en/library/bg/{chapter}/{verse}/"
        r = requests.get(url, timeout=15, headers=HEADERS)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        purport_el = soup.find(class_="av-purport")
        if not purport_el:
            return ""
        text = purport_el.get_text(strip=True)
        text = re.sub(r'^Purport\s*', '', text).strip()
        return text
    except Exception:
        return ""

# ── Field extractors ───────────────────────────────────────────────────────────

def clean(t):
    if not t:
        return ""
    t = re.sub(r'[।|]{2,}\s*\d+[\.\d]*\s*[।|]{2,}', '', t)
    t = re.sub(r'^\d+\.\d+\.?\s*', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def get_hindi(data):
    """Ramsukhdas Hindi translation (rams.ht) — most conversational."""
    for key in ["rams", "tej", "chinmay"]:
        if key in data and data[key].get("ht"):
            return clean(data[key]["ht"])
    return ""


def get_hindi_commentary(dharmic_verse):
    """Ramsukhdas Hindi commentary from DharmicData."""
    if not dharmic_verse:
        return ""
    commentaries = dharmic_verse.get("commentaries", {})
    text = commentaries.get("Swami Ramsukhdas", "")
    if not text:
        return ""
    # Remove verse reference prefix like "2.47।। व्याख्या-- "
    text = re.sub(r'^\d+\.\d+।।\s*(व्याख्या--\s*)?', '', text).strip()
    return text[:400] + "..." if len(text) > 400 else text


def get_lesson(commentary_en, english_fallback):
    """
    Build a short practical lesson (1-2 sentences, max 200 chars).
    Skips the opening 'This is an extremely popular...' type sentences
    and finds the first actionable instruction.
    """
    skip_prefixes = (
        "this is", "the verse", "there are", "as far as",
        "in this", "it is", "here the", "lord krishna",
        "shree krishna", "arjun", "arjuna",
    )
    if commentary_en:
        sentences = [s.strip() for s in commentary_en.split('.') if len(s.strip()) > 30]
        # Find first sentence that isn't scene-setting
        for s in sentences:
            if not s.lower().startswith(skip_prefixes):
                return s + '.'
        # Fallback to second sentence if all start with skip prefixes
        if len(sentences) >= 2:
            return sentences[1] + '.'
    # Final fallback: English translation
    sentences = [s.strip() for s in english_fallback.split('.') if len(s.strip()) > 20]
    return sentences[0] + '.' if sentences else english_fallback[:150]


def get_social_hooks(chapter, english):
    """Generate 2 social hooks: one chapter-level, one from the English translation."""
    chapter_hook = CHAPTER_HOOKS.get(chapter, "Aaj ka Gita shlok — jeene ka gyaan")
    # Verse hook: first clause of English translation, kept short
    parts = english.split(',') if ',' in english else english.split('.')
    verse_hook = parts[0].strip()[:90] if parts else english[:90]
    return [chapter_hook, verse_hook]

# ── Main generator ─────────────────────────────────────────────────────────────

def generate_v8(output_file="gita_v8.json", resume=False, test_mode=False):
    all_verses = []

    # Resume: load existing
    if resume:
        try:
            with open(output_file, encoding="utf-8") as f:
                all_verses = json.load(f)
            print(f"Resuming from {len(all_verses)} existing verses")
        except FileNotFoundError:
            print("No existing file found, starting fresh")

    existing_ids = {v["id"] for v in all_verses}

    # Load bulk datasets once
    gg_index      = load_gita_github_data()
    dharmic_index = load_dharmic_data()

    total   = 1 if test_mode else sum(CHAPTER_VERSES.values())
    fetched = 0
    failed  = []

    chapters_to_run = {2: 47} if test_mode else CHAPTER_VERSES

    print(f"\nStarting V8 generation — {total} verses\n")

    for chapter, verse_count in chapters_to_run.items():
        verses_range = [47] if test_mode else range(1, verse_count + 1)

        for verse in verses_range:
            vid = f"BG_{chapter:02d}_{verse:02d}"

            if vid in existing_ids:
                fetched += 1
                continue

            fetched += 1
            print(f"[{fetched:3d}/{total}] {vid}", end=" ... ")

            # ── Source 1: vedicscriptures (base data) ──────────────────────
            vs_url = f"https://vedicscriptures.github.io/slok/{chapter}/{verse}"
            try:
                vs_data = requests.get(vs_url, timeout=15).json()
            except Exception as e:
                print(f"SKIP (vedicscriptures failed: {e})")
                failed.append(vid)
                time.sleep(1)
                continue

            sanskrit = vs_data.get("slok", "").replace("\n", " ").strip()
            hindi    = get_hindi(vs_data)

            # ── Source 2: gita/gita GitHub (transliteration + word_meanings) ──
            gg = gg_index.get((chapter, verse), {})
            transliteration = gg.get("transliteration", vs_data.get("transliteration", ""))
            transliteration = transliteration.replace("\n", " ").strip()
            word_meanings   = gg.get("word_meanings", "").replace("\n", " ").strip()

            # ── Source 3: DharmicData (Ramsukhdas Hindi commentary) ────────
            dharmic_verse    = dharmic_index.get((chapter, verse))
            hindi_commentary = get_hindi_commentary(dharmic_verse)

            # ── Source 4: Mukundananda (English + commentary) ──────────────
            english, commentary_en = scrape_mukundananda(chapter, verse)

            # Fallback English from vedicscriptures if scrape failed
            if not english:
                for key in ["siva", "purohit", "gambir", "adi", "san"]:
                    if key in vs_data and vs_data[key].get("et"):
                        english = clean(vs_data[key]["et"])
                        break

            # ── Source 5: vedabase.io (Prabhupada purport) ─────────────────
            purport = scrape_vedabase(chapter, verse)
            purport_snippet = purport[:300] + "..." if len(purport) > 300 else purport

            # ── Derived fields ─────────────────────────────────────────────
            lesson       = get_lesson(commentary_en, english)
            social_hooks = get_social_hooks(chapter, english)
            comm_snippet = commentary_en[:500] + "..." if len(commentary_en) > 500 else commentary_en

            entry = {
                "id":               vid,
                "chapter":          chapter,
                "verse":            verse,
                "chapter_title":    CHAPTER_TITLES.get(chapter, ""),
                "category":         CHAPTER_CATEGORIES.get(chapter, "gita"),
                "sanskrit":         sanskrit,
                "transliteration":  transliteration,
                "word_meanings":    word_meanings,
                "hindi":            hindi,
                "hindi_commentary": hindi_commentary,
                "english":          english,
                "lesson":           lesson,
                "commentary_en":    comm_snippet,
                "purport_snippet":  purport_snippet,
                "social_hooks":     social_hooks,
            }

            all_verses.append(entry)
            print(f"OK")

            # Save progress every 25 verses
            if fetched % 25 == 0:
                _save(all_verses, output_file)
                print(f"  [saved {len(all_verses)} verses]\n")

            # Polite delay — 3 sources scraped per verse
            time.sleep(1.5)

    # Final sort + save
    all_verses.sort(key=lambda x: (x["chapter"], x["verse"]))
    _save(all_verses, output_file)

    print(f"\n{'='*50}")
    print(f"Done! {len(all_verses)} verses saved to {output_file}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")
        print("Re-run with --resume to retry failed verses")
    print(f"{'='*50}")


def _save(verses, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    test_mode = "--test"   in sys.argv
    resume    = "--resume" in sys.argv

    if test_mode:
        print("TEST MODE — fetching only BG_02_47")
        generate_v8(output_file="gita_v8_test.json", resume=False, test_mode=True)
    else:
        generate_v8(output_file="gita_v8.json", resume=resume, test_mode=False)
