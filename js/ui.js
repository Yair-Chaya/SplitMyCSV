// UI handling functions
import { detectNameColumns } from './nameNormalizer.js';
import { readFile } from './fileHandler.js';
import { splitAndDownload } from './fileSplitter.js';

export function updateFileInfo(file, data) {
    const fileInfo = document.getElementById('fileInfo');
    const fileStats = document.getElementById('fileStats');
    const nameColumnsSection = document.getElementById('nameColumnsSection');
    
    if (file && data) {
        fileInfo.innerHTML = `
            <p>File: ${file.name}</p>
            <p>Size: ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
            <p>Type: ${file.type || 'Unknown'}</p>
        `;
        
        fileStats.innerHTML = `
            <p>Total Rows: ${data.length.toLocaleString()}</p>
            <p>Total Columns: ${data[0].length}</p>
        `;
        
        // Show name columns section
        nameColumnsSection.style.display = 'block';
        
        // Detect name columns
        const nameColumns = detectNameColumns(data);
        if (nameColumns.length > 0) {
            const nameColumnsList = document.getElementById('nameColumnsList');
            nameColumnsList.innerHTML = nameColumns.map(col => `
                <div class="name-column">
                    <input type="checkbox" id="nameCol_${col.index}" value="${col.index}">
                    <label for="nameCol_${col.index}">
                        ${col.name} (${col.confidence}% confidence)
                    </label>
                </div>
            `).join('');
        } else {
            document.getElementById('nameColumnsList').innerHTML = '<p>No name columns detected</p>';
        }
    } else {
        fileInfo.innerHTML = '';
        fileStats.innerHTML = '';
        nameColumnsSection.style.display = 'none';
    }
}

export function updateSplitEstimate(data, numParts) {
    const splitEstimate = document.getElementById('splitEstimate');
    if (data && numParts) {
        const rowsPerPart = Math.ceil(data.length / numParts);
        splitEstimate.textContent = `Estimated rows per part: ${rowsPerPart.toLocaleString()}`;
    } else {
        splitEstimate.textContent = '';
    }
}

export function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

export function showLoading(show) {
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = show ? 'block' : 'none';
}

// Initialize UI elements
export function initializeUI() {
    // Initialize slider
    const slider = document.getElementById('numParts');
    const numPartsDisplay = document.getElementById('numPartsDisplay');
    
    slider.addEventListener('input', function() {
        numPartsDisplay.textContent = this.value;
        const value = (this.value - this.min) / (this.max - this.min) * 100;
        this.style.background = `linear-gradient(to right, #4CAF50 0%, #4CAF50 ${value}%, #ddd ${value}%, #ddd 100%)`;
    });

    // Initialize file input
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        try {
            const data = await readFile(file);
            updateFileInfo(file, data);
            updateSplitEstimate(data, parseInt(slider.value));
        } catch (error) {
            showError(error.message);
        }
    });

    // Initialize split button
    const splitButton = document.getElementById('splitButton');
    splitButton.addEventListener('click', async function() {
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file first');
            return;
        }

        try {
            showLoading(true);
            const data = await readFile(file);
            const numParts = parseInt(slider.value);
            const keepHeaders = document.getElementById('keepHeaders').checked;
            const shouldRandomize = document.getElementById('randomize').checked;
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            // Get selected name columns
            const nameColumns = Array.from(document.querySelectorAll('#nameColumnsList input:checked'))
                .map(input => parseInt(input.value));

            await splitAndDownload(data, {
                numParts,
                keepHeaders,
                shouldRandomize,
                fileExt,
                nameColumns,
                originalData: data
            });
        } catch (error) {
            showError(error.message);
        } finally {
            showLoading(false);
        }
    });
} 