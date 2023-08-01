import argparse
import json
from pathlib import Path
from typing import Any, Optional, Sequence, Union


class Kwargs:
    def __init__(self):
        self.type = None
        self.default: Any = None
        self.required: bool = False
        self.help: Optional[str] = None
        self.action: Optional[str] = None
        self.choices: Optional[list] = None


def register_parser(
    schema: Union[dict, str, Path],
    args: Optional[Sequence[str]] = None,
    parser: Optional[argparse.ArgumentParser] = None,
) -> dict:
    if not isinstance(schema, dict):
        with open(str(schema)) as f:
            schema: dict = json.load(f)
    assert "type" in schema and schema["type"] == "object"
    assert "properties" in schema

    required_set = set(schema.get("required", []))

    if parser is None:
        parser = argparse.ArgumentParser(description=schema.get("description"))

    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}

    for name, value in schema.get("properties", {}).items():
        assert isinstance(value, dict)

        kwargs = Kwargs()
        kwargs.default = value.get("default")
        kwargs.help = value.get("description")
        kwargs.required = name in required_set

        if kwargs.default is not None:
            kwargs.help = f"{kwargs.help}, [{kwargs.default}] in default"

        if "enum" in value:
            enum_list = value["enum"]
            assert len(enum_list) > 0, "Enum List is Empty"
            arg_type = type(enum_list[0])
            assert all(
                arg_type is type(item) for item in enum_list
            ), f"Items in [{enum_list}] with Different Types"

            kwargs.type = arg_type
            kwargs.choices = enum_list
        else:
            kwargs.type = type_map[value.get("type")]
            del kwargs.choices

        name = f"--{name}"
        # positional = value.get('positional')
        # if positional:
        #     del kwargs.required
        # else:
        #     name = f'--{name}'

        if kwargs.type is bool:
            assert not kwargs.default, "boolean have to be False in default"
            kwargs.default = False
            kwargs.action = "store_true"
            del kwargs.type
        else:
            del kwargs.action

        parser.add_argument(name, **vars(kwargs))
    # return vars(parser.parse_args(args=args))
