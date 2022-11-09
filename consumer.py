import boto3
from configparser import ConfigParser
import messageSqs
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class Consumer:
    def __init__(self, region_name, queue_url,logger):
        self.region_name = region_name
        self.queue_url = queue_url
        self.logger=logger

    def receive_message(self,deleteAfterReceiveing):
        sqs_client = boto3.client("sqs", region_name=self.region_name)
        response = sqs_client.receive_message(
            QueueUrl=self.queue_url,
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
                dlt_response=sqs_client.delete_message(QueueUrl=self.queue_url,ReceiptHandle=receipt_handle)
                if dlt_response['ResponseMetadata']['HTTPStatusCode']==200:
                    self.logger("\tMessage deleted from queue.")
        return True