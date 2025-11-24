// --- CẤU HÌNH ---
// Bạn dán link Google Cloud Run của bạn vào đây TRƯỚC khi đẩy lên GitHub
const BACKEND_URL = "https://edutoolai-830472878190.us-central1.run.app"; 

async function sendMessage() {
    const licenseKey = document.getElementById('licenseKey').value.trim();
    const inputField = document.getElementById('userInput');
    const message = inputField.value.trim();
    const chatBox = document.getElementById('chatContainer');
    const btn = document.getElementById('send-btn');

    if (!message) return;
    if (!licenseKey) {
        alert("Vui lòng nhập Mã Kích Hoạt trước!");
        return;
    }

    // Giao diện khi người dùng gửi
    chatBox.innerHTML += `<div class="message user-msg">${message}</div>`;
    inputField.value = '';
    btn.disabled = true;
    btn.innerText = "Đang xử lý...";
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch(`${BACKEND_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, license_key: licenseKey })
        });

        const data = await response.json();

        if (response.ok) {
            chatBox.innerHTML += `<div class="message ai-msg">${data.reply}</div>`;
        } else {
            chatBox.innerHTML += `<div class="message error-msg">⚠️ Lỗi: ${data.detail || "Lỗi server"}</div>`;
        }
    } catch (error) {
        console.error(error);
        chatBox.innerHTML += `<div class="message error-msg">⚠️ Lỗi kết nối mạng!</div>`;
    } finally {
        btn.disabled = false;
        btn.innerText = "GỬI";
        chatBox.scrollTop = chatBox.scrollHeight;
    }

}
