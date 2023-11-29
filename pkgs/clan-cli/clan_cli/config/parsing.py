import json
import subprocess
from pathlib import Path
from typing import Any

from ..errors import ClanError
from ..nix import nix_eval

script_dir = Path(__file__).parent


type_map: dict[str, type] = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "number": float,
    "string": str,
}


def schema_from_module_file(
    file: str | Path = f"{script_dir}/jsonschema/example-schema.json",
) -> dict[str, Any]:
    absolute_path = Path(file).absolute()
    # define a nix expression that loads the given module file using lib.evalModules
    nix_expr = f"""
        let
            lib = import <nixpkgs/lib>;
            slib = import {script_dir}/jsonschema {{inherit lib;}};
        in
            slib.parseModule {absolute_path}
    """
    # run the nix expression and parse the output as json
    cmd = nix_eval(["--expr", nix_expr])
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    return json.loads(proc.stdout)


def subtype_from_schema(schema: dict[str, Any]) -> type:
    if schema["type"] == "object":
        if "additionalProperties" in schema:
            sub_type = subtype_from_schema(schema["additionalProperties"])
            return dict[str, sub_type]  # type: ignore
        elif "properties" in schema:
            raise ClanError("Nested dicts are not supported")
        else:
            raise ClanError("Unknown object type")
    elif schema["type"] == "array":
        if "items" not in schema:
            raise ClanError("Untyped arrays are not supported")
        sub_type = subtype_from_schema(schema["items"])
        return list[sub_type]  # type: ignore
    else:
        return type_map[schema["type"]]


def type_from_schema_path(
    schema: dict[str, Any],
    path: list[str],
    full_path: list[str] | None = None,
) -> type:
    if full_path is None:
        full_path = path
    if len(path) == 0:
        return subtype_from_schema(schema)
    elif schema["type"] == "object":
        if "properties" in schema:
            subtype = type_from_schema_path(schema["properties"][path[0]], path[1:])
            return subtype
        elif "additionalProperties" in schema:
            subtype = type_from_schema_path(schema["additionalProperties"], path[1:])
            return subtype
        else:
            raise ClanError(f"Unknown type for path {path}")
    else:
        raise ClanError(f"Unknown type for path {path}")


def options_types_from_schema(schema: dict[str, Any]) -> dict[str, type]:
    result: dict[str, type] = {}
    for name, value in schema.get("properties", {}).items():
        assert isinstance(value, dict)
        type_ = value["type"]
        if type_ == "object":
            # handle additionalProperties
            if "additionalProperties" in value:
                sub_type = value["additionalProperties"].get("type")
                if sub_type not in type_map:
                    raise ClanError(
                        f"Unsupported object type {sub_type} (field {name})"
                    )
                result[f"{name}.<name>"] = type_map[sub_type]
                continue
            # handle properties
            sub_result = options_types_from_schema(value)
            for sub_name, sub_type in sub_result.items():
                result[f"{name}.{sub_name}"] = sub_type
            continue
        elif type_ == "array":
            if "items" not in value:
                raise ClanError(f"Untyped arrays are not supported (field: {name})")
            sub_type = value["items"].get("type")
            if sub_type not in type_map:
                raise ClanError(f"Unsupported list type {sub_type} (field {name})")
            sub_type_: type = type_map[sub_type]
            result[name] = list[sub_type_]  # type: ignore
            continue
        result[name] = type_map[type_]
    return result
