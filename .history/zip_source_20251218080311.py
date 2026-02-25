import zipfile
import os
import re
from pathlib import Path

def get_version():
    """Extract version from gui_modern.py"""
    try:
        with open('gui_modern.py', 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error getting version: {e}")
    return '0.0.0'

def zip_source():
    files_to_zip = [
        'gui_modern.py',
        'theme_manager.py',
        'requirements.txt',
        'categories.json',
        'README.MD',
        'LICENSE',
        'CHANGELOG.md',
        'version_info.txt',
        'TSM Scraper.spec'
    ]
    folders_to_zip = [
        'tsm_scraper',
        'config'
    ]
    
    version = get_version()
    output_zip = f'src{version}.zip'
    
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
