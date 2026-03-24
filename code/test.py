import cv2
import numpy as np
import os

# ===== CONFIG =====
input_path = "image1.jpg"   # ảnh gốc của bạn
output_folder = "../../wavelet/dataset/similar"  # nơi lưu ảnh

os.makedirs(output_folder, exist_ok=True)
# đọc ảnh
img = cv2.imread(input_path)

# lưu ảnh gốc
cv2.imwrite(f"{output_folder}/original.jpg", img)

# ===== 1. ROTATE =====
angles = [-15, -7, 7, 15]
h, w = img.shape[:2]

for i, angle in enumerate(angles):
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1)
    rotated = cv2.warpAffine(img, M, (w, h))
    cv2.imwrite(f"{output_folder}/rotate_{i}.jpg", rotated)

# ===== 2. NOISE =====
for i in range(3):
    noise = np.random.normal(0, 20, img.shape)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(f"{output_folder}/noise_{i}.jpg", noisy)

# ===== 3. BLUR =====
blur = cv2.GaussianBlur(img, (5, 5), 0)
cv2.imwrite(f"{output_folder}/blur.jpg", blur)

# ===== 4. BRIGHTNESS =====
bright = cv2.convertScaleAbs(img, alpha=1, beta=30)
dark = cv2.convertScaleAbs(img, alpha=1, beta=-30)

cv2.imwrite(f"{output_folder}/bright.jpg", bright)
cv2.imwrite(f"{output_folder}/dark.jpg", dark)

# ===== 5. FLIP =====
flip = cv2.flip(img, 1)
cv2.imwrite(f"{output_folder}/flip.jpg", flip)

print(" Done!")