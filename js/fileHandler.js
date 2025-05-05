// File handling and processing functions
export async function readFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const data = e.target.result;
                const fileExt = file.name.split('.').pop().toLowerCase();
                let result;

                if (fileExt === 'csv') {
                    // Try to detect delimiter
                    const firstLine = data.split('\n')[0];
                    const delimiter = firstLine.includes(';') ? ';' : ',';
                    
                    // Parse CSV
                    const workbook = XLSX.read(data, { type: 'string', raw: true });
                    result = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { header: 1 });
                } else {
                    // Parse Excel
                    const workbook = XLSX.read(data, { type: 'array' });
                    result = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { header: 1 });
                }

                resolve(result);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = reject;

        if (file.name.endsWith('.csv')) {
            reader.readAsText(file);
        } else {
            reader.readAsArrayBuffer(file);
        }
    });
}

export function validateFileSize(file) {
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        throw new Error('File size exceeds 50MB limit');
    }
    return true;
} 