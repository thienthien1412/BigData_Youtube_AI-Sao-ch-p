import argparse
import html
import sys

from common import (
    RAW_DIR, REVIEW_COLUMNS, REVIEW_CSV, QuotaExceeded, QuotaTracker,
    chunks, dump_jsonl, execute, get_client, load_json, now_iso,
    read_csv, timestamp_slug, write_csv,
)

# ============================================================
# BUOC 1: TIM VIDEO UNG VIEN (CHUA LAY BINH LUAN)
# - Doc tu khoa tu search_keywords.json
# - Ghi video moi vao data/video_review.csv voi review_status=review
# - KHONG ghi de cac dong da duyet truoc do
# ============================================================

SEARCH_COST = 100   # search.list
LIST_COST = 1       # videos.list


def lam_sach(text, gioi_han=200):
    text = " ".join((text or "").split())
    return text[:gioi_han]


def tim_ung_vien(youtube, config, keywords, args, quota):
    from datetime import date, timedelta
    ngay_bat_dau = date.fromisoformat(config["start_date"])
    ngay_ket_thuc = date.fromisoformat(config["end_date"])
    published_after = (ngay_bat_dau - timedelta(days=1)).isoformat() + "T00:00:00Z"
    published_before = (ngay_ket_thuc + timedelta(days=1)).isoformat() + "T00:00:00Z"
    found = {}
    raw = []
    try:
        for nhom in config["video_groups"]:
            for query in keywords["search_queries"][nhom]:
                token = None
                for _ in range(args.max_pages):
                    quota.spend(SEARCH_COST)
                    resp = execute(youtube.search().list(
                        part="snippet",
                        q=query,
                        type="video",
                        regionCode=config["search_region_code"],
                        relevanceLanguage=config["search_relevance_language"],
                        publishedAfter=published_after,
                        publishedBefore=published_before,
                        order=args.order,
                        maxResults=50,
                        pageToken=token,
                    ))
                    raw.append({"query": query, "fetched_at": now_iso(),
                                "response": resp})
                    for item in resp.get("items", []):
                        vid = (item.get("id") or {}).get("videoId")
                        if not vid:
                            continue
                        sn = item.get("snippet", {})
                        e = found.setdefault(vid, {
                            "title": html.unescape(sn.get("title", "")),
                            "channel": html.unescape(
                                sn.get("channelTitle", "")),
                            "published_at": sn.get("publishedAt", ""),
                            "keywords": set(), "groups": set(),
                        })
                        e["keywords"].add(query.strip('"'))
                        e["groups"].add(nhom)
                    token = resp.get("nextPageToken")
                    if not token:
                        break
    except QuotaExceeded as e:
        print(f"[CANH BAO] {e} Luu ket qua da co va dung.")
    return found, raw


def lay_chi_tiet(youtube, ids, quota):
    chi_tiet, raw = {}, []
    try:
        for batch in chunks(ids, 50):
            quota.spend(LIST_COST)
            resp = execute(youtube.videos().list(
                part="snippet,statistics,status", id=",".join(batch)))
            raw.append({"fetched_at": now_iso(), "response": resp})
            for item in resp.get("items", []):
                chi_tiet[item["id"]] = item
    except QuotaExceeded as e:
        print(f"[CANH BAO] {e} Bo qua phan chi tiet con lai.")
    return chi_tiet, raw


def run(youtube, config, keywords, args, quota):
    from datetime import date

    ngay_bat_dau = date.fromisoformat(config["start_date"])
    ngay_ket_thuc = date.fromisoformat(config["end_date"])
    existing = read_csv(REVIEW_CSV)
    da_co = {r["video_id"] for r in existing}

    found, raw_search = tim_ung_vien(youtube, config, keywords, args, quota)
    moi_ids = [v for v in found if v not in da_co]
    chi_tiet, raw_details = lay_chi_tiet(youtube, moi_ids, quota)

    stamp = timestamp_slug()
    dump_jsonl(RAW_DIR / f"search_{stamp}.jsonl", raw_search)
    dump_jsonl(RAW_DIR / f"video_details_{stamp}.jsonl", raw_details)

    moi_rows = []
    for vid in moi_ids:
        e = found[vid]
        d = chi_tiet.get(vid, {})
        sn = d.get("snippet", {})
        published = sn.get("publishedAt") or e["published_at"]
        if not published:
            continue
        try:
            ngay_video = date.fromisoformat(published[:10])
        except (TypeError, ValueError):
            continue
        if not (ngay_bat_dau <= ngay_video <= ngay_ket_thuc):
            continue
        nhan = (d.get("status") or {}).get("containsSyntheticMedia")
        ghi_chu = (f"youtube_synthetic_label={nhan}; "
                   f"desc: {lam_sach(sn.get('description'))}")
        moi_rows.append({
            "video_id": vid,
            "title": html.unescape(sn.get("title") or e["title"]),
            "channel_title": html.unescape(
                sn.get("channelTitle") or e["channel"]),
            "video_url": f"https://www.youtube.com/watch?v={vid}",
            "published_at": published,
            "search_keyword": " | ".join(sorted(e["keywords"])),
            "candidate_group": "|".join(sorted(e["groups"])),
            "video_type": "uncertain",
            "review_status": "review",
            "notes": ghi_chu,
        })

    write_csv(REVIEW_CSV, REVIEW_COLUMNS, existing + moi_rows)
    return len(found), len(moi_rows), len(existing)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-pages", type=int, default=1,
                   help="So trang ket qua cho moi tu khoa (50 video/trang).")
    p.add_argument("--order", default="relevance",
                   choices=["relevance", "date", "viewCount"])
    p.add_argument("--quota-budget", type=int, default=9000,
                   help="Ngan sach quota toi da cho lan chay nay.")
    p.add_argument("--dry-run", action="store_true",
                   help="Chi uoc tinh quota, khong goi API.")
    args = p.parse_args()

    config = load_json("collection_config.json")
    keywords = load_json("search_keywords.json")
    so_query = sum(len(keywords["search_queries"][g])
                   for g in config["video_groups"])
    uoc_tinh = so_query * args.max_pages * SEARCH_COST

    print(f"So tu khoa: {so_query}; trang/tu khoa: {args.max_pages}")
    print(f"Quota uoc tinh (chua tinh videos.list): {uoc_tinh}")
    if args.dry_run:
        return 0

    if not (config.get("data_collection_enabled") is True
            and keywords.get("search_enabled") is True):
        print("[DUNG] Tim kiem dang tat. Dat data_collection_enabled=true "
              "(collection_config.json) va search_enabled=true "
              "(search_keywords.json) neu da san sang.")
        return 1
    if uoc_tinh > args.quota_budget:
        print("[DUNG] Uoc tinh vuot ngan sach. Giam --max-pages hoac "
              "tang --quota-budget.")
        return 1

    youtube = get_client()
    quota = QuotaTracker(args.quota_budget)
    tong, moi, cu = run(youtube, config, keywords, args, quota)
    print(f"Tim thay {tong} video; them moi {moi}; giu nguyen {cu} dong cu.")
    print(f"Quota da dung (uoc tinh): {quota.used}")
    print(f"Ket qua: {REVIEW_CSV}")
    print("Buoc tiep theo: duyet thu cong file CSV (keep/exclude).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
