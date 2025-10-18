import joblib
import os
import logging


class ClassifierService:
    def __init__(self, model_path: str = "app/models/classifier.joblib"):
        logging.info(f"Загрузка модели классификатора из: {model_path}")
        if not os.path.exists(model_path):
            logging.error(f"Файл модели не найден по пути: {model_path}")
            raise FileNotFoundError(f"Model file not found at {model_path}")

        self.pipeline = joblib.load(model_path)
        logging.info("Модель классификатора успешно загружена.")

    def predict(self, text: str) -> str:
        prediction = self.pipeline.predict([text])
        return prediction[0]
