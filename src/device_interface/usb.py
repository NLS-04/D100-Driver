from __future__ import annotations

from typing import Optional

import logging

try:
    import usb.core
    import usb.util
except ImportError:
    raise ImportError( "libusb is not installed" )

from .printer_io import PrinterIO

class USB_Printer(PrinterIO):
    _device: bool | usb.core.Device
    
    def __init__(
        self,
        idVendor    : int,
        idProduct   : int,
        in_ep       : int = 0x82,
        out_ep      : int = 0x02,
        timeout     : int | float = 0,
        usb_args    : dict[str, str | int] = {}
    ):
        """
        Configure the Usb Printer IO parameters

        Args:
            idVendor (int): 16-bit Vendor ID
            idProduct (int): 16-bit Product ID
            in_ep (int, optional): in endpoint. Defaults to 0x82.
            out_ep (int, optional): out endpoint. Defaults to 0x02.
            timeout (int | float, optional): timeout of usb connection in ms. Defaults to 0.
            usb_args (dict[str, str  |  int], optional): additional usb arguments. Defaults to {}.
        """
        self.timeout = timeout
        self.in_ep = in_ep
        self.out_ep = out_ep

        self.usb_args = usb_args or {}
        
        self.usb_args["idVendor"] = idVendor
        self.usb_args["idProduct"] = idProduct

        self._device = False
        self.open()
    
    def open(self):
        '''open the printer device connection'''
        if self._device:
            self.close()

        # Open device
        try:
            self._device = usb.core.find( **self.usb_args )
            assert self._device, IOError(
                f"Device {tuple(self.usb_args.values())} not found or not plugged in."
            )
            self._check_driver()
            self._configure_usb()
        except (AssertionError, usb.core.USBError) as e:
            # Raise exception or log error and cancel
            logging.error("USB device %s not found", tuple(self.usb_args.values()))
            self.device = None
            raise IOError(
                f"Unable to open USB printer on {tuple(self.usb_args.values())}:\n{e}"
            )
            
        logging.info("USB printer enabled")
    
    def _check_driver(self) -> None:
        """Check the driver.

        pyusb has three backends: libusb0, libusb1 and openusb but
        only libusb1 backend implements the methods is_kernel_driver_active()
        and detach_kernel_driver().
        This helps enable this library to work on Windows.
        """
        if not self._device:
            return
        
        if not self._device.backend.__module__.endswith("libusb1"):
            return
        
        check_driver: Optional[bool] = None

        try:
            check_driver = self._device.is_kernel_driver_active(0)
        except NotImplementedError:
            pass

        if check_driver is None or check_driver:
            try:
                self._device.detach_kernel_driver(0)
            except NotImplementedError:
                pass
            except usb.core.USBError as e:
                if check_driver is not None:
                    logging.error("Could not detach kernel driver: %s", str(e))

    def _configure_usb(self) -> None:
        """Configure USB."""
        if not self._device:
            return

        try:
            self._device.set_configuration()
            self._device.reset()
        except usb.core.USBError as e:
            logging.error("Could not set configuration: %s", str(e))

    def close(self):
        '''close the printer device connection'''
        if not self._device:
            return
        
        logging.info(
            "Closing Usb connection to printer %s", tuple(self.usb_args.values())
        )
        
        usb.util.dispose_resources(self._device)
        self._device = False
    
    def _raw(self, msg: bytes) -> None:
        '''send raw bytes to printer device'''
        assert self._device
        logging.debug(f"raw-print: {msg}")
        self._device.write(self.out_ep, msg, self.timeout)
    
    def _read(self) -> bytes:
        '''read raw bytes from printer device'''
        assert self._device
        return self._device.read(self.in_ep, 16)