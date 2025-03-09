import httpx

URL = "http://127.0.0.1:5000/alice"

def send_request(text):
    payload = {
        "request": {
            "original_utterance": text
        },
        "session": {
            "new": True,
            "session_id": "123",
            "message_id": 1,
            "skill_id": "456",
            "user_id": "789"
        },
        "version": "1.0"
    }
    try:
        response = httpx.post(URL, json=payload, timeout=30.0)
        if response.status_code == 200:
            response_data = response.json()
            tts = response_data["response"]["tts"]
            print(f"Ответ: {tts}")
        else:
            print(f"Ошибка: {response.status_code} - {response.text}")
    except httpx.ConnectTimeout:
        print("Таймаут! Сервер не отвечает.")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    print("Вводи текст или 'exit' для выхода:")
    while True:
        text = input("> ")
        if text.lower() == "exit":
            print("Выход.")
            break
        send_request(text)