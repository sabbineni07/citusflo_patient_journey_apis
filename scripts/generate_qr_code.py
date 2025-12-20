#!/usr/bin/env python3
"""
Generate a QR code for CitusFlo app URL
This script creates a QR code that links to https://app.citusflo.com/
"""

import qrcode
from qrcode.image.pil import PilImage
import argparse
import os
from pathlib import Path

def generate_qr_code(url, output_path="qrcode_citusflo.png", size=10, border=4):
    """
    Generate a QR code for the given URL
    
    Args:
        url (str): The URL to encode in the QR code
        output_path (str): Path where the QR code image will be saved
        size (int): Size of each box in the QR code (default: 10)
        border (int): Border size around the QR code (default: 4)
    """
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,  # Controls the size of the QR code
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Error correction level
        box_size=size,
        border=border,
    )
    
    # Add data to QR code
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create image from QR code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image
    img.save(output_path)
    print(f"✅ QR code generated successfully!")
    print(f"   URL: {url}")
    print(f"   Saved to: {os.path.abspath(output_path)}")
    print(f"   Image size: {img.size[0]}x{img.size[1]} pixels")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description="Generate a QR code for CitusFlo app URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_qr_code.py
  python generate_qr_code.py -o citusflo_qr.png
  python generate_qr_code.py --size 15 --border 2
  python generate_qr_code.py --url https://app.citusflo.com/ --output qr.png
        """
    )
    
    parser.add_argument(
        '--url',
        default='https://app.citusflo.com/',
        help='URL to encode in QR code (default: https://app.citusflo.com/)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='qrcode_citusflo.png',
        help='Output file path for the QR code image (default: qrcode_citusflo.png)'
    )
    
    parser.add_argument(
        '--size',
        type=int,
        default=10,
        help='Size of each box in the QR code (default: 10)'
    )
    
    parser.add_argument(
        '--border',
        type=int,
        default=4,
        help='Border size around the QR code (default: 4)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output) if os.path.dirname(args.output) else '.'
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate QR code
    try:
        generate_qr_code(
            url=args.url,
            output_path=args.output,
            size=args.size,
            border=args.border
        )
    except ImportError:
        print("❌ Error: 'qrcode' library not found.")
        print("   Please install it using: pip install qrcode[pil]")
        return 1
    except Exception as e:
        print(f"❌ Error generating QR code: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())


