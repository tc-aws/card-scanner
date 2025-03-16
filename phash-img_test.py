import json
import os

import cv2
import imagehash
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
import sqlite3

RECTANGLE_OFFSET = 2
HASH_SIZE = 32

stable_result = []
scan_now = True

STATUS = "WAITING_FOR_CARD"


def get_cached_phash():
    with open('phash_dict_test2.json', 'r') as file:
        phash_dict = json.load(file)
        for key in phash_dict:
            phash_dict[key] = imagehash.hex_to_hash(phash_dict[key])

    return phash_dict


def get_cached_phash_180():
    with open('phash_dict_180_test2.json', 'r') as file:
        phash_dict_180 = json.load(file)
        for key in phash_dict_180:
            phash_dict_180[key] = imagehash.hex_to_hash(phash_dict_180[key])

    return phash_dict_180


def scan_now_variable():
    global scan_now
    scan_now = not scan_now


def get_card_info(hashed_id):
    conn = sqlite3.connect('Database/CardsDB.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, code, name FROM mainTable WHERE id = ? 
        ''',
        (hashed_id,)
    )
    rows = cursor.fetchall()
    if len(rows) > 0:
        return rows[0]
    else:
        return None


def crop_rectangle(frame):
    # img preprocess
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.erode(edges, kernel, iterations=1)

    # find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Get the maximum area
        max_contour = max(contours, key=cv2.contourArea)

        # Get the rotated bounding box
        min_rect = cv2.minAreaRect(max_contour)
        box = cv2.boxPoints(min_rect)
        box = np.intp(box)
        cv2.drawContours(frame, [box], 0, (0, 0, 255), 2)

        x, y, w, h = cv2.boundingRect(max_contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        center, size, angle = min_rect[0], min_rect[1], min_rect[2]
        center, size = tuple(map(int, center)), tuple(map(int, size))
        height, width = frame.shape[:2]

        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        img_rot = cv2.warpAffine(frame, rot_matrix, (width, height))
        img_crop = cv2.getRectSubPix(img_rot, size, center)

        height, width = img_crop.shape[:2]
        if width > height:
            img_crop = cv2.rotate(img_crop, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # img_crop = cv2.resize(img_crop, (1000, 1500))
        # img = ImageTk.PhotoImage(Image.fromarray(img_crop))
        # video_image_label.tkimg = img
        # video_image_label.config(image=img)
        return img_crop
    else:
        return None


def find_most_similar_image(img_crop):
    target_phash = imagehash.phash(Image.fromarray(img_crop), HASH_SIZE)
    similarity_scores_1 = {}
    for key in phash_dict:
        score_0_0 = target_phash - phash_dict[key]
        score_0_1 = target_phash - phash_dict_180[key]
        if score_0_0 < score_0_1:
            similarity_scores_1[key] = score_0_0
        else:
            similarity_scores_1[key] = score_0_1

    target_phash_180 = imagehash.phash(Image.fromarray(img_crop).rotate(180), HASH_SIZE)
    similarity_scores_2 = {}
    for key in phash_dict:
        score_1_0 = target_phash_180 - phash_dict[key]
        score_1_1 = target_phash_180 - phash_dict_180[key]
        if score_1_0 < score_1_1:
            similarity_scores_2[key] = score_1_0
        else:
            similarity_scores_2[key] = score_1_1

    most_similar_image = min(similarity_scores_1, key=similarity_scores_1.get)
    most_similar_image_2 = min(similarity_scores_2, key=similarity_scores_2.get)
    # print(similarity_scores_1[most_similar_image], similarity_scores_2[most_similar_image_2])

    # THRESHOLD = 0
    # if similarity_scores_1[most_similar_image] > THRESHOLD or similarity_scores_2[most_similar_image_2] > THRESHOLD:
    #     return ""
    if most_similar_image != most_similar_image_2:
        return ""
    return most_similar_image


def update_frame():
    global scan_now, STATUS

    ret, frame = cap.read()

    img_crop = crop_rectangle(frame)

    most_similar_image = find_most_similar_image(img_crop)
    print(most_similar_image)
    # if img_crop is not None and scan_now:
    #     most_similar_image = find_most_similar_image(img_crop)
    #
    #     # print(most_similar_image)
    #     if len(stable_result) < 10:
    #         stable_result.append(most_similar_image)
    #     else:
    #         stable_result.pop(0)
    #         stable_result.append(most_similar_image)
    #
    #     if all(elem == stable_result[0] for elem in stable_result) and stable_result[0] != "":
    #         if STATUS != "DETECTED":
    #             # scan_now = False
    #             card_info = get_card_info(stable_result[0])
    #             print(card_info)
    #             # save record...
    #             STATUS = "DETECTED"
    #     else:
    #         STATUS = "WAITING_FOR_CARD"
    #
    #     print(STATUS)

    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    img = ImageTk.PhotoImage(image=frame)
    video_label.imgtk = img
    video_label.configure(image=img)

    window.after(100, update_frame)  # Update frame after 10 milliseconds


phash_dict = get_cached_phash()
phash_dict_180 = get_cached_phash_180()

window = tk.Tk()
window.title("OpenCV Video Stream in Tkinter")

# Load the webcam
cap = cv2.VideoCapture(1)
# cap = cv2.VideoCapture(2)

# Create a Button
scan_now_button = tk.Button(window, text="掃描", command=scan_now_variable)
scan_now_button.pack()

# Create a Label widget to display card info
card_name_label = tk.Label(window, text="--", font=('Helvetica', 16))
card_name_label.pack()
card_image_label = tk.Label(window, image="")
card_image_label.pack()

# # tmp
video_image_label = tk.Label(window, image="")
video_image_label.pack()

# Create a label to display the video stream
video_label = tk.Label(window)
video_label.pack()

# Start updating the frame
update_frame()

window.mainloop()

# Release the webcam and close the OpenCV window
cap.release()
cv2.destroyAllWindows()
