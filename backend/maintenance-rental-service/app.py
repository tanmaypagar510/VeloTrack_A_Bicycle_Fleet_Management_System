from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from models import db
from routes import maintenance_bp, rentals_bp
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('maintenance-rental-service')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    Swagger(app, template={
        "info": {
            "title": "VeloTrack Maintenance & Rental Service API",
            "version": "1.0.0",
            "description": "Maintenance logs and rental management"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header"
            }
        }
    })

    app.register_blueprint(maintenance_bp)
    app.register_blueprint(rentals_bp)

    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'healthy', 'service': 'maintenance-rental-service'}, 200

    with app.app_context():
        from sqlalchemy import inspect, text
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            if 'maintenance_logs' not in existing_tables:
                db.create_all()
            else:
                # Auto-add missing columns to existing tables
                rentals_columns = [col['name'] for col in inspector.get_columns('rentals')] if 'rentals' in existing_tables else []
                with db.engine.connect() as conn:
                    if 'rate_per_hour' not in rentals_columns:
                        conn.execute(text("ALTER TABLE rentals ADD COLUMN rate_per_hour FLOAT DEFAULT 50.0"))
                        conn.commit()
                        logger.info("Added column rate_per_hour to rentals table")
                    if 'rental_cost' not in rentals_columns:
                        conn.execute(text("ALTER TABLE rentals ADD COLUMN rental_cost FLOAT"))
                        conn.commit()
                        logger.info("Added column rental_cost to rentals table")
            logger.info("Maintenance & Rental Service started successfully")
        except Exception as e:
            logger.warning(f"DB init note: {e}")
            logger.info("Maintenance & Rental Service started successfully")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)

