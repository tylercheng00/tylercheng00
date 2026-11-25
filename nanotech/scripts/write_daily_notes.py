#!/usr/bin/env python3
"""Write five biotech desk notes for the current Hong Kong date.

Notes follow that day's public wires (the news JSON). They are short and
specific. A fixed desk set is used when one has been written for that date;
otherwise the script drafts from the feed's own sentences plus a short
reaction. It does not invent trial numbers.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "data" / "biotech-news.json"
OUT = ROOT / "data" / "biotech-notes.json"
HK = timezone(timedelta(hours=8))
NOTES_PER_DAY = 5
# Keep today plus recent days so the commentary section stays fuller.
HISTORY_DAYS = 4

# Hand-checked against the primary sources on 25 Nov 2026 (Hong Kong).
# Later days are drafted by draft_note() from the feed.
DESK: dict[str, list[dict]] = {
    "2026-11-25": [
        {
            "id": "mend-2026-11-24",
            "publishedAt": "2026-11-24",
            "source": "Nature Biotechnology",
            "url": "https://www.nature.com/articles/s41587-026-03351-6",
            "title": {
                "zh-Hant": "DNA 進核這關，小鼠肝臟只認 BAF v3",
                "zh-Hans": "DNA 进核这关，小鼠肝脏只认 BAF v3",
                "en": "In mouse liver, only BAF v3 moved the DNA",
            },
            "body": {
                "zh-Hant": "Nature Biotechnology 11 月 24 日刊出 MEND：同一顆 LNP 裡再放一段 mRNA，讓細胞先做出輔助蛋白，再處理外來 DNA。小鼠肝臟裡，BAF v3 把表達拉到大約 16 倍；體外很亮的 PWWP 和 H3.3 融合蛋白，到了靜止期的肝細胞就沒有同樣倍數。HepG2 的排名不能直接拿去排肝靶配方。下一題是這些外來蛋白會不會讓方案變得不能重複給藥，而不是再堆一個體外倍數。",
                "zh-Hans": "Nature Biotechnology 11 月 24 日刊出 MEND：同一颗 LNP 里再放一段 mRNA，让细胞先做出辅助蛋白，再处理外来 DNA。小鼠肝脏里，BAF v3 把表达拉到大约 16 倍；体外很亮的 PWWP 和 H3.3 融合蛋白，到了静止期的肝细胞就没有同样倍数。HepG2 的排名不能直接拿去排肝靶配方。下一题是这些外来蛋白会不会让方案变得不能重复给药，而不是再堆一个体外倍数。",
                "en": "Nature Biotechnology on 24 November describes MEND: an extra mRNA in the same LNP so the cell makes a helper protein before it deals with the DNA. In mouse liver, BAF v3 reached about 16-fold over a plain DNA-LNP. The PWWP and H3.3 fusions that looked strong in dividing cells did not carry over. A HepG2 rank list is not a liver-formulation rank list. The next argument is whether those foreign proteins wreck redosing, not whether the in-vitro fold can be pushed higher.",
            },
        },
        {
            "id": "krro-121-2026-11-24",
            "publishedAt": "2026-11-24",
            "source": "Korro Bio / FDA orphan designation",
            "url": "https://www.techtimes.com/articles/331430/20261124/rna-editing-drug-krro-121-wins-fda-orphan-status-before-any-patient-ammonia-disorder-dosed.htm",
            "title": {
                "zh-Hant": "KRRO-121 的孤兒藥資格，病人還沒打第一針",
                "zh-Hans": "KRRO-121 的孤儿药资格，病人还没打第一针",
                "en": "KRRO-121 has an orphan label and zero patients dosed",
            },
            "body": {
                "zh-Hant": "11 月 24 日 Korro 說 FDA 給了 KRRO-121 孤兒藥資格，稿件把尿素循環障礙和肝性腦病都寫了進去。藥是 GalNAc 偶聯的寡核苷酸，招募細胞自己的 ADAR，改谷氨醯胺合成酶的 RNA，不是改 DNA，所以效力會掉，要再打。公司同時寫明兩種病人都還沒有人用過，第一批數據放到 2027 年下半年。歐洲先前的指定只覆蓋尿素循環障礙。孤兒藥資格是稅務抵免和獨佔期，不是療效證明。",
                "zh-Hans": "11 月 24 日 Korro 说 FDA 给了 KRRO-121 孤儿药资格，稿件把尿素循环障碍和肝性脑病都写了进去。药是 GalNAc 偶联的寡核苷酸，招募细胞自己的 ADAR，改谷氨酰胺合成酶的 RNA，不是改 DNA，所以效力会掉，要再打。公司同时写明两种病人都还没有人用过，第一批数据放到 2027 年下半年。欧洲先前的指定只覆盖尿素循环障碍。孤儿药资格是税务抵免和独占期，不是疗效证明。",
                "en": "On 24 November Korro said the FDA granted orphan designation to KRRO-121, and the release names both urea-cycle disorders and hepatic encephalopathy. The drug is a GalNAc oligonucleotide that recruits the cell's own ADAR to edit glutamine-synthetase RNA. It is not a DNA edit, so the change fades and has to be redosed. Korro also says no patient in either group has received it, with first data guided to the second half of 2027. The earlier European designation covered urea-cycle disorders only. Orphan status is a tax credit and an exclusivity clock, not evidence the drug works.",
            },
        },
        {
            "id": "mhra-gt-2026-11-24",
            "publishedAt": "2026-11-24",
            "source": "MHRA",
            "url": "https://www.gov.uk/government/news/mhra-sets-out-regulatory-approach-to-next-generation-innovation",
            "title": {
                "zh-Hant": "英國把基因編輯寫進定義，審批門檻沒有一起降下來",
                "zh-Hans": "英国把基因编辑写进定义，审批门槛没有一起降下来",
                "en": "The UK rewrote the gene-therapy definition, not the approval bar",
            },
            "body": {
                "zh-Hant": "MHRA 11 月 24 日公布基因治療監管諮詢的回應。83% 回應者支持改《2012 年人體藥品規例》裡的定義，讓一部分合成基因治療和基因組編輯產品可以放進現有的先進療法框架。已獲批的藥不用重新歸類。稿件寫得很直：安全、質量、療效的標準不變。對做編輯載體的人，有用的是「算不算基因治療藥」這句開始有方向；審評時鐘不會因此變短。修例仍要走國際通報和國會。",
                "zh-Hans": "MHRA 11 月 24 日公布基因治疗监管咨询的回应。83% 回应者支持改《2012 年人体药品规例》里的定义，让一部分合成基因治疗和基因组编辑产品可以放进现有的先进疗法框架。已获批的药不用重新归类。稿件写得很直：安全、质量、疗效的标准不变。对做编辑载体的人，有用的是「算不算基因治疗药」这句开始有方向；审评时钟不会因此变短。修例仍要走国际通报和国会。",
                "en": "On 24 November the MHRA published the response on gene-therapy regulation. Eighty-three percent of respondents backed changing the definition in the Human Medicines Regulations 2012 so some synthetic gene therapies and genome-editing products sit inside the existing advanced-therapy framework. Licensed medicines would not be reclassified. The release is plain that safety, quality and efficacy standards stay put. Useful if you needed to know whether an editing product is a gene therapy at all. Useless if you hoped the review clock got shorter. The amendment still needs international notification and Parliament.",
            },
        },
        {
            "id": "welgemda-2026-11-23",
            "publishedAt": "2026-11-23",
            "source": "FDA",
            "url": "https://www.fda.gov/news-events/press-announcements/fda-approves-first-treatment-limb-girdle-muscular-dystrophy-type-2ir9",
            "title": {
                "zh-Hant": "LGMD2I/R9 第一個藥是口服核糖醇，不是基因治療",
                "zh-Hans": "LGMD2I/R9 第一个药是口服核糖醇，不是基因治疗",
                "en": "The first LGMD2I/R9 drug is oral ribitol, not a gene therapy",
            },
            "body": {
                "zh-Hant": "FDA 11 月 23 日批了 Welgemda（ribitol 口服溶液），給體重至少 30 公斤、FKRP 相關的 LGMD2I/R9。這是肢帶型肌營養不良裡第一個獲批的藥。機制尚未完全講清，方向是補回 α-dystroglycan 上的糖鏈，不是把基因送回去。NCT05775848 收了 112 人，這次批的是 12 個月中期分析，試驗本身寫到 36 個月。BridgeBio 報 100 米步行速度相對安慰劑多 0.27 米/秒。標籤上腹瀉是 39%，甘露醇對照組是 53%，腸胃反應要連對照一起讀。心臟結果這次中期沒有。",
                "zh-Hans": "FDA 11 月 23 日批了 Welgemda（ribitol 口服溶液），给体重至少 30 公斤、FKRP 相关的 LGMD2I/R9。这是肢带型肌营养不良里第一个获批的药。机制尚未完全讲清，方向是补回 α-dystroglycan 上的糖链，不是把基因送回去。NCT05775848 收了 112 人，这次批的是 12 个月中期分析，试验本身写到 36 个月。BridgeBio 报 100 米步行速度相对安慰剂多 0.27 米/秒。标签上腹泻是 39%，甘露醇对照组是 53%，肠胃反应要连对照一起读。心脏结果这次中期没有。",
                "en": "On 23 November the FDA approved Welgemda (ribitol oral solution) for FKRP-related LGMD2I/R9 in people weighing at least 30 kg. It is the first approved drug for a limb-girdle muscular dystrophy. The mechanism is not fully worked out; the idea is to restore the sugar chain on alpha-dystroglycan, not to deliver a gene. NCT05775848 randomised 112 people. Approval rests on a 12-month interim of a study written out to 36 months. BridgeBio reports a 0.27 m/s benefit on the 100-metre timed test versus placebo. On the label, diarrhoea is 39% on drug and 53% on the mannitol control, so the gut signal only makes sense next to that control. Cardiac outcomes were not in this interim.",
            },
        },
        {
            "id": "denv-n8r-2026-11-23",
            "publishedAt": "2026-11-23",
            "source": "Scientific Reports",
            "url": "https://www.nature.com/articles/s41598-026-82004-9",
            "title": {
                "zh-Hant": "四價登革熱 mRNA：先把 DENV2 的份量壓下去",
                "zh-Hans": "四价登革热 mRNA：先把 DENV2 的份量压下去",
                "en": "A tetravalent dengue mRNA, with DENV2 turned down",
            },
            "body": {
                "zh-Hant": "Scientific Reports 11 月 23 日，韓文忠團隊的四價登革熱 mRNA-LNP。信封蛋白第 8 位天冬酰胺改成精氨酸（N8R），脂質用 AS-CL-28，四型 mRNA 配成 4:1:4:4，用來壓 DENV2 的免疫主導。被動保護裡，N8R 對多個血清型多了一層保護。登革熱疫苗的老問題是抗體依賴增強：交叉但中和不足的抗體會幫病毒進細胞。這篇處理的是配比和一個表位，數據停在動物和血清轉移。不能寫成已經平衡好的臨床疫苗。",
                "zh-Hans": "Scientific Reports 11 月 23 日，韩文忠团队的四价登革热 mRNA-LNP。信封蛋白第 8 位天冬酰胺改成精氨酸（N8R），脂质用 AS-CL-28，四型 mRNA 配成 4:1:4:4，用来压 DENV2 的免疫主导。被动保护里，N8R 对多个血清型多了一层保护。登革热疫苗的老问题是抗体依赖增强：交叉但中和不足的抗体会帮病毒进细胞。这篇处理的是配比和一个表位，数据停在动物和血清转移。不能写成已经平衡好的临床疫苗。",
                "en": "Scientific Reports on 23 November, from Han-Chung Wu's group: a tetravalent dengue mRNA-LNP. Asparagine 8 on the envelope protein is switched to arginine (N8R), the ionisable lipid is AS-CL-28, and the four mRNAs are mixed 4:1:4:4 so DENV2 does not dominate the response. In passive-protection tests the N8R change added protection across serotypes. Dengue vaccines fail when cross-reactive, weakly neutralising antibodies help the virus into cells. This paper is about ratio and one epitope. The data stop at animals and transferred serum. That is not a clinically balanced vaccine.",
            },
        },
    ]
}


def hk_today() -> str:
    return datetime.now(HK).date().isoformat()


def load_news() -> list[dict]:
    if not NEWS.exists():
        return []
    try:
        data = json.loads(NEWS.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") or []
    return [it for it in items if isinstance(it, dict)]


def en_text(value) -> str:
    if isinstance(value, dict):
        return (value.get("en") or "").strip()
    return str(value or "").strip()


def first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    sentence = parts[0].strip()
    if len(sentence) > 240:
        sentence = sentence[:237].rsplit(" ", 1)[0] + "…"
    return sentence


def hk_date_label(iso: str | None) -> tuple[str, str]:
    raw = (iso or "")[:10]
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return ("這幾天", "these past days")
    return (f"{dt.month} 月 {dt.day} 日", f"{dt.day} {dt.strftime('%B')}")


def reaction(blob: str) -> dict[str, str]:
    b = blob.lower()
    if "orphan" in b:
        return {
            "zh-Hant": "孤兒藥資格是稅務和獨佔期，不是有人用過、也不是療效。",
            "zh-Hans": "孤儿药资格是税务和独占期，不是有人用过、也不是疗效。",
            "en": "Orphan designation is a tax credit and an exclusivity clock, not a dosed patient and not efficacy.",
        }
    if any(k in b for k in ("phase 3", "phase iii", "pivotal")):
        return {
            "zh-Hant": "三期標題先看對照組和主要終點有沒有一起公佈，不要只記達標兩個字。",
            "zh-Hans": "三期标题先看对照组和主要终点有没有一起公布，不要只记达标两个字。",
            "en": "On a phase 3 headline, read the control arm and the primary endpoint before repeating the word positive.",
        }
    if any(k in b for k in ("fda approv", "approved")):
        return {
            "zh-Hant": "獲批要分清是完整批准還是加速批准，標籤上的試驗做到第幾個月。",
            "zh-Hans": "获批要分清是完整批准还是加速批准，标签上的试验做到第几个月。",
            "en": "Check whether the approval is traditional or accelerated, and how many months of the trial are actually on the label.",
        }
    if any(k in b for k in ("lnp", "lipid nanoparticle", "mrna", "nanoparticle")):
        return {
            "zh-Hant": "載體論文先分清是體外、小鼠還是人。倍數不能跨這三層直接比較。",
            "zh-Hans": "载体论文先分清是体外、小鼠还是人。倍数不能跨这三层直接比较。",
            "en": "For a delivery paper, separate in vitro, mouse and human. A fold-change does not travel across those three.",
        }
    if any(k in b for k in ("crispr", "gene edit", "base edit", "prime edit")):
        return {
            "zh-Hant": "編輯類消息要看改的是 DNA 還是 RNA，以及脫靶數據有沒有跟療效一起放出來。",
            "zh-Hans": "编辑类消息要看改的是 DNA 还是 RNA，以及脱靶数据有没有跟疗效一起放出来。",
            "en": "For an editing story, check DNA versus RNA, and whether off-target data was published with the efficacy.",
        }
    if any(k in b for k in ("clinical trial", "phase 1", "phase 2", "dosed")):
        return {
            "zh-Hant": "有沒有病人入組，比平台名稱重要。沒有入組就不要寫成臨床結果。",
            "zh-Hans": "有没有病人入组，比平台名称重要。没有入组就不要写成临床结果。",
            "en": "Whether anyone has been dosed matters more than the platform name. No dosing means it is not a clinical result.",
        }
    return {
        "zh-Hant": "先把日期、對象和數字記下來。新聞稿裡的形容詞可以先丟掉。",
        "zh-Hans": "先把日期、对象和数字记下来。新闻稿里的形容词可以先丢掉。",
        "en": "Keep the date, the subject and the number. Drop the adjectives from the release.",
    }


def draft_note(item: dict) -> dict | None:
    title = en_text(item.get("title"))
    summary = en_text(item.get("summary"))
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "來源").split("·")[0].strip()
    if not title or not url:
        return None
    lede = first_sentence(summary if summary and summary.lower() != title.lower() else "")
    if len(lede) < 40:
        return None
    zh_when, en_when = hk_date_label(item.get("publishedAt"))
    react = reaction(f"{title} {summary}")
    note_id = hashlib.sha1(f"{url}|{title}".encode()).hexdigest()[:16]
    return {
        "id": note_id,
        "publishedAt": (item.get("publishedAt") or "")[:10],
        "source": source,
        "url": url,
        "title": {
            "zh-Hant": title,
            "zh-Hans": title,
            "en": title,
        },
        "body": {
            "zh-Hant": f"{source} 在 {zh_when} 的報導，題目是「{title}」。報導寫道：{lede} {react['zh-Hant']}",
            "zh-Hans": f"{source} 在 {zh_when} 的报道，题目是「{title}」。报道写道：{lede} {react['zh-Hans']}",
            "en": f"{source}, {en_when}: {title}. The report says: {lede} {react['en']}",
        },
    }


def draft_from_feed(day: str) -> list[dict]:
    items = load_news()

    def age_from_day(item: dict) -> int | None:
        raw = (item.get("publishedAt") or "")[:10]
        try:
            published = datetime.strptime(raw, "%Y-%m-%d").date()
            today = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            return None
        return (today - published).days

    recent = []
    older = []
    for item in items:
        delta = age_from_day(item)
        if delta is None or delta < -1 or delta > 12:
            continue
        if delta <= 2:
            recent.append(item)
        else:
            older.append(item)
    pool = recent if len(recent) >= NOTES_PER_DAY else recent + older
    notes = []
    seen = set()
    for item in pool:
        key = re.sub(r"[?#].*$", "", item.get("url") or "").rstrip("/").lower()
        if not key or key in seen:
            continue
        note = draft_note(item)
        if not note:
            continue
        seen.add(key)
        notes.append(note)
        if len(notes) >= NOTES_PER_DAY:
            break
    return notes


def load_previous_days() -> dict[str, list[dict]]:
    if not OUT.exists():
        return {}
    try:
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    days: dict[str, list[dict]] = {}
    if isinstance(prev.get("days"), dict):
        for key, value in prev["days"].items():
            if isinstance(value, list) and value:
                days[key] = value
    # Legacy single-day file: fold today's articles under prev["day"].
    if not days and prev.get("day") and isinstance(prev.get("articles"), list):
        days[str(prev["day"])] = prev["articles"]
    return days


def notes_for_day(day: str) -> tuple[list[dict], str]:
    if day in DESK:
        return DESK[day], "desk"
    return draft_from_feed(day), "wire"


def main() -> int:
    day = hk_today()
    articles, origin = notes_for_day(day)
    days = load_previous_days()

    if len(articles) >= NOTES_PER_DAY:
        days[day] = articles
    elif day not in days:
        if not articles:
            # Keep whatever history we already have rather than wiping the page.
            if days:
                print(f"no notes for {day}; keeping previous history")
            else:
                return 1
        else:
            days[day] = articles
    else:
        print(f"only {len(articles)} notes for {day}; keeping prior set for that day")

    # Backfill recent calendar days so the page has more than one desk day.
    today = datetime.strptime(day, "%Y-%m-%d").date()
    for offset in range(1, HISTORY_DAYS):
        past = (today - timedelta(days=offset)).isoformat()
        if past in days and len(days[past]) >= NOTES_PER_DAY:
            continue
        past_notes, _ = notes_for_day(past)
        if past_notes:
            days[past] = past_notes

    keep = {
        (today - timedelta(days=offset)).isoformat()
        for offset in range(HISTORY_DAYS)
    }
    days = {k: v for k, v in days.items() if k in keep and v}
    ordered_days = sorted(days.keys(), reverse=True)
    flat: list[dict] = []
    seen_ids: set[str] = set()
    for d in ordered_days:
        for note in days[d][:NOTES_PER_DAY]:
            nid = note.get("id") or note.get("url") or ""
            if nid and nid in seen_ids:
                continue
            if nid:
                seen_ids.add(nid)
            flat.append(note)

    if not flat:
        return 1

    payload = {
        "day": day,
        "timezone": "Asia/Hong_Kong",
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "perDay": NOTES_PER_DAY,
        "historyDays": HISTORY_DAYS,
        "origin": origin,
        "days": {d: days[d][:NOTES_PER_DAY] for d in ordered_days},
        "articles": flat,
        "disclaimer": {
            "zh-Hant": "當日生物科技公開消息的閱讀筆記，不是投資、臨床或法規建議，也不是本公司論文。",
            "zh-Hans": "当日生物科技公开消息的阅读笔记，不是投资、临床或法规建议，也不是本公司论文。",
            "en": "Reading notes on that day's public biotech record. Not investment, clinical or regulatory advice, and not a Nanotech paper.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT} day={day} origin={origin} "
        f"n_today={len(days.get(day, []))} n_total={len(flat)} days={ordered_days}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
