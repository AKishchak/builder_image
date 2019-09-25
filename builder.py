import sys
import random
import string
import json
import base64
from PIL import Image, ImageFont, ImageDraw
from math import pi
import requests
from io import BytesIO
from effect import *

DESIGNER_JSON = '../application/config/print_designer.json'


class ImageParam(object):
    def __init__(self, ratio, landw_scale, landh_scale, **kwargs):
        self.ratio = ratio
        self.landw_scale = landw_scale
        self.landh_scale = landh_scale
        self.kwargs = kwargs

        self.font_size = None
        self.text = ''
        self.font = ImageFont.load_default()
        self.width = None
        self.height = None
        self.left = 0
        self.top = 0
        self.angle = 0
        self.origin_x = None
        self.origin_y = None
        self.stroke_width = 0
        self.hi_width = 0
        self.hi_height = 0
        self.hi_left = 0
        self.hi_top = 0
        self.type = None
        self.kind = None
        self.filter = None

        for i in kwargs:
            setattr(self, i, kwargs[i])

    def calculate_data(self):
        data = self.kwargs
        data.update({
            'font_size': 24 * self.ratio,
            'width': int(self.hi_width * self.ratio),
            'height': int(self.hi_height * self.ratio),
            'left': int(
                self.hi_left * self.landw_scale * self.ratio),
            'top': int(self.hi_top * self.landh_scale * self.ratio),
            'angle': float(self.angle) * 180 / pi,
            'origin_x': 'center',
            'origin_y': 'center',
            'stroke_width': float(self.stroke_width) * self.ratio,
            'scale_x': 1,
            'scale_y': 1,
        })
        for i in data:
            setattr(self, i, data[i])
        return data


class MyImage(object):
    def __init__(self, path):
        if path[:4] == 'http':
            response = requests.get(path)
            self.image = Image.open(BytesIO(response.content))
        else:
            self.image = Image.open(path)

    def get(self):
        return self.image

    @staticmethod
    def text(canvas, font, prop):
        size = ImageDraw.Draw(canvas).textsize(prop['text'], font=font)

        background_image = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
        txt = Image.new('RGBA', size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        d.text((0, 0), prop['text'], 'black', font=font)
        w = txt.rotate(prop['angle'], expand=1)
        background_image.paste(w, (prop['left'], prop['top']))
        canvas = Image.alpha_composite(canvas, background_image)

        return canvas

    @staticmethod
    def add(canvas, img, prop):
        img = img.resize((prop['width'], prop['height']))

        mark = img.rotate(prop['angle'], Image.BICUBIC)

        background_image = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
        background_image.paste(mark, (prop['left'], prop['top']))

        canvas = Image.alpha_composite(canvas, background_image)

        return canvas

    def filter(self):
        pass


class ImageProcessor(object):
    def __init__(self):

        self.tmp_name = self.random_word(6)
        self.tmp_hue_name = self.random_word(6)
        self.tmp_hires_name = self.random_word(6)

        self.tmp_path = None
        self.name_path = None
        self.bg_path = None

        self.canvas_sizes = None
        self.json_data = None

        self.font = None

        self.get_argv()

        self.cwidth = self.canvas_sizes['cwidth']
        self.cheight = self.canvas_sizes['cheight']
        self.small_w = self.canvas_sizes['small_w']
        self.small_h = self.canvas_sizes['small_h']

        self.ratio = self.cwidth / self.small_w
        self.landh_scale = 1
        self.landw_scale = 1

        self.land_scale()

        self.open_font()

        self.canvas = Image.new('RGBA', (self.cwidth, self.cheight))

        self.processed()

    def land_scale(self):
        if (self.cwidth / self.cheight) > 1:
            self.ratio = self.cheight / self.small_h
            self.landh_scale = self.ratio / (self.cheight / self.small_h)
            self.landw_scale = (self.cwidth / self.small_w) / self.ratio

    @staticmethod
    def get_path(name: string):
        return f'{name}.png'

    @staticmethod
    def random_word(length: int):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def get_argv(self):
        self.tmp_path = sys.argv[1:][1]
        self.name_path = sys.argv[1:][2]
        self.bg_path = sys.argv[1:][3]

        self.canvas_sizes = json.loads(sys.argv[1:][4])
        self.json_data = json.loads(base64.b64decode(sys.argv[1:][0]))

    def open_font(self):
        try:
            with open(DESIGNER_JSON, 'r') as f:
                data = json.load(f)
                for i in data:
                    if data[i].get('web_font'):
                        self.font = ImageFont.truetype(f'../fonts/prints/{data[i].get("file")}', 24)
        except FileNotFoundError as e:
            pass

    def processed(self):
        for k in self.json_data:
            print(k)
            curr_obj = ImageParam(self.ratio, self.landw_scale, self.landh_scale, **k)
            img_data = curr_obj.calculate_data()

            if k.get('type') == 'text':  # Drawing text
                self.canvas = MyImage.text(self.canvas, self.font, img_data)

            elif k.get('type') == 'image':  # Merge images
                path_image = {'name': self.name_path, 'background': self.bg_path, 'logo': self.tmp_path}
                obj_img = MyImage(path_image[k['kind']]).get()

                if k.get('filter'):
                    obj_img = self.apply_filters(obj_img, k.get('filter'), img_data)

                self.canvas = MyImage.add(self.canvas, obj_img, img_data)

        self.canvas.save(self.get_path(self.tmp_name))

    def apply_filters(self, obj, filter, img_data):
        if filter.get('type') == 'css_hue_rotate':
            obj = change_hue(obj, filter.get('value'))
        elif filter.get('type') == 'css_invert':
            obj = invert_colors(obj)
        elif filter.get('type') == 'css_saturate':
            obj = image_tint(obj)
            obj.convert('RGBA')
        return obj


def main():
    obj = ImageProcessor()


if __name__ == '__main__':
    main()
