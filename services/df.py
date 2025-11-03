import json
from fastapi import APIRouter
from bot.Hanerin import hanerin
route = APIRouter(prefix="/df")

@route.post("/music-data/sync")
def refresh_music_data():
    data = hanerin.df.refresh_music_database()
    with open('/mnt/alist/aleafy_cloud/aleafy/Hanerin/music_data.json', 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data