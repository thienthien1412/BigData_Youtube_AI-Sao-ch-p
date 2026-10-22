import argparse
import json
import sys

from googleapiclient.errors import HttpError

from common import (
    COMMENT_COLUMNS, COMMENTS_CSV, METRIC_COLUMNS, METRICS_CSV,
    RAW_DIR, REVIEW_CSV, STATE_JSON, QuotaExceeded, QuotaTracker,
    append_csv, chunks, dump_jsonl, error_reason, execute, get_client,
    load_json, now_iso, read_csv, timestamp_slug,
)

# ============================================================
# BUOC 3: LAY BINH LUAN + SNAPSHOT CHI SO CHO VIDEO DA DUOC DUYET
# - Chi video review_status=keep, du bang chung, video_type hop le
# - Chi binh luan goc (top-level), KHONG lay tra loi
# - Doc lai file duyet MOI LAN CHAY (dam bao con duoc phe duyet)
# ============================================================

CAC_LOAI_HOP_LE = {"ai_cover", "ai_original", "both"}
TRUONG_BANG_CHUNG = [
    "evidence_type", "evidence_source", "evidence_note",
    "reviewed_at", "reviewer",
]
LOI_BO_QUA = {"commentsDisabled", "videoNotFound", "forbidden"}


def kiem_tra_duoc_phep(row):
    if (row.get("review_status") or "").strip().lower() != "keep":
        return False, "review_status khong phai keep"
    loai = (row.get("video_type") or "").strip()
    if loai not in CAC_LOAI_HOP_LE:
        return False, f"video_type khong hop le ({loai or 'trong'})"
    thieu = [f for f in TRUONG_BANG_CHUNG
             if not (row.get(f) or "").strip()]
    if thieu:
        return False, "thieu: " + ", ".join(thieu)
    return True, ""


def lay_binh_luan_goc(youtube, video_id, gioi_han, quota):
    ket_qua, token = [], None
    fetched = now_iso()
    while len(ket_qua) < gioi_han:
        quota.spend(1)
        resp = execute(youtube.commentThreads().list(
            part="snippet",              # khong yeu cau 'replies'
            videoId=video_id,
            order="relevance",
            maxResults=min(100, gioi_han - len(ket_qua)),
            textFormat="plainText",
            pageToken=token,
        ))
        for item in resp.get("items", []):
            top = item["snippet"]["topLevelComment"]
            s = top["snippet"]
            ket_qua.append({
                "comment_id": top["id"],
                "video_id": video_id,
                "comment_text": s.get("textOriginal")
                                or s.get("textDisplay", ""),
                "like_count": s.get("likeCount", 0),
                "published_at": s.get("publishedAt", ""),
                "updated_at": s.get("updatedAt", ""),
                "fetched_at": fetched,
            })
        token = resp.get("nextPageToken")
        if not token:
            break
    return ket_qua[:gioi_han]


def chup_chi_so(youtube, ids, quota):
    snapshot, raw, rows = now_iso(), [], []
    for batch in chunks(ids, 50):
        quota.spend(1)
        resp = execute(youtube.videos().list(
            part="statistics", id=",".join(batch)))
        raw.append({"fetched_at": snapshot, "response": resp})
        for item in resp.get("items", []):
            st = item.get("statistics", {})
            rows.append({
                "video_id": item["id"],
                "snapshot_time": snapshot,
                "view_count": st.get("viewCount", ""),
                "like_count": st.get("likeCount", ""),
                "comment_count": st.get("commentCount", ""),
            })
    return rows, raw


def doc_state():
    if STATE_JSON.is_file():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return {}


def luu_state(state):
    STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run(youtube, config, args, quota):
    gioi_han = config["max_top_level_comments_per_video"]
    duoc_phep, bi_loai = [], []
    for row in read_csv(REVIEW_CSV):
        ok, ly_do = kiem_tra_duoc_phep(row)
        if ok:
            duoc_phep.append(row["video_id"])
        elif (row.get("review_status") or "").strip().lower() == "keep":
            bi_loai.append((row["video_id"], ly_do))

    for vid, ly_do in bi_loai:
        print(f"[BO QUA] {vid}: da danh dau keep nhung {ly_do}")
    print(f"Video du dieu kien: {len(duoc_phep)}")
    if not duoc_phep:
        return 0, 0

    state = doc_state()
    da_co = {r["comment_id"] for r in read_csv(COMMENTS_CSV)}
    tong_moi = 0
    try:
        rows, raw = chup_chi_so(youtube, duoc_phep, quota)
        append_csv(METRICS_CSV, METRIC_COLUMNS, rows)
        dump_jsonl(RAW_DIR / f"metrics_{timestamp_slug()}.jsonl", raw)

        for vid in duoc_phep:
            if vid in state and not args.refresh:
                continue
            try:
                cmts = lay_binh_luan_goc(youtube, vid, gioi_han, quota)
            except HttpError as err:
                ly_do = error_reason(err)
                if ly_do in LOI_BO_QUA:
                    print(f"[BO QUA] {vid}: {ly_do}")
                    state[vid] = {"status": ly_do,
                                  "fetched_at": now_iso()}
                    luu_state(state)
                    continue
                raise
            moi = [c for c in cmts if c["comment_id"] not in da_co]
            da_co.update(c["comment_id"] for c in moi)
            append_csv(COMMENTS_CSV, COMMENT_COLUMNS, moi)
            dump_jsonl(RAW_DIR / f"comments_{vid}.jsonl",
                       [{"fetched_at": now_iso(), "comments": cmts}])
            state[vid] = {"status": "done", "fetched_at": now_iso(),
                          "n_fetched": len(cmts), "n_new": len(moi)}
            luu_state(state)
            tong_moi += len(moi)
            print(f"[OK] {vid}: lay {len(cmts)}, moi {len(moi)}")
    except QuotaExceeded as e:
        print(f"[CANH BAO] {e} Dung an toan; chay lai de tiep tuc.")
        luu_state(state)
    return len(duoc_phep), tong_moi


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quota-budget", type=int, default=9000)
    p.add_argument("--refresh", action="store_true",
                   help="Lay lai binh luan cho video da lay truoc do.")
    args = p.parse_args()

    config = load_json("collection_config.json")
    rules = load_json("video_review_rules.json")
    chinh_sach = rules.get("collection_policy", {})
    if not (config.get("data_collection_enabled") is True
            and rules.get("collection_enabled") is True
            and chinh_sach.get("collection_enabled") is True):
        print("[DUNG] Thu thap dang tat. Bat data_collection_enabled "
              "(collection_config.json) va collection_enabled "
              "(video_review_rules.json, ca collection_policy) khi san "
              "sang.")
        return 1
    if config.get("collect_replies") is not False:
        print("[DUNG] collect_replies phai la false.")
        return 1

    youtube = get_client()
    quota = QuotaTracker(args.quota_budget)
    n_video, n_moi = run(youtube, config, args, quota)
    print(f"Xong. Video: {n_video}; binh luan moi: {n_moi}; "
          f"quota uoc tinh: {quota.used}")
    return 0


if __name__ == "__main__":
    sys.exit(main())