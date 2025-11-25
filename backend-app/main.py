import os
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel

# --- 1. IMPORT QUAN TRỌNG (Đừng xóa dòng dưới) ---
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <--- Dòng này để sửa lỗi CORS
from pydantic import BaseModel

# Cấu hình log để xem lỗi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo ứng dụng
app = FastAPI()

# ==========================================
# 2. CẤU HÌNH CORS (CHÈN ĐOẠN NÀY VÀO)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dấu * nghĩa là: "Ai gọi cũng trả lời" (Cloudflare, Localhost...)
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép mọi hành động (POST, GET...)
    allow_headers=["*"],  # Cho phép mọi loại dữ liệu
)
# ==========================================


# --- CẤU HÌNH AI (Giữ nguyên) ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_REGION", "us-central1")
model = None

try:
    if PROJECT_ID:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel("gemini-1.5-flash-001")
        logger.info(f"✅ AI Sẵn sàng tại: {PROJECT_ID}")
except Exception as e:
    logger.error(f"❌ Lỗi AI: {e}")

# --- MODEL DỮ LIỆU (Giữ nguyên) ---
class GameConfig(BaseModel):
    license_key: str
    bookSeries: str
    grade: str
    subject: str
    lessonName: str
    activityType: str
    gameType: str
    questionCount: int = 5

VALID_KEYS = ["VIP-2025", "DEMO-USER"]

# --- 3. CÁC CHỨC NĂNG (ENDPOINTS) ---

@app.get("/")
def home():
    return {"status": "Server đang chạy ngon lành!"}

@app.post("/generate-game")
async def generate_game(config: GameConfig):
    # 1. Check Key
    if config.license_key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Sai mã kích hoạt!")

    if not model:
        raise HTTPException(status_code=500, detail="Lỗi kết nối AI (Server chưa config Project ID)")

    # 2. Tạo Prompt (Logic cũ của bạn)
    count_req = f"- Số lượng câu hỏi: {config.questionCount}" if config.activityType == 'practice' else ""
    
    prompt = f"""
    Bạn là chuyên gia giáo dục Việt Nam.
    Tạo dữ liệu trò chơi JSON cho bài học:
    - Môn: {config.subject} ({config.grade}) - Sách: {config.bookSeries}
    - Bài: {config.lessonName}
    - Loại game: {config.gameType}
    {count_req}

    TRẢ VỀ JSON DUY NHẤT (Không giải thích):
    {{
        "title": "Tên trò chơi",
        "description": "Cách chơi",
        "questions": [ ... danh sách câu hỏi phù hợp loại game ... ]
    }}
    """

    # 3. Gọi AI
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Lỗi tạo nội dung: {e}")
        raise HTTPException(status_code=500, detail="AI không trả lời đúng định dạng JSON.")

# Chạy app (Dòng cuối cùng)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
