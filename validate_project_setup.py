
import csv
import json
import sys
from pathlib import Path


# ============================================================
# KIEM TRA CAU HINH DU AN BIG DATA YOUTUBE AI
# Chi doc va kiem tra, KHONG tim kiem hay thu thap du lieu.
# ============================================================

THU_MUC = Path(__file__).resolve().parent

CAC_FILE_BAT_BUOC = [
    ".gitignore",
    ".env.example",
    "README.md",
    "collection_config.json",
    "search_keywords.json",
    "video_review_rules.json",
    "video_review_template.csv",
    "review_rules_checklist.md",
]

COT_CSV_BAT_BUOC = [
    "video_id",
    "title",
    "channel_title",
    "video_url",
    "published_at",
    "search_keyword",
    "candidate_group",
    "video_type",
    "evidence_type",
    "evidence_source",
    "evidence_note",
    "review_status",
    "exclusion_reason",
    "reviewed_at",
    "reviewer",
    "notes",
]

NHOM_VIDEO = ["ai_cover", "ai_original"]
CAC_LOAI_VIDEO = ["ai_cover", "ai_original", "both", "uncertain"]
CAC_TRANG_THAI = ["review", "keep", "exclude"]

loi = []


# ------------------------------------------------------------
# CAC HAM KIEM TRA CHUNG
# ------------------------------------------------------------

def in_ok(noi_dung):
    print(f"[OK] {noi_dung}")


def in_loi(noi_dung):
    print(f"[LOI] {noi_dung}")
    loi.append(noi_dung)


def doc_json(ten_file):
    duong_dan = THU_MUC / ten_file

    try:
        with duong_dan.open("r", encoding="utf-8-sig") as tep:
            du_lieu = json.load(tep)

        if not isinstance(du_lieu, dict):
            in_loi(f"{ten_file} phai co cau truc JSON object.")
            return {}

        in_ok(f"Doc JSON thanh cong: {ten_file}")
        return du_lieu

    except FileNotFoundError:
        in_loi(f"Khong tim thay file: {ten_file}")
    except json.JSONDecodeError as e:
        in_loi(
            f"{ten_file} khong dung JSON tai dong "
            f"{e.lineno}, cot {e.colno}."
        )
    except OSError as e:
        in_loi(f"Khong doc duoc {ten_file}: {e}")

    return {}


def kiem_tra_bat_buoc(du_lieu, khoa, gia_tri_mong_doi, ten):
    gia_tri_thuc_te = du_lieu.get(khoa)

    if gia_tri_thuc_te == gia_tri_mong_doi:
        in_ok(ten)
    else:
        in_loi(
            f"{khoa} phai bang {gia_tri_mong_doi!r}, "
            f"hien tai la {gia_tri_thuc_te!r}."
        )


def kiem_tra_true(du_lieu, khoa, ten):
    kiem_tra_bat_buoc(du_lieu, khoa, True, ten)


def kiem_tra_false(du_lieu, khoa, ten):
    kiem_tra_bat_buoc(du_lieu, khoa, False, ten)


def kiem_tra_danh_sach(du_lieu, khoa, danh_sach_mong_doi, ten):
    gia_tri = du_lieu.get(khoa)

    if gia_tri == danh_sach_mong_doi:
        in_ok(ten)
    else:
        in_loi(
            f"{khoa} khong dung. "
            f"Mong doi: {danh_sach_mong_doi!r}; "
            f"hien tai: {gia_tri!r}."
        )


def kiem_tra_cac_khoa(du_lieu, cac_khoa, ten):
    if not isinstance(du_lieu, dict):
        in_loi(f"{ten} phai la mot JSON object.")
        return False

    thieu = [khoa for khoa in cac_khoa if khoa not in du_lieu]

    if thieu:
        in_loi(f"{ten} thieu cac khoa: {', '.join(thieu)}")
        return False

    in_ok(f"{ten} co du cac khoa bat buoc.")
    return True


# ------------------------------------------------------------
# 1. KIEM TRA CAC FILE CAN THIET
# ------------------------------------------------------------

def kiem_tra_file():
    print("\n=== 1. KIEM TRA CAC FILE ===")

    for ten_file in CAC_FILE_BAT_BUOC:
        duong_dan = THU_MUC / ten_file

        if duong_dan.is_file():
            in_ok(f"Tim thay: {ten_file}")
        else:
            in_loi(f"Khong tim thay: {ten_file}")

    tep_env = THU_MUC / ".env"

    if tep_env.is_file():
        in_ok("Tim thay .env (khong hien thi noi dung bi mat).")
    else:
        print(
            "[CANH BAO] Chua tim thay .env. "
            "Chuong trinh kiem tra cau hinh van co the chay."
        )


# ------------------------------------------------------------
# 2. KIEM TRA FILE CSV MAU
# ------------------------------------------------------------

def kiem_tra_csv():
    print("\n=== 2. KIEM TRA FILE CSV MAU ===")

    duong_dan = THU_MUC / "video_review_template.csv"

    if not duong_dan.is_file():
        in_loi("Khong the kiem tra CSV vi file khong ton tai.")
        return

    try:
        with duong_dan.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as tep:
            doc = csv.reader(tep)
            tieu_de = next(doc, None)

        if tieu_de is None:
            in_loi("video_review_template.csv dang rong.")
            return

        if tieu_de == COT_CSV_BAT_BUOC:
            in_ok(f"CSV co dung {len(tieu_de)} cot theo yeu cau.")
        else:
            in_loi(
                "Danh sach cot CSV khong dung thu tu hoac thieu cot.\n"
                f"  Mong doi: {COT_CSV_BAT_BUOC}\n"
                f"  Thuc te: {tieu_de}"
            )

        if len(tieu_de) != len(set(tieu_de)):
            in_loi("CSV co ten cot bi trung lap.")
        else:
            in_ok("Khong co ten cot CSV bi trung lap.")

    except (OSError, csv.Error) as e:
        in_loi(f"Loi khi doc file CSV mau: {e}")


# ------------------------------------------------------------
# 3. KIEM TRA collection_config.json
# ------------------------------------------------------------

def kiem_tra_collection_config(config):
    print("\n=== 3. KIEM TRA collection_config.json ===")

    kiem_tra_bat_buoc(
        config,
        "project_name",
        "youtube_ai_music_analysis",
        "Ten du an dung."
    )

    kiem_tra_bat_buoc(
        config,
        "start_date",
        "2024-01-01",
        "Moc thoi gian bat dau dung."
    )

    kiem_tra_bat_buoc(
        config,
        "end_date",
        "2026-10-22",
        "Moc thoi gian ket thuc dung."
    )

    try:
        from datetime import date
        ngay_bat_dau = date.fromisoformat(config.get("start_date", ""))
        ngay_ket_thuc = date.fromisoformat(config.get("end_date", ""))

        if ngay_ket_thuc >= ngay_bat_dau:
            in_ok("Khoang thoi gian thu thap hop le.")
        else:
            in_loi("end_date khong duoc truoc start_date.")
    except (TypeError, ValueError):
        in_loi("start_date/end_date phai dung dinh dang YYYY-MM-DD.")
    kiem_tra_danh_sach(
        config,
        "video_groups",
        NHOM_VIDEO,
        "Co dung hai nhom video chinh."
    )

    kiem_tra_bat_buoc(
        config,
        "collection_status_default",
        "review",
        "Video moi mac dinh o trang thai review."
    )

    kiem_tra_true(
        config,
        "require_manual_approval",
        "Bat yeu cau phe duyet thu cong."
    )

    kiem_tra_false(
        config,
        "collect_comments_for_unapproved_videos",
        "Khong lay binh luan cua video chua duoc phe duyet."
    )

    kiem_tra_false(
        config,
        "collect_replies",
        "Khong thu thap cac cau tra loi binh luan."
    )

    kiem_tra_false(
        config,
        "data_collection_enabled",
        "Chuc nang thu thap du lieu dang tat."
    )

    kiem_tra_bat_buoc(
        config,
        "search_region_code",
        "VN",
        "Ma khu vuc tim kiem la VN."
    )

    kiem_tra_bat_buoc(
        config,
        "search_relevance_language",
        "vi",
        "Ngon ngu lien quan khi tim kiem la vi."
    )

    so_binh_luan = config.get("max_top_level_comments_per_video")

    if type(so_binh_luan) is int and so_binh_luan == 200:
        in_ok("Gioi han toi da 200 binh luan goc moi video.")
    else:
        in_loi(
            "max_top_level_comments_per_video phai bang 200."
        )


# ------------------------------------------------------------
# 4. KIEM TRA search_keywords.json
# ------------------------------------------------------------

def kiem_tra_search_keywords(keywords):
    print("\n=== 4. KIEM TRA search_keywords.json ===")

    truy_van = keywords.get("search_queries")

    if not isinstance(truy_van, dict):
        in_loi("search_queries phai la mot JSON object.")
        truy_van = {}

    for nhom in NHOM_VIDEO:
        danh_sach = truy_van.get(nhom)

        if not isinstance(danh_sach, list) or not danh_sach:
            in_loi(f"Nhom {nhom} chua co danh sach tu khoa hop le.")
        elif not all(
            isinstance(tu_khoa, str) and tu_khoa.strip()
            for tu_khoa in danh_sach
        ):
            in_loi(f"Nhom {nhom} co tu khoa rong hoac khong hop le.")
        else:
            in_ok(
                f"Nhom {nhom} co {len(danh_sach)} tu khoa hop le."
            )

    kiem_tra_danh_sach(
        keywords,
        "video_types",
        CAC_LOAI_VIDEO,
        "Danh sach loai video dung."
    )

    kiem_tra_danh_sach(
        keywords,
        "review_statuses",
        CAC_TRANG_THAI,
        "Danh sach trang thai duyet dung."
    )

    kiem_tra_false(
        keywords,
        "search_enabled",
        "Chuc nang tim kiem dang tat."
    )

    kiem_tra_false(
        keywords,
        "data_collection_enabled",
        "Chuc nang thu thap du lieu dang tat."
    )

    approval_rules = keywords.get("approval_rules")

    if not isinstance(approval_rules, dict):
        in_loi("approval_rules phai la mot JSON object.")
        return

    print("\n--- Quy tac phe duyet trong search_keywords.json ---")

    kiem_tra_true(
        approval_rules,
        "require_manual_review",
        "Yeu cau duyet thu cong."
    )

    kiem_tra_true(
        approval_rules,
        "require_ai_evidence",
        "Video phai co bang chung AI."
    )

    kiem_tra_false(
        approval_rules,
        "allow_uncertain_video",
        "Khong tu dong chap nhan video uncertain."
    )

    kiem_tra_true(
        approval_rules,
        "collect_comments_only_if_status_keep",
        "Chi lay binh luan khi video co trang thai keep."
    )

    kiem_tra_true(
        approval_rules,
        "allow_title_without_ai_keyword_if_verified",
        "Cho phep giu video khong co tu khoa AI neu da xac minh."
    )


# ------------------------------------------------------------
# 5. KIEM TRA video_review_rules.json
# ------------------------------------------------------------

def kiem_tra_video_review_rules(rules):
    print("\n=== 5. KIEM TRA video_review_rules.json ===")

    kiem_tra_false(
        rules,
        "collection_enabled",
        "Chuc nang thu thap cap goc dang tat."
    )

    review_policy = rules.get("review_policy")

    if not isinstance(review_policy, dict):
        in_loi("review_policy phai la mot JSON object.")
        review_policy = {}

    print("\n--- Quy tac duyet video ---")

    kiem_tra_bat_buoc(
        review_policy,
        "default_status",
        "review",
        "Trang thai mac dinh cua video la review."
    )

    kiem_tra_danh_sach(
        review_policy,
        "allowed_statuses",
        CAC_TRANG_THAI,
        "Cac trang thai duyet dung."
    )

    kiem_tra_danh_sach(
        review_policy,
        "allowed_video_types",
        CAC_LOAI_VIDEO,
        "Cac loai video duoc khai bao dung."
    )

    cac_quy_tac_review = {
        "uncertain_can_be_kept": False,
        "manual_review_required": True,
        "evidence_required_for_keep": True,
        "evidence_source_required_for_keep": True,
        "evidence_note_required_for_keep": True,
        "both_requires_evidence_for_both_groups": True,
        "title_or_keyword_alone_is_sufficient_evidence": False,
        "comments_allowed_only_for_keep": True,
        "comments_require_current_approval": True,
        "collect_replies": False,
        "preserve_existing_data_after_exclusion": True,
        "record_review_history": True,
        "deduplicate_videos_by": "video_id",
        "deduplicate_comments_by": "comment_id",
    }

    for khoa, gia_tri in cac_quy_tac_review.items():
        kiem_tra_bat_buoc(
            review_policy,
            khoa,
            gia_tri,
            f"Quy tac review_policy.{khoa} dung."
        )

    print("\n--- Truong bang chung ---")

    evidence_record = rules.get("evidence_record")

    if not isinstance(evidence_record, dict):
        in_loi("evidence_record phai la mot JSON object.")
    else:
        truong_bat_buoc = [
            "evidence_type",
            "evidence_source",
            "evidence_note",
            "review_status",
            "reviewed_at",
            "reviewer",
        ]

        kiem_tra_danh_sach(
            evidence_record,
            "required_fields_for_keep",
            truong_bat_buoc,
            "Danh sach truong bang chung bat buoc day du."
        )

        kiem_tra_bat_buoc(
            evidence_record,
            "insufficient_evidence_action",
            "review",
            "Bang chung chua du thi giu o trang thai review."
        )

    print("\n--- Lich su duyet ---")

    review_history = rules.get("review_history")

    if not isinstance(review_history, dict):
        in_loi("review_history phai la mot JSON object.")
    else:
        kiem_tra_true(
            review_history,
            "record_status_changes",
            "Ghi lai lich su thay doi trang thai."
        )

        truong_lich_su = [
            "video_id",
            "previous_status",
            "new_status",
            "changed_at",
            "reviewer",
            "reason",
        ]

        kiem_tra_danh_sach(
            review_history,
            "required_fields",
            truong_lich_su,
            "Lich su duyet co du truong bat buoc."
        )

        kiem_tra_false(
            review_history,
            "delete_existing_data_on_exclusion",
            "Khong xoa du lieu cu khi loai video."
        )

    print("\n--- Chinh sach thu thap ---")

    collection_policy = rules.get("collection_policy")

    if not isinstance(collection_policy, dict):
        in_loi("collection_policy phai la mot JSON object.")
        return

    cac_quy_tac_thu_thap = {
        "collection_enabled": False,
        "search_enabled": False,
        "require_manual_approval": True,
        "collect_comments_for_unapproved_videos": False,
        "collect_comments_only_if_current_status_is_keep": True,
        "require_valid_evidence_before_comments": True,
        "collect_replies": False,
        "max_top_level_comments_per_video": 200,
    }

    for khoa, gia_tri in cac_quy_tac_thu_thap.items():
        kiem_tra_bat_buoc(
            collection_policy,
            khoa,
            gia_tri,
            f"Chinh sach thu thap {khoa} dung."
        )


# ------------------------------------------------------------
# 6. KIEM TRA NHAT QUAN GIUA CAC FILE
# ------------------------------------------------------------

def kiem_tra_nhat_quan(config, keywords, rules):
    print("\n=== 6. KIEM TRA NHAT QUAN GIUA CAC FILE ===")

    if config.get("video_groups") == NHOM_VIDEO:
        if isinstance(keywords.get("search_queries"), dict):
            nhom_tu_khoa = list(keywords["search_queries"].keys())

            if nhom_tu_khoa == NHOM_VIDEO:
                in_ok("Hai nhom video nhat quan giua config va tu khoa.")
            else:
                in_loi(
                    "Nhom trong search_queries khong khop "
                    "voi collection_config.json."
                )

    kiem_tra_danh_sach(
        keywords,
        "video_types",
        rules.get("review_policy", {}).get("allowed_video_types", []),
        "Loai video nhat quan giua file tu khoa va file quy tac."
    )

    kiem_tra_danh_sach(
        keywords,
        "review_statuses",
        rules.get("review_policy", {}).get("allowed_statuses", []),
        "Trang thai duyet nhat quan giua cac file."
    )

    if config.get("max_top_level_comments_per_video") == (
        rules.get("collection_policy", {}).get(
            "max_top_level_comments_per_video"
        )
    ):
        in_ok("Gioi han binh luan nhat quan giua cac file.")
    else:
        in_loi("Gioi han binh luan khong nhat quan giua cac file.")

    if (
        config.get("require_manual_approval") is True
        and rules.get("review_policy", {}).get(
            "manual_review_required"
        ) is True
        and rules.get("collection_policy", {}).get(
            "require_manual_approval"
        ) is True
    ):
        in_ok("Yeu cau phe duyet thu cong nhat quan.")
    else:
        in_loi("Yeu cau phe duyet thu cong khong nhat quan.")

    if (
        config.get("data_collection_enabled") is False
        and keywords.get("search_enabled") is False
        and keywords.get("data_collection_enabled") is False
        and rules.get("collection_enabled") is False
        and rules.get("collection_policy", {}).get(
            "collection_enabled"
        ) is False
        and rules.get("collection_policy", {}).get(
            "search_enabled"
        ) is False
    ):
        in_ok("Tat ca cong tac tim kiem va thu thap deu dang tat.")
    else:
        in_loi(
            "Phat hien cau hinh tim kiem/thu thap chua tat "
            "o tat ca cac file."
        )


# ------------------------------------------------------------
# 7. CHAY TOAN BO KIEM TRA
# ------------------------------------------------------------

def main():
    print("=" * 64)
    print("KIEM TRA CAU HINH DU AN BIG DATA YOUTUBE AI")
    print("=" * 64)
    print(f"Thu muc: {THU_MUC}")
    print("Che do: chi doc va kiem tra, khong thu thap du lieu.")
    print("")

    kiem_tra_file()
    kiem_tra_csv()

    config = doc_json("collection_config.json")
    keywords = doc_json("search_keywords.json")
    rules = doc_json("video_review_rules.json")

    kiem_tra_collection_config(config)
    kiem_tra_search_keywords(keywords)
    kiem_tra_video_review_rules(rules)
    kiem_tra_nhat_quan(config, keywords, rules)

    print("\n" + "=" * 64)
    print("KET QUA CUOI CUNG")
    print("=" * 64)

    if loi:
        print(f"[KET QUA] CO {len(loi)} LOI CAN SUA:")
        for stt, noi_dung in enumerate(loi, start=1):
            print(f"  {stt}. {noi_dung}")

        print("\nChua dat. Hay sua cac loi tren roi chay lai.")
        return 1

    print("[OK] Tat ca kiem tra cau hinh deu dat.")
    print("[OK] Tim kiem YouTube van dang tat.")
    print("[OK] Thu thap du lieu van dang tat.")
    print("[OK] Khong co video hay binh luan nao duoc thu thap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
