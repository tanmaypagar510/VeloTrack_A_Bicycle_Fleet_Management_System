import pika
import json
import logging
import os

logger = logging.getLogger('events-publisher')

RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')


def publish_event(exchange, routing_key, message):
    """Publish an event to RabbitMQ"""
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)

        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        connection.close()
        logger.info(f"Published event: {routing_key} -> {message}")
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")


def publish_maintenance_event(bicycle_id, log_id):
    publish_event(
        exchange='velotrack_events',
        routing_key='maintenance.created',
        message={'bicycle_id': bicycle_id, 'log_id': log_id, 'event': 'maintenance_created'}
    )


def publish_rental_checkout_event(bicycle_id, rental_id):
    publish_event(
        exchange='velotrack_events',
        routing_key='rental.checkout',
        message={'bicycle_id': bicycle_id, 'rental_id': rental_id, 'event': 'rental_checkout'}
    )


def publish_rental_return_event(bicycle_id, rental_id, duration_hours, is_anomalous):
    publish_event(
        exchange='velotrack_events',
        routing_key='rental.returned',
        message={
            'bicycle_id': bicycle_id,
            'rental_id': rental_id,
            'duration_hours': duration_hours,
            'is_anomalous': is_anomalous,
            'event': 'rental_returned'
        }
    )

