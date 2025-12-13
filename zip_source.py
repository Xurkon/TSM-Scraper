import zipfile
import os
from pathlib import Path

def zip_source():
    files_to_zip = [
        'gui_modern.py',
        'theme_manager.py',
        'requirements.txt',
        'categories.json',
        'README.MD',
        'LICENSE',
        'CHANGELOG.md'
    ]
    folders_to_zip = [
        'tsm_scraper',
        'config'
    ]
    
    output_zip = 'src2.1.2.zip'
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add files
        for f in files_to_zip:
            if os.path.exists(f):
                zf.write(f)
                print(f"Added {f}")
        
        # Add folders
        for folder in folders_to_zip:
            folder_path = Path(folder)
            if folder_path.exists():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file() and '__pycache__' not in str(file_path):
                        zf.write(file_path)
                        print(f"Added {file_path}")
                        
    print(f"Created {output_zip}")

if __name__ == '__main__':
    zip_source()
