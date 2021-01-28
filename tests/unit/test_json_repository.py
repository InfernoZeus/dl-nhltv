import json
import pytest
from nhltv_lib.json_repository import (
    read_json_list,
    read_json_dict,
    add_to_json_dict,
    add_to_json_list,
)


def mock_json_open(mocker, m_open):
    return mocker.patch("nhltv_lib.json_repository.open", m_open)


@pytest.fixture
def m_open(mocker):
    m_open = mocker.mock_open(read_data="[392]")
    mock_json_open(mocker, m_open)
    return m_open


@pytest.fixture
def m_open_dict(mocker):
    m_open = mocker.mock_open(read_data='{"392": "booboo"}')
    mock_json_open(mocker, m_open)
    return m_open


def _m_isfile(mocker, ret):
    return mocker.patch("os.path.isfile", return_value=ret)


@pytest.fixture
def m_isfile_false(mocker):
    return _m_isfile(mocker, False)


@pytest.fixture
def m_isfile_true(mocker):
    return _m_isfile(mocker, True)


def test_read_json_list(mocker, m_open, m_isfile_true):
    assert read_json_list("test") == [392]


def test_read_json_list_nofile(mocker, m_open, m_isfile_false):
    assert read_json_list("test") == []


def test_add_to_json_list(mocker, m_open):
    mocker.patch(
        "nhltv_lib.json_repository.read_json_list", return_value=[392, "boooo"]
    )
    mjson = mocker.patch("json.dump")
    add_to_json_list("test", 2000)
    mjson.assert_called_once_with([392, "boooo", 2000], m_open())


def test_add_to_json_list_nofile(mocker, m_open, m_isfile_false):
    mjson = mocker.patch("json.dump")
    add_to_json_list("test", 2000)
    mjson.assert_called_once_with([2000], m_open())


def test_read_json_dict(mocker, m_open_dict, m_isfile_true):
    assert read_json_dict("test") == {"392": "booboo"}


def test_read_json_dict_empty(mocker, m_open_dict, m_isfile_false):
    assert read_json_dict("test") == {}


def test_add_to_json_dict(mocker, m_open_dict, m_isfile_true):
    call = mocker.call
    add_to_json_dict("test", {"2000": "3000"})
    calls = [
        call("{"),
        call('"392"'),
        call(": "),
        call('"booboo"'),
        call(", "),
        call('"2000"'),
        call(": "),
        call('"3000"'),
        call("}"),
    ]
    m_open_dict().write.assert_has_calls(calls)


def test_add_to_json_dict_empty(mocker, m_isfile_false):
    call = mocker.call
    m_open = mocker.mock_open(read_data="{}")
    mock_json_open(mocker, m_open)
    add_to_json_dict("test", {"2000": "3000"})
    calls = [call("{"), call('"2000"'), call(": "), call('"3000"'), call("}")]
    m_open().write.assert_has_calls(calls)
