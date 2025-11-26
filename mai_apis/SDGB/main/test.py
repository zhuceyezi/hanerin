from MaiUserData import MaiUserData
from ItemType import ItemType
from Config import userId, music_data

if __name__ == '__main__':
    sdgb = MaiUserData(user_id=userId, music_data=music_data, rating_offset=0)
    sdgb.login().unlock(11677).commit()
    # 1751461894
    # sdgb.logout()
