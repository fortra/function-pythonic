##################################################################################
#
# Pythonic class wrappers around protobuf classes that enables traversing
# and modifying the protobuf message structure much like one can in JavaScript.
# For example, to get a region value from the composite's spec:
#
#   region = request.observed.composite.resource.spec.region
#
# If any item in the path to the field does not exist, None is returned.
# To set a field in the composite status:
#
#   response.desired.composite.resource.status.homepage.url = 'https://for.example.com'
#
# Here all items in the path to the field that do not exist will be created.
#
##################################################################################

import datetime
import google.protobuf.struct_pb2
import json
import yaml


def Map(**kwargs):
    values = Values(None, None, google.protobuf.struct_pb2.Struct(), Values.Type.MAP)
    for key, value in kwargs.items():
        values[key] = value
    return values

def List(*args):
    values = Values(None, None, google.protobuf.struct_pb2.ListValue(), Values.Type.LIST)
    for ix, value in enumerate(args):
        values[ix] = value
    return values

def Yaml(string, readOnly=None):
    return _Object(yaml.safe_load(string), readOnly)

def Json(string, readOnly=None):
    return _Object(json.loads(string), readOnly)

def _Object(object, readOnly=None):
    if isinstance(object, dict):
        values = google.protobuf.struct_pb2.Struct()
        if len(object):
            values.update(object)
        return Values(None, None, values, Values.Type.MAP, readOnly)
    if isinstance(object, (list, tuple)):
        values = google.protobuf.struct_pb2.ListValue()
        if len(object):
            values.extend(object)
        return Values(None, None, values, Values.Type.LIST, readOnly)
    return object


class Message:
    def __init__(self, parent, key, descriptor, message, readOnly=False):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_descriptor'] = descriptor
        self.__dict__['_message'] = message
        self.__dict__['_readOnly'] = readOnly
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        field = self._descriptor.fields_by_name.get(key)
        if not field:
            raise AttributeError(obj=self, name=key)
        if self._message:
            value = getattr(self._message, key)
        else:
            value = None
        if value is None and field.has_default_value:
            value = field.default_value
        if field.type == field.TYPE_MESSAGE:
            if field.message_type.name == 'Struct':
                value = Values(self, key, value, Values.Type.MAP, self._readOnly)
            elif field.message_type.name == 'ListValue':
                value = Values(self, key, value, Values.Type.LIST, self._readOnly)
            elif field.label == field.LABEL_REPEATED:
                if field.message_type.GetOptions().map_entry:
                    value = MapMessage(self, key, field.message_type, value, self._readOnly)
                else:
                    value = RepeatedMessage(self, key, field.message_type, value, self._readOnly)
            else:
                value = Message(self, key, field.message_type, value, self._readOnly)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._message != None

    def __len__(self):
        return len(self._descriptor.fields)

    def __contains__(self, key):
        return key in self._descriptor.fields_by_name

    def __iter__(self):
        for key in self._descriptor.fields_by_name:
            yield key, self[key]

    def __hash__(self):
        if self._message:
            return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
        return 0

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._message is None:
            return other._message is None
        elif other._message is None:
            return False
        if len(self) != len(other):
            return False
        for key, value in self:
            if key not in other:
                return False
            if value != other[key]:
                return False
        return True

    def __str__(self):
        return format(self)

    def __format__(self, spec='yaml'):
        return _formatObject(self, spec)

    @property
    def _fullName(self):
        if self._key is not None:
            if self._parent is not None:
                parent = self._parent._fullName
                if parent:
                    return f"{parent}.{self._key}"
            return self._key
        return ''

    def _create_child(self, key, type=None):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        return getattr(self._message, key)

    def __call__(self, **kwargs):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        self._message.Clear()
        self._cache.clear()
        for key, value in kwargs.items():
            self[key] = value
        return self

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if key not in self._descriptor.fields_by_name:
            raise AttributeError(obj=self, name=key)
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        if isinstance(value, Message):
            value = value._message
        elif isinstance(value, (MapMessage, RepeatedMessage)):
            value = value._messages
        elif isinstance(value, Values):
            value = value._values
        setattr(self._message, key, value)
        self._cache.pop(key, None)

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if key not in self._descriptor.fields_by_name:
            raise AttributeError(obj=self, name=key)
        if self._message is not None:
            del self._message[key]
            self._cache.pop(key, None)


class MapMessage:
    def __init__(self, parent, key, descriptor, messages, readOnly=False):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_field'] = descriptor.fields_by_name['value']
        self.__dict__['_messages'] = messages
        self.__dict__['_readOnly'] = readOnly
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if self._messages is None or key not in self._messages:
            value = None
        else:
            value = self._messages[key]
        if value is None and self._field.has_default_value:
            value = self._field.default_value
        if self._field.type == self._field.TYPE_MESSAGE:
            if self._field.message_type.name == 'Struct':
                value = Values(self, key, value, Values.Type.MAP, self._readOnly)
            elif self._field.message_type.name == 'ListValue':
                value = Values(self, key, value, Values.Type.LIST, self._readOnly)
            elif self._field.label == self._field.LABEL_REPEATED:
                if self._field.message_type.GetOptions().map_entry:
                    value = MapMessage(self, key, self._field.message_type, value, self._readOnly)
                else:
                    value = RepeatedMessage(self, key, self._field.message_type, value, self._readOnly)
            else:
                value = Message(self, key, self._field.message_type, value, self._readOnly)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._messages != None

    def __len__(self):
        return 0 if self._messages is None else len(self._messages)

    def __contains__(self, key):
        return self._messages is not None and key in self._messages

    def __iter__(self):
        if self._messages is not None:
            for key in self._messages:
                yield key, self[key]

    def __hash__(self):
        if self._nessages is not None:
            return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
        return 0

    def __eq__(self, other):
        if not isinstance(other, MapMessage):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._messages is None:
            return other._messages is None
        elif other._messages is None:
            return False
        if len(self) != len(other):
            return False
        for key, value in self:
            if key not in other:
                return False
            if value != other[key]:
                return False
        return True

    def __str__(self):
        return format(self)

    def __format__(self, spec='yaml'):
        return _formatObject(self, spec)

    @property
    def _fullName(self):
        if self._key is not None:
            if self._parent is not None:
                parent = self._parent._fullName
                if parent:
                    return f"{parent}.{self._key}"
            return self._key
        return ''

    def _create_child(self, key, type=None):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        return self._messages[key]

    def __call__(self, **kwargs):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        self._messages.clear()
        self._cache.clear()
        for key, value in kwargs.items():
            self[key] = value
        return self

    def __setattr__(self, key, message):
        self[key] = message

    def __setitem__(self, key, message):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        if isinstance(message, Message):
            message = message._message
        if isinstance(message, str) and self._field.type == self._field.TYPE_BYTES:
            message = message.encode()
        self._messages[key] = message
        self._cache.pop(key, None)

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is not None:
            if key in self._messages:
                del self._messages[key]
            self._cache.pop(key, None)


class RepeatedMessage:
    def __init__(self, parent, key, descriptor, messages, readOnly=False):
        self._parent = parent
        self._key = key
        self._descriptor = descriptor
        self._messages = messages
        self._readOnly = readOnly
        self._cache = {}

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if self._messages is None or key >= len(self._messages):
            message = None
        else:
            message = self._messages[key]
        value = Message(self._parent, key, self._descriptor, message, self._readOnly)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._messages != None

    def __len__(self):
        return 0 if self._messages is None else len(self._messages)

    def __contains__(self, value):
        if self._messages is not None:
            for message in self:
                if value == message:
                    return True
        return False

    def __iter__(self):
        if self._messages is not None:
            for ix in range(len(self._messages)):
                yield self[ix]

    def __hash__(self):
        if self._messages is not None:
            return hash(tuple(hash(item) for item in self))
        return 0

    def __eq__(self, other):
        if not isinstance(other, RepeatedMessage):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._messages is None:
            return other._messages is None
        elif other._messages is None:
            return False
        if len(self) != len(other):
            return False
        for ix, value in enumerate(self):
            if value != other[ix]:
                return False
        return True

    def __str__(self):
        return format(self)

    def __format__(self, spec='yaml'):
        return _formatObject(self, spec)

    @property
    def _fullName(self):
        if self._key is not None:
            if self._parent is not None:
                parent = self._parent._fullName
                if parent:
                    return f"{parent}.{self._key}"
            return self._key
        return ''

    def _create_child(self, key, type=None):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        while key >= len(self._messages):
            self._messages.add()
        return self._messages[key]

    def __call__(self, *args):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        self._messages.Clear()
        self._cache.clear()
        for arg in args:
            self.append(arg)
        return self

    def __setitem__(self, key, message):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        while key >= len(self._messages):
            self._messages.add()
        if isinstance(message, Message):
            message = message._message
        self._messages[key] = message
        self._cache.pop(key, None)

    def __delitem__(self, key):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._values is not None:
            del self._values[key]
            self._cache.pop(key, None)

    def append(self, message=None):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        if message is None:
            message = self._messages.add()
        else:
            message = self._messages.append(message)
        return self[len(self._messages) - 1]


class ProtobufValue:
    @property
    def _protobuf_value(self):
        return None


class Values:
    class Type:
        UNKNOWN = 0
        MAP = 1
        LIST = 2

    def __init__(self, parent, key, values, type, readOnly=None):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_values'] = values
        self.__dict__['_type'] = type
        self.__dict__['_readOnly'] = readOnly
        self.__dict__['_unknowns'] = set()
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if key in self._unknowns:
            value = Values(self, key, None, self.Type.UNKNOWN, self._readOnly)
            self._cache[key] = value
            return value
        if isinstance(key, str):
            if not self._isMap:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None or key not in self._values:
                struct_value = None
            else:
                struct_value = self._values.fields[key]
        elif isinstance(key, int):
            if not self._isList:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None or key >= len(self._values):
                struct_value = None
            else:
                struct_value = self._values.values[key]
        else:
            raise ValueError('Unexpected key type')
        if struct_value is None:
            value = Values(self, key, None, self.Type.UNKNOWN, self._readOnly)
        else:
            kind = struct_value.WhichOneof('kind')
            if kind is None:
                value = Values(self, key, None, self.Type.UNKNOWN, self._readOnly)
            elif kind == 'struct_value':
                value = Values(self, key, struct_value.struct_value, self.Type.MAP, self._readOnly)
            elif kind == 'list_value':
                value = Values(self, key, struct_value.list_value, self.Type.LIST, self._readOnly)
            elif kind == 'string_value':
                value = struct_value.string_value
            elif kind == 'number_value':
                value = struct_value.number_value
                if value.is_integer():
                    value = int(value)
            elif kind == 'bool_value':
                value = struct_value.bool_value
            elif kind == 'null_value':
                value = None
            else:
                raise ValueError(f"Unexpected value kind: {kind}")
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._values != None

    def __len__(self):
        return 0 if self._values is None else len(self._values) + len(self._unknowns)

    def __contains__(self, item):
        if self._values is not None:
            if self._isMap:
                return item in self._values or item in self._unknowns
            if self._isList:
                for value in self:
                    if item == value:
                        return True
                if isinstance(item, Values) and item._isUnknown:
                    return bool(self._unknowns)
        return False

    def __iter__(self):
        if self._values is not None:
            if self._isMap:
                for key in self._values:
                    yield key, self[key]
                for key in self._unknowns:
                    yield key, self[key]
            elif self._isList:
                for ix in range(len(self._values)):
                    yield self[ix]
                for ix in sorted(self._unknowns):
                    if ix >= len(self._values):
                        yield self[ix]

    def __hash__(self):
        if self._values is not None:
            if self._isMap:
                return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
            if self._isList:
                return hash(tuple(hash(item) for item in self))
        return self._type

    def __eq__(self, other):
        if not isinstance(other, Values):
            return False
        if self._type != other._type:
            return False
        if self._values is None:
            return other._values is None
        elif other._values is None:
            return False
        if len(self) != len(other):
            return False
        if self._isMap:
            for key, value in self:
                if key not in other:
                    return False
                if value != other[key]:
                    return False
        if self._isList:
            for ix, value in enumerate(self):
                if value != other[ix]:
                    return False
        return True

    def __str__(self):
        return format(self)

    def __format__(self, spec='yaml'):
        return _formatObject(self, spec)

    @property
    def _fullName(self):
        if self._key is not None:
            if self._parent is not None:
                parent = self._parent._fullName
                if parent:
                    return f"{parent}.{self._key}"
            return str(self._key)
        return ''

    def _create_child(self, key, type):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if isinstance(key, str):
            if not self._isMap:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            struct_value = self._values.fields[key]
        elif isinstance(key, int):
            if not self._isList:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            while key >= len(self._values.values):
                self._values.values.add()
            struct_value = self._values.values[key]
        else:
            raise ValueError('Unexpected key type')
        if type == self.Type.MAP:
            if not struct_value.HasField('struct_value'):
                struct_value.struct_value.Clear()
            return struct_value.struct_value
        if type == self.Type.LIST:
            if not struct_value.HasField('list_value'):
                struct_value.list_value.Clear()
            return struct_value.list_value
        raise ValueError(f"Unexpected type: {type}")

    def __call__(self, *args, **kwargs):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        self._cache.clear()
        self._unknowns.clear()
        if len(kwargs):
            if not self._isMap:
                if not self._isUnknown:
                    raise ValueError('Cannot specify kwargs on lists')
                self.__dict__['_type'] = self.Type.MAP
            if len(args):
                raise ValueError('Connect specify args on maps')
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
            for key, value in kwargs.items():
                self[key] = value
        elif len(args):
            if not self._isList:
                if not self._isUnknown:
                    raise ValueError('Cannot specify args on maps')
                self.__dict__['_type'] = self.Type.LIST
            if len(kwargs):
                raise ValueError('Connect specify kwargs on lists')
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
            for key in range(len(args)):
                self[key] = args[key]
        else:
            if not self._isMap:
                if not self._isUnknown:
                    self.__dict__['_type'] = self.Type.MAP # Assume a map is wanted
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
        return self

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if isinstance(key, str):
            if not self._isMap:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            values = self._values.fields
        elif isinstance(key, int):
            if not self._isList:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            values = self._values.values
            while key >= len(values):
                values.add()
        else:
            raise ValueError('Unexpected key type')
        self._cache.pop(key, None)
        self._unknowns.discard(key)
        if isinstance(value, ProtobufValue):
            value = value._protobuf_value
        if value is None:
            values[key].null_value = 0
        elif isinstance(value, bool): # Must be before int check
            values[key].bool_value = value
        elif isinstance(value, str):
            values[key].string_value = value
        elif isinstance(value, (int, float)):
            values[key].number_value = value
        elif isinstance(value, dict):
            values[key].struct_value.Clear()
            sv = self[key]
            for k, v in value.items():
                sv[k] = v
        elif isinstance(value, (list, tuple)):
            values[key].list_value.Clear()
            sv = self[key]
            for k, v in enumerate(value):
                sv[k] = v
        elif isinstance(value, Values):
            if value._isMap:
                values[key].struct_value.Clear()
                sv = self[key]
                for k, v in value:
                    sv[k] = v
            elif value._isList:
                values[key].list_value.Clear()
                sv = self[key]
                for k, v in enumerate(value):
                    sv[k] = v
            else:
                self._unknowns.add(key)
                if self._isMap:
                    if key in values:
                        del values[key]
                elif self._isList:
                    if key < len(values):
                        values[key].Clear()
                    for ix in reversed(range(len(values))):
                        if ix not in self._unknowns:
                            break
                        del values[ix]
        else:
            raise ValueError('Unexpected type')

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._readOnly:
            raise ValueError(f"{self._readOnly} is read only")
        if isinstance(key, str):
            if not self._isMap:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is not None:
                if key in self._values:
                    del self._values[key]
                self._cache.pop(key, None)
                self._unknowns.discard(key)
        elif isinstance(key, int):
            if not self._isList:
                if not self._isUnknown:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is not None:
                if key < len(self._values):
                    del self._values[key]
                self._cache.pop(key, None)
                self._unknowns.discard(key)
                for ix in sorted([ix in self._unknowns]):
                    if ix > key:
                        self._cache.pop(ix, None)
                        self._unknowns.add(ix - 1)
                        self._unknowns.disacard(ix)
                for ix in reversed(range(len(self._values))):
                    if ix not in self._unknowns:
                        break
                    del self._values[ix]
        else:
            raise ValueError('Unexpected key type')

    @property
    def _isUnknown(self):
        return self._type == self.Type.UNKNOWN

    @property
    def _isMap(self):
        return self._type == self.Type.MAP

    @property
    def _isList(self):
        return self._type == self.Type.LIST

    @property
    def _hasUnknowns(self):
        if self._unknowns:
            return True
        if self._isMap:
            for key, value in self:
                if isinstance(value, Values) and value._hasUnknowns:
                    return True
        elif self._isList:
            for value in self:
                if isinstance(value, Values) and value._hasUnknowns:
                    return True
        return False

    def _patchUnknowns(self, patches):
        for key in [key for key in self._unknowns]:
            self[key] = patches[key]
        if self._isMap:
            for key, value in self:
                if isinstance(value, Values) and len(value):
                    patch = patches[key]
                    if isinstance(patch, Values) and patch._type == value._type and len(patch):
                        value._patchUnknowns(patch)
        elif self._isList:
            for ix, value in enumerate(self):
                if isinstance(value, Values) and len(value):
                    patch = patches[ix]
                    if isinstance(patch, Values) and patch._type == value._type and len(patch):
                        value._patchUnknowns(patch)


def _formatObject(object, spec):
    if spec == 'json':
        return json.dumps(object, indent=2, cls=_JSONEncoder)
    if spec == 'jsonc':
        return json.dumps(object, separators=(',', ':'), cls=_JSONEncoder)
    if spec == 'protobuf':
        if isinstance(object, Message):
            return str(object._message)
        if isinstance(object, (MapMessage, RepeatedMessage)):
            return str(object._messages)
        if isinstance(object, Values):
            return str(object._values)
        return format(object)
    return yaml.dump(object, Dumper=_Dumper)


class _JSONEncoder(json.JSONEncoder):
    def default(self, object):
        if isinstance(object, (Message, MapMessage)):
            if object:
                return {key: value for key, value in object}
            return None
        if isinstance(object, RepeatedMessage):
            if object:
                return [value for value in object]
            return None
        if isinstance(object, Values):
            if object._isMap:
                return {key: value for key, value in object}
            if object._isList:
                return [value for value in object]
            if object._isUnknown:
                return '<<UNKNOWN>>'
            return '<<UNEXPECTED>>'
        if isinstance(object, datetime.datetime):
            return object.isoformat()
        return super(JSONEncoder, self).default(object)


class _Dumper(yaml.SafeDumper):

    def represent_str(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data, '|' if '\n' in data else None)

    def represent_message_dict(self, message):
        return self.represent_dict({key: value for key, value in message})

    def represent_message_list(self, messages):
        return self.represent_list([value for value in messages])

    def represent_values(self, values):
        if values._isMap:
            return self.represent_dict({key: value for key, value in values})
        if values._isList:
            return self.represent_list([value for value in values])
        if values._isUnknown:
            return self.represent_scalar('tag:yaml.org,2002:str', '<<UNKNOWN>>')
        return self.represent_scalar('tag:yaml.org,2002:str', '<<UNEXPECTED>>')

_Dumper.add_representer(str, _Dumper.represent_str)
_Dumper.add_representer(Message, _Dumper.represent_message_dict)
_Dumper.add_representer(MapMessage, _Dumper.represent_message_dict)
_Dumper.add_representer(RepeatedMessage, _Dumper.represent_message_list)
_Dumper.add_representer(Values, _Dumper.represent_values)
