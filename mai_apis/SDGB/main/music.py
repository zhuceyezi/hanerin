import dotenv
dotenv.load_dotenv("/home/aleafy/PycharmProjects/Hanerin-Napcat/.env")
from MaiUserData import MaiUserData
from Config import userId, music_data

if __name__ == '__main__':
    sdgb = MaiUserData(user_id=userId, music_data=music_data, rating_offset=int(input("请输入增加的rating数量，若减少用负数: ")))
    sdgb.login().commit()
