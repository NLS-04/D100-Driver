import logging
import os
from time import sleep

from printers.D100 import D100
from ImageUtils import Canvas, Alignment, Modifier, FontManager

os.environ["PYUSB_DEBUG"] = 'info'
logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':
    # p = D100()
    # p.set_paper_width( 110 )
    
    # p.feed_reverse_dots(30)
    # sleep(1)
    # p.feed_dots(30)
    # p.feed_lines(5)
    
    # p.test_revers_feed( 2, 4, 8, 4*8, 16*8 )
    
    # p.feed_reverse(10)
    # p.feed_lines(1)
    
    # n = 200
    # l = 10
    # b = 8
    # p.feed_reverse_dots(n + ((l*b+1)*1) // 2)
    # sleep(1)
    
    # p.test_checkerboard( b, l, 1, alignment=Alignment.LEFT )
    # # p.test_checkerboard( b, l, 1, alignment=Alignment.CENTER )
    # # p.test_checkerboard( b, l, 1, alignment=Alignment.RIGHT )
    
    # sleep(1)
    # p.feed_dots(n)
    
    # p.test_checkerboard( 2, 10, 10 )
    
    # p.feed_dots( -150 )
    # p.feed_dots( 0 )
    
    # for i in range(5):
    #     p.test_checkerboard( 8, 4, 10, alignment=Alignment.LEFT )
    #     sleep(0.01)
    #     p.feed_dots( -( 8*4 + 1 ) )
    
    # p.feed_reverse_dots( 200 )
    # sleep(1)
    # p.feed_dots( 200 )
    # p.feed_dots( 50 )
    
    
    # p.test_line(500)
    # sleep(1)
    # p.test_line(2)
    # sleep(2)
    # p.feed_lines(2)
    # sleep(2)
    # p.test_line(2)
    
    # p._raw( ESC_POS_CONSTANT.GS + b"$\x05\x80" )
    # p._raw( ESC_POS_CONSTANT.GS + b"H\x01" )
    # p._raw( ESC_POS_CONSTANT.GS + b"f\x00" )
    # p._raw( ESC_POS_CONSTANT.GS + b"h\x40" )
    # p._raw( ESC_POS_CONSTANT.GS + b"k\x0012345678901\x00" )
    
    # p._raw( ESC_POS_CONSTANT.ESC + b"v" )
    # print( p._read() )
    
    # print( s := p.get_status() )
    # print( s.info() )
    
    # p._raw( ESC_POS_CONSTANT.ESC + b"M\x01" )
    # p._raw( ESC_POS_CONSTANT.ESC + b"R\x00" )
    # p._raw( ESC_POS_CONSTANT.ESC + b"r\x00" )
    # p._raw( ESC_POS_CONSTANT.ESC + b"t\x00" )
    # p._raw( ESC_POS_CONSTANT.ESC + b"S" )
    # p._raw( "Hello World\r\n" )
    
    # p._raw( ESC_POS_CONSTANT.FS + b"(L\x02\x00\x43\x32" )
    
    # p.test_line( 1 )
    
    # p.feed_dots(100)
    
    from pprint import pprint
    
    c = Canvas(880)
    c.font.load( "Consolas", s:=100 )
    # c.font.debug_font()
    # pprint( FontManager.fonts )
    
    # print( c.font.get_line_bbox( "A" ) )
    # print( c.font.get_line_bbox( "B" ) )
    # print( c.font.get_line_size( "abcdefghijklmnopqrstuvwxyz0123456789" ) )
    # print( c.font._raw_bbox( "abcdefghijklmnopqrstuvwxyz0123456789", "lt" ) )
    
    c.font.right_space = 0
    c.font.line_space = 0
    
    s = "\n".join( [ " "*i + str(1234) for i in range(10) ] )
    c.font.render( s ).save("test.png")
    c.font.render( "abcdefghijklmnopqrstuvwxyzäöü0123456789\nABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ0123456789" ).save("test.png")
    # c.font.render( "Ag\nÄÄ" ).save("test.png")
    # c.font._render_line_old( "My Hello World\n  Joe ÄÖÜ" ).save("test.png")
    
    # im = c.generate_text( "A", 0, None, Alignment.LEFT )
    # im = c.generate_text( "B", 0, None, Alignment.LEFT )
    # # im = c.generate_text( "AB", 0, None, Alignment.LEFT )
    # im.save("A.png")
    # c.put_image( im, (0,0) )
    
    # for i in range(10):
    #     c.put_image( c.generate_text( f"Hello This is {i}" ), (s*i, s*i) )
    
    # c.show()