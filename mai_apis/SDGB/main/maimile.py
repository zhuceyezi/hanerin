from MaiUserData import MaiUserData
from Config import userId, music_data

if __name__ == '__main__':
    sdgb = MaiUserData(user_id=userId, music_data=music_data, rating_offset=0)
    target = input("舞里程更改为(默认99999)： ")
    if target == "":
        target = "99999"
    target = int(target)
    sdgb.login().maimile(target=target).commit()