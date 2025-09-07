#!/usr/bin/env python3
"""
Generate comprehensive favicon and app icon files from SVG logo.
This script creates all necessary icon sizes for web, iOS, Android, and social media.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import io

def svg_to_png(svg_path, output_path, width, height):
    """Convert SVG to PNG with specified dimensions."""
    try:
        # Read SVG and convert to ReportLab drawing
        drawing = svg2rlg(svg_path)
        
        # Scale the drawing to fit the desired dimensions
        drawing.width = width
        drawing.height = height
        drawing.renderScale = 1
        
        # Render to PNG
        renderPM.drawToFile(drawing, output_path, fmt='PNG')
        
        # Open the image to ensure it's the right size and optimize it
        image = Image.open(output_path)
        if image.size != (width, height):
            image = image.resize((width, height), Image.LANCZOS)
            image.save(output_path, 'PNG', optimize=True)
        
        print(f"Created: {output_path} ({width}x{height})")
        return True
    except Exception as e:
        print(f"Error creating {output_path}: {str(e)}")
        return False

def create_social_media_image(logo_path, output_path, width, height, text="GrowComm"):
    """Create social media image with logo and text on black background."""
    try:
        # Create black background
        image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
        
        # Load and resize logo using svglib
        drawing = svg2rlg(logo_path)
        temp_logo_path = output_path.replace('.png', '_temp_logo.png')
        drawing.width = 300
        drawing.height = 300
        renderPM.drawToFile(drawing, temp_logo_path, fmt='PNG')
        logo = Image.open(temp_logo_path).convert('RGBA')
        
        # Clean up temporary file
        if os.path.exists(temp_logo_path):
            os.remove(temp_logo_path)
        
        # Calculate logo position (centered horizontally, upper third vertically)
        logo_x = (width - logo.width) // 2
        logo_y = height // 4 - logo.height // 2
        
        # Paste logo
        image.paste(logo, (logo_x, logo_y), logo)
        
        # Add text below logo
        draw = ImageDraw.Draw(image)
        
        # Try to use a system font, fallback to default
        font_size = min(width, height) // 15
        try:
            # Try common system fonts
            for font_name in ['arial.ttf', 'Arial.ttf', 'helvetica.ttf', 'DejaVuSans.ttf']:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except:
                    continue
            else:
                # Fallback to default font
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Get text dimensions
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position text below logo
        text_x = (width - text_width) // 2
        text_y = logo_y + logo.height + 40
        
        # Draw text in white
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
        
        # Convert to RGB for JPEG or keep RGBA for PNG
        if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
            final_image = Image.new('RGB', image.size, (0, 0, 0))
            final_image.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            final_image.save(output_path, 'JPEG', quality=90, optimize=True)
        else:
            image.save(output_path, 'PNG', optimize=True)
        
        print(f"Created social media image: {output_path} ({width}x{height})")
        return True
    except Exception as e:
        print(f"Error creating social media image {output_path}: {str(e)}")
        return False

def main():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_images_dir = os.path.join(base_dir, 'static', 'images')
    svg_path = os.path.join(static_images_dir, 'growcomm-logo.svg')
    
    # Check if SVG exists
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found at {svg_path}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(static_images_dir, exist_ok=True)
    
    # Define all icon sizes and their filenames
    icon_configs = [
        # Standard favicons
        ('favicon-16x16.png', 16, 16),
        ('favicon-32x32.png', 32, 32),
        
        # Apple touch icons
        ('apple-touch-icon-57x57.png', 57, 57),
        ('apple-touch-icon-60x60.png', 60, 60),
        ('apple-touch-icon-72x72.png', 72, 72),
        ('apple-touch-icon-76x76.png', 76, 76),
        ('apple-touch-icon-96x96.png', 96, 96),
        ('apple-touch-icon-114x114.png', 114, 114),
        ('apple-touch-icon-120x120.png', 120, 120),
        ('apple-touch-icon-144x144.png', 144, 144),
        ('apple-touch-icon-152x152.png', 152, 152),
        ('apple-touch-icon.png', 180, 180),  # Default Apple touch icon
        
        # Android icons
        ('android-icon-192x192.png', 192, 192),
        ('android-icon-512x512.png', 512, 512),
        
        # Microsoft icon
        ('ms-icon-144x144.png', 144, 144),
    ]
    
    success_count = 0
    total_count = len(icon_configs)
    
    # Generate all standard icons
    print("Generating standard icons...")
    for filename, width, height in icon_configs:
        output_path = os.path.join(static_images_dir, filename)
        if svg_to_png(svg_path, output_path, width, height):
            success_count += 1
    
    # Generate social media images
    print("\nGenerating social media images...")
    social_configs = [
        ('og-image.png', 1200, 630),  # Open Graph
        ('twitter-image.png', 1200, 600),  # Twitter Card
    ]
    
    for filename, width, height in social_configs:
        output_path = os.path.join(static_images_dir, filename)
        if create_social_media_image(svg_path, output_path, width, height):
            success_count += 1
            total_count += 1
    
    print(f"\nIcon generation complete!")
    print(f"Successfully created {success_count} out of {total_count} icons")
    
    if success_count < total_count:
        print(f"Failed to create {total_count - success_count} icons")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)