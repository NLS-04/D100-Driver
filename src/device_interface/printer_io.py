

#--------------------------------------------------------------------------
# I/O - Interface
#--------------------------------------------------------------------------
class PrinterIO():
    """generic io interface for thermal pinter"""
    
    def open(self):
        '''open the printer device connection'''
        raise NotImplementedError()
    
    def close(self):
        '''close the printer device connection'''
        raise NotImplementedError()
    
    def _raw(self, msg: bytes) -> None:
        '''send raw bytes to printer device'''
        raise NotImplementedError()
    
    def _read(self) -> bytes:
        '''read raw bytes from printer device'''
        raise NotImplementedError()