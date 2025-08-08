import base64

from .composite import BaseComposite
from .protobuf import Map, List, Unknown, Yaml, Json
B64Encode = lambda s: base64.b64encode(s.encode('utf-8')).decode('utf-8')
B64Decode = lambda s: base64.b64decode(s.encode('utf-8')).decode('utf-8')

__all__ = [
    'BaseComposite',
    'Map',
    'List',
    'Unknown',
    'Yaml',
    'Json',
    'B64Encode',
    'B64Decode',
]
