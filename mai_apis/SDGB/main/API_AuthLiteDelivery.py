# Alls.Net AuthLite 更新获取

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import httpx
from loguru import logger
from urllib.parse import parse_qs
import configparser as ini

LITE_AUTH_KEY = bytes([47, 63, 106, 111, 43, 34, 76, 38, 92, 67, 114, 57, 40, 61, 107, 71])
LITE_AUTH_IV = bytes.fromhex('00000000000000000000000000000000')

def auth_lite_encrypt(plaintext: str) -> bytes:
    # 构造数据：16字节头 + 16字节0前缀 + 明文
    header = bytes(16)
    content = bytes(16) + plaintext.encode('utf-8')
    data = header + content
    # 填充并加密
    padded_data = pad(data, AES.block_size)
    cipher = AES.new(LITE_AUTH_KEY, AES.MODE_CBC, LITE_AUTH_IV)
    return cipher.encrypt(padded_data)

def auth_lite_decrypt(ciphertext: bytes) -> str:
    # 解密并去除填充
    cipher = AES.new(LITE_AUTH_KEY, AES.MODE_CBC, LITE_AUTH_IV)
    decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
    # 提取内容并解码
    content = decrypted_data[16:]  # 去除头部的16字节
    return content.decode('utf-8').strip()

def getRawDelivery(title_ver:str="1.51"):
    encrypted = auth_lite_encrypt(f'title_id=SDGB&title_ver={title_ver}&client_id=A63E01C2805')
    r = httpx.post(
        'http://at.sys-allnet.cn/net/delivery/instruction',
        data = encrypted,
        headers = {
            'User-Agent': "SDGB;Windows/Lite",
            'Pragma': 'DFI'
        }
    )
    resp_data = r.content
    decrypted_str = auth_lite_decrypt(resp_data)
    # 过滤所有控制字符
    decrypted_str = ''.join([i for i in decrypted_str if 31 < ord(i) < 127])
    logger.info(f"RAW Response: {decrypted_str}")
    
    return decrypted_str

def parseRawDelivery(deliveryStr):
    """解析 RAW 的 Delivery 字符串，返回其中的有效的 instruction URL 的列表"""
    parsedResponseDict = {key: value[0] for key, value in parse_qs(deliveryStr).items()}
    urlList = parsedResponseDict['uri'].split('|')
    # 过滤掉空字符串和内容为 null 的情况
    urlList = [url for url in urlList if url and url != 'null']
    logger.info(f"Parsed URL List: {urlList}")
    validURLs = []
    for url in urlList:
        # 检查是否是 HTTPS 的 URL，以及是否是 txt 文件，否则忽略
        if not url.startswith('https://') or not url.endswith('.txt'):
            logger.warning(f"Invalid URL will be ignored: {url}")
            continue
        validURLs.append(url)
    logger.info(f"Verified Valid URLs: {validURLs}")
    return validURLs

def getUpdateIniFromURL(url):
    # 发送请求
    response = httpx.get(url, headers={
        'User-Agent': 'SDGB;Windows/Lite',
        'Pragma': 'DFI'
    })
    logger.info(f"成功自 {url} 获取更新信息")
    return response.text

def parseUpdateIni(iniText):
    # 解析配置
    config = ini.ConfigParser(allow_no_value=True)
    config.read_string(iniText)
    logger.info(f"成功解析配置文件，包含的节有：{config.sections()}")
    
    # 获取 COMMON 节的配置
    common = config['COMMON']
    
    # 初始化消息列表
    message = []
    
    # 获取游戏描述并去除引号
    game_desc = common['GAME_DESC'].strip('"')
    
    # 根据前缀选择消息模板和图标
    prefix_icons = {
        'PATCH': ('💾 游戏程序更新 (.app) ', 'PATCH_'),
        'OPTION': ('📚 游戏内容更新 (.opt) ', 'OPTION_')
    }
    icon, prefix = prefix_icons.get(game_desc.split('_')[0], ('📦 游戏更新 ', ''))
    
    # 构建消息标题
    game_title = game_desc.replace(prefix, '', 1)
    message.append(f"{icon}{game_title}")
    
    # 添加可选文件的下载链接（如果有）
    if 'OPTIONAL' in config:
        message.append("往期更新包：")
        optional_files = [f"{url.split('/')[-1]} {url}" for _, url in config.items('OPTIONAL')]
        message.extend(optional_files)
    
    # 添加主文件的下载链接
    main_file = common['INSTALL1']
    main_file_name = main_file.split('/')[-1]
    message.append(f"此次更新包: \n{main_file_name} {main_file}")

    # 添加发布时间信息
    release_time = common['RELEASE_TIME'].replace('T', ' ')
    message.append(f"正式发布时间：{release_time}。\n")
    
    # 构建最终的消息字符串
    final_message = '\n'.join(message)
    logger.info(f"消息构建完成，最终的消息为：\n{final_message}")
    
    return final_message

def get_options(version):
    urlList = parseRawDelivery(getRawDelivery(version))
    for url in urlList:
        iniText = getUpdateIniFromURL(url)
        message = parseUpdateIni(iniText)

if __name__ == '__main__':
    get_options("1.51")
