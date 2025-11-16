from __future__ import annotations

from math import floor, ceil
from typing import Final, Optional
from typing_extensions import Self

import enum
import logging

from PIL import Image, ImageFont, ImageText, ImageDraw, ImageOps


class Alignment(enum.Enum):
    """Horizontal alignment of content"""
    LEFT   = 0
    CENTER = 1
    RIGHT  = 2

class Modifier(enum.IntFlag):
    '''character modifier for printing text'''
    ...


u8 = int

Pos = tuple[int, int]
'''(width, height)'''

class Canvas():
    width: int
    image_buffer: Image.Image
    font: ImageFont.FreeTypeFont
    font_size: int
    
    def __init__(self, width: int, font_size:int=20):
        self.width = width
        self.font = ImageFont.load_default( 20 )
        self.reset()
    
    def get_true_color_image(self) -> Image.Image:
        return ImageOps.invert( self.image_buffer.convert("RGB") ).convert("1")
    
    def show(self) -> None:
        '''show the internal image buffer as an gui image'''
        self.get_true_color_image().show()
    
    def reset(self) -> None:
        self.image_buffer = Image.new( "1", (self.width, 1) )
    
    def set_width(self, width:int) -> None:
        self.width = width
        new_image = Image.new( "1", (self.width, self.image_buffer.height) )
        new_image.paste( self.image_buffer )
        self.image_buffer = new_image
    
    def get_draw_image(self) -> ImageDraw.ImageDraw:
        return ImageDraw.ImageDraw( self.image_buffer )
    
    def put_image(self, img:Image.Image, pos:Pos) -> None:
        '''draw a pre rendered image on the current image buffer will resize if necessary'''
        required_height = pos[1] + img.height
        
        if( required_height > self.image_buffer.height ): # resize the available canvas
            new_image = Image.new( "1", (self.width, required_height) )
            new_image.paste( self.image_buffer )
            self.image_buffer = new_image
        
        self.image_buffer.paste( img, pos, img )
    
    
    def get_text_bbox(self, text:str, line_space:int=10, mod:Modifier|None=None, alignment:Alignment=Alignment.LEFT) -> tuple[int, int, int, int]:
        return ImageText.Text(text, self.font, "1", line_space).get_bbox()
    def get_text_size(self, text:str, line_space:int=10, mod:Modifier|None=None, alignment:Alignment=Alignment.LEFT) -> tuple[int, int]:
        bbox = self.get_text_bbox( text, line_space, mod, alignment )
        
        return (bbox[2]-bbox[0], bbox[3]-bbox[1])
    
    def generate_text(self, text:str, line_space:int=10, mod:Modifier|None=None, alignment:Alignment=Alignment.LEFT) -> Image.Image:
        txt = ImageText.Text(text, self.font, "1", line_space)
        
        bbox = self.get_text_bbox( text, line_space, mod, alignment )
        
        text_img = Image.new("1", (bbox[2]-bbox[0], bbox[3]-bbox[1]) )
        
        d = ImageDraw.Draw(text_img)
        d.text((-bbox[0], -bbox[1]), txt, 1)
        
        return text_img
    
    
    def generate_barcode(self) -> Image.Image:
        ...
    def generate_qrcode(self) -> Image.Image:
        ...
    def generate_image(self, src, scale, position) -> Image.Image:
        ...
    
    def set_font(self, font_name_ttf:str, size:int) -> Self:
        assert size > 0
        self.font_size = size
        self.font = ImageFont.truetype( font_name_ttf, self.font_size )
        
    def get_font_size(self) -> int:
        return self.font_size
    
    def set_right_space(self, n:u8) -> Self:
        '''set right-side character spacing'''
        ...
    def get_right_space(self) -> u8:
        '''get right-side character spacing'''
        ...
    