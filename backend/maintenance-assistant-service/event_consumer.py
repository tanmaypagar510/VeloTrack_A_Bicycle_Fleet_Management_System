import pika
import json
import threading
import logging
import requests
import os
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

logger = logging.getLogger('event-consumer')


def _create_service_token(secret):
    """Create a JWT token for internal service-to-service calls"""
    payload = {
        'user_id': 0,
        'email': 'service@velotrack.internal',
        'role': 'admin',
        'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        'iat': datetime.now(timezone.utc)
    }
    return pyjwt.encode(payload, secret, algorithm='HS256')


class EventConsumer:
    """Consumes RabbitMQ events to trigger risk score recalculation and vector indexing"""

    def __init__(self, app, rag_pipeline, risk_scorer):
        self.app = app
        self.rag_pipeline = rag_pipeline
        self.risk_scorer = risk_scorer
        self.rabbitmq_url = app.config.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')

    def start(self):
        """Start consuming events in a background thread"""
        thread = threading.Thread(target=self._consume, daemon=True)
        thread.start()
        logger.info("Event consumer started")

    def _consume(self):
        """Connect and consume events"""
        try:
            params = pika.URLParameters(self.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(exchange='velotrack_events', exchange_type='topic', durable=True)

            # Create queue for this service
            result = channel.queue_declare(queue='assistant_events', durable=True)
            queue_name = result.method.queue

            # Bind to all relevant events
            channel.queue_bind(exchange='velotrack_events', queue=queue_name, routing_key='maintenance.*')
            channel.queue_bind(exchange='velotrack_events', queue=queue_name, routing_key='rental.*')

            channel.basic_consume(queue=queue_name, on_message_callback=self._on_message, auto_ack=True)

            logger.info("Listening for events on velotrack_events exchange")
            channel.start_consuming()

        except Exception as e:
            logger.error(f"Event consumer failed: {e}")
            # Retry after delay
            import time
            time.sleep(10)
            self._consume()

    def _on_message(self, channel, method, properties, body):
        """Handle incoming events"""
        try:
            event = json.loads(body)
            event_type = event.get('event', '')
            bicycle_id = event.get('bicycle_id')

            logger.info(f"Received event: {event_type} for bike #{bicycle_id}")

            if bicycle_id:
                with self.app.app_context():
                    self._update_bike_data(bicycle_id)

        except Exception as e:
            logger.error(f"Failed to process event: {e}")

    def _update_bike_data(self, bicycle_id):
        """Re-index bike history and recalculate risk score"""
        from models import db, RiskScore, RiskScoreHistory
        from datetime import datetime, timezone

        base_url = self.app.config.get('MAINTENANCE_RENTAL_SERVICE_URL', 'http://localhost:5003')
        bike_url = self.app.config.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')

        try:
            # Generate a service-to-service auth token for internal API calls
            token = _create_service_token(self.app.config.get('JWT_SECRET', ''))
            headers = {'Authorization': f'Bearer {token}'}

            history_resp = requests.get(f"{base_url}/api/maintenance/history/{bicycle_id}", headers=headers, timeout=10)
            bike_resp = requests.get(f"{bike_url}/api/bicycles/{bicycle_id}", headers=headers, timeout=10)

            if history_resp.status_code == 200 and bike_resp.status_code == 200:
                history = history_resp.json()
                bike = bike_resp.json().get('bicycle', {})

                # Re-index in vector store
                self.rag_pipeline.index_bike_history(
                    bicycle_id,
                    history.get('maintenance_logs', []),
                    history.get('rentals', [])
                )

                # Recalculate risk score
                score_val, level, features = self.risk_scorer.compute_score(
                    bike,
                    history.get('maintenance_logs', []),
                    history.get('rentals', [])
                )

                # Update database
                existing = RiskScore.query.filter_by(bicycle_id=bicycle_id).first()
                if existing:
                    existing.score = score_val
                    existing.risk_level = level
                    existing.feature_importance = features
                    existing.computed_at = datetime.now(timezone.utc)
                else:
                    existing = RiskScore(
                        bicycle_id=bicycle_id, score=score_val,
                        risk_level=level, feature_importance=features
                    )
                    db.session.add(existing)

                db.session.add(RiskScoreHistory(bicycle_id=bicycle_id, score=score_val))
                db.session.commit()

                logger.info(f"Updated risk score for bike #{bicycle_id}: {score_val} ({level})")

        except Exception as e:
            logger.error(f"Failed to update bike data: {e}")

