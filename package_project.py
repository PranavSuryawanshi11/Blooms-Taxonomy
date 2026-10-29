"""
BloomCraft AI - Project Packaging Script
Packages the repository into a clean, standalone ZIP file.
Excludes venv, __pycache__, .git, and temporary files.
"""

import os
import zipfile

def create_project_zip():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(base_dir, "bloomcraft_ai_project.zip")

    exclude_dirs = {"venv", ".venv", "__pycache__", ".git", ".idea", ".vscode", "node_modules"}
    exclude_exts = {".pyc", ".pyo", ".pyd"}
    exclude_files = {".env", "user_store.json", "bloomcraft_ai_project.zip"}

    print(f"Packaging BloomCraft Project from: {base_dir}")
    print(f"Destination: {zip_path}")

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]

            for file in files:
                if (file in exclude_files 
                    or file.endswith(".env") 
                    or (file.startswith(".env.") and not file.endswith(".example")) 
                    or any(file.endswith(ext) for ext in exclude_exts)):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)
                zf.write(file_path, arcname)
                file_count += 1

    zip_size_kb = os.path.getsize(zip_path) / 1024
    print(f"Successfully packaged {file_count} files into '{os.path.basename(zip_path)}' ({zip_size_kb:.1f} KB)")
    return zip_path

if __name__ == "__main__":
    create_project_zip()
