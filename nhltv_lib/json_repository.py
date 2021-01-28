from typing import Union, List, Dict
import json
import os

JSON_FILE_ENDING = ".json"

# LIST


def read_json_list(listname: str) -> List[Union[str, int]]:
    listname += JSON_FILE_ENDING
    if not os.path.isfile(listname):
        return []
    with open(listname, "r") as f:
        return json.load(f)


def add_to_json_list(listname: str, addition: Union[str, int]):
    list_: List[Union[str, int]] = read_json_list(listname)
    listname += JSON_FILE_ENDING
    if addition not in list_:
        with open(listname, "w") as f:
            list_.append(addition)
            json.dump(list_, f)


# DICT


def read_json_dict(dictname: str) -> Dict[str, str]:
    dictname += JSON_FILE_ENDING
    if not os.path.isfile(dictname):
        return {}
    with open(dictname, "r") as f:
        return json.load(f)


def add_to_json_dict(dictname: str, addition: dict) -> None:
    dict_: Dict[str, str] = read_json_dict(dictname)
    dictname += JSON_FILE_ENDING
    with open(dictname, "w") as f:
        dict_.update(addition)
        json.dump(dict_, f)
