import os
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# --- 1. CẤU HÌNH LOGGING (Để soi lỗi trên Cloud) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- 2. CẤU HÌNH CORS (Cho phép Web gọi vào) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Mở cửa cho mọi tên miền (Cloudflare, Localhost...)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. KHỞI TẠO GOOGLE VERTEX AI ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_REGION", "us-central1")

model = None

try:
    if PROJECT_ID:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        # Sử dụng model Flash cho nhanh và rẻ
        model = GenerativeModel("gemini-1.5-flash-001")
        logger.info(f"✅ Vertex AI đã khởi tạo thành công tại: {PROJECT_ID}")
    else:
        logger.warning("⚠️ Chưa cấu hình biến môi trường GCP_PROJECT. AI sẽ không chạy được.")
except Exception as e:
    logger.error(f"❌ Lỗi khởi tạo Vertex AI: {e}")

# --- 4. ĐỊNH NGHĨA DỮ LIỆU ĐẦU VÀO ---
class GameConfig(BaseModel):
    license_key: str
    bookSeries: str
    grade: str
    subject: str
    lessonName: str
    activityType: str # 'practice' hoặc 'warm-up'
    gameType: str     # 'quiz', 'simulation', ...
    questionCount: int = 5

# Danh sách mã kích hoạt hợp lệ
VALID_KEYS = ["VIP-2025", "DEMO-USER", "GV-GIOI"]

# --- 5. CÁC API ENDPOINT ---

@app.get("/")
def health_check():
    """API kiểm tra sức khỏe Server"""
    status = "Online" if model else "Offline (AI Error)"
    return {"status": status, "project": PROJECT_ID, "message": "Server Game Generator đang chạy!"}

@app.post("/generate-game")
async def generate_game(config: GameConfig):
    """API chính để tạo nội dung game"""
    
    # BƯỚC 1: Kiểm tra mã kích hoạt
    if config.license_key not in VALID_KEYS:
        logger.warning(f"Truy cập trái phép với key: {config.license_key}")
        raise HTTPException(status_code=401, detail="Mã kích hoạt không hợp lệ!")

    if not model:
        raise HTTPException(status_code=500, detail="Hệ thống AI chưa được khởi tạo đúng cách trên Server.")

    logger.info(f"Đang xử lý yêu cầu: {config.lessonName} - {config.gameType}")

    # BƯỚC 2: Xây dựng Prompt (Dựa trên logic TypeScript của bạn)
    count_req = f"- Số lượng câu hỏi: {config.questionCount}" if config.activityType == 'practice' else ""
    
    prompt = f"""
    Bạn là chuyên gia giáo dục Việt Nam, am hiểu SGK {config.bookSeries}.
    Nhiệm vụ: Tạo dữ liệu trò chơi JSON cho bài học:
    - Môn: {config.subject} ({config.grade})
    - Bài: {config.lessonName}
    - Loại game: {config.gameType}
    {count_req}

    HÃY TRẢ VỀ JSON DUY NHẤT THEO CẤU TRÚC SAU (Không giải thích thêm):
    {{
        "title": "Tên trò chơi hấp dẫn",
        "description": "Hướng dẫn cách chơi ngắn gọn",
        "questions": [
            ... Tạo danh sách câu hỏi phù hợp với loại game '{config.gameType}' ...
        ]
    }}

    GỢI Ý CẤU TRÚC CÂU HỎI CHO '{config.gameType}':
    - Nếu là 'quiz': {{ "id": "q1", "question": "...", "options": ["A","B","C","D"], "correctAnswer": "A", "explanation": "..." }}
    - Nếu là 'simulation': Tạo 1 item chứa 'simulationConfig' với 'zones' (vùng thả) và 'items' (vật thể kéo thả).
    - Nếu là 'sequencing': Tạo danh sách các bước có 'sequenceOrder'.
    
    LƯU Ý QUAN TRỌNG:
    1. Nội dung phải sát thực tế SGK {config.bookSeries}.
    2. Chỉ trả về JSON thuần túy (Raw JSON).
    """

    # BƯỚC 3: Gọi AI và Xử lý lỗi
    try:
        response = model.generate_content(prompt)
        raw_text = response.text

        # Làm sạch JSON (Cực kỳ quan trọng vì AI hay thêm ```json)
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # Parse sang JSON
        game_data = json.loads(cleaned_text)
        
        return game_data

    except json.JSONDecodeError:
        logger.error(f"Lỗi JSON: AI trả về định dạng sai.\nRaw: {raw_text}")
        raise HTTPException(status_code=500, detail="AI trả về dữ liệu bị lỗi định dạng. Vui lòng thử lại.")
    except Exception as e:
        logger.error(f"Lỗi xử lý AI: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

# Chạy server (Dùng cho test local)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
