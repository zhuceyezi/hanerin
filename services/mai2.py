from io import BytesIO
from fastapi import APIRouter, Response
from fastapi.params import Query

from bot.Hanerin import hanerin
import json

from utils.maimai_best_50 import generate50

route = APIRouter(prefix="/mai2")


@route.get("/{qq}/get_music_info")
def get_music_info(qq):
    return hanerin.route.get_user_music_info(qq)


@route.get("/{qq}/upload_df")
def wahlap_to_df(qq):
    user_music = hanerin.route.get_user_music_info(qq)
    combo = ["", "fc", "fcp", "ap", "app"]
    sync = ["", "sync", "fs", "fsp", "fsd", "fsdp"]
    with open('/mnt/alist/aleafy_cloud/aleafy/Hanerin/music_data.json', 'r', encoding="utf-8") as f:
        music_data = json.load(f)
    sy_list = []
    for music in user_music["userMusicList"]:
        music_id = music["userMusicDetailList"][0]["musicId"]
        for chart in music["userMusicDetailList"]:
            chart_info = music_data[str(music_id)]
            sy_list.append({
                "achievements": chart["achievement"] / 10000,  # 1010000 -> 101.0000%
                "dxScore": chart["deluxscoreMax"],
                "fc": combo[chart["comboStatus"]],
                "fs": sync[chart["syncStatus"]],
                "level_index": chart["level"],
                "title": chart_info["title"],
                "type": chart_info["type"]
            })
    return sy_list


@route.get("/{qq}/b50")
async def b50_divingfish(qq):
    pic, _ = await generate50({
        'qq': qq,
        'b50': True
    })
    img_io = BytesIO()
    pic.save(img_io, format='PNG')
    return Response(content=img_io.getvalue(), media_type="image/png")

@route.get("/getUserIdFromQRCode")
async def get_userId_from_qrcode(qrcode=Query(...)):
    return hanerin.mai2.get_userId_from_qrcode(qrcode)