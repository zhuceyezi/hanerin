from PIL import Image, ImageDraw, ImageFont


def truncate_text(draw, text, font, block_width, padding=10):
    """根据小块宽度自动截断文字"""
    ellipsis = "..."
    max_width = block_width - 2 * padding
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    if width <= max_width:
        return text
    else:
        while width > max_width and len(text) > 0:
            text = text[:-1]
            bbox = draw.textbbox((0, 0), text + ellipsis, font=font)
            width = bbox[2] - bbox[0]
        return text + ellipsis

background = Image.open("../cloud/assets/templates/b50.png").convert("RGBA")
# 读入背景图
draw = ImageDraw.Draw(background)

# 加载字体
font = ImageFont.truetype('../cloud/assets/fonts/bb4171.ttf', 24)

# 曲目信息示例
songs = [
    {"name": "INTERNET OVERDOSE", "rating": 13.5, "score": 100.9152}
]  * 50

# 布局参数
num_line = 6
width = 210
width_space = 10
height = 120
height_space = 15
x_offset = 50
y_offset = 300
padding = 10

for idx, song in enumerate(songs):
    # 计算位置
    x = (idx % num_line) * (width + width_space) + x_offset
    y = (idx // num_line) * (height + height_space) + y_offset

    # 画圆角小方块
    draw.rounded_rectangle([(x, y), (x + width, y + height)], radius=20, fill=(255, 255, 255, 200))

    # 文字处理
    song_name = truncate_text(draw, song["name"], font, width, padding)
    text_bbox = draw.textbbox((0, 0), song_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]

    # 居中绘制曲名
    draw.text((x + (width - text_width) / 2, y + 10), song_name, font=font, fill="black")

    # 居中绘制得分（比如放在下面一点）
    score_text = f"{song['score']:.4f}%"
    score_bbox = draw.textbbox((0, 0), score_text, font=font)
    score_width = score_bbox[2] - score_bbox[0]
    draw.text((x + (width - score_width) / 2, y + 60), score_text, font=font, fill="black")

# 保存
background.save("output.png")
