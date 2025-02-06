import pandas as pd
import os
import zipfile
from flask import Flask, request, send_file, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'split_sheets'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def split_excel_and_zip(input_file, num_sheets, has_headers, output_zip='split_files.zip'):
    if input_file.endswith('.xls'):
        df = pd.read_excel(input_file, engine='xlrd')
    else:
        df = pd.read_excel(input_file, engine='openpyxl')
    
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    chunk_size = len(df) // num_sheets
    remainder = len(df) % num_sheets
    
    start_idx = 0
    output_files = []
    
    for i in range(num_sheets):
        end_idx = start_idx + chunk_size + (1 if i < remainder else 0)
        df_chunk = df.iloc[start_idx:end_idx]
        output_file = os.path.join(OUTPUT_FOLDER, f'split_part_{i+1}.xlsx')
        df_chunk.to_excel(output_file, index=False, header=has_headers)
        output_files.append(output_file)
        start_idx = end_idx
    
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for file in output_files:
            zipf.write(file, os.path.basename(file))
    
    return output_zip

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        num_sheets = int(request.form['num_sheets'])
        has_headers = 'has_headers' in request.form
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            zip_path = split_excel_and_zip(filepath, num_sheets, has_headers)
            return send_file(zip_path, as_attachment=True)
    
    return render_template_string('''
        <!doctype html>
        <title>Upload Excel File</title>
        <h1>Upload Excel file to split</h1>
        <form method=post enctype=multipart/form-data>
            <input type=file name=file required>
            <input type=number name=num_sheets min=1 required>
            <label><input type=checkbox name=has_headers> First row contains column names</label>
            <input type=submit value=Upload>
        </form>
    ''')

if __name__ == '__main__':
    app.run(debug=True)
