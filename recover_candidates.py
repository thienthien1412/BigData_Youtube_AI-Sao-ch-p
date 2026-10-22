
import csv
import json
import html
import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
CSV_PATH = ROOT / "data" / "video_review.csv"
CONFIG_PATH = ROOT / "collection_config.json"
KEYWORDS_PATH = ROOT / "search_keywords.json"

SEARCH_LOG = RAW / "search_20261022T055321Z.jsonl"
DETAIL_LOG = RAW / "video_details_20261022T055321Z.jsonl"

COLUMNS = [
    "video_id", "title", "channel_title", "video_url",
    "published_at", "search_keyword", "candidate_group",
    "video_type", "evidence_type", "evidence_source",
    "evidence_note", "review_status", "exclusion_reason",
    "reviewed_at", "reviewer", "notes"
]


def read_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Lỗi JSON tại {path.name}, dòng {line_no}: {exc}"
                ) from exc
    return records


def main():
    for path in (SEARCH_LOG, DETAIL_LOG, CSV_PATH,
                 CONFIG_PATH, KEYWORDS_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy: {path}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    keyword_config = json.loads(
        KEYWORDS_PATH.read_text(encoding="utf-8")
    )

    start = date.fromisoformat(config["start_date"])
    end = date.fromisoformat(config["end_date"])
    groups_allowed = set(config["video_groups"])
    search_queries = keyword_config["search_queries"]

    found = defaultdict(lambda: {
        "keywords": set(), "groups": set()
    })

    search_records = read_jsonl(SEARCH_LOG)
    detail_records = read_jsonl(DETAIL_LOG)

    query_to_group = {}
    for group, queries in search_queries.items():
        for query in queries:
            query_to_group[query] = group

    unknown_queries = []
    for record in search_records:
        query = record.get("query", "")
        group = query_to_group.get(query)

        if group is None:
            unknown_queries.append(query)
            continue

        response = record.get("response") or {}
        for item in response.get("items", []):
            video_id = (item.get("id") or {}).get("videoId")
            if not video_id:
                continue

            found[video_id]["keywords"].add(query.strip('"'))
            found[video_id]["groups"].add(group)

    details = {}
    for record in detail_records:
        response = record.get("response") or {}
        items = response.get("items", [])

        # Hỗ trợ cả log chứa trực tiếp item video và log
        # chứa response của videos.list.
        if record.get("id") and record.get("snippet"):
            items = [record]

        for item in items:
            video_id = item.get("id")
            if video_id:
                details[video_id] = item

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        existing_ids = {
            row.get("video_id", "").strip()
            for row in existing_rows
            if row.get("video_id", "").strip()
        }

    new_rows = []
    missing_details = []
    out_of_range = []
    no_search_match = []

    for video_id, item in details.items():
        if video_id not in found:
            no_search_match.append(video_id)
            continue

        snippet = item.get("snippet") or {}
        published_at = snippet.get("publishedAt", "")

        try:
            published_date = date.fromisoformat(published_at[:10])
        except ValueError:
            out_of_range.append(video_id)
            continue

        if not (start <= published_date <= end):
            out_of_range.append(video_id)
            continue

        if video_id in existing_ids:
            continue

        groups = found[video_id]["groups"] & groups_allowed
        if not groups:
            continue

        title = html.unescape(snippet.get("title", ""))
        channel = html.unescape(snippet.get("channelTitle", ""))
        description = html.unescape(snippet.get("description", ""))
        description = " ".join(description.split())

        new_rows.append({
            "video_id": video_id,
            "title": title,
            "channel_title": channel,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": published_at,
            "search_keyword": " | ".join(
                sorted(found[video_id]["keywords"])
            ),
            "candidate_group": "|".join(sorted(groups)),
            "video_type": "uncertain",
            "evidence_type": "",
            "evidence_source": "",
            "evidence_note": "",
            "review_status": "review",
            "exclusion_reason": "",
            "reviewed_at": "",
            "reviewer": "",
            "notes": "Phục hồi từ log; chưa xác minh AI. Mô tả: "
                     + description
        })


    print("=== XEM TRUOC PHUC HOI UNG VIEN ===")
    print(f"Khoảng ngày: {start} đến {end}")
    print(f"Dòng hiện có trong CSV: {len(existing_rows)}")
    print(f"ID hiện có trong CSV: {len(existing_ids)}")
    print(f"Số bản ghi log tìm kiếm: {len(search_records)}")
    print(f"Số ID tìm kiếm duy nhất: {len(found)}")
    print(f"Số bản ghi log chi tiết: {len(detail_records)}")
    print(f"Số ID chi tiết duy nhất: {len(details)}")
    print(f"Ứng viên mới dự kiến: {len(new_rows)}")
    print(f"ID thiếu trong log tìm kiếm: {len(no_search_match)}")
    print(f"ID ngoài khoảng ngày/ngày lỗi: {len(out_of_range)}")
    print(f"Query không khớp cấu hình: {len(unknown_queries)}")

    if unknown_queries:
        print("\nQuery chưa khớp:")
        for query in sorted(set(unknown_queries)):
            print(" -", repr(query))

    print("\nMột số ứng viên dự kiến:")
    for row in new_rows[:10]:
        print(
            f"- {row['video_id']} | {row['published_at'][:10]} | "
            f"{row['candidate_group']} | {row['title'][:100]}"
        )

    if not args.apply:
        print("\nCHẾ ĐỘ XEM TRƯỚC: chưa sửa CSV.")
        print("Muốn ghi dữ liệu, chạy lại với tham số --apply.")
        return

    if unknown_queries or no_search_match or out_of_range:
        raise RuntimeError(
            "Có bản ghi bất thường. Dừng ghi để kiểm tra trước."
        )

    if not new_rows:
        print("Không có ứng viên mới để ghi.")
        return

    if len(existing_ids) != len(existing_rows):
        raise RuntimeError(
            "CSV có ID trống hoặc ID trùng. Dừng ghi."
        )

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise RuntimeError(
                "Các cột CSV không khớp cấu trúc dự kiến. Dừng ghi."
            )

    new_ids = [row["video_id"] for row in new_rows]
    if len(new_ids) != len(set(new_ids)):
        raise RuntimeError("Ứng viên mới có ID trùng nhau. Dừng ghi.")

    if set(new_ids) & existing_ids:
        raise RuntimeError(
            "Phát hiện ID trùng với CSV hiện tại. Dừng ghi."
        )

    with CSV_PATH.open(
        "a", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=COLUMNS, extrasaction="raise"
        )
        writer.writerows(new_rows)

    print("\nĐÃ GHI THÊM ỨNG VIÊN.")
    print(f"Số dòng thêm: {len(new_rows)}")
    print(f"Tổng dòng dự kiến sau ghi: {len(existing_rows) + len(new_rows)}")
    print("Các ứng viên vẫn ở trạng thái review, video_type=uncertain.")
    print("Không gọi API và không thu thập bình luận.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi các ứng viên đã phục hồi vào CSV."
    )
    args = parser.parse_args()
    main()
