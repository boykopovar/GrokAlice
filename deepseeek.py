import os
import logging
import re
import json
import random
from typing import List, Dict
import asyncio
from multiprocessing import freeze_support
import threading

import httpx
from flask import Flask, request, Response
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()
app = Flask(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PERSONALITY = os.getenv("PERSONALITY", "Отвечай кратко.")
MODEL_NAME = "deepseek/deepseek-r1"
SCENARIO_ID = os.getenv("SCENARIO_ID")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")
HISTORY_LENGTH = int(os.getenv("HISTORY_LENGTH", 5))

session_data = {}

initial_thinking_phrases = [
    "Сейчас подумаю.",
    "Дай мне секунду.",
    "Ща прикину.",
    "Погоди, думаю."
]

ongoing_thinking_phrases = [
    "Всё ещё думаю.",
    "Ещё не готово.",
    "Пока размышляю.",
    "Думаю дальше."
]

async def request_deepseek(system_prompt: str, messages: List[Dict], user_msg: Dict, deepseek_api_key: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages,
            user_msg,
        ],
        "stream": False,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip() if data["choices"] else ""
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)
            return reply
        else:
            return ""

def start_scenario():
    url = f"https://api.iot.yandex.net/v1.0/scenarios/{SCENARIO_ID}/actions"
    headers = {"Authorization": f"Bearer {YANDEX_API_TOKEN}"}
    response = httpx.post(url, headers=headers, timeout=30.0)

def process_deepseek(query: str, history: List[Dict], session_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    user_msg = {"role": "user", "content": query}
    response_text = loop.run_until_complete(request_deepseek(PERSONALITY, history[-HISTORY_LENGTH:], user_msg, DEEPSEEK_API_KEY))
    if response_text:
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response_text})
        session_data[session_id]["answer"] = response_text
    session_data[session_id]["is_processing"] = False

@app.route('/alice', methods=['POST'])
def alice_endpoint():
    data = request.get_json(silent=True)
    if not data or "request" not in data or "original_utterance" not in data["request"] or "session" not in data:
        response_data = {
            "response": {"text": "Неверный запрос.", "tts": "Неверный запрос.", "end_session": False},
            "session": {},
            "version": "1.0"
        }
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    session_id = data["session"]["session_id"]
    if session_id not in session_data:
        session_data[session_id] = {"answer": None, "is_processing": False, "history": []}
    session_info = session_data[session_id]
    history = session_info["history"]
    session_data_from_request = data.get("session", {})

    query = data["request"]["original_utterance"].strip().lower() or "Очень кратко, парой слов ответь кто ты?"

    if session_info["answer"]:
        response_text = session_info["answer"]
        session_info["answer"] = None
        threading.Thread(target=start_scenario).start()
        end_session = False
    elif session_info["is_processing"]:
        response_text = random.choice(ongoing_thinking_phrases)
        end_session = False
    else:
        response_text = random.choice(initial_thinking_phrases)
        session_info["is_processing"] = True
        threading.Thread(target=process_deepseek, args=(query, history, session_id)).start()
        end_session = False

    response_data = {
        "response": {"text": response_text, "tts": response_text, "end_session": end_session},
        "session": session_data_from_request,
        "session_state": {"value": 12},
        "user_state_update": {"value": 12},
        "application_state": {"value": 12},
        "version": "1.0"
    }
    return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

if __name__ == "__main__":
    freeze_support()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)