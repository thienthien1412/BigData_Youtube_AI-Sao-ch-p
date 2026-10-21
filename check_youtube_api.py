import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Doc API key tu file .env
load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

if not api_key:
    print("CHUA CO API KEY: Hay kiem tra file .env.")
    raise SystemExit(1)

try:
    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key,
        cache_discovery=False
    )

    # Chi doc thong tin mot kenh cong khai de kiem tra ket noi.
    # Khong tim video, khong lay binh luan, khong luu du lieu.
    response = youtube.channels().list(
        part="snippet",
        id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        maxResults=1
    ).execute()

    if response.get("items"):
        channel = response["items"][0]["snippet"]["title"]
        print("KET NOI YOUTUBE API THANH CONG.")
        print("Kenh kiem tra:", channel)
    else:
        print("API da phan hoi, nhung khong tim thay kenh kiem tra.")

except HttpError as e:
    print("YOUTUBE API TRA VE LOI HTTP:", e.resp.status)
    print("Hay kiem tra API, khoa va quota.")
except Exception as e:
    print("LOI KET NOI:", type(e).__name__)
    print("Hay kiem tra mang va cau hinh.")
