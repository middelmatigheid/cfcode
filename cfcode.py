import cv2 as cv
import numpy as np
from PIL import Image, ImageDraw


# Перевод из одной системы счисления в другую
async def convert_to(n, base_from, base_to):
    alph = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'
    m = 0
    for i in range(len(n) - 1, -1, -1):
        m += alph.find(n[i]) * base_from ** (len(n) - i - 1)
    result = ''
    while m != 0:
        result += alph[m % base_to]
        m //= base_to
    return result[::-1]


# Уменьшение размера изображения для удобства отображения при отладке
async def rescale_frame(frame, scale=0.5):
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)
    return cv.resize(frame, (width, height), interpolation=cv.INTER_AREA)


# Считывание кода с изображения
async def detect_code(image):
    # Различные преобразования и фильтрации изображения
    image = cv.cvtColor(np.array(image), cv.COLOR_RGB2BGR)
    min_p = (150, 150, 150)
    max_p = (255, 255, 255)
    image_g = cv.inRange(image, min_p, max_p)
    kernel = np.ones((3, 3), np.uint8)
    opening = cv.morphologyEx(image_g, cv.MORPH_OPEN, kernel)
    dilation = cv.dilate(opening, kernel, iterations=2)
    closing = cv.morphologyEx(dilation, cv.MORPH_CLOSE, kernel)
    sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpen = cv.filter2D(closing, -1, sharpen_kernel)
    canny = cv.Canny(sharpen, 125, 275)

    # Анализ найденных на изображении контуров
    boxes = []
    max_ss = 0
    contours, hierarchy = cv.findContours(canny, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    for contour in contours[2::2]:
        rect = cv.minAreaRect(contour)
        area = int(rect[1][0] * rect[1][1])

        epsilon = 0.01 * cv.arcLength(contour, True)
        approx = cv.approxPolyDP(contour, epsilon, True)
        approx_arr = []
        approx_arr_i = []
        approx_s = sorted(approx.tolist())
        max_s = ((approx_s[0][0][0] - approx_s[-1][0][0]) ** 2 + (
                        approx_s[0][0][1] - approx_s[-1][0][1]) ** 2) ** 0.5
        for i in range(len(approx)):
            for j in range(i + 1, len(approx)):
                if i in approx_arr_i:
                    break
                s = ((approx[i][0][0] - approx[j][0][0]) ** 2 + (approx[i][0][1] - approx[j][0][1]) ** 2) ** 0.5
                if int(s) / int(max_s / 2) < 1:
                    approx_arr_i.append(j)
            if i not in approx_arr_i:
                approx_arr.append(approx[i])
        x, y, w, h = cv.boundingRect(contour)
        ratio = float(w) / h
        if len(approx_arr) == 4 and area > 100 and 1.1 >= ratio >= 0.9:
            boxes.append(approx)
            if max_s < max_ss or max_ss == 0:
                max_ss = max_s

    # Расположение найденных ячеек кода в правильной последовательности
    boxes_y_set = []
    [boxes_y_set.append(max(box[0][0][1], box[1][0][1], box[2][0][1], box[3][0][1])) for box in boxes]
    boxes_y_set = sorted(list(set(boxes_y_set)), reverse=True)
    boxes_y_set.append([])
    i = 0
    while i < len(boxes_y_set) - 1:
        i_end = i
        while i_end < len(boxes_y_set) - 2 and boxes_y_set[i] - boxes_y_set[i_end + 1] < max_ss:
            i_end += 1
        boxes_y_set[-1].append([boxes_y_set[i: i_end + 1], []])
        i = i_end + 1
    boxes_y_set = boxes_y_set[-1]

    boxes_x_set = []
    [boxes_x_set.append(max(box[0][0][0], box[1][0][0], box[2][0][0], box[3][0][0])) for box in boxes]
    boxes_x_set = sorted(list(set(boxes_x_set)), reverse=True)
    boxes_x_set.append([])
    i = 0
    while i < len(boxes_x_set) - 1:
        i_end = i
        while i_end < len(boxes_x_set) - 2 and boxes_x_set[i] - boxes_x_set[i_end + 1] < max_ss:
            i_end += 1
        boxes_x_set[-1].append([boxes_x_set[i: i_end + 1], []])
        i = i_end + 1
    boxes_x_set = boxes_x_set[-1]

    for i in range(len(boxes)):
        for j in range(len(boxes_x_set)):
            if max(boxes[i][0][0][0], boxes[i][1][0][0], boxes[i][2][0][0], boxes[i][3][0][0]) in boxes_x_set[j][0]:
                boxes_x_set[j][1].append(i)
        for j in range(len(boxes_y_set)):
            if max(boxes[i][0][0][1], boxes[i][1][0][1], boxes[i][2][0][1], boxes[i][3][0][1]) in boxes_y_set[j][0]:
                boxes_y_set[j][1].append(i)

    res = []
    for i in range(len(boxes_y_set)):
        for j in range(len(boxes_x_set)):
            for elem in boxes_x_set[j][-1]:
                if elem in boxes_y_set[i][-1]:
                    res.append(elem)

    # Преобразование цветов в числа
    result = ''
    colors = {'0, 0, 0': 0, '0, 0, 255': 1, '0, 255, 255': 2, '0, 255, 0': 3, '255, 255, 0': 4, '255, 0, 0': 5,
                  '255, 0, 255': 6}
    b, g, r = cv.split(image)
    _, image_b = cv.threshold(b, 120, 255, cv.THRESH_BINARY)
    _, image_g = cv.threshold(g, 120, 255, cv.THRESH_BINARY)
    _, image_r = cv.threshold(r, 120, 255, cv.THRESH_BINARY)
    for elem in res:
        elem_x = sorted([boxes[elem][0][0][0], boxes[elem][1][0][0], boxes[elem][2][0][0], boxes[elem][3][0][0]])
        elem_y = sorted([boxes[elem][0][0][1], boxes[elem][1][0][1], boxes[elem][2][0][1], boxes[elem][3][0][1]])
        color = colors[
            f'{image_b[elem_y[0] + (elem_y[-1] - elem_y[0]) // 2, elem_x[0] + (elem_x[-1] - elem_x[0]) // 2]}, {image_g[elem_y[0] + (elem_y[-1] - elem_y[0]) // 2, elem_x[0] + (elem_x[-1] - elem_x[0]) // 2]}, {image_r[elem_y[0] + (elem_y[-1] - elem_y[0]) // 2, elem_x[0] + (elem_x[-1] - elem_x[0]) // 2]}']
        result += str(color)
    return await convert_to(result[::-1], 7, 64), len(boxes_y_set), len(boxes_x_set)


# Попытка найти cf code на изображении
async def detect_code_try(image):
    try:
        return await detect_code(image)
    except:
        return None


# Генерация cf code'а
async def generate_code(n, h, w, borders, user_id=None, convert=True):
    image_shape = [h, w]
    if not borders and convert:
        n = await convert_to(n, 64, 7)
    border = 400
    square = 200
    grid_gap = 50
    arrow_gap = 200
    arrow_triange = 100
    arrow_body = round(arrow_triange / 2) - 5
    colors = {'0': (0, 0, 0), '1': (0, 0, 255), '2': (0, 190, 255), '3': (0, 255, 0), '4': (255, 255, 0), '5': (255, 0, 0), '6': (255, 0, 255), '7': (255, 255, 255)}
    image = Image.new('RGB', (border * 2 + grid_gap * (image_shape[1] - 1) + square * image_shape[1], border * 2 + grid_gap * (image_shape[0] - 1) + square * image_shape[0] + arrow_gap + arrow_triange), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for i in range(image_shape[0]):
        for j in range(image_shape[1]):
            x1 = border + j * (square + grid_gap)
            y1 = border + i * (square + grid_gap)
            x2 = border + (j + 1) * square + j * grid_gap
            y2 = border + (i + 1) * square + i * grid_gap
            if borders:
                if i * image_shape[1] + j == str(n).find('7'):
                    draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1], outline=(0, 255, 0), width=10)
                else:
                    draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1], outline=(0, 0, 0), width=10)
            else:
                draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1])
    x1 = border
    y1 = border + image_shape[0] * square + (image_shape[0] - 1) * grid_gap + arrow_gap + (arrow_triange - arrow_body) // 2
    x2 = border + image_shape[1] * square + (image_shape[1] - 1) * grid_gap - arrow_triange * 3
    y2 = border + image_shape[0] * square + (image_shape[0] - 1) * grid_gap + arrow_gap + (arrow_triange - arrow_body) // 2 + arrow_body
    draw.rectangle((x1, y1, x2, y2), fill=(0, 0, 0))
    x1 = border + image_shape[1] * square + (image_shape[1] - 1) * grid_gap - arrow_triange * 3
    y1 = border + image_shape[0] * square + (image_shape[0] - 1) * grid_gap + arrow_gap
    x2 = border + image_shape[1] * square + (image_shape[1] - 1) * grid_gap - arrow_triange * 3
    y2 = border + image_shape[0] * square + (image_shape[0] - 1) * grid_gap + arrow_gap + arrow_triange
    x3 = border + image_shape[1] * square + (image_shape[1] - 1) * grid_gap
    y3 = border + image_shape[0] * square + (image_shape[0] - 1) * grid_gap + arrow_gap + round(arrow_triange / 2)
    draw.polygon(((x1, y1), (x2, y2), (x3, y3)), fill=(0, 0, 0))
    if borders:
        image.save(f'images//{user_id}.png')
        return True
    else:
        image.save(f'images//{h} {w} {await convert_to(n, 7, 64)}.png')
        return f'{h} {w} {await convert_to(n, 7, 64)}'

#generate_code()
#cap = cv.VideoCapture(1)
#while True:
    #ret, img = cap.read()
    #cv.imshow('img', img)
    #if cv.waitKey(10) == 27:
        #break
    #detect_code(0)

#cap.release()
#cv.destroyAllWindows()

