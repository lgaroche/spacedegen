from PIL import Image, ImageDraw, ImageFont, ImageSequence

from app.game import Direction

for lives in range(1, 4):
    for moves in range(1, 11):
        for d in range(0, 1):
            direction = Direction(d)
            with Image.open(f"app/static/{direction.name}.gif") as img:
                font = ImageFont.truetype("app/static/upheavtt.ttf", 36)
                frames = []
                for f in ImageSequence.Iterator(img):
                    f = f.convert('RGBA')
                    ImageDraw.Draw(f).text((16, 10), f"moves left: {moves}", font=font, fill=(218, 218, 255, 170))
                    ImageDraw.Draw(f).text((600, 10), f"lives: {lives}", font=font, fill=(218, 218, 255, 170))
                    frames.append(f)
                frames[0].save(f"animation/{direction.value:x}{lives:x}{moves:x}.gif", format='GIF', save_all=True, append_images=frames[1:])
                print(f"animation/{direction.value:x}{lives:x}{moves:x}.gif")