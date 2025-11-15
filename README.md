# Rasterized ESC/POS Printer API
### ESC/POS Printer Emulator with Raster Output Pipeline

A raster-based ESC/POS printer interface that emulates the behavior of standard ESC/POS printers by prerendering **text, images, barcodes, and QR codes** into a bitmap buffer before sending them to devices that only support limited ESC/POS command sets.

This approach is especially useful for printers that implement only a limited subset of the ESC/POS specification, lack advanced text or barcode support, or require fully rasterized data for correct output.

---

## Features

- Provides interface for connecting to ESC/POS speaking printers
- Sends and receives basic control commands like:
    - feeding and reverse feeding
    - cutting
    - status inquiry
- Sends bitmaps/raster images for printing
- Emulates the general behavior and features of regular ESC/POS printers
- Renders basic ESC/POS elements like **text, images, barcodes, and QR codes** onto the internal image buffer
- Rasterizes and sends internal buffer image for printing
- Supports custom font rendering and layout logic
- Allows printers with limited or incomplete ESC/POS support to behave predictably
- Extensible architecture for adding additional ESC/POS commands or printer drivers
- No dependencies on printer firmware capabilities beyond raw image printing

---

## How It Works

- **ESC/POS Control commands**  
    Basic control and real time commands are sent and received directly by the printer.

1. **Rendering Pipeline**  
    All print commands/elements, which includes **text, barcode, QR code, images**, are dynamically aggregated and drawn onto an internal image buffer. Allowing for full flexibility in the layout process.

2. **Rasterization**  
    The final composed image is rasterized into a bitmap matching the target printer's configuration.

3. **Printer Output**  
    The resulting raster image is sent to the printer through a wired IO interface (USB, Serial, Network, or mock print driver).

This system ensures consistent and flexible results across a wide variety of printers, regardless of their level of ESC/POS command support.

---

## Use Cases

- Printers that support only the `GS v 0` (raster image print) command
- Embedded printers with incomplete ESC/POS implementations
- Environments where reliable, identical output across different printer models is required
- Virtual Prototyping: Debugging, simulation, and testing of ESC/POS output without the HIL (Hardware In the Loop)

---

## Explicitly Implemented Printers

- Marklife D100

---

## Installation
### Requirements

_TODO_

---

## Example

TODO