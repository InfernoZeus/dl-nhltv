import requests_mock
import pytest
from nhltv_lib.download import (
    _get_download_from_stream,
    _decode_ts_file,
    _get_quality_url,
    _verify_game_is_not_blacked_out,
    _verify_nhltv_request_status_succeeded,
    _extract_session_key,
    _extract_media_auth,
    Download,
    _merge_fragments_to_single_video,
    _decode_video_and_get_concat_file_content,
    _get_session_key,
    _get_raw_file_name,
    _get_master_file_name,
    _get_quality_file_name,
    _shorten_video,
    _get_chosen_quality,
    _download_page_with_aria2,
    _download_master_file,
    _download_quality_file,
    clean_up_download,
    _create_download_folder,
    _parse_quality_file,
    _remove_ts_files,
    _download_individual_video_files,
    _hexdump_keys,
    download_game,
)
from nhltv_lib.stream import Stream
from nhltv_lib.exceptions import (
    BlackoutRestriction,
    AuthenticationFailed,
    DecodeError,
    DownloadError,
    ExternalProgramError,
    RequestFailed,
)
from nhltv_lib.models import GameStatus

FAKE_URL = "http://nhl"


@pytest.fixture(scope="function", autouse=True)
def mock_game_tracking(mocker):
    return mocker.patch("nhltv_lib.download.game_tracking")


@pytest.fixture(scope="function", autouse=True)
def mock_rmtree(mocker):
    return mocker.patch("nhltv_lib.download.rmtree")


@pytest.fixture(scope="function", autouse=True)
def mock_move(mocker):
    return mocker.patch("nhltv_lib.download.move")


@pytest.fixture(scope="function", autouse=True)
def mock_call_subp_and_raise(mocker):
    return mocker.patch(
        "nhltv_lib.download.call_subprocess_and_raise_on_error"
    )


@pytest.fixture(scope="function")
def mock_for_dl_individual_files(mocker):
    mocky = mocker.Mock()
    mocky.returncode = 0
    mocker.patch(
        "nhltv_lib.download.call_subprocess_and_get_stdout_iterator",
        return_value=(
            mocky,
            (
                i
                for i in [
                    b"Download complete: foo.ts\n",
                    b"Download complete: bar.ts\n",
                ]
            ),
        ),
    )
    return mocky


@pytest.fixture(scope="function")
def mock_for_hexdump_keys(mocker):
    mocky = mocker.Mock()
    mocky.returncode = 0
    mocker.patch(
        "nhltv_lib.download.call_subprocess_and_get_stdout_iterator",
        return_value=(mocky, (i for i in [b"NOT KEY\n", b"KEY\n"])),
    )
    return mocky


def test_hexdump_keys(fake_download, mock_for_hexdump_keys):
    assert _hexdump_keys(fake_download, 0) == (b"KEY", 0)


def test_hexdump_keys_raises_externalprogramerror(
    fake_download, mock_for_hexdump_keys
):
    mock_for_hexdump_keys.returncode = 1
    with pytest.raises(ExternalProgramError):
        _hexdump_keys(fake_download, 0)


def test_parse_quality_file(
    mocker,
    fake_quality_file,
    fake_download,
    fake_download_file,
    fake_decode_hashes,
):
    mocker.patch(
        "nhltv_lib.download.read_lines_from_file",
        return_value=fake_quality_file,
    )
    mocker.patch(
        "nhltv_lib.download._get_chosen_quality",
        return_value="5600K/5600_complete-trimmed.m3u8",
    )
    dlc, dch = _parse_quality_file(fake_download)
    assert dlc == fake_download_file
    assert dch == fake_decode_hashes


def test_get_download_from_stream(mocker, fake_stream_json, fake_streams):
    mocker.patch("requests.cookies")
    mocker.patch("nhltv_lib.download.save_cookies_to_txt")
    mocker.patch(
        "nhltv_lib.download.get_auth_cookie_value_login_if_needed",
        return_value="foo",
    )
    mocker.patch("nhltv_lib.download._get_session_key", return_value="raboof")
    mocker.patch(
        "nhltv_lib.download._verify_game_is_not_blacked_out", return_value=None
    )
    mocker.patch(
        "nhltv_lib.download._verify_nhltv_request_status_succeeded",
        return_value=None,
    )
    stream_url = FAKE_URL
    mocker.patch("nhltv_lib.download.get_stream_url", return_value=stream_url)

    stream = fake_streams[0]

    with requests_mock.Mocker() as rm:
        rm.get(stream_url, json=fake_stream_json)
        assert _get_download_from_stream(stream) == Download(
            2019020104,
            "2019-10-18_NSH-ARI",
            "https://vod-l3c-na1.med.nhl.com/ps01/nhl/2019/10/18/NHL_GAME_VIDEO_NSHARI_M2_VISIT_20191018_1570700310035/master_tablet60.m3u8",  # noqa: E501
            "raboof",
        )


def test_get_quality_url(mocker, fake_download):
    mocker.patch(
        "nhltv_lib.download._get_chosen_quality",
        return_value="5600K/5600_complete-trimmed.m3u8",
    )
    assert (
        _get_quality_url(fake_download)
        == "https://vod-l3c-na1.med.nhl.com/ps01/nhl/2019/10/18/NHL_GAME_VIDEO_NSHARI_M2_VISIT_20191018_1570700310035/5600K/5600_complete-trimmed.m3u8"  # noqa: E501
    )


def test_decode_ts_file(mocker, mock_call_subp_and_raise):
    _decode_ts_file("abc".encode(), {"iv": "baabaa"}, 5, 8)
    mock_call_subp_and_raise.assert_called_once_with(
        'openssl enc -aes-128-cbc -in "8/5.ts" -out "8/5.ts.dec" -d -K abc -iv baabaa',  # noqa: E501
        DecodeError,
    )


def test_remove_ts_files(mocker, mock_os_remove):
    call = mocker.call
    mocker.patch("nhltv_lib.download.iglob", return_value=["foo", "bar"])
    _remove_ts_files(3)
    calls = [call("foo"), call("bar")]
    mock_os_remove.assert_has_calls(calls)


def test_get_raw_file_name():
    assert _get_raw_file_name(30) == "30_raw.mkv"


def test_get_master_file_name():
    assert _get_master_file_name(30) == "30/master.m3u8"


def test_get_quality_file_name():
    assert _get_quality_file_name(30) == "30/input.m3u8"


def test_extract_session_key(mocker):
    retjson = {"session_key": 3000}
    assert _extract_session_key(retjson) == "3000"


def test_get_session_key(mocker, fake_session_json):
    mocker.patch(
        "nhltv_lib.download.get_auth_cookie_value_login_if_needed",
        return_value="bar",
    )
    mocker.patch("nhltv_lib.download.get_referer", return_value="foo")
    mocker.patch(
        "nhltv_lib.download.get_session_key_url", return_value=FAKE_URL
    )
    with requests_mock.Mocker() as m:
        m.get(FAKE_URL, json=fake_session_json)
        assert _get_session_key(Stream(1, 2, 3)) == "foo="


def test_verify_req_stat_succeeded():
    dict_ = {"status_code": 1}
    assert _verify_nhltv_request_status_succeeded(dict_) is None


def test_verify_req_stat_succeeded_raises():
    dict_ = {"status_code": -3500, "status_message": "foo"}
    with pytest.raises(AuthenticationFailed) as e:
        _verify_nhltv_request_status_succeeded(dict_)
    assert str(e.value) == "foo"


def test_verify_game_not_blacked_out():
    dict_ = {
        "status_code": 1,
        "user_verified_event": [
            {
                "user_verified_content": [
                    {
                        "user_verified_media_item": [
                            {"blackout_status": {"status": "BlackedOutStatus"}}
                        ]
                    }
                ]
            }
        ],
    }
    with pytest.raises(BlackoutRestriction) as e:
        _verify_game_is_not_blacked_out(dict_)
    assert str(e.value) == "This game is affected by blackout restrictions."


def test_merge_frags_to_single(mocker):
    mock_cct = mocker.patch("nhltv_lib.download.concat_video")

    _merge_fragments_to_single_video(30)
    mock_cct.assert_called_once_with(
        "30/concat.txt", "30_raw.mkv", extra_args="-bsf:a aac_adtstoasc"
    )


def test_download_page_with_aria2(mocker, mock_call_subp_and_raise):
    _download_page_with_aria2(1, "file", "url")
    mock_call_subp_and_raise.assert_called_once_with(
        "aria2c -o file --load-cookies=1.txt --log='1_dl.log' --log-level=notice --quiet=false --retry-wait=10 --max-tries=0 --header='Accept: */*' --header='Accept-Language: en-US,en;q=0.8' --header='Origin: https://www.nhl.com' -U='Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36' --enable-http-pipelining=true --auto-file-renaming=false --allow-overwrite=true url"  # noqa: E501
    )


def test_get_chosen_quality(mocker, fake_master_file):
    mo = mocker.mock_open(read_data=fake_master_file)
    mocker.patch("builtins.open", mo)
    assert _get_chosen_quality(1) == "5600K/5600_complete-trimmed.m3u8\n"

    mocker.patch("nhltv_lib.download.get_quality", return_value=3500)
    assert _get_chosen_quality(1) == "3500K/3500_complete-trimmed.m3u8\n"


def test_download_master_file(mocker, fake_download):
    m = mocker.patch("nhltv_lib.download._download_page_with_aria2")
    _download_master_file(fake_download)
    m.assert_called_once_with(
        2019020104,
        "2019020104/master.m3u8",
        "https://vod-l3c-na1.med.nhl.com/ps01/nhl/2019/10/18/NHL_GAME_VIDEO_NSHARI_M2_VISIT_20191018_1570700310035/master_tablet60.m3u8",  # noqa: E501
    )


def test_extract_media_auth(mocker, fake_stream_json):
    assert _extract_media_auth(fake_stream_json) == "mediaAuth=bar"


def test_extract_media_auth_wo_session(mocker, fake_stream_json):
    del fake_stream_json["session_info"]
    with pytest.raises(RequestFailed):
        _extract_media_auth(fake_stream_json)


def test_download_quality_file(mocker):
    m = mocker.patch("nhltv_lib.download._download_page_with_aria2")
    _download_quality_file(1, FAKE_URL)
    m.assert_called_once_with(1, "1/input.m3u8", FAKE_URL)


def test_clean_up_before_dl(mocker, mock_os_remove, mock_rmtree):
    clean_up_download(1)
    mock_os_remove.assert_called_once_with("1_dl.log")
    mock_rmtree.assert_called_once_with("1")


def test_clean_up_before_dl_and_cookie(mocker, mock_os_remove, mock_rmtree):
    call = mocker.call

    clean_up_download(1, True)

    calls = [call("1_dl.log"), call("1.txt")]
    mock_os_remove.assert_has_calls(calls)

    mock_rmtree.assert_called_once_with("1")


def test_download_individual_video_files(
    mocker, fake_download, mock_for_dl_individual_files
):
    _download_individual_video_files(fake_download, 2)


def test_download_individual_video_files_raises_downloaderror(
    mocker, fake_download, mock_for_dl_individual_files, mock_move
):
    mock_for_dl_individual_files.returncode = 1
    with pytest.raises(DownloadError):
        _download_individual_video_files(fake_download, 2)
    mock_move.assert_called_once()


def test_create_dl_folder(mocker, mock_os_path_exists):
    mock_os_path_exists.return_value = False
    mock_mkdirs = mocker.patch("os.makedirs")
    _create_download_folder(1)
    mock_mkdirs.assert_called_once_with("1/keys")


def test_shorten_video(mocker, mock_call_subp_and_raise):
    _shorten_video(1)
    mock_call_subp_and_raise.assert_called_once_with(
        "mv 1/download_file.txt 1/download_file_orig.txt;head -100 "
        + "1/download_file_orig.txt > 1/download_file.txt;rm -f "
        + "1/download_file_orig.txt;"
    )


def test_decode_video_get_concat_file_content(
    mocker, fake_download, fake_decode_hashes, fake_concat_file
):
    mocker.patch("nhltv_lib.download.print_progress_bar")
    mocker.patch("nhltv_lib.download._decode_ts_file")
    mocker.patch("nhltv_lib.download._hexdump_keys", return_value=(1, 2))
    mocker.patch("os.replace")

    assert (
        _decode_video_and_get_concat_file_content(
            fake_download, fake_decode_hashes
        )
        == fake_concat_file
    )


def test_download_game(mocker, fake_streams, fake_download):
    """
    This test is probably too complex to be of any use
    if it ends up causing issues let's just get rid of it
    """

    tracker = mocker.patch("nhltv_lib.download.game_tracking")

    mocker.patch(
        "nhltv_lib.download._get_download_from_stream",
        return_value=fake_download,
    )

    mocker.patch("nhltv_lib.download.tprint")
    clean = mocker.patch("nhltv_lib.download.clean_up_download")
    create = mocker.patch("nhltv_lib.download._create_download_folder")
    dlmaster = mocker.patch("nhltv_lib.download._download_master_file")
    dlq = mocker.patch("nhltv_lib.download._download_quality_file")
    mocker.patch(
        "nhltv_lib.download._parse_quality_file",
        return_value=([1, 2, 3], [9, 8, 7]),
    )
    mocker.patch(
        "nhltv_lib.download._get_quality_url", return_value="http://url"
    )
    dlivf = mocker.patch("nhltv_lib.download._download_individual_video_files")
    mocker.patch(
        "nhltv_lib.download._decode_video_and_get_concat_file_content"
    )
    mocker.patch("nhltv_lib.download.write_lines_to_file")
    mocker.patch("nhltv_lib.download._merge_fragments_to_single_video")
    mocker.patch("nhltv_lib.download._remove_ts_files")

    assert download_game(fake_streams[0]) == fake_download

    dlmaster.assert_called_once_with(fake_download)
    clean.assert_called_once_with(fake_download.game_id)
    create.assert_called_once_with(fake_download.game_id)

    dlq.assert_called_once_with(fake_download.game_id, "http://url")

    dlivf.assert_called_once_with(fake_download, 3)

    tracker.update_game_status.assert_called_once_with(
        fake_download.game_id, GameStatus.downloading
    )
    tracker.download_started.assert_called_once_with(fake_download.game_id)
    tracker.set_game_info.assert_called_once_with(
        fake_download.game_id, "2019-10-18_NSH-ARI"
    )
