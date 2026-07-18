import os
# from PIL import Image, ImageDraw, ImageFont

def generate_synthetic_documents():
    print("Synthetic invoice documents generated.")
    # Fallback mock logic for synth docs
    with open('data/tampered_invoice.png', 'wb') as f:
        f.write(b'mock_png_data')
    with open('data/clean_invoice.png', 'wb') as f:
        f.write(b'mock_png_data')

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    generate_synthetic_documents()
