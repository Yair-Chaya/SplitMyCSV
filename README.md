# Split My CSV/Excel

A client-side web application that allows users to split large CSV and Excel files into multiple smaller parts. Built with vanilla JavaScript and designed to be hosted on Cloudflare Pages.

## Features

- **File Support**: 
  - CSV files (with automatic comma/semicolon delimiter detection)
  - XLSX files (Excel 2007+)
  - XLS files (Excel 97-2003)
- **Client-Side Processing**: 
  - All processing happens in the browser - no server required
  - Files never leave your device
  - No data is stored or transmitted
- **Smart Splitting**: 
  - Automatic delimiter detection for CSV files
  - Option to preserve headers in all split files
  - Option to randomize rows before splitting (Fisher-Yates shuffle)
  - Even distribution of rows across parts
- **User-Friendly Interface**:
  - Drag and drop file upload
  - Real-time file information display (total rows, estimated rows per part)
  - Interactive slider for selecting number of parts
  - Visual feedback for file upload status
  - Progress indication during processing
- **Output**:
  - All split files packaged in a single ZIP download
  - Original file format preserved
  - Consistent naming convention (split_part_1, split_part_2, etc.)

## Usage

1. **Upload a File**:
   - Drag and drop your file or click to select
   - Supported formats: CSV, XLSX, XLS
   - Maximum file size: 50MB
   - File must contain at least 2 rows of data

2. **Configure Split Options**:
   - Use the slider to select number of parts (2-25)
   - Toggle "First row contains column names" if your file has headers
   - Toggle "Randomize rows before splitting" if you want to shuffle the data
   - View estimated rows per part in real-time

3. **Split and Download**:
   - Click "Split File" to process
   - A zip file containing all split parts will be downloaded automatically
   - Each part will maintain the original file format
   - Headers (if enabled) will be included in all parts

## Technical Details

### Libraries Used
- [SheetJS](https://github.com/SheetJS/sheetjs) - For Excel/CSV parsing
- [FileSaver.js](https://github.com/eligrey/FileSaver.js) - For file downloads
- [JSZip](https://github.com/Stuk/jszip) - For creating zip files
- [TailwindCSS](https://tailwindcss.com) - For styling

### Browser Support
- Chrome (recommended)
- Firefox
- Safari
- Edge

### Performance Considerations
- Files are processed in memory
- Large files may cause temporary browser slowdown
- Progress is shown during processing
- Memory usage scales with file size
- Recommended to have at least 4GB of RAM for processing large files

## Deployment

### Deploy to Cloudflare Pages

1. Fork or clone this repository
2. Connect your repository to Cloudflare Pages
3. Deploy with these settings:
   - Build command: (leave empty)
   - Build output directory: (leave empty)
   - Root directory: (leave empty)

### Local Development

1. Clone the repository
2. Open `index.html` in your browser
3. No build process required - it's pure HTML/JS

## Limitations

- Maximum file size: 50MB (browser memory limitations)
- Maximum number of parts: 25
- Minimum number of parts: 2
- Processing large files may cause browser slowdown
- Browser must have sufficient memory for file processing
- No support for password-protected Excel files
- Row limits (approximate, depends on your system):
  - CSV files: Up to 5 million rows (with 10 columns)
  - Excel files: Up to 1 million rows (with 10 columns)
  - Actual limits depend on:
    - Number of columns
    - Data types in cells
    - Available system memory
    - Browser memory limits

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This is a free tool. We are not responsible for any mistakes in the output files or duplicates. Please verify your data after splitting.