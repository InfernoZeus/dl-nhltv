from typing import List
from nhltv_lib.json_repository import read_json_list


def get_downloaded_games() -> List[int]:
    return [
        i for i in read_json_list("downloaded_games") if isinstance(i, int)
    ]
