from PIL import Image, ImageDraw, ImageFont
import os

def create_frame():
    width, height = 1080, 1920
    # Create a transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a thin white border
    border_thickness = 10
    draw.rectangle([border_thickness, border_thickness, width - border_thickness, height - border_thickness], outline="white", width=border_thickness)
    
    # Add some text placeholders (using default font if custom not available)
    try:
        # Try to use a common system font, or fallback
        font_header = ImageFont.load_default()
        font_footer = ImageFont.load_default()
    except:
        font_header = None
        font_footer = None
        
    draw.text((width // 2, 100), "EchoFrame Bot", fill="white", anchor="mt")
    draw.text((width // 2, height - 100), "repurposed by EchoFrame", fill="white", anchor="mb")
    
    os.makedirs("assets/frames", exist_ok=True)
    image.save("assets/frames/frame.png")
    print("Created assets/frames/frame.png")

if __name__ == "__main__":
    create_frame()
