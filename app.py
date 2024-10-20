import os
import tempfile
import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image
import io
import gradio as gr
import json

# Function to load API key from local storage
def load_api_key():
    try:
        with open('api_key.json', 'r') as f:
            data = json.load(f)
            return data.get('api_key')
    except FileNotFoundError:
        return None

# Function to save API key to local storage
def save_api_key(api_key):
    with open('api_key.json', 'w') as f:
        json.dump({'api_key': api_key}, f)

# Load API key from local storage
api_key = load_api_key()

# Initialize Gemini model (will be set up later if API key is available)
model = None

def setup_gemini_model(api_key):
    global model
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-002')

def process_image(image_path):
    """Process a single image and return the extracted text."""
    with Image.open(image_path) as img:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

    response = model.generate_content([
        "Extract HIGH QUALITY text from the handwriting in the image",
        {"mime_type": "image/jpeg", "data": img_byte_arr}
    ])
    
    return response.text

def convert_pdf_to_images(pdf_path, output_folder):
    """Convert a PDF file to images."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pages = convert_from_path(pdf_path, 300)
    image_paths = []

    for i, page in enumerate(pages):
        image_path = os.path.join(output_folder, f'page_{i+1}.jpg')
        page.save(image_path, 'JPEG')
        image_paths.append(image_path)

    return image_paths

def process_files(files):
    """Process uploaded files (images or PDF) and return extracted text."""
    if model is None:
        return "Please set up your API key first."

    with tempfile.TemporaryDirectory() as temp_dir:
        results = []
        
        for file in files:
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension == '.pdf':
                pdf_images = convert_pdf_to_images(file.name, temp_dir)
                for img_path in pdf_images:
                    extracted_text = process_image(img_path)
                    results.append(f"Page {os.path.basename(img_path)}:\n{extracted_text}\n\n")
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
                extracted_text = process_image(file.name)
                results.append(f"File {os.path.basename(file.name)}:\n{extracted_text}\n\n")
            else:
                results.append(f"Unsupported file type: {file.name}\n\n")
        
    return "".join(results)

def set_api_key(new_api_key):
    global api_key
    api_key = new_api_key
    save_api_key(api_key)
    setup_gemini_model(api_key)
    return "API key set successfully. You can now use the OCR functionality."

# Define the Gradio interface
with gr.Blocks() as iface:
    gr.Markdown("# Handwriting OCR using Gemini Vision")
    gr.Markdown("Set your API first")
    gr.Markdown("Then upload your files/pdf. PNGs need to not have an alpha channel.")
    
    with gr.Tab("Set API Key"):
        api_key_input = gr.Textbox(label="Enter your Gemini API Key", type="password")
        set_key_button = gr.Button("Set API Key")
        api_key_message = gr.Textbox(label="Status")
        set_key_button.click(set_api_key, inputs=api_key_input, outputs=api_key_message)

    with gr.Tab("OCR"):
        file_input = gr.File(file_count="multiple", label="Upload images or PDF")
        ocr_button = gr.Button("Extract Text")
        text_output = gr.Textbox(label="Extracted Text", lines=10)
        ocr_button.click(process_files, inputs=file_input, outputs=text_output)

# Set up the model if API key is available
if api_key:
    setup_gemini_model(api_key)

# Launch the app
iface.launch()