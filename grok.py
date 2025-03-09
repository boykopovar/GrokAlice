import json
import os
import logging
import re
from flask import Flask, request, Response
from grok3api.client import GrokClient
import threading
import httpx
from dotenv import load_dotenv
from multiprocessing import freeze_support

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

PERSONALITY = os.getenv("PERSONALITY", "Отвечай максимально кратко.\n")
SCENARIO_ID = os.getenv("SCENARIO_ID")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")

CLIENT = None
current_answer = None
current_query_id = 0
client_lock = threading.Lock()
is_processing = False
processing_lock = threading.Lock()

def remove_emoji(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

def init_client():
    global CLIENT
    with client_lock:
        if CLIENT is None:
            logger.info("Инициализируем GrokClient")
            CLIENT = GrokClient(history_msg_count=5)
            logger.info("GrokClient успешно инициализирован")

def process_grok_and_scenario(query):
    global current_answer, current_query_id, is_processing
    try:
        init_client()
        CLIENT.history.set_main_system_prompt(PERSONALITY)
        logger.info(f"Отправляем запрос к Grok: {query}")
        result = CLIENT.send_message(query)
        response = result.modelResponse.message if result and result.modelResponse else "Grok не отвечает."
        response = remove_emoji(response)
        logger.info(f"Ответ от Grok: {response}")
        current_answer = (current_query_id, response)
        start_scenario()
    except Exception as e:
        error_msg = remove_emoji(f"Ошибка: {str(e)}")
        logger.error(error_msg)
        current_answer = (current_query_id, error_msg)
    finally:
        with processing_lock:
            is_processing = False

def start_scenario():
    url = f"https://api.iot.yandex.net/v1.0/scenarios/{SCENARIO_ID}/actions"
    headers = {"Authorization": f"Bearer {YANDEX_API_TOKEN}"}
    try:
        response = httpx.post(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            logger.info("Сценарий успешно запущен")
        else:
            logger.error(f"Ошибка запуска сценария: {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при запуске сценария: {str(e)}")

@app.route('/alice', methods=['POST'])
def alice_endpoint():
    global current_answer, current_query_id, is_processing
    data = request.get_json(silent=True)
    logger.info(f"Получен запрос: {request.data.decode('utf-8')}")

    if not data or "request" not in data or "original_utterance" not in data["request"]:
        response_data = {
            "response": {
                "text": "Неверный запрос.",
                "tts": "Неверный запрос.",
                "end_session": True
            },
            "session": {},
            "version": "1.0"
        }
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    query = remove_emoji(data["request"]["original_utterance"].strip().lower()) or "расскажи о себе"

    session_data = data.get("session", {})

    with processing_lock:
        if is_processing:
            response_text = "Я всё ещё думаю над предыдущим запросом."
            end_session = True
        else:
            response_text = "Сейчас подумаю."
            is_processing = True
            current_query_id += 1
            threading.Thread(target=process_grok_and_scenario, args=(query,)).start()
            end_session = True

    response_text = remove_emoji(response_text)
    response_data = {
        "response": {
            "text": response_text[:1024],
            "tts": response_text[:1024],
            "end_session": end_session,
        },
        "session": session_data,
        "session_state": {
            "value": 12
        },
        "user_state_update": {
            "value": 12
        },
        "application_state": {
            "value": 12
        },
        "version": "1.0"
    }
    answer = Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')
    print(answer.get_data(as_text=True))
    return answer

if __name__ == "__main__":
    freeze_support()
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Запускаем Flask на порту {port}")
    app.run(host="0.0.0.0", port=port)