
from google.protobuf.struct_pb2 import Struct, ListValue


def message_merge(message, values):
    for field, value in values.items():
        if isinstance(value, (dict, list, tuple)):
            current = getattr(message, field)
            if isinstance(value, dict):
                if isinstance(current, Struct):
                    map_merge(current, value)
                else:
                    descriptor = message.DESCRIPTOR.fields_by_name.get(field)
                    if descriptor.label == descriptor.LABEL_REPEATED:
                        if descriptor.message_type.GetOptions().map_entry:
                            message_map_merge(descriptor, current, value)
                        else:
                            message_list_merge(current, value)
                    else:
                        message_merge(current, value)
            else:
                list_merge(current, value)
            continue
        setattr(message, field, value)

def message_map_merge(descriptor, message, values):
    descriptor = descriptor.message_type.fields_by_name['value']
    for field, value in values.items():
        if isinstance(value, (dict, list, tuple)):
            current = message[field]
            if isinstance(current, Struct):
                map_merge(current, value)
            else:
                message_merge(current, value)
        else:
            if isinstance(value, str) and descriptor.type == descriptor.TYPE_BYTES:
                value = value.encode()
            message[field] = value

def message_list_merge(message, values):
    for ix, value in enumerate(values):
        if ix < len(message):
            message_merge(message[ix], value)
        else:
            message_merge(message.add(), value)

def map_merge(message, values):
    for field, value in values.items():
        if isinstance(value, (dict, list, tuple)):
            if field in message:
                current = message[field]
                if isinstance(value, dict):
                    map_merge(current, value)
                else:
                    list_merge(current, value)
                continue
        message[field] = value

def list_merge(message, values):
    for ix, value in enumerate(values):
        if ix < len(message):
            if isinstance(value, (dict, list, tuple)):
                current = message[ix]
                if isinstance(value, dict):
                    map_merge(current, value)
                else:
                    list_merge(current, value)
            else:
                message[ix] = value
        else:
            message.append(value)


def message_defaults(message, defaults):
    for field, value in defaults.items():
        if isinstance(value, (dict, list, tuple)):
            #if field in message:
            current = getattr(message, field)
            if isinstance(value, dict):
                if isinstance(current, Struct):
                    map_defaults(current, value)
                else:
                    descriptor = message.DESCRIPTOR.fields_by_name.get(field)
                    if descriptor.label == descriptor.LABEL_REPEATED:
                        if descriptor.message_type.GetOptions().map_entry:
                            message_map_defaults(descriptor, current, value)
                        else:
                            message_list_defaults(current, value)
                    else:
                        message_defaults(current, value)
            else:
                list_defaults(current, value)
        else:
            setattr(message, field, value)

def message_map_defaults(descriptor, message, values):
    descriptor = descriptor.message_type.fields_by_name['value']
    for field, value in values.items():
        if isinstance(value, (dict, list, tuple)):
            current = message[field]
            if isinstance(current, Struct):
                map_defaults(current, value)
            else:
                message_defaults(current, value)
        else:
            if field not in message:
                message[field] = value

def message_list_defaults(message, values):
    for ix, value in enumerate(values):
        if ix < len(message):
            message_defaults(message[ix], value)
        else:
            message_defaults(message.add(), value)

def map_defaults(message, defaults):
    for field, value in defaults.items():
        current = message.get(field, None)
        if isinstance(value, (dict, list, tuple)):
            if current is not None:
                if isinstance(value, dict):
                    map_defaults(current, value)
                else:
                    list_defaults(current, value)
                continue
        if current is None:
            message[field] = value

def list_defaults(message, defaults):
    for ix, value in enumerate(defaults):
        if ix < len(message):
            if isinstance(value, (dict, list, tuple)):
                current = message[ix]
                if isinstance(value, dict):
                    map_defaults(current, value)
                else:
                    list_defaults(current, value)
        else:
            message.append(value)


def message_dict(message):
    result = {}
    for field, value in message.ListFields():
        if field.type == field.TYPE_MESSAGE:
            if field.message_type.name == 'Struct':
                value = map_dict(value)
            elif field.message_type.name == 'ListValue':
                value = list_list(value)
            elif field.label == field.LABEL_REPEATED:
                if field.message_type.GetOptions().map_entry:
                    value = message_map_dict(field, value)
                else:
                    value = message_list_list(field, value)
            else:
                value = message_dict(value)
        result[field.name] = value
    return result

def message_map_dict(descriptor, message):
    descriptor = descriptor.message_type.fields_by_name['value']
    result = {}
    for field, value in message.items():
        if descriptor.type == descriptor.TYPE_MESSAGE:
            if descriptor.message_type.name == 'Struct':
                value = map_dict(value)
            elif descriptor.message_type.name == 'ListValue':
                value = list_list(value)
            elif descriptor.label == descriptor.LABEL_REPEATED:
                if descriptor.message_type.GetOptions().map_entry:
                    value = message_map_dict(value)
                else:
                    value = message_list_list(value)
            else:
                value = message_dict(value)
        elif descriptor.type == descriptor.TYPE_BYTES:
            value = value.decode()
        result[field] = value
    return result

def message_list_list(descriptor, message):
    result = []
    for value in message:
        if descriptor.type == descrptor.TYPE_MESSAGE:
            if descriptor.message_type.name == 'Struct':
                value = map_dict(value)
            elif descriptor.message_type.name == 'ListValue':
                value = list_list(value)
            elif descriptor.label == descriptor.LABEL_REPEATED:
                if descriptor.message_type.GetOptions().map_entry:
                    value = message_map_dict(value)
                else:
                    value = message_list_list(value)
            else:
                value = message_dict(value)
        elif descriptor.type == descriptor.TYPE_BYTES:
            value = value.decode()
        result.append(value)
    return result

def map_dict(message):
    result = {}
    for field, value in message.items():
        if isinstance(value, Struct):
            value = map_dict(value)
        elif isinstance(value, ListValue):
            value = list_list(value)
        result[field] = value
    return result

def list_list(message):
    result = []
    for value in message:
        if isinstance(value, Struct):
            value = map_dict(value)
        elif isinstance(value, ListValue):
            value = list_list(value)
        result.append(value)
    return result
