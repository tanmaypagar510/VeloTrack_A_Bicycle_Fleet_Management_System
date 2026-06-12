from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from models import db
from routes import assistant_bp, risk_bp
from config import Config
from llm_client import OllamaClient
from vector_store import VectorStore
from rag_pipeline import RAGPipeline
from risk_scorer import RiskScorer
from event_consumer import EventConsumer
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('maintenance-assistant-service')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    Swagger(app, template={
        "info": {
            "title": "VeloTrack Maintenance Assistant Service API",
            "version": "1.0.0",
            "description": "RAG-powered maintenance assistant and ML risk scoring"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header"
            }
        }
    })

    # Initialize components
    llm_client = OllamaClient(base_url=Config.OLLAMA_URL, model=Config.OLLAMA_MODEL)
    vector_store = VectorStore(index_path=Config.FAISS_INDEX_PATH)
    rag_pipeline = RAGPipeline(vector_store=vector_store, llm_client=llm_client)
    risk_scorer = RiskScorer(model_path=Config.MODEL_PATH)

    # Store in app config for access in routes
    app.config['RAG_PIPELINE'] = rag_pipeline
    app.config['RISK_SCORER'] = risk_scorer

    app.register_blueprint(assistant_bp)
    app.register_blueprint(risk_bp)

    @app.route('/health', methods=['GET'])
    def health():
        return {
            'status': 'healthy',
            'service': 'maintenance-assistant-service',
            'ollama_available': llm_client.is_available()
        }, 200

    with app.app_context():
        from sqlalchemy import inspect
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            if 'risk_scores' not in existing_tables:
                db.create_all()
        except Exception as e:
            logger.warning(f"DB init note: {e}")

        # Start event consumer in background
        try:
            consumer = EventConsumer(app, rag_pipeline, risk_scorer)
            consumer.start()
        except Exception as e:
            logger.warning(f"Event consumer failed to start: {e}")

        logger.info("Maintenance Assistant Service started successfully")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)

