import os
import json
import logging
import re  # <--- Thêm thư viện này để xử lý văn bản
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CẤU HÌNH AI ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_REGION", "us-central1")
model = None

try:
    if PROJECT_ID:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        # Khởi tạo Model
        model = GenerativeModel("gemini-1.5-flash-001")
        logger.info(f"✅ AI Ready: {PROJECT_ID}")
except Exception as e:
    logger.error(f"❌ AI Init Error: {e}")

# --- DATA MODEL ---
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

@app.post("/generate-game")
async def generate_game(config: GameConfig):
    if config.license_key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Sai mã kích hoạt!")

    if not model:
        raise HTTPException(status_code=500, detail="Lỗi kết nối AI (Biến môi trường chưa nhận)")

    # Logic Prompt
    count_req = f"- Số lượng câu hỏi: {config.questionCount}" if config.activityType == 'practice' else ""
    prompt = f"""
    Bạn là chuyên gia giáo dục. Nhiệm vụ: Tạo dữ liệu trò chơi JSON.
    - Môn: {config.subject} ({config.grade}) - Sách: {config.bookSeries}
    - Bài: {config.lessonName}
    - Loại game: {config.gameType}
    {count_req}

    YÊU CẦU TUYỆT ĐỐI:
    1. Chỉ trả về 1 JSON object duy nhất.
    2. Không được viết thêm lời dẫn như "Đây là kết quả", "Vâng thưa bạn".
    3. Cấu trúc JSON:
    {{
        "title": "Tên trò chơi",
        "description": "Cách chơi",
        "questions": []
    }}
    """

    try:
        # --- CẤU HÌNH QUAN TRỌNG: ÉP TRẢ VỀ JSON ---
        generation_config = GenerationConfig(
            response_mime_type="application/json", # <--- Dòng này ép AI chỉ được nhả JSON
            temperature=0.5
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        raw_text = response.text
        logger.info(f"AI Raw Response: {raw_text[:100]}...") # Ghi log để kiểm tra

        # --- LÀM SẠCH MẠNH TAY HƠN ---
        # 1. Xóa markdown code block
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # 2. Dùng Regex để tìm đúng đoạn bắt đầu bằng { và kết thúc bằng }
        # Phòng trường hợp AI vẫn nói nhảm ở đầu/cuối
        match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if match:
            cleaned_text = match.group(0)
        
        return json.loads(cleaned_text)

    except json.JSONDecodeError:
        logger.error(f"JSON Error. Raw text received: {raw_text}")
        raise HTTPException(status_code=500, detail="AI trả về dữ liệu lỗi định dạng. Hãy thử lại.")
    except Exception as e:
        logger.error(f"System Error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
