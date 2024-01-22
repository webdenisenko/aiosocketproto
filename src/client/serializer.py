from abc import ABC
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from .client import AsyncSocketClient

SIMPLE_TYPES = (int, float, str, bool)

CUSTOM_TYPE_HEADER = '__customtype__'
TUPLE_TYPE_NAME = 'builtins.tuple'
SET_TYPE_NAME = 'builtins.set'


class SerializerType(ABC):
    """ Class for create a serializer of a custom object type """

    INSTANCE: object
    default: "Serializer"

    @classmethod
    def serialize(cls, data: any) -> any:
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data: any) -> any:
        raise NotImplementedError


class BytesSerializer(SerializerType):
    """ Default Bytes Serializer """

    INSTANCE = bytes

    @classmethod
    def serialize(cls, data: bytes) -> str:
        return data.hex()

    @classmethod
    def deserialize(cls, data: str) -> bytes:
        return bytes.fromhex(data)


class ByteArraySerializer(SerializerType):
    """ Default Bytearray Serializer """

    INSTANCE = bytearray

    @classmethod
    def serialize(cls, data: bytearray) -> str:
        return data.hex()

    @classmethod
    def deserialize(cls, data: str) -> bytearray:
        return bytearray.fromhex(data)


class Serializer(ABC):
    """ Serializer for simple data types """

    def __init__(self: "AsyncSocketClient"):
        super().__init__()
        self.add_serializer(BytesSerializer) # default bytes serializer
        self.add_serializer(ByteArraySerializer) # default bytearray serializer

    @staticmethod
    def get_data_type_str(data: Type[any]) -> str:
        return '{}.{}'.format(data.__module__, data.__name__)

    def serialize(self: "AsyncSocketClient", data: any) -> any:
        if data is None:
            return data

        elif isinstance(data, SIMPLE_TYPES):
            return data

        elif isinstance(data, list):
            return [self.serialize(value) for value in data]

        elif isinstance(data, tuple):
            return CUSTOM_TYPE_HEADER, TUPLE_TYPE_NAME, [self.serialize(value) for value in data]

        elif isinstance(data, set):
            return CUSTOM_TYPE_HEADER, SET_TYPE_NAME, [self.serialize(value) for value in data]

        elif isinstance(data, dict):
            return {name: self.serialize(value) for name, value in data.items()}

        else:
            data_type = self.get_data_type_str(type(data))
            serializer = self.custom_serializers.get(data_type, None)

            if not serializer:
                raise ValueError(f'unsupported data type: {data_type}')

            serialized_object = serializer.serialize(data)

            return CUSTOM_TYPE_HEADER, data_type, serialized_object

    def deserialize(self: "AsyncSocketClient", data: any) -> any:
        if data is None:
            return data

        elif isinstance(data, SIMPLE_TYPES):
            return data

        elif isinstance(data, list):

            if len(data) == 3 and data[0] == CUSTOM_TYPE_HEADER:
                if data[1] == TUPLE_TYPE_NAME:
                    return tuple([self.deserialize(value) for value in data[2]])
                elif data[1] == SET_TYPE_NAME:
                    return set([self.deserialize(value) for value in data[2]])
                elif data[1] in self.custom_serializers:
                    deserialized_object = self.custom_serializers[data[1]].deserialize(data[2])
                    return deserialized_object
                else:
                    raise ValueError(f'unsupported data type: {data[1]}')

            return [self.deserialize(value) for value in data]

        elif isinstance(data, dict):
            return {name: self.deserialize(value) for name, value in data.items()}

        else:
            raise ValueError(f'unsupported data type: {type(data)}')
