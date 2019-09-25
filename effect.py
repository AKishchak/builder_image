from PIL import Image
from PIL.ImageColor import getcolor, getrgb
from PIL.ImageOps import grayscale, invert


def image_tint(current_image, tint='#ffffff'):
    if current_image.mode not in ['RGB', 'RGBA']:
        raise TypeError('Unsupported source image mode: {}'.format(current_image.mode))
    current_image = current_image.convert('RGB')
    current_image.load()

    tr, tg, tb = getrgb(tint)
    tl = getcolor(tint, "L")  # tint color's overall luminosity
    if not tl: tl = 1  # avoid division by zero
    tl = float(tl)  # compute luminosity preserving tint factors
    sr, sg, sb = map(lambda tv: tv / tl, (tr, tg, tb))  # per component
    # adjustments
    # create look-up tables to map luminosity to adjusted tint
    # (using floating-point math only to compute table)
    luts = (tuple(map(lambda lr: int(lr * sr + 0.5), range(256))) +
            tuple(map(lambda lg: int(lg * sg + 0.5), range(256))) +
            tuple(map(lambda lb: int(lb * sb + 0.5), range(256))))
    l = grayscale(current_image)  # 8-bit luminosity version of whole image
    if Image.getmodebands(current_image.mode) < 4:
        merge_args = (current_image.mode, (l, l, l))  # for RGB verion of grayscale
    else:  # include copy of image image's alpha layer
        a = Image.new("L", current_image.size)
        a.putdata(current_image.getdata(3))
        merge_args = (current_image, (l, l, l, a))  # for RGBA verion of grayscale
        luts += tuple(range(256))  # for 1:1 mapping of copied alpha values
    print(merge_args)
    print(luts)
    print(Image.merge(*merge_args))
    print(Image.merge(*merge_args).point(luts))

    return Image.merge(*merge_args).point(luts)


def invert_colors(current_image):
    try:
        current_image = current_image.convert('RGBA')
        r, g, b, a = current_image.split()
        rgb_image = Image.merge('RGB', (r, g, b))

        inverted_image = invert(rgb_image)

        r2, g2, b2 = inverted_image.split()

        final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
        current_image = final_transparent_image
        return current_image
    except Exception as exc:
        print("Error in invert_colors")
        print(exc)
        return None


def change_hue(current_image, amount):
    try:
        # Open and ensure it is RGB, not palettised
        img = current_image.convert('RGBA')

        # Save the Alpha channel to re-apply at the end
        A = img.getchannel('A')

        # Convert to HSV and save the V (Lightness) channel
        V = img.convert('RGB').convert('HSV').getchannel('V')

        # Synthesize new Hue and Saturation channels using values from colour picker
        # colpickerH, colpickerS = 10, 255
        newH = Image.new('L', img.size, (amount))
        newS = Image.new('L', img.size, (255))

        # Recombine original V channel plus 2 synthetic ones to a 3 channel HSV image
        HSV = Image.merge('HSV', (newH, newS, V))

        # Add original Alpha layer back in
        R, G, B = HSV.convert('RGB').split()
        RGBA = Image.merge('RGBA', (R, G, B, A))

        return RGBA
    except Exception as exc:
        print("Exception in change_hue")
        print(exc)
        return None
