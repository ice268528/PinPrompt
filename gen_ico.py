"""Generate a proper square multi-size ICO file from PinPrompt.png"""
from PIL import Image
import struct
import os

img = Image.open('PinPrompt.png').convert('RGBA')

# Crop to square (center crop)
w, h = img.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
img_square = img.crop((left, top, left + side, top + side))
print(f'Source: {w}x{h} -> Cropped to square: {side}x{side}')

# Generate multi-size ICO
img_square.save(
    'PinPrompt.ico',
    format='ICO',
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)

# Verify the result
with open('PinPrompt.ico', 'rb') as f:
    header = f.read(6)
    count = struct.unpack('<H', header[4:6])[0]
    print(f'ICO entries: {count}')
    for i in range(count):
        entry = f.read(16)
        w_entry = entry[0] if entry[0] != 0 else 256
        h_entry = entry[1] if entry[1] != 0 else 256
        print(f'  {i+1}. {w_entry}x{h_entry}')

print(f'File size: {os.path.getsize("PinPrompt.ico")} bytes')
