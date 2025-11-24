import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# 1. Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Cấu hình Google AI
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_REGION", "us-central1")

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Cấu hình công cụ tìm kiếm (Google Search Grounding)
    # Lưu ý: Cần bật tính năng này trong Google Cloud Console nếu muốn dùng
    tools = [Tool.from_google_search_retrieval(google_search_retrieval=vertexai.generative_models.GoogleSearchRetrieval())]
    model = GenerativeModel("gemini-1.5-flash-001", tools=tools)
except Exception as e:
    print(f"Warning Vertex AI Init: {e}")
    # Fallback nếu không init được tools (chạy model thường)
    model = GenerativeModel("gemini-1.5-flash-001")

# 3. Định nghĩa dữ liệu đầu vào (Khớp với GameConfig của bạn)
class GameConfig(BaseModel):
    license_key: str
    bookSeries: str
    subject: str
    grade: str
    lessonName: str
    activityType: str
    gameType: str
    questionCount: int = 5 # Mặc định là 5

# Mock License Key
VALID_KEYS = ["VIP-2025", "DEMO-USER"]

@app.post("/generate-game")
async def generate_game(config: GameConfig):
    # Kiểm tra License Key
    if config.license_key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Sai mã kích hoạt!")

    # Logic Prompt (Chuyển từ code TypeScript của bạn sang Python)
    question_count_prompt = f"- Số lượng câu hỏi: {config.questionCount}" if config.activityType == 'practice' else ""
    json_requirement = f"Yêu cầu về số lượng: Tạo chính xác {config.questionCount} mục trong mảng 'questions'." if config.activityType == 'practice' else ""

    prompt = f"""
    Bạn là một chuyên gia giáo dục Việt Nam, am hiểu chương trình GDPT 2018 và SGK {config.bookSeries}.
    Nhiệm vụ: Tạo nội dung trò chơi giáo dục cho bài học:
    - Môn: {config.subject}
    - Lớp: {config.grade}
    - Bài: {config.lessonName}
    - Hoạt động: {config.activityType}
    - Loại game: {config.gameType}
    {question_count_prompt}

    1. Hãy TÌM KIẾM nội dung thực tế của bài học này trong SGK.
    2. Tạo dữ liệu trò chơi dưới dạng JSON.
    {json_requirement}

    CẤU TRÚC JSON TRẢ VỀ:
    {{
        "title": "Tên trò chơi",
        "description": "Hướng dẫn cách chơi",
        "questions": [ ... danh sách câu hỏi dựa trên cấu trúc loại game {config.gameType} ...]
    }}
    
    YÊU CẦU: Trả về JSON thuần, không markdown.
    """

    try:
        response = model.generate_content(prompt)
        # Làm sạch JSON (xóa ```json và ```)
        text_response = response.text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(text_response)
    except Exception as e:
        print(f"Error: {e}")
        # Trả về lỗi giả lập để Frontend không bị treo
        return {
            "title": "Lỗi tạo nội dung",
            "description": "Không thể tạo nội dung lúc này hoặc AI trả về sai định dạng.",
            "questions": [],
            "debug_error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
