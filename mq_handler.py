"""
This module integrates RabbitMQ using the pika library to handle messaging between task producers and consumers.
It provides functions to send messages to a queue and consume messages from it. The module is designed to work with the scraping logic and MongoDB storage.
It also includes error handling and logging for better traceability.
"""


import pika
import json
from config import RABBITMQ_URL

def send_message(queue, message):
    """Send a message (dict) to the specified RabbitMQ queue."""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        )
    )
    connection.close()

def start_consuming(queue, callback):
    """Start consuming messages from the specified queue with the given callback."""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue, on_message_callback=callback)
    channel.start_consuming()
