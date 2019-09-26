from PIL import Image, ImageFont, ImageDraw
from PIL.ImageColor import getcolor, getrgb
from PIL.ImageOps import grayscale, invert
from PIL.ImageChops import multiply

from math import pi
from io import BytesIO

import json
import base64
import requests
import string
import random

from sys import argv


class ImageProcessor(object):
    def __init__(self, params, logo_path, name_path, bg_path, ratio_json):
        self.params = params
        self.logo_path = logo_path
        self.name_path = name_path
        self.bg_path = bg_path
        self.ratio_json = ratio_json

        # Init variables
        self.tmp_path = ''
        self.cwidth = 100
        self.cheight = 100
        self.small_h = 50
        self.small_w = 50
        self.landh_scale = 1
        self.landw_scale = 1
        self.ratio = 1
        self.font = None
        self.canvas = None

    def create_data(self):
        letters = string.ascii_lowercase
        rand_str = lambda l: ''.join(random.choice(letters) for i in range(l))
        self.font = ImageFont.truetype('UbuntuMono-BI.ttf', 24)

        self.tmp_path = f'result/{rand_str(6)}.png'
        self.cwidth = self.ratio_json['cwidth']
        self.cheight = self.ratio_json['cheight']
        self.small_h = self.ratio_json['small_h']
        self.small_w = self.ratio_json['small_w']

        if self.cwidth / self.cheight > 1:
            self.ratio = self.cheight / self.small_h
            self.landh_scale = self.ratio / (self.cheight / self.small_h)
            self.landw_scale = (self.cwidth / self.small_w) / self.ratio
        else:
            self.ratio = self.cwidth / self.small_w
            self.landh_scale = 1
            self.landw_scale = 1

        # create canvas
        self.canvas = Image.new('RGBA', (self.cwidth, self.cheight))

    def open_font(self):
        try:
            with open('../application/config/print_designer.json', 'r') as f:
                data = json.load(f)
                for i in data:
                    if data[i].get('web_font'):
                        self.font = ImageFont.truetype(f'../fonts/prints/{data[i].get("file")}', 24)
        except FileNotFoundError as e:
            pass

    def processed(self):
        for data in self.params:
            obj_prop = ImageProp(self.ratio, self.landw_scale, self.landh_scale, **data)
            if obj_prop.type == 'text':
                self.open_font()
                self.canvas = MyImage.text(self.canvas, self.font, obj_prop)

            elif obj_prop.type == 'image':
                path_image = {'name': self.name_path, 'background': self.bg_path, 'logo': self.logo_path}
                if path_image[obj_prop.kind] == '-':
                    continue
                obj_img = MyImage(path_image[obj_prop.kind]).get()

                if obj_prop.filter:
                    obj_img = MyImage.apply_filters(obj_img, obj_prop.filter, obj_prop)

                self.canvas = MyImage.add(self.canvas, obj_img, obj_prop)
        self.canvas.save(self.tmp_path)


class MyImage(object):
    def __init__(self, path):
        path = BytesIO(requests.get(path).content) if path[:4] == 'http' else path
        self.image = Image.open(path)

    def get(self):
        return self.image

    @staticmethod
    def text(canvas, font, prop):
        size = ImageDraw.Draw(canvas).textsize(prop.text, font=font)  # Size area with text

        background_image = Image.new('RGBA', canvas.size, (255, 255, 255, 0))  # Temporary canvas
        txt = Image.new('RGBA', size, (255, 255, 255, 0))  # new transparent picture
        d = ImageDraw.Draw(txt)
        d.text((0, 0), prop.text, 'black', font=font)  # Draw text
        w = txt.rotate(prop.angle, expand=1)  # Turn the text
        background_image.paste(w, (prop.left, prop.top))  # Paste the text into a temporary picture
        canvas = Image.alpha_composite(canvas, background_image)  # Paste text into canvas

        return canvas

    @staticmethod
    def add(canvas, img, prop):
        img = img.resize((prop.width, prop.height))  # Scale image

        mark = img.rotate(prop.angle, Image.BICUBIC)  # Turn the image

        background_image = Image.new('RGBA', canvas.size, (255, 255, 255, 0))  # Temporary canvas
        background_image.paste(mark, (prop.left, prop.top))  # Paste image into a temporary canvas
        # background_image.show()

        canvas = Image.alpha_composite(canvas, background_image)  # Paste into canvas

        return canvas

    @staticmethod
    def apply_filters(img, filter, prop):
        if filter.get('type') == 'css_hue_rotate':
            img = MyImage.change_hue(img, int(filter.get('value')))
        elif filter.get('type') == 'css_invert':
            img = MyImage.invert_colors(img)
        elif filter.get('type') == 'css_saturate':
            img = MyImage.image_tint(img, filter.get('tint'))
            img.convert('RGBA')
        # else:
        #     img = MyImage.image_multiply(img)
        return img

    @staticmethod
    def blend_images(background_image: str, foreground_image: str, alpha: float) -> Image:
        """
        Function to blend two images

        Parameters:
        background_image (str): Path to the image that will act as the background
        foreground_image (str): Path to the image that will act as the foreground
        alpha(float) : Alpha value, can be used to distinguish area of intersection between two images

        Returns:
        Image object for further use
        """
        try:
            background = Image.open(background_image)
            foreground = Image.open(foreground_image)
            merged_image = Image.blend(background, foreground, alpha)
            return merged_image
        except Exception as exc:
            print("Exception in overlay_with_alpha")
            print(exc)
            return None

    @staticmethod
    def overlay_images(background_image: str, foreground_image: str) -> Image:
        """
        Function to merge two images without alpha

        Parameters:
        background_image (str): Path to the image that will act as the background
        foreground_image (str): Path to the image that will act as the foreground

        Returns:
        Image object for further use
        """
        try:
            background = Image.open(background_image)
            foreground = Image.open(foreground_image)
            background.paste(foreground, (0, 0), foreground)
            return background
        except Exception as exc:
            print("Exception in overlay_without_alpha")
            print(exc)
            return None

    @staticmethod
    def change_hue(image, amount: float) -> Image:
        """
        Function to change hue of an image by given amount

        Parameters:
        image (str): Path to the image
        amount (float): Hue amount

        Returns:
        Image object for further use
        """
        # try:
        # Open and ensure it is RGB, not palettised
        img = image.convert('RGBA')

        # Save the Alpha channel to re-apply at the end
        a = img.getchannel('A')

        # Convert to HSV and save the V (Lightness) channel
        v = img.convert('RGB').convert('HSV').getchannel('V')

        # Synthesize new Hue and Saturation channels using values from colour picker
        # colpickerH, colpickerS = 10, 255
        new_h = Image.new('L', img.size, (amount,))
        new_s = Image.new('L', img.size, (255,))

        # Recombine original V channel plus 2 synthetic ones to a 3 channel HSV image
        hsv = Image.merge('HSV', (new_h, new_s, v))

        # Add original Alpha layer back in
        r, g, b = hsv.convert('RGB').split()
        rgba = Image.merge('RGBA', (r, g, b, a))

        return rgba
        # except Exception as exc:
        #     print("Exception in change_hue")
        #     print(exc)
        #     return None

    @staticmethod
    def image_tint(image, tint='#ffffff'):
        """
        Function to merge two images without alpha

        Parameters:
        image (str): Path to the image
        tint (str): Hex code for the tint

        Returns:
        Image object for further use
        """
        image = image.convert('RGB')
        image.load()

        tr, tg, tb = getrgb(tint)
        tl = getcolor(tint, "L")  # tint color's overall luminosity
        tl = 1 if not tl else tl  # avoid division by zero
        tl = float(tl)  # compute luminosity preserving tint factors
        sr, sg, sb = map(lambda tv: tv / tl, (tr, tg, tb))  # per component
        # adjustments
        # create look-up tables to map luminosity to adjusted tint
        # (using floating-point math only to compute table)
        luts = (
                tuple(map(lambda lr: int(lr * sr + 0.5), range(256))) +
                tuple(map(lambda lg: int(lg * sg + 0.5), range(256))) +
                tuple(map(lambda lb: int(lb * sb + 0.5), range(256)))
        )
        lum = grayscale(image)  # 8-bit luminosity version of whole image
        if Image.getmodebands(image.mode) < 4:
            merge_args = (image.mode, (lum, lum, lum))  # for RGB verion of grayscale
        else:  # include copy of image image's alpha layer
            a = Image.new("L", image.size)
            a.putdata(image.getdata(3))
            merge_args = (image, (lum, lum, lum, a))  # for RGBA verion of grayscale
            luts += tuple(range(256))  # for 1:1 mapping of copied alpha values

        return Image.merge(*merge_args).point(luts)

    @staticmethod
    def invert_colors(image) -> Image:
        """
        Function to invert colors of an image

        Parameters:
        image (str): Path to the image

        Returns:
        Image object for further use
        """
        try:
            image = image.convert('RGBA')
            r, g, b, a = image.split()
            rgb_image = Image.merge('RGB', (r, g, b))

            inverted_image = invert(rgb_image)

            r2, g2, b2 = inverted_image.split()

            final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
            image = final_transparent_image
            return image
        except Exception as exc:
            print("Error in invert_colors")
            print(exc)
            return None

    @staticmethod
    def image_multiply(first_image: str, second_image: str) -> Image:
        """
        Function to multiply two images

        Parameters:
        first_image (str): Path to the first image
        second_image (str): Path to the second image

        Returns:
        Image object for further use
        """
        try:
            image_1 = Image.open(first_image)
            image_2 = Image.open(second_image)
            multiplied_image = multiply(image_1, image_2)
            return multiplied_image
        except Exception as exc:
            print("Error in image_multiply")
            print(exc)
            return None


class ImageProp(object):
    def __init__(self, ratio, landw_scale, landh_scale, **kwargs):
        self.ratio = ratio
        self.landw_scale = landw_scale
        self.landh_scale = landh_scale
        self.kwargs = kwargs

        # init variables
        self.hi_width = 100
        self.hi_height = 100
        self.hi_left = 0
        self.hi_top = 0
        self.stroke_width = 0
        self.type = None
        self.text = ''
        self.kind = ''
        self.filter = None

        for i in kwargs:
            setattr(self, i, kwargs[i])

        self.font_size = 24 * self.ratio
        self.width = int(self.hi_width * self.ratio)
        self.height = int(self.hi_height * self.ratio)
        self.left = int(self.hi_left * self.landw_scale * self.ratio)
        self.top = int(self.hi_top * self.landh_scale * self.ratio)
        self.angle = float(self.angle) * 180 / pi


def main():
    params = json.loads(base64.b64decode(argv[1]))
    logo_image_path = argv[2]
    name_image_path = argv[3]
    background_image_path = argv[4]
    ratio_json = json.loads(argv[5])

    processor = ImageProcessor(params, logo_image_path, name_image_path, background_image_path, ratio_json)
    processor.create_data()
    processor.processed()


def test():
    params = [
        {"type": "image", "kind": "background", "logo": "template.jpg", "hi_width": 291, "hi_height": 360, "hi_left": 0,
         "hi_right": 10, "hi_top": 0, "hi_bottom": 10, "angle": 0, "filter": {"type": "css_hue_rotate", "value": "50"}},
        {"type": "image", "kind": "logo", "logo": "template.jpg", "hi_width": 291, "hi_height": 360, "hi_left": 0,
         "hi_right": 10, "hi_top": 0, "hi_bottom": 10, "angle": 0, "filter": {"type": "css_invert", "value": "100"}},
        {"angle": 0, "hi_width": 145, "hi_height": 180, "type": "text", "text": "Testtext", "font": "KrinkesRegular"}
    ]
    logo_image_path = 'https://i.ibb.co/Byptx3h/new-logo.png'
    name_image_path = 'https://i.ibb.co/WnZttMH/star.png'
    background_image_path = 'https://i.ibb.co/XWB8Rft/template.png'
    ratio_json = {"cwidth": 1455, "cheight": 1800, "small_w": 291, "small_h": 360}

    str_param = f'{base64.b64encode(json.dumps(params).encode("utf-8")).decode()} {logo_image_path} {name_image_path} {background_image_path} \'{json.dumps(ratio_json)}\''
    print(str_param)

    processor = ImageProcessor(params, logo_image_path, name_image_path, background_image_path, ratio_json)
    processor.create_data()
    processor.processed()


if __name__ == '__main__':
    if len(argv) == 1:
        test()
    else:
        main()
