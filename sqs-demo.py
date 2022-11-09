from colorama import Fore
from configparser import ConfigParser
from consumer import Consumer
from datetime import datetime
from messageSqs import MessageSqs
from producer import Producer
import time
import threading
import uuid

config_object = ConfigParser()
config_object.read("config.ini")
aws_conf = config_object["AWS"]
demo_conf = config_object["DEMO"]
message_to_sent = int(demo_conf["PRODUCER_MESSAGES_TO_SENT"])
max_attempts_if_queue_is_empty = int(
    demo_conf["CONSUMER_EXIT_IF_QUEUE_IS_EMPTY_AFTER_ATTEMPTS"])
consumer_start_delay = float(demo_conf["CONSUMER_START_DELAY_IN_SECONDS"])
producer_start_delay = float(demo_conf["PRODUCER_START_DELAY_IN_SECONDS"])


def log(task_name, text, textColor):
    print(textColor + f"{task_name}:{text}" + Fore.WHITE)

def produce_task(task_name="producer"):
    logger=lambda text: log(task_name, text, Fore.YELLOW)
    logger("Running ...")
    time.sleep(producer_start_delay)

    message_index=0
    producer=Producer(aws_conf["REGION"], aws_conf["QUEUE_URL"], logger)
    while (message_index < message_to_sent):
        m=MessageSqs(
            jsonStr = f"{{\"data\":\"mydata{message_index}\",\"ts\":\"{datetime.now().isoformat()}\",\"id\":\"{uuid.uuid4()}\" }}")
        producer.send_message(m)
        message_index += 1
        time.sleep(0.5)
    logger("Terminated!")


def consume_task(task_name = "consumer"):
    logger=lambda text: log(task_name, text, Fore.GREEN)
    receiver = Consumer(aws_conf["REGION"],
                        aws_conf["QUEUE_URL"], logger)
    logger("Running...")
    time.sleep(consumer_start_delay)
    attempts = 0
    while (attempts < max_attempts_if_queue_is_empty):
        if not receiver.receive_message(True):
            attempts += 1
        time.sleep(0.5)

print(Fore.WHITE + '\nStarting demo AWS SQS..\n')

if __name__ == "__main__":
    tasks = []
    tasks.append(threading.Thread(target=produce_task, args=("Producer-SQS",)))
    tasks.append(threading.Thread(target=consume_task, args=("Consumer-SQS",)))

    for t in tasks:
        t.start()

    for t in tasks:
        t.join()

    print(Fore.WHITE + "\n\nAWS SQS Demo terminated!\n\n")
