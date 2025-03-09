import os
from flask import Flask, request, jsonify
from grok3api.client import GrokClient
import threading
import httpx
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PERSONALITY = os.getenv("PERSONALITY", "Отвечай максимально кратко.\n")
SCENARIO_ID = os.getenv("SCENARIO_ID")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")

current_answer = None
current_query_id = 0

def get_answer_from_grok(query):
    """
    Отправляет запрос к Grok и сохраняет ответ в глобальной переменной current_answer.
    """
    global current_answer, current_query_id
    query_id = current_query_id
    CLIENT.history.set_main_system_prompt(PERSONALITY)
    try:
        result = CLIENT.send_message(query)
        response = result.modelResponse.message if result and result.modelResponse else "Grok не отвечает."
    except Exception as e:
        response = f"Ошибка: {str(e)}"
    current_answer = (query_id, response)

def start_scenario():
    """
    Запускает сценарий в Яндекс Умном Доме через API с использованием httpx.
    """
    url = f"https://api.iot.yandex.net/v1.0/scenarios/{SCENARIO_ID}/actions"
    headers = {"Authorization": f"Bearer {YANDEX_API_TOKEN}"}
    try:
        response = httpx.post(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            print("Сценарий успешно запущен.")
        else:
            print(f"Ошибка запуска сценария: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Ошибка при запуске сценария: {str(e)}")

@app.route('/alice', methods=['POST'])
def alice_endpoint():
    """
    Обрабатывает входящие POST-запросы от Алисы, управляет ответами и запуском сценариев.
    """
    global current_query_id, current_answer
    data = request.get_json(silent=True)
    print(f"Получен запрос: {request.data.decode('utf-8')}")

    if not data or "request" not in data or "original_utterance" not in data["request"]:
        response_text = "Неверный запрос."
        print("Данные пустые или некорректны.")
    else:
        query = data["request"]["original_utterance"].strip().lower()
        if not query:
            query = "расскажи о себе"
            print("Запрос пустой, подставлен: 'Расскажи о себе'")

        if current_answer is not None and isinstance(current_answer, tuple) and len(current_answer) > 0 and \
                current_answer[0] == current_query_id:
            response_text = current_answer[1]
            current_answer = None
            print(f"Ответ готов: {response_text}")
        else:
            current_query_id += 1
            response_text = "Сейчас подумаю."
            thread = threading.Thread(target=get_answer_from_grok, args=(query,))
            thread.start()
            start_scenario()
            print(f"Запрос принят: {query}")

    return jsonify({
        "response": {
            "text": response_text,
            "tts": response_text,
            "end_session": True
        }
    })

if __name__ == "__main__":
    CLIENT = GrokClient(history_msg_count=5)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)