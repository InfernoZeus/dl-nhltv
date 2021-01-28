from nhltv_lib.downloaded_games import get_downloaded_games


def test_get_downloaded_games(mocker):
    mocker.patch(
        "nhltv_lib.downloaded_games.read_json_list", return_value=[3000]
    )
    assert get_downloaded_games() == [3000]
