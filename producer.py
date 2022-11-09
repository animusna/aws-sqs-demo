import boto3
import uuid
from messageSqs import MessageSqsJSONEncoder
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class Producer:
    
    def __init__(self,region_name,queue_url,logger):
        self.region_name = region_name
        self.queue_url= queue_url
        self.logger=logger

    def send_message(self,message):
        sqs_client = boto3.client("sqs", self.region_name)
        self.logger(f"Sending message with id {message.id}...")        
        response = sqs_client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=MessageSqsJSONEncoder().encode(message),
            MessageGroupId="test",
            MessageDeduplicationId=f"DeduplicationId-{uuid.uuid4()}"
        )
        self.logger(f"SQS Response: Status:{response['ResponseMetadata']['HTTPStatusCode']}\tSQS Message Id:{response['MessageId']}")        