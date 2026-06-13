from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from models import db
from routes import bicycles_bp
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('bicycle-service')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    Swagger(app, template={
        "info": {
            "title": "VeloTrack Bicycle Service API",
            "version": "1.0.0",
            "description": "Bicycle fleet management service"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header"
            }
        }
    })

    app.register_blueprint(bicycles_bp)

    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'healthy', 'service': 'bicycle-service'}, 200

    with app.app_context():
        from sqlalchemy import inspect
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            if 'bicycles' not in existing_tables:
                db.create_all()
            logger.info("Bicycle Service started successfully")
        except Exception as e:
            logger.warning(f"DB init note: {e}")
            logger.info("Bicycle Service started successfully")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)

