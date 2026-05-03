# Credit Default Prediction Service

Сервис прогнозирования дефолта по кредитным картам с A/B‑тестированием, контейнеризацией и production‑ready подходами.

## Цели проекта

- Внедрить ML‑модель в production‑like‑среду.
- Обеспечить воспроизводимость (Docker + requirements.txt).
- Реализовать A/B‑тестирование двух версий модели.
- Документировать архитектурные и инфраструктурные решения.

## Доменные данные

Датасет: [Default of Credit Card Clients Dataset](https://www.kaggle.com/datasets/uciml/default-of-credit-card-clients-dataset)  
Таргет: `default.payment.next.month` (дефолт в следующем месяце)  
Признаки: 23.

---

## Быстрый старт

### Запуск локально

```bash
git clone https://github.com/baro4ka/SF/edit/main/credit-card-ml-deployment.git
cd credit-card-ml-deployment
pip install -r requirements.txt
python app/API.py
```

### Запуск через Docker

```bash
docker pull cr.yandex/crpk4u2d1dcukcnbk0jv/credit-default-predictor:v2
docker run -p 5000:5000 cr.yandex/crpk4u2d1dcukcnbk0jv/credit-default-predictor:v2
```

Сервис будет доступен по адресу `http://localhost:5000`.

---

## API Endpoints

### `GET /health`

Проверка работоспособности сервиса.

**Ответ:**
```json
{
  "service": "credit-default-predictor",
  "status": "healthy"
}
```

### `POST /predict`

Предсказание дефолта.

**Формат запроса (JSON):**
- `user_id` (опционально) — для A/B‑тестирования.
- Все 23 признака из датасета `UCI_Credit_Card.csv`.

**Пример запроса (curl):**
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 12345,
    "LIMIT_BAL": 50000,
    "SEX": 1,
    "EDUCATION": 3,
    "MARRIAGE": 2,
    "AGE": 25,
    "PAY_0": 2,
    "PAY_2": 2,
    "PAY_3": 2,
    "PAY_4": 2,
    "PAY_5": 2,
    "PAY_6": 2,
    "BILL_AMT1": 10000,
    "BILL_AMT2": 9000,
    "BILL_AMT3": 8000,
    "BILL_AMT4": 7000,
    "BILL_AMT5": 6000,
    "BILL_AMT6": 5000,
    "PAY_AMT1": 1000,
    "PAY_AMT2": 900,
    "PAY_AMT3": 800,
    "PAY_AMT4": 700,
    "PAY_AMT5": 600,
    "PAY_AMT6": 500
}'
```

**Пример ответа:**
```json
{
  "prediction": 1,
  "probability": 0.727,
  "model_version": "v1",
  "default_risk": "High"
}
```

---

## A/B‑тестирование

- **Разделение трафика**: `user_id % 2 == 0` → v2, иначе → v1.
- **Длительность**: 14 дней или 10 000 запросов.
- **Метрики**:
  - Основная: **F1‑score** (дефолт)
  - Дополнительная: **Precision** (важно для банка — минимизация ложных дефолтов)
- **Статистический тест**: z-test для пропорций, доверительный интервал 95%.
- **Критерий успеха**: p‑value < 0.05 и метрика(v2) > метрика(v1).

### Результаты офлайн‑теста на тестовой выборке (6000 объектов, 20% данных)

| Версия | Модель                | F1    | Precision | Recall |
|--------|----------------------|-------|-----------|--------|
| v1     | RandomForest          | 0.5596| **0.7950**| 0.4296 |
| v2     | GradientBoosting      | 0.4636| 0.6579    | 0.3580 |

### Статистическая значимость (z-test для Precision)

| Параметр | v1 | v2 |
|----------|----|----|
| Precision | 0.7950 | 0.6579 |
| Количество положительных предсказаний | 717 | 722 |

**Результат z-test:**
- z-статистика = 5.83
- p-value < 0.000001

**Вывод:** Различия статистически значимы (p < 0.05).

---

## Архитектура и масштабирование (концепция)

### Монолит vs микросервисы

Выбран **монолитный подход**:
- Проще для старта и CI/CD.
- Для учебного проекта достаточен.
- При росте нагрузки предиктор можно вынести в отдельный сервис с очередью.

### Брокеры сообщений (RabbitMQ)

В гипотетическом масштабировании **RabbitMQ** решает:
- Асинхронный скоринг больших батчей.
- Retry логики при временных сбоях.
- Rate limiting и мониторинг очередей.

### Логирование и мониторинг

В коде (`API.py`) логируются **запрос и ответ в JSON**:
```json
{"user_id": 12345, "model_version": "v1", "endpoint": "/predict", "timestamp": "..."}
```
В production эти логи отправляются в **ELK‑стек** (Elasticsearch, Logstash, Kibana).

### ONNX‑ML (оптимизация модели)

Модель можно конвертировать в **ONNX**. Пример для RandomForest:
```python
import onnxmltools
onnx_model = onnxmltools.convert.convert_sklearn(model, "pipeline")
```
Выгода: ускорение инференса до 2–3 раз, кроссплатформенность.

### uWSGI + NGINX в production

- **uWSGI** — WSGI‑сервер с пулом процессов/тредов.
- **NGINX** — реверс‑прокси: отдача статики, балансировка, защита от DOS.
Связка убирает встроенный сервер Flask, делая систему промышленной.

---

## MLOps инструменты (концептуально)

- **DVC** — версионирование данных и пайплайнов (обучающая выборка → контроль качества).
- **MLflow** — эксперименты, метрики, регистрация моделей (история F1 по версиям).

---

## Бизнес‑метрики

1. **Ожидаемые финансовые потери от дефолтов**  
   `Loss = FN * L_default + FP * C_opportunity`  
   Улучшение модели напрямую снижает эту метрику.

2. **Доля одобренных заявок при фиксированном уровне риска**  
   Если модель точнее, можно безопасно одобрить больше клиентов.

---

## Структура репозитория

```
credit-card-ml-deployment/
├── app/API.py
├── src/predict_utils.py
├── models/
│   ├── rf_default_model.pkl      # v1
│   └── rf_default_model_v2.pkl   # v2
├── notebooks/
│   ├── RandomForestClassifier.ipynb
│   └── GradientBoostingClassifier.ipynb
├── docker/Dockerfile
├── tests/
│   ├── A_B_test_hight_risk.jpg
│   ├── Test_hight_risk.jpg
│   └── Test_low_risk.jpg
├── requirements.txt
└── README.md
```

---

## Docker‑образы (публичный registry)

Яндекс Container Registry (альтернатива Docker Hub):

```bash
cr.yandex/crpk4u2d1dcukcnbk0jv/credit-default-predictor:v1
cr.yandex/crpk4u2d1dcukcnbk0jv/credit-default-predictor:v2
```

---

## Воспроизводимость

- Все зависимости фиксированы в `requirements.txt`.
- `Dockerfile` собирает образ с моделью, кодом и портом 5000.
- Контейнер протестирован локально и в облачном registry.

---
