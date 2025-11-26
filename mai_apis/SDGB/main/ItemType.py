from enum import Enum


class ItemType(Enum):
    PLATE =1 # 姓名框
    TITLE =2 # 称号
    ICON =3 # 头像
    PRESENT=4 # 礼物
    MUSIC=5 # 乐曲
    MUSIC_MASTER=6 # 紫谱
    MUSIC_REMASTER=7 # 白谱
    MUSIC_STRONG=8 # 传导（?)
    CHARACTER=9 # 旅行伙伴
    PARTNER =10 # 搭档
    FRAME =11 # 背景板
    TICKET =12 # 功能票
    MILE=13 # 里程
    IntimateItem=14 # 亲密道具
    KaleidxScopeKey=15 # KaleidxScopeKey