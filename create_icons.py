from PIL import Image
import os

os.makedirs('static/images', exist_ok=True)
os.makedirs('staticfiles/images', exist_ok=True)

# Load the original logo
logo_path = 'static/images/brainet-logo.png'
logo = Image.open(logo_path).convert('RGBA')

# Create icon images
sizes = [(192, 192), (512, 512)]

for size in sizes:
    # Resize logo to fit icon size
    resized = logo.resize(size, Image.Resampling.LANCZOS)
    
    # Regular icon (white background)
    bg = Image.new('RGB', size, color='white')
    bg.paste(resized, (0, 0), resized)
    bg.save(f'static/images/brainet-icon-{size[0]}.png')
    bg.save(f'staticfiles/images/brainet-icon-{size[0]}.png')
    
    # Maskable icon (transparent background)
    resized.save(f'static/images/brainet-maskable-{size[0]}.png')
    resized.save(f'staticfiles/images/brainet-maskable-{size[0]}.png')

print("Icons created successfully from brainet-logo.png!")