from __future__ import annotations

from math import floor, ceil
from typing import Final, Optional
from typing_extensions import Self
from time import sleep

import enum
import logging

from device_interface.printer_io import PrinterIO
from ImageUtils import Canvas, Alignment, Modifier

# partially as labelled in https://www.novopos.ch/client/EPSON/TM-T20/TM-T20_eng_qr.pdf
class ESC_POS_CONSTANT():
    NUL: Final[bytes] = b"\x00"
    EOT: Final[bytes] = b"\x04"
    ENQ: Final[bytes] = b"\x05"
    DLE: Final[bytes] = b"\x10"
    DC4: Final[bytes] = b"\x14"
    CAN: Final[bytes] = b"\x18"
    ESC: Final[bytes] = b"\x1b"
    FS : Final[bytes] = b"\x1c"
    GS : Final[bytes] = b"\x1d"
    
    RT_STATUS: Final[bytes] = DLE + EOT


#------------------------------------------------------------------------------
# Configuration Enums
#------------------------------------------------------------------------------

class Status():
    '''Printer Status and flags for general esc pos thermal printer'''
    class Status_Flag(enum.Enum):
        '''Bit-Flags for individual statuses'''
        # regard pages 6-7 for reference: https://aures-support.com/DATA/drivers/Imprimantes/Commande%20ESCPOS.pdf
        
        OFFLINE                : Final[Status.Status_Flag] = ( 0, 0b0000_1000 )
        COVER_OPEN             : Final[Status.Status_Flag] = ( 1, 0b0000_0100 )
        PRINTING_STOPPED       : Final[Status.Status_Flag] = ( 1, 0b0010_0000 )
        FEED_BY_BUTTON         : Final[Status.Status_Flag] = ( 1, 0b0000_1000 )    # may not be present
        ERROR_OCCURRED         : Final[Status.Status_Flag] = ( 1, 0b0100_0000 )
        ERROR_UNRECOVERABLE    : Final[Status.Status_Flag] = ( 2, 0b0010_0000 )
        ERROR_AUTO_RECOVERABLE : Final[Status.Status_Flag] = ( 2, 0b0100_0000 )
        PAPER_NEAR_END         : Final[Status.Status_Flag] = ( 3, 0b0000_0110 )    # may always be true
        NO_PAPER               : Final[Status.Status_Flag] = ( 3, 0b0110_0000 )
        
        byte: int
        flag: int
        def __init__(self, byte, flag):
            self.byte = byte
            self.flag = flag
            

    status: bytes
    
    def __contains__(self, flag:Status_Flag) -> bool:
        if flag.byte >= len(self.status):
            return False
        
        return (self.status[flag.byte] & flag.flag) == flag.flag
    def __and__(self, flag:Status_Flag) -> bool:
        return self.__contains__(flag)
    def __str__(self) -> str:
        return self.status.hex(":")
    def info(self) -> str:
        s = ""
        
        for byte in range(len(self.status)):
            s += f"{hex( self.status[byte] )}: "
            
            flags = [ sf.name for sf in Status.Status_Flag if sf.byte == byte and sf in self ]
            
            s += ', '.join(flags) + "\n"
        
        return s

class High_Density_Flag(enum.Enum):
    """Density Modifier for raster images. Will double the dots per bit in the specified axes"""
    NONE  : int = 0b00
    WIDTH : int = 0b01
    HEIGHT: int = 0b10
    BOTH  : int = WIDTH | HEIGHT

class MODE(enum.Enum):
    '''Print Mode'''
    DIRECT = enum.auto()
    """
    in *DIRECT* mode all print events will in general be send directly to the
    thermal printer.
    """
    
    BUFFERED = enum.auto()
    """
    in *BUFFERED* mode all print events will be buffered in the internal view
    buffer and must be explicitly flushed to be send to the thermal printer
    """


u8 = int

class Printer( PrinterIO ):
    """
    High-level synthesized ESC/POS-style printer interface.

    This class provides a feature-compatible ESC/POS-like API for printers that
    do not fully implement the ESC/POS command set. Instead of sending native
    ESC/POS instructions, all printable content—text, images, barcodes,
    QR codes, and raster graphics—is prerendered into an internal buffer
    or directly rasterized into a byte stream suitable for the target device.

    The goal is to emulate the observable behavior of a traditional ESC/POS
    printer while bypassing unsupported or nonstandard command sequences.
    This interface exposes a compatible, high-level API whose output is converted
    into rasterized image data before transmission.

    Core responsibilities:
        • Manage printer geometry (dots per mm, paper width, margins).
        • Handle movement operations (feeding, reverse feeding, alignment).
        • Maintain internal text/graphics state (font, spacing, modifiers).
        • Render content into a paint buffer or directly output raster images.
        • Provide status inquiry methods.

    This abstraction enables consistent behavior across heterogeneous,
    partially-ESC/POS-compatible printers by using a unified raster pipeline.
    
    Functionalities and Features are inspired and based on the common esc/pos definitions
    found under https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/index.html
    """
    
    _dpmm: Final[int]
    '''dot density in dots per mm'''
    
    _width_physical: Final[int]
    '''true (max possible) width in mm'''
    
    _width_assumed: int
    '''assumed width in mm'''
    
    _status_bytes: Final[int]
    '''number of status fields in bytes to be inquired'''
    
    _print_auto_feed: Final[int]
    '''automatic feed in dots performed by the printer after printing an image'''
    
    _cut_print_head_distance: Final[int]
    '''the distance in dots the cut edge is away from the print head'''
    
    def __init__(
        self,
        dpmm:int,
        max_width_mm:int,
        status_bytes:int=4,
        auto_feeding:int=1,
        cut_head_distance:int=0
    ):
        """
        Configure printer parameters

        Args:
            dpmm (int): dot density in dots per mm
            max_width_mm (int): max physical paper width in mm
            status_bytes (int): number of status fields in bytes to be inquired. Defaults to 4 for general esc pos printers
        """
        self._dpmm = dpmm
        self._width_physical = max_width_mm
        self._width_assumed = self._width_physical
        self._status_bytes = status_bytes
        self._cut_print_head_distance = cut_head_distance
        self._print_auto_feed = auto_feeding
        
        self._print_mode = MODE.DIRECT
        self._image_buffer = Canvas( self.dots_width )
    
    def __del__(self):
        """clean up printer communication"""
        self.close()
    
    #--------------------------------------------------------------------------
    # Attributes
    #--------------------------------------------------------------------------
    @property
    def max_width(self) -> int:
        '''get the max physical paper width in mm'''
        return self._width_physical
    @property
    def width(self) -> int:
        '''get the current paper width in mm'''
        return self._width_assumed
    @property
    def dpmm(self) -> int:
        '''get the dots density in dots per mm of the printer head'''
        return self._dpmm
    @property
    def dpi(self) -> int:
        '''get the dots density in dots per inch of the printer head'''
        mm_per_in = 25.4
        return floor( self._dpmm * mm_per_in )
    
    @property
    def dots_width(self) -> int:
        '''return the printable width in dots'''
        return floor( self._dpmm * self._width_assumed )
    
    def set_paper_width(self, width_mm:int ) -> None:
        '''set a new centered paper width in mm'''
        assert 0 < width_mm, f"new width must be greater than 0"
        assert width_mm <= self._width_physical, f"new width must be smaller than the physical possible width of {self._width_physical}mm"
        self._width_assumed = width_mm
    
    def reset_paper_width(self) -> None:
        '''reset to the max physical paper width'''
        self.set_paper_width( self._width_physical )
    
    
    #--------------------------------------------------------------------------
    # Status Inquiry
    #--------------------------------------------------------------------------
    def _raw_status_query(self, byte_index:int) -> int:
        '''inquires the supplied status byte'''
        assert byte_index >= 1, "byte index must be at least 1"
        
        self._raw( ESC_POS_CONSTANT.RT_STATUS + byte_index.to_bytes(1, "little") )
        
        return int(self._read()[0])
    
    def get_status(self) -> Status:
        '''get whole status of printer'''
        status = Status()
        
        status.status = bytes( [self._raw_status_query(i) for i in range(1, self._status_bytes+1)] )
        
        return status
    
    
    #--------------------------------------------------------------------------
    # Feeding - Interface
    #--------------------------------------------------------------------------
    def _feed(self, n:int, mode:bytes) -> None:
        assert n >= 0, "n must be greater than 0"
        assert mode in [ b"d", b"J", b"e", b"K" ], f"invalid feed mode {mode}"
        
        # recursively feed the max amount if n is lager than the max amount 255
        if n > 0xff:
            self._feed( 0xff, mode )
            self._feed( n-0xff, mode )
            return
        
        self._raw(ESC_POS_CONSTANT.ESC + mode + n.to_bytes(1, "little"))
    
    def feed_lines(self, n: int) -> None:
        '''feed the paper by *n* lines'''
        
        if n < 0: # if feed opposite direction
            self.feed_reverse_lines( -n )
            return

        # ESC d n
        self._feed( n, b"d" )
    
    def feed_dots(self, n: int) -> None:
        '''feed the paper by *n* dots'''
        
        if n < 0: # if feed opposite direction
            self.feed_reverse_dots( -n )
            return

        # ESC J n
        self._feed( n, b"J" )
    
    def feed_reverse_lines(self, n:int) -> None:
        '''reverse feed the paper by *n* lines'''
        
        if n < 0: # if feed opposite direction
            self.feed_lines( -n )
            return

        # ESC e n*32
        self._feed( n, b"e" )
    
    def feed_reverse_dots(self, n:int) -> None:
        '''reverse feed the paper by *n* dots'''
        
        if n < 0: # if feed opposite direction
            self.feed_dots( -n )
            return

        # ESC K n*32
        self._feed( n, b"K" )
    
    
    def feed_for_cut(self) -> None:
        '''feed the paper by the amount the cut edge is away from the print head'''
        self.feed_dots( self._cut_print_head_distance )
    
    def reverse_feed_from_cut(self) -> None:
        '''reverse feed the paper by the amount the cut edge is away from the print head'''
        self.feed_dots( -self._cut_print_head_distance )
    
    #--------------------------------------------------------------------------
    # Printing
    #--------------------------------------------------------------------------
    _print_mode: MODE
    '''internal printing mode'''
    
    _modifier: Modifier
    '''active character modifier'''
    
    _image_buffer: Canvas
    '''internal image buffer'''
    
    # mode --------------------------------------------------------------------
    def set_mode(self, mode:MODE) -> None:
        '''set the current printing mode'''
        self._print_mode = mode
    
    def get_mode(self) -> MODE:
        return self._print_mode
    
    # view buffer -------------------------------------------------------------
    def flush(self):
        '''print and resets the internal buffer'''
        raise NotImplementedError()
    
    def clear(self):
        '''clear the internal buffer'''
        raise NotImplementedError()
    
    def get_view_buffer(self) -> object:
        '''get the internal buffered image'''
        raise NotImplementedError()
    
    # text --------------------------------------------------------------------
    def print(self, text:str) -> Self:
        ...
    
    def set_font(self, font:object) -> Self:
        ...
    def get_font(self) -> object:
        ...
   
    def set_font_size(self, size:int) -> Self:
        ...
    def get_font_size(self) -> int:
        ...
    
    def set_line_spacing(self, n:u8) -> Self:
        '''set line spacing [ESC 3]'''
        ...
    def get_line_spacing(self) -> u8:
        ...
    
    def set_right_space(self, n:u8) -> Self:
        '''set right-side character spacing [ESC SP]'''
        ...
    def get_right_space(self) -> u8:
        '''get right-side character spacing'''
        ...
    
    def set_text_modifier(self, mod:Modifier) -> Self:
        ...
    def unset_text_modifier(self, mod:Modifier) -> Self:
        ...
    def get_text_modifier(self) -> Modifier:
        ...
    
    def set_horizontal_tab_positions(self, *tab_pos:u8) -> Self:
        '''set horizontal tab positions [ESC D]'''
        ...
    def get_horizontal_tab_positions(self) -> list[u8]:
        ...
    
    def HT(self, index:Optional[int]=None) -> Self:
        '''Horizontal tab'''
        ...
    
    def set_left_margin(self, left:int) -> Self:
        '''set left margin [GS L]'''
        ...
    def get_left_margin(self) -> int:
        ...
    
    def set_print_area_width(self, width:int) -> Self:
        '''set print area width [GS W]'''
        ...
    def get_print_area_width(self) -> int:
        ...
    
    def move_cursor_abs(self, column:int, line:int) -> Self:
        ...
    def move_cursor_rel(self, column:int, line:int=0) -> Self:
        ...
    def get_cursor(self) -> tuple[int, int]:
        ...
    
    def set_alignment(self, alignment:Alignment) -> Self:
        '''set print area alignment [ESC a]'''
        ...
    def get_alignment(self) -> Alignment:
        ... 
    
    def barcode(self) -> Self:
        ...
    def qrcode(self) -> Self:
        ...
    
    def image(self, src, scale, position) -> Self:
        ...
    
    
    def print_raster_image(
        self,
        data              : bytes,
        width_in_bytes    : int,
        alignment         : Alignment = Alignment.CENTER,
        density           : High_Density_Flag = High_Density_Flag.NONE,
        assert_image_width: bool = False
    ) -> None:
        """
        directly send and print a rasterized image

        - Note: This bypasses the internal paint buffer and directly prints to the label
        - Note: dots are printed from left to right where the least significant bit is printed first
                and the most significant bit is printed last

        Args:
            data (bytes): raster image data as bytes
            width_in_bytes (int): width of raster image in bytes
            alignment (Alignment, optional): align image in the assumed width. Defaults to Alignment.CENTER.
            density (High_Density_Flag, optional): density modifier. Defaults to 0.
            assert_image_width (bool, optional): will throw an assertion error when image is too wide to fit in the print space. Defaults to False.
        """
        
        rows = ceil( len(data) / width_in_bytes )
        
        assert 0 < width_in_bytes < 2**16, f"byte_width is {width_in_bytes} but must be between [0, {2**16}]"
        assert 0 < rows < 2**16, f"data contains {rows} many rows but row count must be between [0, {2**16}]"
        
        width_offset_mm = ( self._width_physical - self._width_assumed ) / 2
        width_offset_dots = width_offset_mm * self._dpmm
        width_offset_bytes = floor( width_offset_dots / 8 )
        
        image_space_avail = (self._width_assumed * self._dpmm) // 8 - width_in_bytes  # in bytes
        
        if assert_image_width:
            assert image_space_avail >= 0, f"image is {width_in_bytes * 8} dots in width and too wide to fit in the available space: {self._width_assumed * self._dpmm} dots"
        
        padding_bytes = width_offset_bytes
        
        if alignment == Alignment.CENTER:
            padding_bytes += image_space_avail // 2
        if alignment == Alignment.RIGHT:
            padding_bytes += image_space_avail
        
        padded_data = bytearray()
        for i in range( rows ):
            padded_data.extend( bytes(padding_bytes) )
            padded_data.extend( data[ i*width_in_bytes : (i+1)*width_in_bytes ] )
        
        self._raw( self._raster_img_format( padded_data, padding_bytes + width_in_bytes, density ) )
        
        # for some reason reverse feedings will be blocked until one (forward) feeding command was send to the printer
        self.feed_dots( 0 )
    
    #--------------------------------------------------------------------------
    # Testing / Debugging
    #--------------------------------------------------------------------------
    def test_checkerboard(
        self,
        checker_size:int                   = 8,
        lines       :int                   = 4,
        columns     :int|None              = None,
        density     :High_Density_Flag|int = High_Density_Flag.NONE,
        alignment   :Alignment             = Alignment.CENTER
    ) -> None:
        """
        print test checkerboard
        
        Args:
            checker_size (int): size in dots of a single tiling square. Defaults to 8.
            lines (int, optional): amount of lines. Defaults to 4.
            columns (int|None, optional): amount of columns. If None will fill whole width. Defaults to None.
            density (High_Density_Flag, optional): density modifier. Defaults to 0.
            alignment (Alignment, optional): align the pattern in the print space, has no effect when _columns_ is None. Defaults to Alignment.CENTER.
        """
        density = density.value if isinstance( density, High_Density_Flag ) else density
        dots_per_bit = 1 + ( density & High_Density_Flag.WIDTH.value )
        
        avail_dots = self._dpmm * self._width_assumed
        
        # assert that at least 2 tiles fit on one line
        assert dots_per_bit <= checker_size <= avail_dots//2, f"checker_size is {checker_size} but must be in between {[dots_per_bit, avail_dots//2]}"
        assert lines > 0, f"lines is {lines} but must be greater than 0"
        assert 0 < columns <= avail_dots // checker_size, f"columns is {columns} but must be in between {[0, avail_dots // checker_size]}"
        
        bits_per_tile  = ceil( checker_size / dots_per_bit )
        bits_per_line  = columns * bits_per_tile
        
        bytes_per_line = bits_per_line // 8
        
        assert bytes_per_line > 0, "pattern must be at least one byte long"
        
        tile_black = [ 1 for _ in range(bits_per_tile) ]
        tile_white = [ 0 for _ in range(bits_per_tile) ]
        
        total_bits = []
        for l in range(lines):
            line_bits = []
            
            is_inverse_pattern = l % 2 # shift row pattern
            for i in range(is_inverse_pattern, columns+is_inverse_pattern):
                line_bits.extend( tile_white if i % 2 == 0 else tile_black )
            
            line_bits = line_bits[:bits_per_line] # truncate to fit into available space
            
            total_bits += line_bits*checker_size
        
        data = Printer._bits_to_bytes( total_bits )
        
        self.print_raster_image( data, bytes_per_line, alignment, density, False )

    def test_line(self, height:int=8, density:High_Density_Flag|int=High_Density_Flag.NONE) -> None:
        """print single bar of dot height over entire line"""
        assert height > 0, f"height is {height} must be greater than 0"
        
        density = density.value if isinstance( density, High_Density_Flag ) else density
        dots_per_bit = 1 + ( density & High_Density_Flag.WIDTH.value )
        
        max_dots = self._dpmm * self._width_physical
        
        bits_per_line  = max_dots // dots_per_bit
        bytes_per_line = bits_per_line // 8

        data = bytearray( [0xFF,]*bytes_per_line ) * height
        
        self._raw( self._raster_img_format( data, bytes_per_line, density ) )
    
    def test_revers_feed(self, feed_start:int, feed_end:int, test_points:int, spacing:int=32, padding:int=64) -> None:
        """
        This is a test to calibrate the reverse feed offset.
        
        This will loop over the range supplied with _feed_start_ and _feed_end_ and 
        will feed and reverse feed _test_points_ many times

        NOTE: This will cause high load/stress for the mechanical feeding system and
              should therefor be utilized with care else potentially risking fatigue or loss of precision

        Args:
            feed_start (int): starting feed line number
            feed_end (int): end feed line number
            test_points (int): repetitions/points per feed
            spacing (int, optional): spacing in dots between individual feed loops. Defaults to 32.
            padding (int, optional): left side padding in dots. Defaults to 64.
        """
        assert test_points > 0, f"test_points is {test_points} must be greater than 0"
        assert spacing > 0 and spacing % 8 == 0, f"spacing is {spacing} must be greater than 0 and divisible by 8"
        assert padding > 0 and padding % 8 == 0, f"padding is {padding} must be greater than 0 and divisible by 8"
        assert 0 <= feed_start <= feed_end, f"feed_start is {feed_start} must be between [0, {feed_end}]"

        max_dots = self._dpmm * self._width_physical
        max_feed_end = feed_start + (max_dots - 2*padding) // (spacing-1 + test_points)
        assert feed_start <= feed_end < max_feed_end, f"feed_end is {feed_end} must be between [{feed_start}, {max_feed_end}]"
        
        test_point_byte_width = ceil(test_points / 8)
        
        pad_bytes = padding // 8
        pads = bytearray( padding // 8 )
        
        density = High_Density_Flag.BOTH
        
        for feed in range(feed_start, feed_end+1):
            # print reference line
            buffer = pads + bytes([0xFF,]*test_point_byte_width)
            self._raw( self._raster_img_format( buffer, pad_bytes + test_point_byte_width, density ) )
            
            self.feed_lines(feed) # pre-feed for loop
            for tp in range(test_points):
                self.feed_reverse_lines(feed) # un-feed
                
                bits = [0,]*test_points
                bits[tp] = 1
                
                buffer = pads + Printer._bits_to_bytes( bits )
                self._raw( self._raster_img_format( buffer, test_point_byte_width, density ) )
                
                self.feed_lines(feed) # re-feed for next loop
                logging.info( f"feed: {feed} / {feed_end} tp: {tp+1} / {test_points}" )
            self.feed_reverse_lines(feed) # un-feed from loop
            
            logging.info( "-"*len(f"feed: {feed_end} / {feed_end} tp: {test_points} / {test_points}") )
            sleep(0.1)
            
            # add spacing to padding for next feed loop
            pad_bytes += spacing // 8
            pads += bytearray( spacing // 8 )
    
    #--------------------------------------------------------------------------
    # Statics / Helper
    #--------------------------------------------------------------------------
    @staticmethod
    def _raster_img_format(data:bytes, byte_width:int, density:High_Density_Flag|int=High_Density_Flag.NONE ) -> bytes:
        """
        generate raster image format to be send to the label printer

        Note: dots are printed from left to right where the least significant bit is printed first
              and the most significant bit is printed last

        Args:
            data (bytes): raster image data as bytes
            width_in_bytes (int): width of raster image in bytes
            density (High_Density_Flag, optional): density modifier. Defaults to 0.

        Returns:
            bytes: resulting byte stream of image with header
        """
        rows, rest = divmod( len(data), byte_width )
        
        assert rest == 0, f"raster image must fill the whole byte_width but has an remainder of {rest}"
        assert 0 < byte_width < 2**16, f"byte_width is {byte_width} but must be between [0, {2**16}]"
        assert 0 < rows < 2**16, f"data contains {rows} many rows but row count must be between [0, {2**16}]"
        
        density = density.value if isinstance( density, High_Density_Flag ) else density
        
        header = (
            ESC_POS_CONSTANT.GS
            + b"v0"
            + bytes((density,))
            + byte_width.to_bytes(2, "little")
            + rows.to_bytes(2, "little")
        )
        
        # Attention:
        # Be aware that the raster image byte format decodes each bit in "big endianness",
        # meaning that bytes are printed from left to right but the bits of each byte are
        # printed from lowest to highest from right to left.
        # meaning that: 0xF2 = 0b11110010 results in -> |X|X|X|X| | |X| |
        # ==> Therefore we need to flip each byte
        reversed_bytes_data = Printer._reverse_bits( data )
        
        return header + reversed_bytes_data
    
    @staticmethod
    def _bits_to_bytes(bits:list[bool], pad_zeros:bool=True) -> bytes:
        """convert a list of bits to their respective bytes"""
        assert pad_zeros or len(bits) % 8 == 0, "bits must be divisible by 8 or pad_zeros must be True"
        
        def __pack_bits(_bits:list[bool]) -> int:
            assert len(_bits) % 8 == 0
            x = 0
            
            for i, b in enumerate(_bits):
                x |= int(b) << i
            
            return x

        if pad_zeros:
            overhang = len(bits) % 8
            if overhang > 0: # zero pad so that the bits are a multiple of 8
                bits = bits + [0,]*( 8 - overhang )
        
        return bytes( [__pack_bits(bits[i:i+8]) for i in range(0, len(bits), 8)] )
    
    @staticmethod
    def _reverse_bits(data:bytes) -> bytes:
        """reverses the bit order of each byte"""
        # for explanation see: https://web.archive.org/web/20150228074432/http://graphics.stanford.edu/~seander/bithacks.html#ReverseByteWith64BitsDiv
        return bytes( [(b * 0x0202020202 & 0x010884422010) % 1023 for b in data] )

