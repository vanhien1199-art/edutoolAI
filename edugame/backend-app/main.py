import os
import vertexai
from vertexai.generative_models import GenerativeModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# --- CẤU HÌNH CORS (QUAN TRỌNG) ---
# Cho phép Cloudflare hoặc bất kỳ trang web nào gọi vào
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CẤU HÌNH GOOGLE AI ---
# Lấy Project ID từ biến môi trường (như đã hướng dẫn ở câu trước)
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_REGION", "us-central1")

# Khởi tạo Vertex AI (Nếu chưa set biến môi trường sẽ báo lỗi)
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel("gemini-1.5-flash-001") # Dùng bản Flash cho nhanh và rẻ
except Exception as e:
    print(f"Lỗi khởi tạo Vertex AI: {e}")

# --- MÔ HÌNH DỮ LIỆU GỬI LÊN ---
class ChatRequest(BaseModel):
    message: str
    license_key: str

# --- MOCK DATABASE KEY (Giả lập) ---
# Trong thực tế, bạn sẽ nối cái này vào Database SQL
VALID_KEYS = ["VIP-2025", "DEMO-USER", "KHACH-HANG-1"]

@app.get("/")
def home():
    return {"status": "Backend đang chạy ổn định!"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Kiểm tra License Key
    if request.license_key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Mã kích hoạt không hợp lệ hoặc đã hết hạn!")

    # 2. Gọi Google AI
    try:
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Xin lỗi, hệ thống AI đang bận. Vui lòng thử lại sau."}

# Chạy server (Dùng cho local test)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))