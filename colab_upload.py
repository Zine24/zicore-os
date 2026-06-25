"""
ZICORE Upload Helper — Run this BEFORE colab_setup.py
Upload your zicore-system.zip file to Google Colab.
"""
import os
import subprocess
import zipfile
from pathlib import Path

print("=" * 60)
print("  ZICORE — FILE UPLOAD HELPER")
print("=" * 60)

# Check if already uploaded
ZICORE_DIR = Path("/content/zicore-system")
if ZICORE_DIR.exists():
    print("\n[OK] zicore-system already exists at /content/zicore-system")
    print("[OK] Ready to run colab_setup.py")
else:
    print("\n[INFO] Please upload your zicore-system.zip file")
    print("[INFO] Use the file upload dialog below...")
    print()

    try:
        from google.colab import files
        uploaded = files.upload()

        if uploaded:
            filename = list(uploaded.keys())[0]
            print(f"\n[OK] Uploaded: {filename}")

            if filename.endswith('.zip'):
                print("[INFO] Extracting...")
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    zip_ref.extractall("/content/")
                print("[OK] Extracted to /content/")

                # Check if extracted folder exists
                extracted = Path("/content/zicore-system")
                if extracted.exists():
                    print(f"[OK] Found {extracted}")
                    print("\n[NEXT] Now run: python colab_setup.py")
                else:
                    # Try to find what was extracted
                    contents = os.listdir("/content/")
                    print(f"[INFO] Contents: {contents}")
                    print("[INFO] You may need to rename the folder to 'zicore-system'")
            else:
                print("[ERROR] Please upload a .zip file")
        else:
            print("[ERROR] No file uploaded")

    except ImportError:
        print("[ERROR] google.colab not available. Run this in Google Colab.")
        print()
        print("Alternative: Mount Google Drive")
        print("  from google.colab import drive")
        print("  drive.mount('/content/drive')")
        print("  !cp -r /content/drive/MyDrive/zicore-system /content/")

print()
print("=" * 60)
