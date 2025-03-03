import os

from flask import Flask, request, jsonify
from grok3api.client import GrokClient

app = Flask(__name__)
PERSONALITY = "Отвечай максимально кратко\n"

@app.route('/alice', methods=['POST'])
def alice_endpoint():
    data = request.get_json()
    query = data['request']['original_utterance'].lower()
    client = GrokClient()
    try:
        result = client.ChatCompletion.create(PERSONALITY + query)
        response = result.modelResponse.message if result and result.modelResponse else "Grok молчит!"
        print(f"Response: {response}")
    except Exception as e:
        response = f"Ошибка: {str(e)}"
        print(f"Error: {response}")
    return jsonify({
        "response": {
            "text": response,
            "end_session": True
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)