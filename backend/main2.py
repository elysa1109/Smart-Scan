from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import base64
import time
import pytesseract
from datetime import datetime
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

os.makedirs("logs", exist_ok=True)

app = FastAPI(title="Smart Scan AI - Report Version")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_counter = 0

def safe_int(value):
    try:
        return int(float(value))
    except:
        return 0


class DocumentClassifier:

    @staticmethod
    def detect_document_type(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        edge_density = np.sum(edges > 0) / edges.size
        variance = np.var(gray)
        std_dev = np.std(gray)

        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
        line_count = len(lines) if lines is not None else 0

        horizontal = 0
        vertical = 0

        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                if angle < 10 or angle > 170:
                    horizontal += 1
                elif 80 < angle < 100:
                    vertical += 1

        if edge_density > 0.15 and variance > 1500 and std_dev > 60:
            doc_type = "handwritten"
            confidence = 0.85
            reason = "High variance and irregular edges"
        elif line_count > 20 and horizontal > 5 and vertical > 3:
            doc_type = "id_card"
            confidence = 0.80
            reason = "Structured layout detected"
        elif variance < 1000 and edge_density < 0.1:
            doc_type = "printed"
            confidence = 0.90
            reason = "Clean printed text"
        else:
            doc_type = "mixed"
            confidence = 0.70
            reason = "Mixed content"

        return {
            "type": doc_type,
            "confidence": confidence,
            "reason": reason,
            "features": {
                "edge_density": round(edge_density, 4),
                "variance": round(variance, 2),
                "std_dev": round(std_dev, 2),
                "line_count": line_count,
                "horizontal_lines": horizontal,
                "vertical_lines": vertical
            }
        }


class DocumentProcessor:

    @staticmethod
    def resize_image(image, max_width=1200):
        h, w = image.shape[:2]
        if w > max_width:
            ratio = max_width / w
            image = cv2.resize(image, (max_width, int(h * ratio)))
        return image

    @staticmethod
    def _fit_line_from_segments(segments):
        points = []
        for seg in segments:
            x1, y1, x2, y2 = seg
            points.append([x1, y1])
            points.append([x2, y2])
        pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        line = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
        vx, vy = float(line[0][0]), float(line[1][0])
        x0, y0 = float(line[2][0]), float(line[3][0])
        return vx, vy, x0, y0

    @staticmethod
    def _line_intersection(l1, l2):
        vx1, vy1, x01, y01 = l1
        vx2, vy2, x02, y02 = l2
        denom = vx1 * vy2 - vy1 * vx2
        if abs(denom) < 1e-10:
            return None
        t = ((x02 - x01) * vy2 - (y02 - y01) * vx2) / denom
        return (x01 + t * vx1, y01 + t * vy1)

    @staticmethod
    def find_document_corners(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, 150,
            minLineLength=int(min(w, h) * 0.2),
            maxLineGap=30
        )

        if lines is None or len(lines) < 2:
            return None

        right_lines, left_lines, bottom_lines, top_lines = [], [], [], []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            avg_x = (x1 + x2) / 2.0
            avg_y = (y1 + y2) / 2.0

            if abs(angle) > 70:
                if avg_x > w / 2:
                    right_lines.append(line[0])
                else:
                    left_lines.append(line[0])
            else:
                if avg_y > h / 2:
                    bottom_lines.append(line[0])
                else:
                    top_lines.append(line[0])

        if not (right_lines and left_lines and bottom_lines and top_lines):
            return None

        right_line  = DocumentProcessor._fit_line_from_segments(right_lines)
        left_line   = DocumentProcessor._fit_line_from_segments(left_lines)
        bottom_line = DocumentProcessor._fit_line_from_segments(bottom_lines)
        top_line    = DocumentProcessor._fit_line_from_segments(top_lines)

        TL = DocumentProcessor._line_intersection(top_line, left_line)
        TR = DocumentProcessor._line_intersection(top_line, right_line)
        BR = DocumentProcessor._line_intersection(bottom_line, right_line)
        BL = DocumentProcessor._line_intersection(bottom_line, left_line)

        if None in (TL, TR, BR, BL):
            return None

        def clamp(pt):
            return [
                max(0, min(w - 1, int(round(pt[0])))),
                max(0, min(h - 1, int(round(pt[1]))))
            ]

        corners = np.array(
            [clamp(TL), clamp(TR), clamp(BR), clamp(BL)],
            dtype=np.float32
        )
        return corners

    @staticmethod
    def perspective_transform(image, corners):
        TL, TR, BR, BL = corners

        maxWidth = int(max(
            np.linalg.norm(BR - BL),
            np.linalg.norm(TR - TL)
        ))
        maxHeight = int(max(
            np.linalg.norm(TR - BR),
            np.linalg.norm(TL - BL)
        ))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(corners, dst)
        warped = cv2.warpPerspective(
            image, M, (maxWidth, maxHeight),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        return warped

    @staticmethod
    def remove_shadow(image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        background = cv2.medianBlur(gray, 201)

        normalised = (gray.astype(np.float64) / (background.astype(np.float64) + 1.0)) * 255.0
        normalised = np.clip(normalised, 0, 255).astype(np.uint8)

        return normalised

    @staticmethod
    def enhance_document(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        processed = gray.copy()

        laplacian_var  = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_detected  = laplacian_var < 100

        hp = cv2.filter2D(gray.astype(np.float32), -1,
                          np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32))
        noise_sigma    = float(np.median(np.abs(hp)) / 0.6745)
        noise_detected = noise_sigma > 10

        contrast_std   = float(gray.std())
        low_contrast   = contrast_std < 50

        brightness_mean  = float(gray.mean())
        brightness_issue = brightness_mean < 100 or brightness_mean > 180

        if noise_detected:
            processed = cv2.bilateralFilter(processed, d=9, sigmaColor=75, sigmaSpace=75)

        if low_contrast or brightness_issue:
            processed = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(processed)

        if blur_detected:
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
            processed = cv2.filter2D(processed, -1, kernel)

        if low_contrast:
            _, processed = cv2.threshold(processed, 0, 255,
                                         cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def extract_text(image):
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        config = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
        data = pytesseract.image_to_data(
            image, config=config,
            output_type=pytesseract.Output.DICT
        )

        line_words = {}
        text_data = []

        for i in range(len(data["text"])):
            word = data["text"][i].strip()
            raw_conf = data["conf"][i]
            conf = int(raw_conf) if str(raw_conf) != "-1" else 0

            if word and conf > 0:
                key = (int(data["block_num"][i]), int(data["line_num"][i]))
                line_words.setdefault(key, []).append(word)
                text_data.append({
                    "text": word,
                    "confidence": round(conf / 100.0, 3),
                    "position": {
                        "x": int(data["left"][i]),
                        "y": int(data["top"][i]),
                        "width": int(data["width"][i]),
                        "height": int(data["height"][i]),
                    }
                })

        result_lines = []
        prev_block = None
        for (block, line) in sorted(line_words.keys()):
            if prev_block is not None and block != prev_block:
                result_lines.append("")
            result_lines.append(" ".join(line_words[(block, line)]))
            prev_block = block

        return "\n".join(result_lines), text_data


def log_test_result(result_data):
    global test_counter
    test_counter += 1

    csv_file = "logs/test_results.csv"
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, 'a') as f:
        if not file_exists:
            f.write("Test_ID,Timestamp,Document_Type,Mode,OCR_Engine,Processing_Time,"
                    "Edge_Detection_Time,OCR_Time,Characters_Extracted,Word_Count,"
                    "Contour_Found,Edge_Density,Variance,Confidence\n")

        f.write(f"{test_counter},"
                f"{result_data['timestamp']},"
                f"{result_data['doc_type']},"
                f"{result_data['mode']},"
                f"{result_data['ocr_engine']},"
                f"{result_data['total_time']:.3f},"
                f"{result_data['edge_time']:.3f},"
                f"{result_data['ocr_time']:.3f},"
                f"{result_data['char_count']},"
                f"{result_data['word_count']},"
                f"{result_data['contour_found']},"
                f"{result_data.get('edge_density', 0):.4f},"
                f"{result_data.get('variance', 0):.2f},"
                f"{result_data.get('confidence', 0):.2f}\n")


@app.get("/")
def root():
    return {
        "message": "Smart Scan AI - Report Version",
        "test_counter": test_counter,
        "logs_saved": "logs/test_results.csv"
    }


@app.post("/api/process")
async def process_document(file: UploadFile = File(...)):
    start_time = time.time()

    try:
        print("\n" + "=" * 80)
        print(f"📄 TEST #{test_counter + 1} - PROCESSING DOCUMENT")
        print("=" * 80)
        print(f"Filename: {file.filename}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        contents = await file.read()
        img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

        if img is None:
            return JSONResponse(status_code=400, content={"error": "Invalid image"})

        t1 = time.time()
        print(f"\n[1] Image Loaded: {img.shape} ({t1 - start_time:.3f}s)")

        original_size = img.shape
        img = DocumentProcessor.resize_image(img, max_width=1200)
        t2 = time.time()
        print(f"[2] Resized: {original_size} → {img.shape} ({t2 - t1:.3f}s)")

        print(f"\n🤖 AI DOCUMENT CLASSIFICATION:")
        classification = DocumentClassifier.detect_document_type(img)
        doc_type = classification['type']
        print(f"   Type: {doc_type.upper()}")
        print(f"   Confidence: {classification['confidence'] * 100:.1f}%")
        print(f"   Reason: {classification['reason']}")
        print(f"   Features:")
        for key, val in classification['features'].items():
            print(f"      - {key}: {val}")

        t3 = time.time()

        print(f"\n📐 CORNER DETECTION (HoughLines):")
        corners = DocumentProcessor.find_document_corners(img)
        edge_time = time.time() - t3
        corners_found = corners is not None

        if corners_found:
            print(f"   ✅ Document corners detected:")
            for label, pt in zip(["TL", "TR", "BR", "BL"], corners):
                print(f"      {label}: ({pt[0]:.0f}, {pt[1]:.0f})")
        else:
            print(f"   ⚠️  Corner detection failed - using full image")

        print(f"   Time: {edge_time:.3f}s")
        t4 = time.time()

        if corners_found:
            print(f"\n📐 PERSPECTIVE CORRECTION:")
            img = DocumentProcessor.perspective_transform(img, corners)
            print(f"   ✅ Warped to: {img.shape}")
        t5 = time.time()

        print(f"\n🌑 SHADOW REMOVAL:")
        shadow_removed = DocumentProcessor.remove_shadow(img)
        print(f"   ✅ Shadow removed (median-blur background division)")
        print(f"   Time: {time.time() - t5:.3f}s")
        t6 = time.time()

        print(f"\n🎨 IMAGE ENHANCEMENT (Adaptive):")
        enhanced = DocumentProcessor.enhance_document(shadow_removed)
        print(f"   Time: {time.time() - t6:.3f}s")
        t7 = time.time()

        print(f"\n📝 OCR PROCESSING:")
        print(f"   Engine: Tesseract LSTM")
        ocr_start = time.time()
        text, blocks = DocumentProcessor.extract_text(enhanced)
        ocr_time = time.time() - ocr_start

        char_count = len(text)
        word_count = len(text.split())

        print(f"   Characters extracted: {char_count}")
        print(f"   Words extracted: {word_count}")
        print(f"   Text blocks found: {len(blocks)}")
        print(f"   Time: {ocr_time:.3f}s")

        _, buf = cv2.imencode(".jpg", enhanced, [cv2.IMWRITE_JPEG_QUALITY, 90])
        img_b64 = base64.b64encode(buf).decode()
        t8 = time.time()

        total_time = time.time() - start_time

        print(f"\n⏱️  PERFORMANCE SUMMARY:")
        print(f"   Total Processing Time: {total_time:.3f}s")
        print(f"   Breakdown:")
        print(f"      - Image loading:       {t1 - start_time:.3f}s")
        print(f"      - Resizing:            {t2 - t1:.3f}s")
        print(f"      - Classification:      {t3 - t2:.3f}s")
        print(f"      - Corner detection:    {edge_time:.3f}s")
        print(f"      - Perspective warp:    {t5 - t4:.3f}s")
        print(f"      - Shadow removal:      {t6 - t5:.3f}s")
        print(f"      - Enhancement:         {t7 - t6:.3f}s")
        print(f"      - OCR:                 {ocr_time:.3f}s")
        print(f"      - Encoding:            {t8 - t7:.3f}s")

        result_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'doc_type': doc_type,
            'mode': 'auto',
            'ocr_engine': 'tesseract',
            'total_time': total_time,
            'edge_time': edge_time,
            'ocr_time': ocr_time,
            'char_count': char_count,
            'word_count': word_count,
            'contour_found': corners_found,
            'edge_density': classification['features']['edge_density'],
            'variance': classification['features']['variance'],
            'confidence': classification['confidence']
        }
        log_test_result(result_data)

        print(f"\n✅ Test logged to: logs/test_results.csv")
        print("=" * 80 + "\n")

        return {
            "success": True,
            "test_id": test_counter,
            "extracted_text": text,
            "text_blocks": blocks,
            "processed_image": f"data:image/jpeg;base64,{img_b64}",
            "processing_time": round(total_time, 3),
            "classification": classification,
            "mode": "auto",
            "ocr_engine_used": "tesseract",
            "contour_found": corners_found,
            "statistics": {
                "characters": char_count,
                "words": word_count,
                "blocks": len(blocks),
                "ocr_time": round(ocr_time, 3),
                "edge_detection_time": round(edge_time, 3)
            }
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("🚀 SMART SCAN AI - FYP REPORT VERSION")
    print("=" * 80)
    print("Features:")
    print("  ✅ Detailed console logging for each test")
    print("  ✅ Automatic CSV export: logs/test_results.csv")
    print("  ✅ AI document classification")
    print("  ✅ HoughLines corner detection + perspective correction")
    print("  ✅ Shadow removal (median-blur background division)")
    print("  ✅ Performance breakdown by stage")
    print("  ✅ Character & word count")
    print("=" * 80 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
