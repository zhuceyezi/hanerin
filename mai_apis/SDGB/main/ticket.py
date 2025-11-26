from MaiUserData import MaiUserData
from Config import userId, music_data

if __name__ == "__main__":
    # timestamp = int(time.time())
    # print(timestamp)
    # print(login(timestamp))
    # print(get_ticket())
    # print(logout(timestamp))
    response = input("请注意，不能在上机时使用本工具。请只在出勤时使用本工具。发票后，除非上机打掉，否则无法对账号进行任何操作。同意请按y: ")
    if response.strip() == "y" or response.strip() == "Y":
        sdgb = MaiUserData(userId, music_data)
        sdgb.login().ticket().logout()
    else:
        print("已退出, 未进行任何操作")


