import os
from typing import Optional
import logging
from flask import Flask, request, jsonify
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

CLIENT: Optional[GrokClient] = None
client_lock = threading.Lock()


def init_client():
    """Инициализирует CLIENT, если он ещё не создан."""
    global CLIENT
    with client_lock:
        if CLIENT is None:
            logger.info("Инициализируем GrokClient")
            try:
                CLIENT = GrokClient(history_msg_count=5)
                logger.info("GrokClient успешно инициализирован")
            except Exception as e:
                logger.critical(f"Ошибка при инициализации GrokClient: {str(e)}")
                raise


current_answer = None
current_query_id = 0


def get_answer_from_grok(query: str):
    """
    Отправляет запрос к Grok и сохраняет ответ в глобальной переменной current_answer.
    """
    global current_answer, current_query_id
    query_id = current_query_id

    # Убеждаемся, что CLIENT инициализирован
    init_client()

    try:
        logger.info(f"Устанавливаем промпт для Grok: {PERSONALITY}")
        CLIENT.history.set_main_system_prompt(PERSONALITY)
        logger.info(f"Отправляем запрос к Grok: {query}")
        result = CLIENT.send_message(query)
        response = result.modelResponse.message if result and result.modelResponse else "Grok не отвечает."
    except Exception as e:
        logger.error(f"Ошибка в get_answer_from_grok: {str(e)}")
        response = f"Ошибка: {str(e)}"
    current_answer = (query_id, response)
    logger.info(f"Ответ от Grok: {response}")


def start_scenario():
    """
    Запускает сценарий в Яндекс Умном Доме через API с использованием httpx.
    """
    url = f"https://api.iot.yandex.net/v1.0/scenarios/{SCENARIO_ID}/actions"
    headers = {"Authorization": f"Bearer {YANDEX_API_TOKEN}"}
    try:
        logger.info("Запускаем сценарий Яндекс Умного Дома")
        response = httpx.post(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            logger.info("Сценарий успешно запущен")
        else:
            logger.error(f"Ошибка запуска сценария: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запуске сценария: {str(e)}")


@app.route('/alice', methods=['POST'])
def alice_endpoint():
    """
    Обрабатывает входящие POST-запросы от Алисы, управляет ответами и запуском сценариев.
    """
    global current_answer, current_query_id
    data = request.get_json(silent=True)
    logger.info(f"Получен запрос: {request.data.decode('utf-8')}")

    if not data or "request" not in data or "original_utterance" not in data["request"]:
        response_text = "Неверный запрос."
        logger.warning("Данные пустые или некорректны")
    else:
        query = data["request"]["original_utterance"].strip().lower()
        if not query:
            query = "расскажи о себе"
            logger.info("Запрос пустой, подставлен: 'Расскажи о себе'")

        if current_answer is not None and isinstance(current_answer, tuple) and len(current_answer) > 0 and \
                current_answer[0] == current_query_id:
            response_text = current_answer[1]
            current_answer = None
            logger.info(f"Ответ готов: {response_text}")
        else:
            current_query_id += 1
            response_text = "Сейчас подумаю."
            thread = threading.Thread(target=get_answer_from_grok, args=(query,))
            thread.start()
            start_scenario()
            logger.info(f"Запрос принят: {query}")

    return jsonify({
        "response": {
            "text": response_text,
            "tts": response_text,
            "end_session": True
        }
    })


if __name__ == "__main__":
    freeze_support()
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Запускаем Flask на порту {port}")
    app.run(host="0.0.0.0", port=port)