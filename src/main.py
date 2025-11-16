from time import sleep

from printers.D100 import D100
from ImageUtils import Canvas

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
    
    
    
    
    c = Canvas(880)
    c.set_font( "arial.ttf", s:=100 )
    im = c.generate_text( "Bye Bye", 0 )
    c.put_image( im, (0,0) )
    
    for i in range(10):
        c.put_image( c.generate_text( f"Hello This is {i}" ), (s*i, s*i) )
    
    c.show()