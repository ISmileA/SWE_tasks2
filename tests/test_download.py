from scripts.download_data import parse_md5


def test_published_bsd_md5_and_gnu_md5_are_supported():
    assert parse_md5('MD5 (ml-100k.zip) = 0e33842e24a9c977be4e0107933c0723')=='0e33842e24a9c977be4e0107933c0723'
    assert parse_md5('0e33842e24a9c977be4e0107933c0723  ml-100k.zip')=='0e33842e24a9c977be4e0107933c0723'
