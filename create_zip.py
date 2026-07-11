import os
import zipfile

def create_project_zip(output_filename="IPO_Copilot_AI_Project.zip"):
    # Directories and files to exclude to keep the zip file size reasonable
    exclude_dirs = {
        'node_modules', 
        'venv', 
        '.venv', 
        'env', 
        '.git', 
        '__pycache__', 
        'chroma_db', 
        '.pytest_cache',
        'dist',
        'build'
    }
    exclude_extensions = {'.pyc', '.pyo', '.pyd'}

    print(f"Creating {output_filename}...")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Skip excluded extensions or the zip file itself and the script
                if any(file.endswith(ext) for ext in exclude_extensions) or \
                   file == output_filename or file == "create_zip.py":
                    continue
                
                file_path = os.path.join(root, file)
                # Ensure we don't zip up huge sqlite journals if any
                if file.endswith('.db-wal') or file.endswith('.db-shm'):
                    continue
                    
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)
                
    print("Zip file created successfully!")

if __name__ == "__main__":
    create_project_zip()
