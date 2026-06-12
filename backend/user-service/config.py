import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://velotrack:velotrack_secret@localhost:5432/velotrack')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.environ.get('JWT_SECRET', 'supersecretjwtkey123')
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))
    PORT = int(os.environ.get('PORT', 5001))

