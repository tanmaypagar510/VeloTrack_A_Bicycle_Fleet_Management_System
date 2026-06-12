import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://velotrack:velotrack_secret@localhost:5432/velotrack')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.environ.get('JWT_SECRET', 'supersecretjwtkey123')
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    BICYCLE_SERVICE_URL = os.environ.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')
    PORT = int(os.environ.get('PORT', 5003))

