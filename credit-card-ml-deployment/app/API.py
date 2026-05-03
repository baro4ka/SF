from flask import Flask, request, jsonify
import sys
import hashlib
from pathlib import Path
import logging
import json
import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent.parent / "src"))
from predict_utils import load_model, predict_default

app = Flask(__name__)

# Загружаем обе модели при старте
load_model("v1")
load_model("v2")

def get_model_version(user_id):
    """Определяет версию модели на основе user_id"""
    if not user_id:
        return "v1"
    
    hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest()[:8], 16)
    return "v2" if hash_val % 2 == 0 else "v1"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"service": "credit-default-predictor", "status": "healthy"}), 200

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        user_id = data.get('user_id', None)
        
        # Определяем версию модели
        model_version = get_model_version(user_id)
        
        # Логируем запрос (JSON формат для ELK)
        log_entry = {
            "user_id": user_id,
            "model_version": model_version,
            "endpoint": "/predict",
            "timestamp": pd.Timestamp.now().isoformat()
        }
        app.logger.info(json.dumps(log_entry))
        
        # Убираем user_id из признаков
        features = {k: v for k, v in data.items() if k != 'user_id'}
        
        # Предсказание
        prediction, probability = predict_default(features, version=model_version)
        
        # Логируем ответ
        response_log = {
            "user_id": user_id,
            "model_version": model_version,
            "prediction": prediction,
            "probability": probability,
            "default_risk": "High" if probability > 0.5 else "Low",
            "timestamp": pd.Timestamp.now().isoformat()
        }
        app.logger.info(json.dumps(response_log))
        
        return jsonify({
            "prediction": prediction,
            "probability": probability,
            "model_version": model_version,
            "default_risk": "High" if probability > 0.5 else "Low"
        })
    except Exception as e:
        error_log = {
            "error": str(e),
            "user_id": data.get('user_id', None) if 'data' in locals() else None,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        app.logger.error(json.dumps(error_log))
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)