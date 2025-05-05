// Name detection and normalization functions
export function detectNameColumns(data) {
    if (!data || data.length < 2) return [];
    
    const namePatterns = [
        /^[A-Z][a-z]+$/,  // Single word starting with capital
        /^[A-Z][a-z]+\s+[A-Z][a-z]+$/,  // Two words, both capitalized
        /^[A-Z][a-z]+-[A-Z][a-z]+$/,  // Hyphenated names
        /^[A-Z][a-z]+'[A-Z][a-z]+$/,  // Names with apostrophes
    ];

    const nameColumns = [];
    const sampleSize = Math.min(100, data.length - 1); // Check first 100 rows
    
    // Check each column
    for (let col = 0; col < data[0].length; col++) {
        let nameScore = 0;
        let totalChecked = 0;
        
        // Check sample rows
        for (let row = 1; row <= sampleSize; row++) {
            const value = String(data[row][col] || '').trim();
            if (value) {
                totalChecked++;
                // Check if value matches any name pattern
                if (namePatterns.some(pattern => pattern.test(value))) {
                    nameScore++;
                }
            }
        }
        
        // If more than 70% of non-empty values look like names, consider it a name column
        if (totalChecked > 0 && (nameScore / totalChecked) > 0.7) {
            nameColumns.push({
                index: col,
                name: data[0][col] || `Column ${col + 1}`,
                confidence: (nameScore / totalChecked) * 100
            });
        }
    }
    
    return nameColumns;
}

export function normalizeName(name) {
    if (!name) return '';
    
    // Convert to string and trim
    name = String(name).trim();
    
    // Split into words
    const words = name.split(/[\s-']+/);
    
    // Capitalize each word
    return words.map(word => {
        if (!word) return '';
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    }).join(' ');
} 