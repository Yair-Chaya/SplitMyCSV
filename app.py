import pandas as pd
import os
import zipfile
from flask import Flask, request, send_file, render_template_string, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime, timedelta
import uuid
import threading
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Use absolute paths for the folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'split_sheets')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Cleanup thread function
def cleanup_old_files():
    while True:
        try:
            current_time = datetime.now()
            # Clean up files older than 1 hour
            for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                        if current_time - file_time > timedelta(hours=1):
                            try:
                                os.remove(filepath)
                            except Exception as e:
                                print(f"Error cleaning up file {filepath}: {str(e)}")
        except Exception as e:
            print(f"Error in cleanup thread: {str(e)}")
        time.sleep(300)  # Run cleanup every 5 minutes

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

# Ensure directories exist
def ensure_directories():
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        print(f"Created directories: {UPLOAD_FOLDER} and {OUTPUT_FOLDER}")
    except Exception as e:
        print(f"Error creating directories: {str(e)}")
        raise

# Call this at startup
ensure_directories()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_folder():
    """Get or create a user-specific folder for file operations"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_folder = os.path.join(UPLOAD_FOLDER, session['user_id'])
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def cleanup_files(filepath, output_files, zip_path):
    """Clean up all temporary files after serving"""
    try:
        # Remove the uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Remove all split files
        for file in output_files:
            if os.path.exists(file):
                os.remove(file)
        
        # Remove the zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

def split_file_and_zip(input_file, num_sheets, has_headers, randomize=True, output_zip='split_files.zip'):
    try:
        # Get user-specific folder
        user_folder = get_user_folder()
        
        file_ext = input_file.rsplit('.', 1)[1].lower()
        
        # Create output zip path in the user's folder
        output_zip = os.path.join(user_folder, output_zip)
        
        if file_ext == 'csv':
            # Try to detect the delimiter
            with open(input_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if ';' in first_line:
                    delimiter = ';'
                else:
                    delimiter = ','
            
            # Read CSV with more flexible parsing
            df = pd.read_csv(input_file, 
                           delimiter=delimiter,
                           encoding='utf-8',
                           on_bad_lines='warn',
                           skipinitialspace=True,
                           quoting=1)
            
            # Clean up any extra columns that might have been created
            if len(df.columns) > 0:
                non_null_counts = df.count(axis=1)
                most_common_count = non_null_counts.mode().iloc[0]
                df = df.iloc[:, :most_common_count]
                df.columns = [f'Column_{i+1}' for i in range(len(df.columns))]
        elif file_ext == 'xls':
            df = pd.read_excel(input_file, engine='xlrd')
        else:  # xlsx
            df = pd.read_excel(input_file, engine='openpyxl')
        
        if len(df) == 0:
            raise Exception("The file appears to be empty")
            
        if randomize:
            df = df.sample(frac=1, random_state=42).reset_index(drop=True)
            
        chunk_size = len(df) // num_sheets
        remainder = len(df) % num_sheets
        
        start_idx = 0
        output_files = []
        
        for i in range(num_sheets):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0)
            df_chunk = df.iloc[start_idx:end_idx]
            output_file = os.path.join(user_folder, f'split_part_{i+1}.{file_ext}')
            
            if file_ext == 'csv':
                df_chunk.to_csv(output_file, index=False, header=has_headers, quoting=1)
            else:
                df_chunk.to_excel(output_file, index=False, header=has_headers)
                
            output_files.append(output_file)
            start_idx = end_idx
        
        if os.path.exists(output_zip):
            os.remove(output_zip)
            
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for file in output_files:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
                else:
                    raise Exception(f"Split file not found: {file}")
        
        if not os.path.exists(output_zip):
            raise Exception("Failed to create zip file")
            
        return output_zip, output_files
    except Exception as e:
        raise Exception(f"Error processing file: {str(e)}")

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template_string(error_template, error="No file selected")
        
        file = request.files['file']
        if file.filename == '':
            return render_template_string(error_template, error="No file selected")
        
        if not allowed_file(file.filename):
            return render_template_string(error_template, error="Invalid file type. Allowed types: xlsx, xls, csv")
        
        try:
            num_sheets = int(request.form['num_sheets'])
            if num_sheets < 1:
                raise ValueError("Number of sheets must be positive")
        except ValueError:
            return render_template_string(error_template, error="Invalid number of sheets")
        
        has_headers = 'has_headers' in request.form
        randomize = 'randomize' in request.form
        
        try:
            # Ensure directories exist before saving file
            ensure_directories()
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            if not os.path.exists(filepath):
                raise Exception("Failed to save uploaded file")
            
            zip_path, output_files = split_file_and_zip(filepath, num_sheets, has_headers, randomize)
            if not os.path.exists(zip_path):
                raise Exception("Failed to create zip file")
            
            # Create a response with the zip file
            response = send_file(zip_path, as_attachment=True, download_name='split_files.zip')
            
            # Clean up files after sending
            cleanup_files(filepath, output_files, zip_path)
            
            return response
        except Exception as e:
            # Clean up any files that might have been created
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            if 'output_files' in locals():
                for file in output_files:
                    if os.path.exists(file):
                        os.remove(file)
            if 'zip_path' in locals() and os.path.exists(zip_path):
                os.remove(zip_path)
                
            return render_template_string(error_template, error=str(e))
    
    return render_template_string('''
        <!doctype html>
        <html>
        <head>
            <title>Split My CSV</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Inter', sans-serif;
                }
            </style>
        </head>
        <body class="bg-gray-50 min-h-screen">
            <div class="max-w-2xl mx-auto px-4 py-8">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                    <div class="text-center mb-8">
                        <h1 class="text-3xl font-semibold text-gray-900 mb-2">Split My CSV/Excel</h1>
                        <p class="text-gray-500">Split your files into multiple parts with ease</p>
                    </div>
                    
                    <form method=post enctype=multipart/form-data class="space-y-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">Select File</label>
                            <div id="dropZone" class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-blue-500 transition-colors">
                                <div id="uploadPrompt" class="space-y-1 text-center">
                                    <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                                        <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                                    </svg>
                                    <div class="flex text-sm text-gray-600">
                                        <label class="relative cursor-pointer rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none">
                                            <span>Upload a file</span>
                                            <input type="file" name="file" id="fileInput" class="sr-only" required accept=".csv,.xlsx,.xls">
                                        </label>
                                        <p class="pl-1">or drag and drop</p>
                                    </div>
                                    <p class="text-xs text-gray-500">CSV, XLSX, or XLS up to 10MB</p>
                                </div>
                                <div id="fileInfo" class="hidden space-y-2 text-center">
                                    <svg class="mx-auto h-12 w-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <p id="fileName" class="text-sm font-medium text-gray-900"></p>
                                    <button type="button" id="removeFile" class="text-sm text-red-600 hover:text-red-500">
                                        Remove file
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">Number of Parts</label>
                            <div class="flex items-center space-x-4">
                                <input type="range" name="num_sheets" id="numSheets" min="2" max="25" value="2" required
                                    class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                    oninput="updateSliderValue(this.value)">
                                <span id="sliderValue" class="text-sm font-medium text-gray-700 min-w-[2rem] text-center">2</span>
                            </div>
                            <div id="fileStats" class="mt-2 text-sm text-gray-600 hidden">
                                <p id="totalRows"></p>
                                <p id="rowsPerPart"></p>
                            </div>
                        </div>

                        <div class="space-y-4">
                            <div class="flex items-center">
                                <input type="checkbox" name="has_headers" id="has_headers" checked
                                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                                <label for="has_headers" class="ml-2 block text-sm text-gray-700">
                                    First row contains column names
                                </label>
                            </div>

                            <div class="flex items-center">
                                <input type="checkbox" name="randomize" id="randomize" checked
                                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                                <label for="randomize" class="ml-2 block text-sm text-gray-700">
                                    Randomize rows before splitting
                                </label>
                            </div>
                        </div>

                        <div class="pt-4">
                            <button type="submit"
                                class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
                                Split File
                            </button>
                            <p class="mt-3 text-xs text-gray-500 text-center">
                                This is a free tool. We are not responsible for any mistakes in the output files or duplicates. Please verify your data after splitting.
                            </p>
                        </div>
                    </form>
                </div>
            </div>

            <script>
                // Add drag and drop functionality
                const dropZone = document.getElementById('dropZone');
                const fileInput = document.getElementById('fileInput');
                const uploadPrompt = document.getElementById('uploadPrompt');
                const fileInfo = document.getElementById('fileInfo');
                const fileName = document.getElementById('fileName');
                const removeFile = document.getElementById('removeFile');
                const sliderValue = document.getElementById('sliderValue');
                const totalRows = document.getElementById('totalRows');
                const rowsPerPart = document.getElementById('rowsPerPart');
                const fileStats = document.getElementById('fileStats');

                function updateSliderValue(value) {
                    sliderValue.textContent = value;
                    if (totalRows.textContent) {
                        const total = parseInt(totalRows.textContent.split(': ')[1].replace(/,/g, ''));
                        const parts = parseInt(value);
                        const rowsPerPartValue = Math.ceil(total / parts);
                        rowsPerPart.textContent = `Estimated ${rowsPerPartValue.toLocaleString()} rows per part`;
                    }
                }

                async function getFileInfo(file) {
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                        const response = await fetch('/get_file_info', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            throw new Error('Failed to get file info');
                        }
                        
                        const data = await response.json();
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        
                        totalRows.textContent = `Total rows: ${data.total_rows.toLocaleString()}`;
                        const parts = parseInt(sliderValue.textContent);
                        const rowsPerPartValue = Math.ceil(data.total_rows / parts);
                        rowsPerPart.textContent = `Estimated ${rowsPerPartValue.toLocaleString()} rows per part`;
                        fileStats.classList.remove('hidden');
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Error getting file information: ' + error.message);
                    }
                }

                function updateFileDisplay(file) {
                    if (file) {
                        uploadPrompt.classList.add('hidden');
                        fileInfo.classList.remove('hidden');
                        fileName.textContent = file.name;
                        getFileInfo(file);
                    } else {
                        uploadPrompt.classList.remove('hidden');
                        fileInfo.classList.add('hidden');
                        fileStats.classList.add('hidden');
                        fileName.textContent = '';
                        fileInput.value = '';
                        totalRows.textContent = '';
                        rowsPerPart.textContent = '';
                    }
                }

                // Handle file selection
                fileInput.addEventListener('change', (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        updateFileDisplay(file);
                    }
                });

                // Handle file removal
                removeFile.addEventListener('click', () => {
                    updateFileDisplay(null);
                });

                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                    dropZone.addEventListener(eventName, preventDefaults, false);
                });

                function preventDefaults (e) {
                    e.preventDefault();
                    e.stopPropagation();
                }

                ['dragenter', 'dragover'].forEach(eventName => {
                    dropZone.addEventListener(eventName, highlight, false);
                });

                ['dragleave', 'drop'].forEach(eventName => {
                    dropZone.addEventListener(eventName, unhighlight, false);
                });

                function highlight(e) {
                    dropZone.classList.add('border-blue-500');
                }

                function unhighlight(e) {
                    dropZone.classList.remove('border-blue-500');
                }

                dropZone.addEventListener('drop', handleDrop, false);

                function handleDrop(e) {
                    const dt = e.dataTransfer;
                    const files = dt.files;
                    if (files.length > 0) {
                        fileInput.files = files;
                        updateFileDisplay(files[0]);
                    }
                }
            </script>
        </body>
        </html>
    ''')

    # Update error templates to match the new style
    error_template = '''
        <!doctype html>
        <html>
        <head>
            <title>Error</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Inter', sans-serif;
                }
            </style>
        </head>
        <body class="bg-gray-50 min-h-screen">
            <div class="max-w-2xl mx-auto px-4 py-8">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                    <div class="text-center">
                        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <h1 class="text-xl font-semibold text-gray-900 mb-2">Error</h1>
                        <p class="text-gray-600 mb-6">{{ error }}</p>
                        <a href="/" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
                            Back to Upload
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    '''

@app.route('/get_file_info', methods=['POST'])
def get_file_info():
    if 'file' not in request.files:
        return {'error': 'No file selected'}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400
    
    if not allowed_file(file.filename):
        return {'error': 'Invalid file type'}, 400
    
    try:
        # Get user-specific folder
        user_folder = get_user_folder()
        
        # Save file temporarily with unique name
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(user_folder, unique_filename)
        file.save(filepath)
        
        # Read file based on extension
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if ';' in first_line:
                    delimiter = ';'
                else:
                    delimiter = ','
            
            df = pd.read_csv(filepath, 
                           delimiter=delimiter,
                           encoding='utf-8',
                           on_bad_lines='warn',
                           skipinitialspace=True,
                           quoting=1)
        elif file_ext == 'xls':
            df = pd.read_excel(filepath, engine='xlrd')
        else:  # xlsx
            df = pd.read_excel(filepath, engine='openpyxl')
        
        total_rows = len(df)
        total_columns = len(df.columns)
        
        # Clean up the temporary file
        os.remove(filepath)
        
        return {
            'total_rows': total_rows,
            'total_columns': total_columns,
            'filename': filename
        }
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return {'error': str(e)}, 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
