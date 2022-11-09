import json

class MessageSqs(object):

    def __init__(self,data=None,ts=None,id=None, jsonStr=None):
        if isinstance(jsonStr,str):
            self.__dict__ = json.loads(jsonStr)
        else:               
            self.data = data
            self.ts = ts 
            self.id = id

class MessageSqsJSONEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__