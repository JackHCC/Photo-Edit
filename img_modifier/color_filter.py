import logging

logger = logging.getLogger()


class ColorFilters:
    filters = {"sepia": "Sepia", "negative": "Negative", "black_white": "Black & White"}
    SEPIA, NEGATIVE, BLACK_WHITE = filters.keys()

#黑白滤镜
def sepia(img):
    pix = img.load()
    for i in range(img.width):
        for j in range(img.height):
            s = sum(pix[i, j]) // 3
            k = 30
            pix[i, j] = (s+k*2, s+k, s)

#均值滤波
def black_white(img):
    pix = img.load()
    for i in range(img.width):
        for j in range(img.height):
            s = sum(pix[i, j]) // 3
            pix[i, j] = (s, s, s)

#负滤镜，底片滤镜
def negative(img):
    pix = img.load()
    for i in range(img.width):
        for j in range(img.height):
            pix[i, j] = (255 - pix[i, j][0], 255 - pix[i, j][1], 255 - pix[i, j][2])


def color_filter(img, filter_name):
    img_copy = img.copy()
    if filter_name == ColorFilters.SEPIA:
        sepia(img_copy)
    elif filter_name == ColorFilters.NEGATIVE:
        negative(img_copy)
    elif filter_name == ColorFilters.BLACK_WHITE:
        black_white(img_copy)
    else:
        logger.error(f"can't find filter {filter_name}")
        raise ValueError(f"can't find filter {filter_name}")

    return img_copy
