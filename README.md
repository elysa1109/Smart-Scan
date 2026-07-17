================================================================
SMART SCAN AI - ADAPTIVE OCR DOCUMENT SCANNER
README / SETUP INSTRUCTIONS
================================================================

PROJECT OVERVIEW
-----------------
Smart Scan AI is a document scanning system that automatically classifies 
document types (printed, handwritten, ID card, mixed), corrects perspective 
distortion, removes shadows, applies adaptive image enhancement based on 
detected image quality issues (blur, noise, low contrast), and extracts 
text using Tesseract OCR.

The system has two parts:
1. Backend - Python FastAPI server that handles all image processing and OCR
2. Frontend - Flutter mobile app that captures/uploads images and displays results

================================================================
1. REQUIRED TOOLS AND VERSIONS
================================================================

1.1 Python
    - Version: Python 3.9 or above (3.10/3.11 recommended)
    - Download: https://www.python.org/downloads/

1.2 Tesseract OCR Engine
    - This is a separate program, NOT a Python package. It must be 
      installed on the system directly.
    - Windows installer (UB Mannheim build, recommended):
      https://github.com/UB-Mannheim/tesseract/wiki
    - After installing, confirm the install path matches the path set 
      in main2.py:
          pytesseract.pytesseract.tesseract_cmd = 
              r"C:\Program Files\Tesseract-OCR\tesseract.exe"
      If installed elsewhere, update this line to match your system.

1.3 Flutter SDK
    - Version: Flutter 3.x (stable channel)
    - Download: https://docs.flutter.dev/get-started/install

1.4 Android Studio
    - Required for running the mobile app on an Android Emulator
    - Download: https://developer.android.com/studio
    - Make sure an Android Virtual Device (AVD) is created and running 
      before starting the Flutter app.

1.5 Python Libraries (backend)
    - fastapi
    - uvicorn
    - opencv-python (cv2)
    - numpy
    - pytesseract

================================================================
2. DATASET
================================================================

You can view and download the dataset in the dataset folder, or go to https://www.kaggle.com/datasets/elysalee/smart-scan-dataset to download the dataset.

================================================================
3. SETUP INSTRUCTIONS
================================================================

STEP 1: Get the source code
----------------------------
Download/clone the project folder from the link provided in the 
submission. It should contain two main folders:
    smart_scan/backend   -> Python FastAPI server
    smart_scan/mobile    -> Flutter mobile app

STEP 2: Install Tesseract OCR
-------------------------------
Install Tesseract using the link in section 1.2. Note the install path 
(default is C:\Program Files\Tesseract-OCR\tesseract.exe on Windows).

STEP 3: Set up the backend
----------------------------
Open a terminal in the backend folder:

    cd smart_scan\backend
    python -m venv venv
    venv\Scripts\activate
    pip install fastapi uvicorn opencv-python numpy pytesseract

(If a requirements.txt is included in the folder, you can instead run:
    pip install -r requirements.txt )

STEP 4: Set up the mobile app
-------------------------------
Open a separate terminal in the mobile folder:

    cd smart_scan\mobile
    flutter pub get

Make sure Android Studio is installed and an Android Emulator (AVD) is 
set up and started before proceeding to the next step.

================================================================
4. HOW TO RUN THE PROJECT
================================================================

TERMINAL 1 - Start the backend server:

    cd "smart_scan\backend"
    venv\Scripts\activate
    uvicorn main2:app --host 0.0.0.0 --port 8000 --reload

The server will start at http://0.0.0.0:8000 
You should see a startup message confirming Smart Scan AI is running.

TERMINAL 2 - Start the mobile app:

    cd "smart_scan\mobile"
    flutter run

- Make sure the Android Emulator is already open in Android Studio 
  before running this command, so Flutter can detect and launch on it.
- The app will connect to the backend server to process scanned images.

================================================================
5. NOTES
================================================================
- Backend logs each processed test to logs/test_results.csv automatically 
  (this folder is created automatically if it doesn't exist).
- If the emulator cannot reach the backend at localhost, use your 
  machine's local IP address (e.g. 10.0.2.2 for Android Emulator's 
  loopback to host machine) in the Flutter app's API config instead of 
  localhost.
- Ensure both the backend server and emulator are running at the same 
  time; the mobile app depends on the backend being live to process images.

================================================================
END OF README
================================================================
