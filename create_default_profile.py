#!/usr/bin/env python3
"""
Create a default profile image for users
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_default_profile_image():
    """Create a simple default profile image"""
    # Create a 200x200 image with a nice background color
    img = Image.new('RGB', (200, 200), color='#4F46E5')  # Indigo background

    # Get a default font (or use basic if not available)
    try:
        # Try to use a system font
        font = ImageFont.load_default()
    except:
        font = None

    # Draw a simple user icon (circle with person silhouette)
    draw = ImageDraw.Draw(img)

    # Draw a circle for the head
    circle_center = (100, 80)
    circle_radius = 40
    draw.ellipse(
        [(circle_center[0] - circle_radius, circle_center[1] - circle_radius),
         (circle_center[0] + circle_radius, circle_center[1] + circle_radius)],
        fill='white'
    )

    # Draw a simple body (rectangle)
    body_rect = [70, 120, 130, 180]
    draw.rectangle(body_rect, fill='white')

    # Add "User" text at the bottom
    if font:
        try:
            text = "User"
            # Get text size for centering
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = (200 - text_width) // 2
            text_y = 185

            draw.text((text_x, text_y), text, fill='white', font=font)
        except:
            pass  # Skip text if font rendering fails

    # Ensure profiles directory exists
    os.makedirs('uploads/profiles', exist_ok=True)

    # Save the image
    output_path = 'uploads/profiles/default_avatar.png'
    img.save(output_path, 'PNG')

    print(f"✅ Created default profile image: {output_path}")
    return output_path

if __name__ == "__main__":
    create_default_profile_image()
