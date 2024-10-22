import os
import tempfile
import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image
import io
import gradio as gr
import subprocess

# Environment variable name for the API key
API_KEY_ENV_VAR = "GEMINI_API_KEY"

# Initialize Gemini model (will be set up later if API key is available)
model = None

def get_api_key():
    """Get the API key from environment or prompt user if not set."""
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        api_key = input(f"Please enter your Gemini API Key: ").strip()
        if api_key:
            # Set the environment variable for the current session
            os.environ[API_KEY_ENV_VAR] = api_key
            # Attempt to set it permanently
            try:
                shell = os.environ.get('SHELL', '/bin/bash').split('/')[-1]
                config_file = f'.{shell}rc'
                home = os.path.expanduser('~')
                with open(os.path.join(home, config_file), 'a') as f:
                    f.write(f'\nexport {API_KEY_ENV_VAR}="{api_key}"\n')
                print(f"API key has been added to {config_file}. Please restart your terminal or run 'source ~/{config_file}' for it to take effect.")
            except Exception as e:
                print(f"Could not automatically set the environment variable permanently: {e}")
                print(f"Please manually add the following line to your shell configuration file:")
                print(f"export {API_KEY_ENV_VAR}='{api_key}'")
    return api_key

def setup_gemini_model():
    global model
    api_key = get_api_key()
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-002')
        return True
    return False

def process_image(image_path):
    """Process a single image and return the extracted text."""
    with Image.open(image_path) as img:
        # Convert image to RGB if it has an alpha channel
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
            img = bg
        
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

# def process_files(files):
#     """Process uploaded files (images or PDF) and return extracted text."""
#     if model is None:
#         return "Failed to set up the Gemini model. Please check your API key."

#     with tempfile.TemporaryDirectory() as temp_dir:
#         results = []
        
#         for file in files:
#             file_extension = os.path.splitext(file.name)[1].lower()
            
#             if file_extension == '.pdf':
#                 pdf_images = convert_pdf_to_images(file.name, temp_dir)
#                 for img_path in pdf_images:
#                     extracted_text = process_image(img_path)
#                     results.append(f"Page {os.path.basename(img_path)}:\n{extracted_text}\n\n")
#             elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
#                 extracted_text = process_image(file.name)
#                 results.append(f"File {os.path.basename(file.name)}:\n{extracted_text}\n\n")
#                 print(f"File {os.path.basename(file.name)}:\n{extracted_text}\n\n")
#             else:
#                 results.append(f"Unsupported file type: {file.name}\n\n")
        
#     return "".join(results)

def process_files(files):
    """Process uploaded files (images or PDF) and return extracted text."""
    if model is None:
        return "Failed to set up the Gemini model. Please check your API key."

    results_text = []  # Keep all results in a list for writing to file
    with tempfile.TemporaryDirectory() as temp_dir:
        results = []

        for file in files:
            file_extension = os.path.splitext(file.name)[1].lower()

            if file_extension == '.pdf':
                pdf_images = convert_pdf_to_images(file.name, temp_dir)
                for img_path in pdf_images:
                    extracted_text = process_image(img_path)
                    results.append(f"Page {os.path.basename(img_path)}:\n{extracted_text}\n\n")
                    results_text.append(f"Page {os.path.basename(img_path)}:\n{extracted_text}\n\n")
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
                extracted_text = process_image(file.name)
                results.append(f"File {os.path.basename(file.name)}:\n{extracted_text}\n\n")
                results_text.append(f"File {os.path.basename(file.name)}:\n{extracted_text}\n\n")
            else:
                results.append(f"Unsupported file type: {file.name}\n\n")

    # Write all results to a file in the current directory
    with open("extracted_text_results.txt", "w") as f:
        f.write("".join(results_text))

    return "".join(results)

# Set up the model before launching the Gradio interface
setup_gemini_model()

# Define the Gradio interface
with gr.Blocks() as iface:
    gr.Markdown("# Handwriting OCR using Gemini Vision")
    
    with gr.Tab("OCR"):
        file_input = gr.File(file_count="multiple", label="Upload images or PDF")
        ocr_button = gr.Button("Extract Text")
        text_output = gr.Textbox(label="Extracted Text", lines=10)
        ocr_button.click(process_files, inputs=file_input, outputs=text_output)
    
    with gr.Tab("Instructions"):
        gr.Markdown("""
        # Instructions for Using the Handwriting OCR App

        Welcome to the Handwriting OCR application! This tool uses Google's Gemini Vision model to extract text from handwritten documents. Here's how to use it:

        ## First-Time Setup
        1. When you first run the application, you'll be prompted in the terminal to enter your Gemini API key.
        2. The app will attempt to save your API key in your shell configuration file for future use.
        3. If automatic saving fails, you'll see instructions in the terminal on how to manually set the API key.

        ## Using the OCR Feature
        1. Go to the "OCR" tab.
        2. Click on "Upload images or PDF" to select the files you want to process.
        3. You can upload multiple image files (PNG, JPG, JPEG, TIFF, BMP, GIF) or a single PDF file.
        4. Click the "Extract Text" button to start the OCR process.
        5. The extracted text will appear in the text box below.

        ## Warning
        The free tier with Gemini _may_ use any materials you process as part of future training iterations. Also, you are severly rate limited (meaning you can only process so much, so quickly). If you get 'error' in the output box, look at your terminal/console; if you see a '429' error this is because you've exceeded those limitations.

        ## Troubleshooting
        - If you see an error about the Gemini model not being set up, check that your API key is correctly set in your environment.
        - To manually set your API key, add the following line to your shell configuration file (e.g., .bashrc, .zshrc):
          ```
          export GEMINI_API_KEY='your_api_key_here'
          ```
        - After manually setting the API key, restart your terminal or run `source ~/.bashrc`, (or equivalent for your shell, eg for zsh `source ~/.zshrc`).

        ## Tips
        - For best results, ensure your images are clear and well-lit.
        - If processing a PDF, make sure it's not password-protected.

        If you encounter any issues or have questions, please refer to the Gemini API documentation or contact support.
        """)

# Launch the app
iface.launch()