from __future__ import annotations

from math import floor, ceil
from typing import ClassVar, Final, Optional, Literal
from typing_extensions import Self

import enum
import logging

import os
import sys
from difflib import get_close_matches
from typing import NamedTuple
from PIL import Image, ImageFont, ImageText, ImageDraw, ImageOps


class Alignment(enum.Enum):
    """Horizontal alignment of content"""
    LEFT    = "left"
    CENTER  = "center"
    RIGHT   = "right"
    JUSTIFY = "justify"

class Modifier(enum.IntFlag):
    '''character modifier for printing text'''
    NONE       = enum.auto()
    BOLD       = enum.auto()
    ITALIC     = enum.auto()
    INVERSE    = enum.auto()
    UNDERSCORE = enum.auto()
    STRIKE     = enum.auto()
    OVERSCORE  = enum.auto()

StrOrBytesPath = str | bytes | os.PathLike[str] | os.PathLike[bytes]

u8 = int

Pos = tuple[int, int]
'''(width, height)'''

class Size():
    width : int
    height: int
    
    @property
    def T(self) -> tuple[int, int]:
        return (self.width, self.height)
    
    def __init__(self, width:int=0, height:int=0):
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f"Size(width={self.width}, height={self.height})"

class BBox():
    left  : int
    top   : int
    right : int
    bottom: int
    
    def __init__(self,
        left  : int = 0,
        top   : int = 0,
        right : int = 0,
        bottom: int = 0
    ):
        self.left   = left
        self.top    = top
        self.right  = right
        self.bottom = bottom
    
    def size(self) -> Size:
        return Size( self.right - self.left, self.bottom - self.top )
    
    @property
    def T(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)
    
    def __str__(self) -> str:
        return f"BBox(left={self.left} top={self.top} right={self.right} bottom={self.bottom})"

class FontVariation(NamedTuple):
    style: str
    file_path: str

FontSet = dict[str, list[FontVariation]]

class FontManager():
    fonts: ClassVar[FontSet]
    
    font_fft: ImageFont.FreeTypeFont
    variations: list[FontVariation]
    
    line_space: int = 0
    right_space: int = 0
    mode: Literal["1", "L"] = "1"
    
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "fonts"):
            FontManager.fonts = FontManager.get_all_fonts()
        return super().__new__(cls)
    
    def __init__(self, font:StrOrBytesPath|None=None, font_size:int=20) -> None:
        '''if font_name is None when default font is loaded'''
        if font is None:
            self.load_default( font_size )
        else:
            self.load( font, font_size )
    
    def load(self, font:StrOrBytesPath, font_size:int=20) -> None:
        assert font_size > 0
        
        # first try getting the Font directly via path or look up by ImageFont
        try:
            self.font_fft = ImageFont.truetype( font, font_size )
        except OSError:
            # else try matching with global fonts
            logging.info( "ImageFont could not find font. Try finding matching font name." )
            
            matches = get_close_matches( font, FontManager.fonts.keys(), 1, 0.5 )
            
            if not matches:
                raise ValueError( f"font \"{font}\" could not be found!" )
            
            
            best_match = matches[0]
            best_file = FontManager.fonts[best_match][0].file_path
            
            for var in FontManager.fonts[best_match]:
                if var.style.lower() == "regular" or var.style.lower() == "book":
                    best_file = var.file_path
                    break
            
            self.font_fft = ImageFont.truetype( best_file, font_size )
            logging.info( f"matched \"{font}\" with \"{best_match} - {self.font_style}\"" )
        
        self.variations = FontManager.get_font_variations( self.font_fft )
    
    def load_default(self, font_size:int=20) -> None:
        self.font_fft = ImageFont.load_default(font_size)
    
    @property
    def font_size(self) -> int:
        return self.font_fft.font.size
    @property
    def font_family(self) -> str:
        return self.font_fft.font.family
    @property
    def font_style(self) -> str:
        return self.font_fft.font.style
    @property
    def font_path(self) -> str:
        return self.font_fft.path
    
    
    def _ascend_height_offset(self) -> int:
        return 0
        # return self._raw_bbox( "Ä", "la" ).size().height \
        #      - self._raw_bbox( "g", "lt" ).size().height
    
    def _raw_bbox(self, text:str, anchor:str="lt") -> BBox:
        size, offset = self.font_fft.font.getsize(
            text, self.mode, "ltr", None, None, anchor
        )
        return BBox( offset[0], offset[1], offset[0]+size[0], offset[1]+size[1] )
    
    def get_line_bbox(self, text_line:str, mod:Modifier|None=None) -> BBox:
        assert "\n" not in text_line
        
        bbox = self._raw_bbox( text_line[0], "la" )
        
        for c in text_line[1::]:
            # "lt" so that we get the true height of the character and not the ascended height
            c_bbox = self._raw_bbox( c, "la" )
            bbox.right += c_bbox.right + self.right_space
            bbox.top = min( bbox.top, c_bbox.top )
            bbox.bottom = max( bbox.bottom, c_bbox.bottom )
        
        return bbox
    
    def get_text_bbox(self, text:str, mod:Modifier|None=None) -> Size:
        size = Size()
        
        lines = text.splitlines()
        for line in lines:
            s = self.get_line_bbox(line, mod).size()
            size.width = max( size.width, s.width )
            size.height += s.height

        size.height += ( len(lines) - 1 ) * ( self._ascend_height_offset() + self.line_space )
        
        return size
    
    def _render_line_old(self, text:str):
        txt = ImageText.Text(text, self.font_fft, "1")
        
        bbox = BBox( *txt.get_bbox((0,0)) )
        
        print( bbox, bbox.size() )
        
        text_img = Image.new("1", bbox.size().T)
        
        d = ImageDraw.Draw(text_img)
        d.fontmode = self.mode
        d.text((-bbox.left, -bbox.top), txt, 1)
        
        return text_img
    
    def render_line(
        self,
        text_line:str,
        mod:Modifier|None=None,
        width:int=None,
        alignment:Alignment=Alignment.LEFT
    ) -> Image.Image:
        text_bbox = self.get_line_bbox( text_line, mod )
        
        assert not width or width >= text_bbox.size().width
        
        text_img = Image.new("1", (width or text_bbox.size().width, text_bbox.size().height))
        
        d = ImageDraw.Draw(text_img)
        d.fontmode = self.mode
        
        x_offset = -text_bbox.left
        y_offset = -text_bbox.top
        
        for c in text_line:
            d.text( (x_offset, y_offset), c, 1, self.font_fft, "la", 0 )
            c_size = self._raw_bbox( c, "la" ).size()
            x_offset += c_size.width + self.right_space
        
        return text_img
    
    def render(self, text:str, mod:Modifier|None=None, alignment:Alignment=Alignment.LEFT) -> Image.Image:
        text_size = self.get_text_bbox( text, mod )
        
        text_img = Image.new("1", text_size.T )
        
        y_offset = 0
        height_offset = self._ascend_height_offset()
        
        for line in text.splitlines():
           line_image = self.render_line( line, mod, text_size.width, alignment )
           line_height = self.get_line_bbox( line, mod ).size().height
           
           text_img.paste( line_image, (0, y_offset), line_image )
           
           y_offset += line_height + height_offset + self.line_space
        
        return text_img
    
    
    def debug_font(self) -> None:
        def _debug(x, s) -> None:
            for d in x.__dir__():
                attr = x.__getattribute__(d)
                if not callable(attr):
                    print( s, f"{d}: {attr}" )
        
        print( "ImageFont:" )
        _debug( self.font_fft, "\t" )
        print( "ImageFont.Font:" )
        _debug( self.font_fft.font, "\t" )
    
    
    @classmethod
    def get_font_variations(cls, font:ImageFont.FreeTypeFont) -> list[FontVariation]:
        variations: list[FontVariation] = [ FontVariation( font.font.style, font.path ) ]
        
        if font.font.family in cls.fonts:
            variations.extend( cls.fonts[font.font.family] )
        
        return variations
    
    
    @staticmethod
    def get_font_dirs() -> list[str]:
        '''get common directories where fonts are stored'''
        
        # borrowed from Pillows: ImageFont.py @ truetype(...)
        dirs = []
        if sys.platform == "win32":
            # check the windows font repository
            # NOTE: must use uppercase WINDIR, to work around bugs in
            # 1.5.2's os.environ.get()
            windir = os.environ.get("WINDIR")
            if windir:
                dirs.append(os.path.join(windir, "fonts"))
        elif sys.platform in ("linux", "linux2"):
            data_home = os.environ.get("XDG_DATA_HOME")
            if not data_home:
                # The freedesktop spec defines the following default directory for
                # when XDG_DATA_HOME is unset or empty. This user-level directory
                # takes precedence over system-level directories.
                data_home = os.path.expanduser("~/.local/share")
            xdg_dirs = [data_home]

            data_dirs = os.environ.get("XDG_DATA_DIRS")
            if not data_dirs:
                # Similarly, defaults are defined for the system-level directories
                data_dirs = "/usr/local/share:/usr/share"
            xdg_dirs += data_dirs.split(":")

            dirs += [os.path.join(xdg_dir, "fonts") for xdg_dir in xdg_dirs]
        elif sys.platform == "darwin":
            dirs += [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        return dirs

    @staticmethod
    def get_all_fonts() -> FontSet:
        '''get all available fonts returns dict[family, FontVariation]]'''
        
        all_font_files: list[str] = []
        
        for dir in FontManager.get_font_dirs():
            for dirpath, dirnames, filenames in os.walk( dir ):
                all_font_files.extend( [ os.path.join(dirpath, f) for f in filenames ] )
        
        all_font_files = list( filter( lambda s: os.path.splitext(s)[1].lower() in [".ttf", ".ttc"], all_font_files ) )
        
        families: FontSet = dict()
        
        for file in all_font_files:
            try:
                font = ImageFont.truetype( file )
            except OSError:
                continue
            
            if font.font.family not in families:
                families[font.font.family] = []
            
            families[font.font.family].append( FontVariation(font.font.style, file) )
            del font
        
        # log all non assigned fonts
        for f in all_font_files:
            for vars in families.values():
                for var in vars:
                    if f == var.file_path:
                        break
                else:
                    continue # inner loop did not break
                break   # inner loop breaked
            else:
                # inner loop did not break
                logging.debug( f"\x1b[31mNOT FOUND\x1b[0m file \x1b[34m{f}\x1b[0m" )
                continue
        
        return families
    
    
class Canvas():
    width: int
    image_buffer: Image.Image
    font: FontManager
    
    def __init__(self, width: int, font_size:int=20):
        self.width = width
        self.font = FontManager( None, font_size )
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
    
    
    def generate_text(self, text:str, line_space:int=10, mod:Modifier|None=None, alignment:Alignment=Alignment.LEFT) -> Image.Image:
        self.font.line_space = line_space
        return self.font.render( text, mod, alignment )
    
    
    def generate_barcode(self) -> Image.Image:
        ...
    def generate_qrcode(self) -> Image.Image:
        ...
    def generate_image(self, src, scale, position) -> Image.Image:
        ...
    
    def set_right_space(self, n:u8) -> None:
        '''set right-side character spacing'''
        ...
    def get_right_space(self) -> u8:
        '''get right-side character spacing'''
        ...
    