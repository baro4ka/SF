import pickle
import pandas as pd
from pathlib import Path

_models = {}

def load_model(version="v1", model_path=None):
    """Загружает модель указанной версии"""
    global _models
    
    if version in _models:
        return _models[version]
    
    if model_path is None:
        if version == "v1":
            model_path = "models/rf_default_model.pkl"
        elif version == "v2":
            model_path = "models/rf_default_model_v2.pkl"
        else:
            raise ValueError(f"Unknown model version: {version}")
    
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    
    _models[version] = model
    print(f"Model {version} loaded from {model_path}")
    return model

def get_model(version="v1"):
    """Возвращает загруженную модель"""
    if version not in _models:
        load_model(version)
    return _models[version]

def predict_default(input_data, version="v1"):
    """
    Предсказание для одного клиента указанной версией модели
    """
    model = get_model(version)
    
    if isinstance(input_data, dict):
        input_df = pd.DataFrame([input_data])
    else:
        input_df = input_data
    
    prediction = model.predict(input_df)[0]
    probability = model.predict_proba(input_df)[0][1]
    
    return int(prediction), float(probability)