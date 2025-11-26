import json
import math
import os
import zlib
import hashlib
from datetime import datetime, timedelta
import copy
from enum import Enum
from typing import Any

import dotenv

from mai_apis.SDGB.main.API_AuthLiteDelivery import get_options
from mai_apis.SDGB.main.ItemType import ItemType
import httpx
import pytz
from loguru import logger
import random
import time
from ctypes import c_int32
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
VERSION = os.getenv("MAI2_VERSION")

class SDGBApiError(Exception):
    pass

class SDGBRequestError(SDGBApiError):
    pass

class SDGBResponseError(SDGBApiError):
    pass

class SDGBLoginError(SDGBApiError):
    pass

class MaiUserData(object):
    class Aes_pkcs7(object):
        def __init__(self, key: str, iv: str):
            self.key = key.encode('utf-8')
            self.iv = iv.encode('utf-8')
            self.mode = AES.MODE_CBC

        def encrypt(self, content: bytes) -> bytes:
            cipher = AES.new(self.key, self.mode, self.iv)
            content_padded = pad(content, AES.block_size)
            encrypted_bytes = cipher.encrypt(content_padded)
            return encrypted_bytes

        def decrypt(self, content):
            cipher = AES.new(self.key, self.mode, self.iv)
            decrypted_padded = cipher.decrypt(content)
            decrypted = unpad(decrypted_padded, AES.block_size)
            return decrypted

        def pkcs7unpadding(self, text):
            length = len(text)
            unpadding = ord(text[length - 1])
            return text[0:length - unpadding]

        def pkcs7padding(self, text):
            bs = 16
            length = len(text)
            bytes_length = len(text.encode('utf-8'))
            padding_size = length if (bytes_length == length) else bytes_length
            padding = bs - padding_size % bs
            padding_text = chr(padding) * padding
            return text + padding_text

    def __init__(self, user_id: str | int, music_data = None, keychip: str = "A63E01C2805", place_id = 1403, region_name ="北京", region_id = 1,
                 place_name = "插电师电玩北京西单大悦城店", use_proxy: bool = False, proxy_url: str = "", rating_offset = 0):
        if music_data is None:
            music_data = {
                "musicId": 11693,
                "level": 0,
                "playCount": 1,
                "achievement": 0,
                "comboStatus": 0,
                "syncStatus": 0,
                "deluxscoreMax": 0,
                "scoreRank": 0,
                "extNum1": 0
            }
        self.__SCORE_RANK_COEFFICIENT = [0, 0, 0, 0, 0, 80 * 0.136, 90 * 0.152, 94 * 0.168, 97 * 0.2, 98 * 0.203,99 * 0.208, 99.5 * 0.211,100 * 0.216,100.5 * 0.224]
        self.__SPECIAL_SCORE_BORDER = [100.4999 * 0.222, 99.9999 * 0.214, 98.9999 * 0.206]
        self.__RATING_OFFSET = rating_offset
        self.__AES_KEY = "a>32bVP7v<63BVLkY[xM>daZ1s9MBP<R"
        self.__AES_IV = "d6xHIKq]1J]Dt^ue"
        self.__OBFUSCATE_PARAM = "B44df8yT"
        self.__userall_data = None
        self.__upload_playlog_data = None
        self.user_id = user_id
        self.login_timestamp = None
        self.login_id = None
        self.keychip = keychip
        self.place_id = place_id
        self.region_name = region_name
        self.region_id = region_id
        self.place_name = place_name
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.music_data = music_data
        self.play_special = self.__calcPlaySpecial()
        self.__replace_flag = False

    def __get_SDGB_api_hash(self, api):
        # API 的 Hash 的生成
        # 有空做一下 Hash 的彩虹表？
        return hashlib.md5((api + "MaimaiChn" + self.__OBFUSCATE_PARAM).encode()).hexdigest()

    def __calcPlaySpecial(self):
        """使用 c_int32 实现的 SpecialNumber 算法"""
        rng = random.SystemRandom()
        num2 = rng.randint(1, 1037933) * 2069
        num2 += 1024  # GameManager.CalcSpecialNum()
        num2 = c_int32(num2).value
        result = c_int32(0)
        for _ in range(32):
            result.value <<= 1
            result.value += num2 & 1
            num2 >>= 1
        return c_int32(result.value).value

    def get_score_rank_from_achivement(self, achivement):
        score_rank = 13
        if achivement < 100.5:
            score_rank -= 1
        if achivement < 100:
            score_rank -= 1
        if achivement < 99:
            score_rank -= 1
        if achivement < 98:
            score_rank -= 1
        if achivement < 94:
            score_rank -= 1
        if achivement < 90:
            score_rank -= 1
        if achivement < 80:
            score_rank -= 1
        return score_rank

    def __calc_rating_from_achivement(self, achievement, difficulty):
        """
        从定数和达成率计算获得的分数。
        :param achievement: 达成率，以百分比形式，如101.0000
        :param difficulty: 谱面定数
        :return: 谱面分数
        """
        score_rank = self.get_score_rank_from_achivement(achievement)
        rating = 0
        if achievement == 100.4999:
            rating = difficulty * self.__SPECIAL_SCORE_BORDER[0]
        elif achievement == 99.9999:
            rating = difficulty * self.__SPECIAL_SCORE_BORDER[1]
        elif achievement == 98.9999:
            rating = difficulty * self.__SPECIAL_SCORE_BORDER[2]
        else:
            rating = difficulty * self.__SCORE_RANK_COEFFICIENT[score_rank]
        return math.floor(rating)

    def __sdgb_api(self, targetApi: str, data: dict, noLog: bool = False, timeout: int = 30,
                   maxRetries: int = 3) -> dict:
        """
        舞萌DX 2025 API 通讯用函数
        :param data: 请求数据
        :param targetApi: 使用的 API
        :param userAgentExtraData: UA 附加信息，机台相关则为狗号（如A63E01E9564），用户相关则为 UID
        :param noLog: 是否不记录日志
        :param timeout: 请求超时时间（秒）
        :return: 解码后的响应数据
        """
        userAgentExtraData = str(self.user_id)
        # 处理参数
        agentExtra = str(userAgentExtraData)
        aes = self.Aes_pkcs7(self.__AES_KEY, self.__AES_IV)
        endpoint = "https://maimai-gm.wahlap.com:42081/Maimai2Servlet/"

        # 准备好请求数据
        data = json.dumps(data)
        requestDataFinal = aes.encrypt(zlib.compress(data.encode('utf-8')))

        if not noLog:
            logger.debug(f"开始请求 {targetApi}，以 {data}")

        retries = 0
        while retries < maxRetries:
            try:
                # 配置 HTTP 客户端
                if self.use_proxy and self.proxy_url:
                    logger.debug("使用代理")
                    httpClient = httpx.Client(proxy=self.proxy_url, verify=False)
                else:
                    logger.debug("不使用代理")
                    httpClient = httpx.Client(verify=False)

                # 发送请求
                response = httpClient.post(
                    url= endpoint + self.__get_SDGB_api_hash(targetApi),
                    headers={
                        "User-Agent": f"{self.__get_SDGB_api_hash(targetApi)}#{agentExtra}",
                        "Content-Type": "application/json",
                        "Mai-Encoding": "1.50",
                        "Accept-Encoding": "",
                        "Charset": "UTF-8",
                        "Content-Encoding": "deflate",
                        "Expect": "100-continue"
                    },
                    content=requestDataFinal,  # 数据
                    timeout=timeout
                )

                if not noLog:
                    logger.info(f"{targetApi} 请求结果: {response.status_code}")

                if response.status_code != 200:
                    errorMessage = f"请求失败: {response.status_code}"
                    logger.error(errorMessage)
                    raise SDGBRequestError(errorMessage)

                # 处理响应内容
                responseContentRaw = response.content

                # 先尝试解密
                try:
                    responseContentDecrypted = aes.decrypt(responseContentRaw)
                    if not noLog:
                        logger.debug("成功解密响应！")
                except Exception as e:
                    logger.warning(f"解密失败，原始响应: {responseContentRaw}, 错误: {e}")
                    raise SDGBResponseError("解密失败")
                # 然后尝试解压
                try:
                    # 看看文件头是否正确
                    if not responseContentDecrypted.startswith(b'\x78\x9c'):
                        logger.warning("NOT ZLIB FORMAT")
                        raise Exception(f"响应内容不是 zlib 压缩格式, 内容: {responseContentDecrypted}")
                    responseContentFinal = zlib.decompress(responseContentDecrypted).decode('utf-8')
                    if not noLog:
                        # logger.debug("成功解压响应！")
                        logger.debug(f"响应: {responseContentFinal}")
                    return json.loads(responseContentFinal)
                except:
                    logger.warning(f"解压失败，原始响应: {responseContentDecrypted}")
                    raise SDGBResponseError("解压失败")
            except SDGBRequestError as e:
                logger.error(f"请求格式错误: {e}")
                raise
            except SDGBResponseError as e:
                logger.warning(f"响应错误，将重试: {e}")
                retries += 1
                time.sleep(2)
            except Exception as e:
                logger.warning(f"请求失败，将重试: {e}")
                retries += 1
                time.sleep(2)

            finally:
                if 'httpClient' in locals():
                    httpClient.close()

        raise SDGBApiError("重试多次仍然无法成功请求服务器")

    def __get_count(self, ids):
        count = 1
        if isinstance(ids, list):
            count = len(ids)
        return count

    def __login(self):
        self.login_timestamp = int(time.time()) - 60
        file_name = f"/home/aleafy/PycharmProjects/Hanerin-Napcat/apis/SDGB/main/log/last_success_login_timestamp_{self.user_id}"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "w") as f:
            f.write(str(self.login_timestamp))
            f.close()
        logger.info("成功登录")
        logger.debug(f"登录时间戳: {self.login_timestamp}")
        data = {
            "userId": self.user_id,
            "accessCode": "",
            "regionId": self.region_id,
            "placeId": self.place_id,
            "clientId": self.keychip,
            "dateTime": self.login_timestamp,
            "isContinue": False,
            "genericFlag": 0
        }

        login_result = self.__sdgb_api("UserLoginApi", data)
        if login_result["returnCode"] != 1:
            reason = "登录失败!"
            if login_result["returnCode"] == 100:
                reason += "原因: 账号未登出(小黑屋)"
            if login_result["returnCode"] == 102:
                reason += "原因: 账号凭证已过期, 请于公众号重新获取二维码。"
            logger.error(reason)
            raise SDGBLoginError(reason)

        self.login_id = login_result["loginId"]
        return login_result

    def login(self, load_full_data=True):
        """

        :param load_full_data: 是否请求完整的userAll, 仅当确定不需要传分时才使用
        :return:
        """
        self.__login()
        if load_full_data:
            self.__generate_full_userall()
        return self

    def logout(self, timestamp="", check=True):
        if timestamp == "":
            if self.login_timestamp is None:
                file_name = f"/home/aleafy/PycharmProjects/Hanerin-Napcat/apis/SDGB/main/log/last_success_login_timestamp_{self.user_id}"
                with open(file_name,"r") as f:
                    timestamp = f.read()
            else:
                timestamp = self.login_timestamp
        data = {
            "userId": self.user_id,
            "accessCode": "",
            "regionId": self.region_id,
            "placeId": self.place_id,
            "clientId": self.keychip,
            "dateTime": timestamp,
            "type": 1
        }

        logout_result = self.__sdgb_api("UserLogoutApi", data)
        self.login_timestamp = None
        self.login_id = None
        logger.info("成功执行登出操作")

        if not check:
            return self
        res = self.__sdgb_api("GetUserPreviewApi", {"userId":self.user_id,"segaIdAuthKey":""}, noLog=True)
        if res["isLogin"]:
            logger.error("登出失败")
            raise SDGBApiError("登出失败")
        logger.info("登出成功")
        return self

    def __generate_full_userall(self):
        """从服务器取得必要的数据并构建一个比较完整的 UserAll"""
        currentPlaySpecial = self.play_special

        currentUserData2 = self.__sdgb_api("GetUserDataApi", {
            "userId": int(self.user_id),
        }, )['userData']

        # 先构建一个基础 UserAll
        currentUserAll = {
            "userId": self.user_id,
            "playlogId": self.login_id,
            "isEventMode": False,
            "isFreePlay": False,
            "upsertUserAll": {
                "userData": [
                    {
                        "accessCode": "",
                        "userName": currentUserData2['userName'],
                        "isNetMember": 1,
                        "point": currentUserData2['point'],
                        "totalPoint": currentUserData2['totalPoint'],
                        "iconId": currentUserData2['iconId'],
                        "plateId": currentUserData2['plateId'],
                        "titleId": currentUserData2['titleId'],
                        "partnerId": currentUserData2['partnerId'],
                        "frameId": currentUserData2['frameId'],
                        "selectMapId": currentUserData2['selectMapId'],
                        "totalAwake": currentUserData2['totalAwake'],
                        "gradeRating": currentUserData2['gradeRating'],
                        "musicRating": currentUserData2['musicRating'] + self.__RATING_OFFSET,
                        "playerRating": currentUserData2['playerRating'] + self.__RATING_OFFSET,
                        "highestRating": max(currentUserData2['highestRating'], currentUserData2['playerRating'] + self.__RATING_OFFSET),
                        "gradeRank": currentUserData2['gradeRank'],
                        "classRank": currentUserData2['classRank'],
                        "courseRank": currentUserData2['courseRank'],
                        "charaSlot": currentUserData2['charaSlot'],
                        "charaLockSlot": currentUserData2['charaLockSlot'],
                        "contentBit": currentUserData2['contentBit'],
                        "playCount": currentUserData2['playCount'],
                        "currentPlayCount": currentUserData2['currentPlayCount'],
                        "renameCredit": 0,
                        "mapStock": currentUserData2['mapStock'],
                        "eventWatchedDate": currentUserData2['eventWatchedDate'] + ".0",
                        "lastGameId": "SDGB",
                        "lastRomVersion": currentUserData2['lastRomVersion'],
                        "lastDataVersion": currentUserData2['lastDataVersion'],
                        "lastLoginDate": datetime.fromtimestamp(self.login_timestamp).strftime(
                            '%Y-%m-%d %H:%M:%S') + ".0",
                        "lastPlayDate": datetime.now(pytz.timezone('Asia/Shanghai')).strftime(
                            '%Y-%m-%d %H:%M:%S') + '.0',
                        "lastPlayCredit": 1,
                        "lastPlayMode": 0,
                        "lastPlaceId": self.place_id,
                        "lastPlaceName": self.place_name,
                        "lastAllNetId": 0,
                        "lastRegionId": self.region_id,
                        "lastRegionName": self.region_name,
                        "lastClientId": self.keychip,
                        "lastCountryCode": "CHN",
                        "lastSelectEMoney": 0,
                        "lastSelectTicket": 0,
                        "lastSelectCourse": currentUserData2['lastSelectCourse'],
                        "lastCountCourse": 0,
                        "firstGameId": "SDGB",
                        "firstRomVersion": currentUserData2['firstRomVersion'],
                        "firstDataVersion": currentUserData2['firstDataVersion'],
                        "firstPlayDate": currentUserData2['firstPlayDate'],
                        "compatibleCmVersion": currentUserData2['compatibleCmVersion'],
                        "dailyBonusDate": currentUserData2['dailyBonusDate'],
                        "dailyCourseBonusDate": currentUserData2['dailyCourseBonusDate'],
                        "lastPairLoginDate": currentUserData2['lastPairLoginDate'],
                        "lastTrialPlayDate": currentUserData2['lastTrialPlayDate'],
                        "playVsCount": 0,
                        "playSyncCount": 0,
                        "winCount": 0,
                        "helpCount": 0,
                        "comboCount": 0,
                        "totalDeluxscore": currentUserData2['totalDeluxscore'],
                        "totalBasicDeluxscore": currentUserData2['totalBasicDeluxscore'],
                        "totalAdvancedDeluxscore": currentUserData2['totalAdvancedDeluxscore'],
                        "totalExpertDeluxscore": currentUserData2['totalExpertDeluxscore'],
                        "totalMasterDeluxscore": currentUserData2['totalMasterDeluxscore'],
                        "totalReMasterDeluxscore": currentUserData2['totalReMasterDeluxscore'],
                        "totalSync": currentUserData2['totalSync'],
                        "totalBasicSync": currentUserData2['totalBasicSync'],
                        "totalAdvancedSync": currentUserData2['totalAdvancedSync'],
                        "totalExpertSync": currentUserData2['totalExpertSync'],
                        "totalMasterSync": currentUserData2['totalMasterSync'],
                        "totalReMasterSync": currentUserData2['totalReMasterSync'],
                        "totalAchievement": currentUserData2['totalAchievement'],
                        "totalBasicAchievement": currentUserData2['totalBasicAchievement'],
                        "totalAdvancedAchievement": currentUserData2['totalAdvancedAchievement'],
                        "totalExpertAchievement": currentUserData2['totalExpertAchievement'],
                        "totalMasterAchievement": currentUserData2['totalMasterAchievement'],
                        "totalReMasterAchievement": currentUserData2['totalReMasterAchievement'],
                        "playerOldRating": currentUserData2['playerOldRating'],
                        "playerNewRating": currentUserData2['playerNewRating'],
                        "banState": 0,
                        "friendRegistSkip": currentUserData2['friendRegistSkip'],
                        "dateTime": self.login_timestamp
                    }
                ],
                "userExtend": [],  # 需要填上
                "userOption": [],  # 需要填上
                "userGhost": [],
                "userCharacterList": [],
                "userMapList": [],
                "userLoginBonusList": [],
                "userRatingList": [],  # 需要填上
                "userItemList": [],  # 可选，但经常要填上
                "userMusicDetailList": [],  # 需要填上
                "userCourseList": [],
                "userFriendSeasonRankingList": [],
                "userChargeList": [],  # 需要填上
                "userFavoriteList": [],
                "userActivityList": [],  # 需要填上
                "userGamePlaylogList": [
                    {
                        "playlogId": self.login_id,
                        "version": VERSION,
                        "playDate": datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S') + '.0',
                        "playMode": 0,  # // 0: 一般 | 1: Freedom | 2: 段位 | 3: KaleidxScope
                        "useTicketId": -1,
                        "playCredit": 1,
                        "playTrack": 1,
                        "clientId": self.keychip,
                        "isPlayTutorial": False,
                        "isEventMode": False,
                        "isNewFree": False,
                        "playCount": currentUserData2['playCount'],
                        "playSpecial": currentPlaySpecial,
                        "playOtherUserId": 0
                    }
                ],
                "user2pPlaylog": {
                    "userId1": 0,
                    "userId2": 0,
                    "userName1": "",
                    "userName2": "",
                    "regionId": 0,
                    "placeId": 0,
                    "user2pPlaylogDetailList": []
                },
                "userIntimateList": [],
                "userShopItemStockList": [],
                "userGetPointList": [],
                "userTradeItemList": [],
                "userFavoritemusicList": [],
                "userKaleidxScopeList": [],
                "isNewCharacterList": "",
                "isNewMapList": "",
                "isNewLoginBonusList": "",
                "isNewItemList": "",
                "isNewMusicDetailList": "1",  # 可选但经常要填上
                "isNewCourseList": "0",
                "isNewFavoriteList": "",
                "isNewFriendSeasonRankingList": "",
                "isNewUserIntimateList": "",
                "isNewFavoritemusicList": "",
                "isNewKaleidxScopeList": ""
            }
        }
        data = {
            "userId": int(self.user_id)
        }
        # 然后从服务器取得必要的数据
        currentUserExtend = self.__sdgb_api("GetUserExtendApi", data)
        currentUserOption = self.__sdgb_api("GetUserOptionApi", data)
        currentUserRating = self.__sdgb_api("GetUserRatingApi", data)
        currentUserActivity = self.__sdgb_api("GetUserActivityApi", data)
        currentUserCharge = self.__sdgb_api("GetUserChargeApi", data)

        # 清票
        for ticket in currentUserCharge['userChargeList']:
            if int(ticket['stock']) >= 0:
                ticket['stock'] = 0

        # 把这些数据都追加进去
        currentUserAll['upsertUserAll']['userExtend'] = [currentUserExtend['userExtend']]
        currentUserAll['upsertUserAll']['userOption'] = [currentUserOption['userOption']]
        currentUserAll['upsertUserAll']['userRatingList'] = [currentUserRating['userRating']]
        currentUserAll['upsertUserAll']['userActivityList'] = [currentUserActivity['userActivity']]
        currentUserAll['upsertUserAll']['userChargeList'] = currentUserCharge['userChargeList']
        currentUserAll['upsertUserAll']['userMusicDetailList'] = [self.music_data]

        currentUserAll['upsertUserAll']['userGamePlaylogList'] = [
            self.__generate_random_userall_playlog(currentUserData2)]

        currentUserAll['upsertUserAll']["isNewMusicDetailList"] = 0 if self.__replace_flag else 1

        # 完事
        self.__userall_data = currentUserAll
        self.__upload_playlog_data = currentUserData2

    def __generate_random_playlog(self, currentUserData2: dict, track_no = 1) -> dict:
        data = {
            "userId": 0,
            "orderId": 0,
            "playlogId": self.login_id,
            "version": VERSION.split('.', 1)[0] + '0' + VERSION.split('.', 1)[1].replace('.', '') + '0', # 1.51.00 -> 1051000
            "placeId": self.place_id,
            "placeName": self.place_name,
            "loginDate": int(time.time()),  # 似乎和登录timestamp不同
            "playDate": datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d'),
            "userPlayDate": datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S') + '.0',
            "type": 0,
            "musicId": int(self.music_data['musicId']),
            "level": int(self.music_data['level']),
            "trackNo": track_no,
            "vsMode": 0,
            "vsUserName": "",
            "vsStatus": 0,
            "vsUserRating": 0,
            "vsUserAchievement": 0,
            "vsUserGradeRank": 0,
            "vsRank": 0,
            "playerNum": 1,
            "playedUserId1": 0,
            "playedUserName1": "",
            "playedMusicLevel1": 0,
            "playedUserId2": 0,
            "playedUserName2": "",
            "playedMusicLevel2": 0,
            "playedUserId3": 0,
            "playedUserName3": "",
            "playedMusicLevel3": 0,
            "characterId1": currentUserData2['charaSlot'][0],
            "characterLevel1": random.randint(1000, 6500),
            "characterAwakening1": 5,
            "characterId2": currentUserData2['charaSlot'][1],
            "characterLevel2": random.randint(1000, 6500),
            "characterAwakening2": 5,
            "characterId3": currentUserData2['charaSlot'][2],
            "characterLevel3": random.randint(1000, 6500),
            "characterAwakening3": 5,
            "characterId4": currentUserData2['charaSlot'][3],
            "characterLevel4": random.randint(1000, 6500),
            "characterAwakening4": 5,
            "characterId5": currentUserData2['charaSlot'][4],
            "characterLevel5": random.randint(1000, 6500),
            "characterAwakening5": 5,
            "achievement": int(self.music_data['achievement']),
            "deluxscore": int(self.music_data['deluxscoreMax']),
            "scoreRank": int(self.music_data['scoreRank']),
            "maxCombo": 0,
            "totalCombo": random.randint(700, 900),
            "maxSync": 0,
            "totalSync": 0,
            "tapCriticalPerfect": 0,
            "tapPerfect": 0,
            "tapGreat": 0,
            "tapGood": 0,
            "tapMiss": random.randint(1, 10),
            "holdCriticalPerfect": 0,
            "holdPerfect": 0,
            "holdGreat": 0,
            "holdGood": 0,
            "holdMiss": random.randint(1, 15),
            "slideCriticalPerfect": 0,
            "slidePerfect": 0,
            "slideGreat": 0,
            "slideGood": 0,
            "slideMiss": random.randint(1, 15),
            "touchCriticalPerfect": 0,
            "touchPerfect": 0,
            "touchGreat": 0,
            "touchGood": 0,
            "touchMiss": random.randint(1, 15),
            "breakCriticalPerfect": 0,
            "breakPerfect": 0,
            "breakGreat": 0,
            "breakGood": 0,
            "breakMiss": random.randint(1, 15),
            "isTap": True,
            "isHold": True,
            "isSlide": True,
            "isTouch": True,
            "isBreak": True,
            "isCriticalDisp": True,
            "isFastLateDisp": True,
            "fastCount": 0,
            "lateCount": 0,
            "isAchieveNewRecord": True,
            "isDeluxscoreNewRecord": True,
            "comboStatus": 0,
            "syncStatus": 0,
            "isClear": False,
            'beforeRating': currentUserData2['playerRating'],
            'afterRating': currentUserData2['playerRating'] + self.__RATING_OFFSET,
            "beforeGrade": 0,
            "afterGrade": 0,
            "afterGradeRank": 1,
            'beforeDeluxRating': currentUserData2['playerRating'],
            'afterDeluxRating': currentUserData2['playerRating'] + self.__RATING_OFFSET,
            "isPlayTutorial": False,
            "isEventMode": False,
            "isFreedomMode": False,
            "playMode": 0,
            "isNewFree": False,
            "trialPlayAchievement": -1,
            "extNum1": 0,
            "extNum2": 0,
            "extNum4": 3020,
            "extBool1": False,
            "extBool2": False
        }
        return data

    def __generate_random_userall_playlog(self, currentUserData2: dict, total_track_count = 1) -> dict:
        data = {
                        "playlogId": self.login_id,
                        "version": VERSION,
                        "playDate": datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S') + '.0',
                        "playMode": 0,
                        "useTicketId": -1,
                        "playCredit": 1,
                        "playTrack": total_track_count,
                        "clientId": self.keychip,
                        "isPlayTutorial": False,
                        "isEventMode": False,
                        "isNewFree": False,
                        "playCount": currentUserData2['playCount'],
                        "playSpecial": self.play_special,
                        "playOtherUserId": 0
                    }
        return data

    def __upload_user_playlog(self) -> str:
        """
        上传一个 UserPlayLog。
        注意：成绩为随机的空成绩，只用作占位
        返回 Json String。"""

        # 构建一个 PlayLog
        data = {
            "userId": int(self.user_id),
            "userPlaylogList": [self.__generate_random_playlog(self.__upload_playlog_data)]
        }
        # 发送请求
        result = self.__sdgb_api("UploadUserPlaylogListApi", data)
        logger.info("上传游玩记录：结果：" + str(result))
        # 返回响应
        return result

    def __login_and_upload_playlog(self):
        """
        初始化对象，登录并上传playlog。会执行一切所需的操作，如：
        获取并构建初步userall。此时的userall未经过任何修改，存储在
        self.__userall_data中。
        """
        self.__login()
        self.__generate_full_userall()

        # 得先上传
        res = self.__upload_user_playlog()
        return self.__userall_data, res

    def __insert_unlock_data(self, unlock_ids, item_type_list):
        if item_type_list is None or len(item_type_list) == 0:
            logger.warning("[解锁物品] 未指定解锁物品类型，操作未继续！")
            return self
        if unlock_ids is None or len(unlock_ids) == 0:
            logger.warning("[解锁物品] 未指定解锁物品ID，操作未继续！")
            return self
        for item_type in item_type_list:
            if isinstance(unlock_ids, list):
                self.__userall_data['upsertUserAll']['isNewItemList'] = "1" * len(unlock_ids)
                for unlock_id in unlock_ids:
                        self.__userall_data['upsertUserAll']['userItemList'].append(
                            {
                                "itemKind": ItemType.MUSIC,
                                "itemId": item_type,
                                "stock": 1,
                                "isValid": True
                            }
                        )
                        self.__userall_data['upsertUserAll']['userItemList'].append(
                            {
                                "itemKind": item_type,
                                "itemId": unlock_id,
                                "stock": 1,
                                "isValid": True
                            }
                        )
            else:
                self.__userall_data['upsertUserAll']['isNewItemList'] = "11"
                self.__userall_data['upsertUserAll']['userItemList'].append(
                    {
                        "itemKind": item_type,
                        "itemId": unlock_ids,
                        "stock": 1,
                        "isValid": True
                    }
                )
                self.__userall_data['upsertUserAll']['userItemList'].append(
                    {
                        "itemKind": item_type,
                        "itemId": unlock_ids,
                        "stock": 1,
                        "isValid": True
                    }
                )
        return self

    def preview(self):
        return self.__sdgb_api("GetUserPreviewApi", {"userId":self.user_id,"segaIdAuthKey":""}, noLog=True)

    def get_userall(self):
        return self.__userall_data

    def api(self, data, target_api):
        self.__sdgb_api(target_api, data)
        return self

    def unlock(self, unlock_ids, item_type_list=None):
        if item_type_list is None:
            item_type_list = [ItemType.MUSIC, ItemType.MUSIC_MASTER]
        self.__insert_unlock_data(unlock_ids, item_type_list)
        return self

    def replace(self, flag: bool = True):
        """
        设置乐曲覆盖选项，默认为True，True则强制覆盖现有成绩，False则不会影响成绩。
        :param flag: 可选项，设置乐曲是否要覆盖现有成绩。
        """
        self.__replace_flag = flag
        if not self.__userall_data is None:
            self.__userall_data['upsertUserAll']["isNewMusicDetailList"] = 0 if self.__replace_flag else 1
        return self

    def music(self, music_data=None):
        '''
        显式设置传哪首歌, 如果设置过对象的music_data不需要传入
        :param music_data:
        :return:
        '''
        if not music_data is None:
            self.music_data = music_data
            self.__userall_data['upsertUserAll']['userMusicDetailList'] = [music_data]
        return self

    def __upsert_userall_data(self):
        return self.__sdgb_api("UpsertUserAllApi", self.__userall_data)

    def get_active_ticket(self):
        return self.__sdgb_api("GetUserChargeApi", {"userId":self.user_id})

    def ticket(self, ticketId:int = 6, price:int = 4):
        """
        发票，默认6倍票
        请注意号里有票传不上数据，需要先消耗掉
        """
        data = {
            "userId": self.user_id,
            "userCharge": {
                "chargeId": ticketId,
                "stock": 1,
                "purchaseDate": (datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(hours=1)).strftime(
                    "%Y-%m-%d %H:%M:%S.0"),
                "validDate": (datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(hours=1) + timedelta(
                    days=90)).replace(hour=4, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
            },
            "userChargelog": {
                "chargeId": ticketId,
                "price": price,
                "purchaseDate": (datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(hours=1)).strftime(
                    "%Y-%m-%d %H:%M:%S.0"),
                "placeId": self.place_id,
                "regionId": self.region_id,
                "clientId": self.keychip
            }
        }
        self.__sdgb_api("UpsertUserChargelogApi", data)
        return self

    def maimile(self, target=99999):
        """
        修改舞里程
        :param target: 需要达到的舞里程数量
        """
        if target % 10 != 9 or target % 10 != 0:
            logger.error("[舞里程修改] 舞里程不以9或0结尾，为异常数据，不允许上传！未进行任何操作")
            return self
        diff = target - self.__userall_data['upsertUserAll']['userData'][0]['point']
        self.__userall_data['upsertUserAll']['userData'][0]['point'] = target
        self.__userall_data['upsertUserAll']['userData'][0]['totalPoint'] += diff
        return self

    def partner(self, partner_ids, target_level=9999):
        return self.__insert_unlock_data(partner_ids,[ItemType.PARTNER])
    
    def commit(self, max_retries=1):
        """
        上传数据并登出, 仅在需要上传乐曲时使用
        :param max_retries: 可选，最大重试次数，默认1次
        :return:
        """
        try:
            self.__upload_user_playlog()
            self.__upsert_userall_data()
            self.logout()
            return self
        except Exception as e:
            self.logout()
            raise e

    def custom(self, data):
        return self.__sdgb_api("UpsertUserAllApi", data)

    def get_options(self, url):
        return get_options(url)












