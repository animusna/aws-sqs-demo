Demo to use **[Amazon Simple Query Service](https://aws.amazon.com/it/sqs/)** a.k.a. **Amazon SQS**  using **Python**.

## What do you need before to start?
- **AWS account**
  If you don't have one you can activate using [free-tier  plan](https://aws.amazon.com/it/free/?all-free-tier.sort-by=item.additionalFields.SortRank&all-free-tier.sort-order=asc&awsf.Free%20Tier%20Types=*all&awsf.Free%20Tier%20Categories=*all).
- [AWS CLI](https://aws.amazon.com/cli/) installed.
- **Python** basic knowledge level
- **Python 3** installed
- Access to a **bash** shell

## Scenario

The goal of this article is to implement a classic consumer/producer problem using a [FIFO queue](https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics)) where a *producer* sends one or more messages to a queue and a consumer receives these messages reading the same queue. We choose as queue model a FIFO queue to guarantee that the order of the receiving messages is the same of the order of the sending messages (pretending that this matters).

## What's Amazon SQS
From the [documentation](https://aws.amazon.com/documentation-overview/sqs/):

*Amazon Simple Queue Service (SQS) is a managed message queuing service that enables you to decouple and scale microservices, distributed systems, and serverless applications. SQS reduces the complexity of managing and operating message-oriented middleware. SQS is designed so that you can send, store, and receive messages between software components at any volume, without losing messages or requiring other services to be available.*

![AWS SQS](https://d2u3159clq64q4.cloudfront.net/sqsconsole-20220913172024551/assets/images/5e3f44ce52788a4fb8b8432e4441bf3f-SQS-diagram.svg)

## Setting up the environment

To permit to **AWS CLI** to access to the AWS cloud we need to configure it running the command *** aws configure ***

### Configure AWS Command Line Interface

```
am@animusna:~$aws configure
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: eu-west-1
Default output format [None]: json
```
In case you need to create the keys follow the [official guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-creds-create) 

### Creation of a FIFO queue

Let's create a FIFO queue:

```
am@animusna:~$aws sqs create-queue --queue-name test.fifo --attributes FifoQueue=true
{
    "QueueUrl": "https://eu-west-1.queue.amazonaws.com/123456789012/test.fifo"
}
```

The output report is in JSON format and it represents the URL of the query that will be used to address the queue.

## Let's code

The solution is composed by three Python files and one configuration file. 
To implement the demo we'll use:
- [boto3](https://aws.amazon.com/it/sdk-for-python/) the official AWS SDK for Python.
- [colorama](https://pypi.org/project/colorama/) module to highlight to prettify the outputs of the running threads making them more understandable.


### Implementing the consumer

In the **consumer.py** there is the class **Consumer** that implements the message reader of the queue. The consumer read one message at a time and after the reading remove it.

```
import boto3
from configparser import ConfigParser
import messageSqs
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class Consumer:
    def __init__(self, regionName, queueUrl,logger):
        self.regionName = regionName
        self.queueUrl = queueUrl
        self.logger=logger

    def receive_message(self,deleteAfterReceiveing):
        sqs_client = boto3.client("sqs", region_name=self.regionName)
        response = sqs_client.receive_message(
            QueueUrl=self.queueUrl,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=15,
        )

        messages=response.get("Messages", [])

        self.logger(f"Number of messages received: {len(messages)}")
        
        if len(messages)==0:
            return False

        for message in messages:
            m=messageSqs.MessageSqs(jsonStr=message["Body"])
            self.logger(f"\tMessage read from queue: Data:{m.data}\tTime Stamp:{m.ts}\t Id:{m.id}")
            if deleteAfterReceiveing:
                receipt_handle = message['ReceiptHandle']
                dlt_response=sqs_client.delete_message(QueueUrl=self.queueUrl,ReceiptHandle=receipt_handle)
                if dlt_response['ResponseMetadata']['HTTPStatusCode']==200:
                    self.logger("\tMessage deleted from queue.")
        return True
```

### Implementing the producer
In the **producer.py** there is the Producer class that implements the message sender of the queue. The producer create one message at a time and then send it to the queue.
```
import boto3
import uuid
from messageSqs import MessageSqsJSONEncoder
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class Producer:
    
    def __init__(self,regionName,queueUrl,logger):
        self.regionName = regionName
        self.queueUrl= queueUrl
        self.logger=logger

    def send_message(self,message):
        sqs_client = boto3.client("sqs", self.regionName)
        self.logger(f"Sending message with id {message.id}...")        
        response = sqs_client.send_message(
            QueueUrl=self.queueUrl,
            MessageBody=MessageSqsJSONEncoder().encode(message),
            MessageGroupId="test",
            MessageDeduplicationId=f"DeduplicationId-{uuid.uuid4()}"
        )
        self.logger(f"SQS Response: Status:{response['ResponseMetadata']['HTTPStatusCode']}\tSQS Message Id:{response['MessageId']}")        
```

### Implementing the scenario
In the module **sqs-demo.py** we run in different concurrent threads the producer and consumer where the producer send a message each half second and the consumer try to read a message each half second.

```
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
messageToSent = int(demo_conf["PRODUCER_MESSAGES_TO_SENT"])
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

    messageIndex=0
    producer=Producer(aws_conf["REGION"], aws_conf["QUEUE_URL"], logger)
    while (messageIndex < messageToSent):
        m=MessageSqs(
            jsonStr = f"{{\"data\":\"mydata{messageIndex}\",\"ts\":\"{datetime.now().isoformat()}\",\"id\":\"{uuid.uuid4()}\" }}")
        producer.send_message(m)
        messageIndex += 1
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

```

### The configuration file

In the file **config.ini** there is the configuration of the demo:

```
[AWS]
REGION = eu-west-1
QUEUE_URL = https://eu-west-1.queue.amazonaws.com/123456789012/test.fifo
[DEMO] 
#Total messages sent by producer
PRODUCER_MESSAGES_TO_SENT = 100
#Delay in seconds before to start the producer
PRODUCER_START_DELAY_IN_SECONDS=0.5
#If the consumer checks the queue is empty it exits after this number of attempts.
CONSUMER_EXIT_IF_QUEUE_IS_EMPTY_AFTER_ATTEMPTS = 10     
#Delay in seconds before to start teh consumer
CONSUMER_START_DELAY_IN_SECONDS=2
```
### Output of the demo

Following some screenshots of the demo in action:

![Starting Output ](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/80dkl9wayow3yh7lqjoe.png)

![Middle Output](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/gj12qy6w5l5oqu6guqtz.png)

![Final output](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/wch1ssed1cce8aephxgm.png)
