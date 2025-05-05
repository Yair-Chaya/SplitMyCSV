// File splitting and processing functions
import { normalizeName } from './nameNormalizer.js';

export async function splitAndDownload(data, options) {
    const {
        numParts,
        keepHeaders,
        shouldRandomize,
        fileExt,
        nameColumns,
        originalData
    } = options;

    // Prepare data
    let processedData = [...data];
    
    // Normalize names in selected columns
    if (nameColumns.length > 0) {
        for (let row = 1; row < processedData.length; row++) {
            for (const colIndex of nameColumns) {
                if (processedData[row][colIndex]) {
                    processedData[row][colIndex] = normalizeName(processedData[row][colIndex]);
                }
            }
        }
    }

    if (shouldRandomize) {
        // Fisher-Yates shuffle
        for (let i = processedData.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [processedData[i], processedData[j]] = [processedData[j], processedData[i]];
        }
    }

    // Calculate chunk sizes
    const chunkSize = Math.floor(processedData.length / numParts);
    const remainder = processedData.length % numParts;

    // Create zip file
    const zip = new JSZip();

    // Split data and create files
    let startIdx = 0;
    for (let i = 0; i < numParts; i++) {
        const endIdx = startIdx + chunkSize + (i < remainder ? 1 : 0);
        const chunk = processedData.slice(startIdx, endIdx);
        
        // Convert to appropriate format
        let content;
        if (fileExt === 'csv') {
            // For CSV files
            if (keepHeaders) {
                // Add header row to each file
                content = originalData[0].join(',') + '\n' + chunk.map(row => row.join(',')).join('\n');
            } else {
                content = chunk.map(row => row.join(',')).join('\n');
            }
        } else {
            // For Excel files
            const ws = XLSX.utils.aoa_to_sheet(chunk);
            if (keepHeaders) {
                // Add header row to each file
                XLSX.utils.sheet_add_aoa(ws, [originalData[0]], { origin: 'A1' });
                // Shift the data down by one row
                const range = XLSX.utils.decode_range(ws['!ref']);
                const data = [];
                for (let R = range.s.r; R <= range.e.r; R++) {
                    const row = [];
                    for (let C = range.s.c; C <= range.e.c; C++) {
                        const cell = ws[XLSX.utils.encode_cell({r: R, c: C})];
                        row.push(cell ? cell.v : '');
                    }
                    data.push(row);
                }
                ws['!ref'] = XLSX.utils.encode_range({
                    s: {r: 0, c: 0},
                    e: {r: data.length, c: data[0].length - 1}
                });
                data.forEach((row, R) => {
                    row.forEach((val, C) => {
                        ws[XLSX.utils.encode_cell({r: R + 1, c: C})] = {v: val};
                    });
                });
            }
            content = XLSX.utils.sheet_to_csv(ws);
        }

        // Add to zip
        zip.file(`split_part_${i + 1}.${fileExt}`, content);
        startIdx = endIdx;
    }

    // Generate and download zip
    const zipContent = await zip.generateAsync({ type: 'blob' });
    saveAs(zipContent, 'split_files.zip');
} 