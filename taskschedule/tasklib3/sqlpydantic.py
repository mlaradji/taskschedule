from typing import Generic, TypeVar, List, Callable, Any, Optional
from typing_extensions import Annotated
from sqlmodel import TypeDecorator, JSON
from pydantic import (
    parse_obj_as,
    PlainSerializer,
    WithJsonSchema,
    BeforeValidator,
)
from fastapi.encoders import jsonable_encoder
from pydantic._internal._model_construction import ModelMetaclass
from datetime import datetime
import json

T = TypeVar("T")

CommaSeparatedList = Annotated[
    List[str],
    BeforeValidator(lambda x: x.split(",")),
    PlainSerializer(lambda x: ",".join(x), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

Epoch = Annotated[
    datetime,
    BeforeValidator(lambda x: datetime.fromtimestamp(int(x))),
    PlainSerializer(lambda x: x.timestamp(), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


def pydantic_column_type(pydantic_type):
    class PydanticJSONType(TypeDecorator, Generic[T]):
        impl = JSON()

        def __init__(
            self,
            json_encoder=json,
        ):
            self.json_encoder = json_encoder
            super(PydanticJSONType, self).__init__()

        def bind_processor(self, dialect):
            impl_processor = self.impl.bind_processor(dialect)
            dumps = self.json_encoder.dumps
            if impl_processor:

                def process(value: T):
                    if value is not None:
                        if isinstance(pydantic_type, ModelMetaclass):
                            # This allows to assign non-InDB models and if they're
                            # compatible, they're directly parsed into the InDB
                            # representation, thus hiding the implementation in the
                            # background. However, the InDB model will still be returned
                            value_to_dump = pydantic_type.from_orm(value)  # type: ignore[attr-defined]
                        else:
                            value_to_dump = value
                        value = jsonable_encoder(value_to_dump)
                    return impl_processor(value)

            else:

                def process(value: T):
                    if isinstance(pydantic_type, ModelMetaclass):
                        # This allows to assign non-InDB models and if they're
                        # compatible, they're directly parsed into the InDB
                        # representation, thus hiding the implementation in the
                        # background. However, the InDB model will still be returned
                        value_to_dump = pydantic_type.from_orm(value)  # type: ignore[attr-defined]
                    else:
                        value_to_dump = value
                    value = dumps(jsonable_encoder(value_to_dump))
                    return value

            return process

        def result_processor(self, dialect, coltype) -> Callable[[Any], Optional[T]]:
            impl_processor = self.impl.result_processor(dialect, coltype)
            if impl_processor:

                def process(value) -> Optional[T]:
                    value = impl_processor(value)
                    if value is None:
                        return None

                    data = value
                    # Explicitly use the generic directly, not type(T)
                    full_obj = parse_obj_as(pydantic_type, data)
                    return full_obj

            else:

                def process(value) -> Optional[T]:
                    if value is None:
                        return None

                    # Explicitly use the generic directly, not type(T)
                    full_obj = parse_obj_as(pydantic_type, value)
                    return full_obj

            return process

        def compare_values(self, x, y) -> bool:
            return x == y

    return PydanticJSONType
