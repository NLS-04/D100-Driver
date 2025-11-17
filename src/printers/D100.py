
from enum import Enum

from device_interface.usb import USB_Printer
from Printer import Printer, Status, Alignment, High_Density_Flag, ESC_POS_CONSTANT


class D100(Printer, USB_Printer):
    class State(Enum):
        NORMAL      = 0
        LID_OPEN    = 1
        NO_PAPER    = 2
        FEED_FAILED = 3
        UNKNOWN     = 4
    
    def __init__(
        self,
        idVendor    : int = 0x08A5,
        idProduct   : int = 0x058A,
        in_ep       : int = 0x82,
        out_ep      : int = 0x02,
        timeout     : int | float = 0,
        usb_args    : dict[str, str | int] = {}
    ):
        USB_Printer.__init__( self, idVendor, idProduct, in_ep, out_ep, timeout, usb_args )
        Printer.__init__(
            self,
            8,      # dpmm
            110,    # mm
            5,      # status bytes
            1,      # dot
            125     # dot
        )
    
    def get_state(self) -> State:
        '''analyzes the status from the printer and matches it with predefined states'''
        # Known Statuses:
        # -------------------------------------------------------------------------------------------------------------------------
        #         status name | printer status    | off-line status   | error status      | paper sensor status | "not documented"
        #               index | 1                 | 2                 | 3                 | 4                   | 5
        # --------------------|-------------------|-------------------|-------------------|---------------------|------------------
        # closed with paper   | 0x12 0b0001_0010  | 0x12 0b0001_0010  | 0x12 0b0001_0010  | 0x16 0b0001_0110    | 0x00 0b0000_0000
        # closed w/o  paper   | 0x1a 0b0001_1010  | 0x32 0b0011_0010  | 0x12 0b0001_0010  | 0x76 0b0111_0110    | 0x02 0b0000_0010
        # closed feed failed  | 0x1a 0b0001_1010  | 0x12 0b0001_0010  | 0x12 0b0001_0010  | 0x16 0b0001_0110    | 0x02 0b0000_0010
        # opened              | 0x1a 0b0001_1010  | 0x36 0b0011_0110  | 0x12 0b0001_0010  | 0x76 0b0111_0110    | 0x02 0b0000_0010
        
        response = self.get_status()
        
        s_normal     : bytes = bytes( [0x12, 0x12, 0x12, 0x16, 0x00] )
        s_lid_open   : bytes = bytes( [0x1a, 0x32, 0x12, 0x76, 0x02] )
        s_no_paper   : bytes = bytes( [0x1a, 0x12, 0x12, 0x16, 0x02] )
        s_feed_failed: bytes = bytes( [0x1a, 0x36, 0x12, 0x76, 0x02] )
        
        if response.status == s_normal     : return D100.State.NORMAL
        if response.status == s_lid_open   : return D100.State.LID_OPEN
        if response.status == s_no_paper   : return D100.State.NO_PAPER
        if response.status == s_feed_failed: return D100.State.FEED_FAILED
        
        # fallback
        return D100.State.UNKNOWN
