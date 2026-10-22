import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# TIEN ICH DUNG CHUNG CHO CAC SCRIPT THU THAP
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"          # da nam trong .gitignore
RAW_DIR = DATA_DIR / "raw"
REVIEW_CSV = DATA_DIR / "video_review.csv"
COMMENTS_CSV = DATA_DIR / "comments.csv"
METRICS_CSV = DATA_DIR / "video_metrics.csv"
STATE_JSON = DATA_DIR / "comments_state.json"

# Phai khop voi video_review_template.csv
REVIEW_COLUMNS = [
    "video_id", "title", "channel_title", "video_url", "published_at",
    "search_keyword", "candidate_group", "video_type", "evidence_type",
    "evidence_source", "evidence_note", "review_status",
    "exclusion_reason", "reviewed_at", "reviewer", "notes",
]
# Khong luu ten tac gia binh luan (giam du lieu ca nhan)
COMMENT_COLUMNS = [
    "comment_id", "video_id", "comment_text", "like_count",
    "published_at", "updated_at", "fetched_at",
]
METRIC_COLUMNS = [
    "video_id", "snapshot_time", "view_count", "like_count",
    "comment_count",
]

QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded"}


class QuotaExceeded(Exception):
    pass


class QuotaTracker:
    """Dem quota uoc tinh de dung truoc khi cham tran."""

    def __init__(self, budget):
        self.budget = budget
        self.used = 0

    def spend(self, cost):
        if self.used + cost > self.budget:
            raise QuotaExceeded(
                f"Dat ngan sach quota {self.budget} (da dung {self.used})."
            )
        self.used += cost


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp_slug():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(ten_file):
    with (ROOT / ten_file).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_csv(path):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_csv(path, columns, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    moi = not path.is_file()
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if moi:
            w.writeheader()
        w.writerows(rows)


def dump_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def error_reason(err):
    try:
        data = json.loads(err.content.decode("utf-8"))
        return data["error"]["errors"][0].get("reason", "")
    except Exception:
        return ""


def execute(request, retries=4):
    """Goi API, thu lai co lui dan khi loi tam thoi, dung khi het quota."""
    from googleapiclient.errors import HttpError

    delay = 2
    for lan in range(retries + 1):
        try:
            return request.execute()
        except HttpError as err:
            status = err.resp.status
            reason = error_reason(err)
            if reason in QUOTA_REASONS:
                raise QuotaExceeded(
                    f"YouTube bao het quota trong ngay ({reason})."
                ) from err
            tam_thoi = (
                status in (500, 502, 503, 504)
                or reason in ("rateLimitExceeded", "backendError")
            )
            if tam_thoi and lan < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def get_client():
    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("CHUA CO API KEY: Hay kiem tra file .env.")
        raise SystemExit(1)
    return build(
        "youtube", "v3", developerKey=api_key, cache_discovery=False
    )