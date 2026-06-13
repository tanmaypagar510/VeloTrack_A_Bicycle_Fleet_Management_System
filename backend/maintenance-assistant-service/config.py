import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://velotrack:velotrack_secret@localhost:5432/velotrack')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.environ.get('JWT_SECRET', 'supersecretjwtkey123')
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'tinyllama')
    MAINTENANCE_RENTAL_SERVICE_URL = os.environ.get('MAINTENANCE_RENTAL_SERVICE_URL', 'http://localhost:5003')
    BICYCLE_SERVICE_URL = os.environ.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')
    FAISS_INDEX_PATH = os.environ.get('FAISS_INDEX_PATH', '/app/data/faiss_index')
    MODEL_PATH = os.environ.get('MODEL_PATH', '/app/data/models/risk_model.xgb')
    PORT = int(os.environ.get('PORT', 5004))

