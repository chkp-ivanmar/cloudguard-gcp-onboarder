import base64
import json


def decode_key(key):
    key_bytes = key.encode('utf-8')    
    key_64_bytes = base64.b64decode(key_bytes)
    return json.loads(key_64_bytes.decode('utf-8'))