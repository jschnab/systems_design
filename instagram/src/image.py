import io

from PIL import Image, ImageOps

ALLOWED_FORMATS = {"BMP", "GIF", "JPEG", "PNG"}
IMG_MAX_SIZE = 1080
THUMBNAIL_SIZE = 128, 128


def resize(img):
    scale = max(img.width, img.height) / IMG_MAX_SIZE
    if scale <= 1:
        return img
    width = int(abs(img.width / scale))
    height = int(abs(img.height / scale))
    fmt = img.format
    resized = img.resize((width, height))
    resized.format = fmt
    return resized


def to_bytes(img):
    fobj = io.BytesIO()
    if img.format == "BMP":
        img.save(fobj, "JPEG")
    else:
        img.save(fobj, img.format)
    return fobj.getvalue()


def check_format(img):
    if img.format not in ALLOWED_FORMATS:
        raise ValueError(
            f"Image format is {img.format}. "
            f"Should be one of {ALLOWED_FORMATS}."
        )


def make_thumbnail(img):
    img_copy = img.copy()
    img_copy.format = img.format
    img_copy.thumbnail(THUMBNAIL_SIZE)
    return img_copy


def crop_image(img):
    width, height = img.size
    if width > height:
        crop_width = (width - height) // 2
        crop_height = 0
    else:
        crop_width = 0
        crop_height = (height - width) // 2
    return img.crop(
        (crop_width, crop_height, width - crop_width, height - crop_height)
    )


def process_image(data, crop=False):
    img = Image.open(io.BytesIO(data))
    fmt = img.format
    if crop:
        img = crop_image(img)
    img = ImageOps.exif_transpose(img)
    img.format = fmt
    check_format(img)
    img = resize(img)
    return to_bytes(img), to_bytes(make_thumbnail(img))
