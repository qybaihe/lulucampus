"""HTTP share-link taste import helpers (no live Douyin network in CI)."""

from __future__ import annotations

from onemore.modules.taste_profile.providers.douyin_http import extract_share_url


def test_extract_share_url_from_card_paste():
    text = (
        "yinhe18985 4- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 "
        "https://v.douyin.com/72Q4_JwqJxg/ 7@7.com :0pm"
    )
    assert extract_share_url(text) == "https://v.douyin.com/72Q4_JwqJxg/"


def test_extract_share_url_ignores_trailing_share_card_junk():
    text = (
        "8- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 "
        "https://v.douyin.com/6tRdrQEDajg/ 2@1.com :5pm"
    )
    assert extract_share_url(text) == "https://v.douyin.com/6tRdrQEDajg/"


def test_extract_share_url_when_junk_is_glued():
    assert (
        extract_share_url("https://v.douyin.com/6tRdrQEDajg/2@1.com :5pm")
        == "https://v.douyin.com/6tRdrQEDajg/"
    )


def test_extract_user_url():
    url = "https://www.douyin.com/user/MS4wLjABAAAASdy-Nhpq4QXMAO9rfVaXfTJEZepMdSorc3OrZNlP4d_-wuoaMHHbiokLWt1e4hKw"
    assert extract_share_url(url) == url


def test_demo_from_link_schema_on_status(client):
    response = client.get("/demo/taste/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "http_link_import_ready" in data


def test_from_link_request_defaults_include_collects():
    from onemore.modules.taste_profile.schemas import DemoTasteFromLinkRequest

    body = DemoTasteFromLinkRequest(share_url="https://v.douyin.com/72Q4_JwqJxg/")
    assert body.likes_limit == 30
    assert body.posts_limit == 20
    assert body.collects_limit == 30
    assert body.force is True


def test_validate_cookie_header_accepts_raw_cookie():
    from onemore.modules.taste_profile.providers.douyin_http import validate_cookie_header

    header = validate_cookie_header("sessionid=abc; sid_tt=xyz")
    assert "sessionid=abc" in header


def test_authenticated_from_link_persists_profile(client, auth_headers, monkeypatch):
    class FakeCollector:
        def __init__(self, **kwargs):
            pass

        def collect_recent(self, share_text, **kwargs):
            return {
                "sec_uid": "MS4wLjABAAAASdy-Nhpq4QXMAO9rfVaXfTJEZepMdSorc3OrZNlP4d_-wuoaMHHbiokLWt1e4hKw",
                "profile_url": "https://www.douyin.com/user/MS4wLjABAAAASdy-Nhpq4QXMAO9rfVaXfTJEZepMdSorc3OrZNlP4d_-wuoaMHHbiokLWt1e4hKw",
                "resolved_url": "https://www.douyin.com/user/MS4wLjABAAAASdy-Nhpq4QXMAO9rfVaXfTJEZepMdSorc3OrZNlP4d_-wuoaMHHbiokLWt1e4hKw",
                "source_profile": {
                    "nickname": "小鹤Timo",
                    "avatar_url": None,
                    "uid": "3913884925184093",
                    "sec_uid": "MS4wLjABAAAASdy-Nhpq4QXMAO9rfVaXfTJEZepMdSorc3OrZNlP4d_-wuoaMHHbiokLWt1e4hKw",
                },
                "posts_raw": [
                    {
                        "aweme_id": "post1",
                        "desc": "黑客松写代码 华强北买硬件",
                        "author": {"nickname": "小鹤Timo", "uid": "1"},
                    }
                ],
                "likes_raw": [
                    {
                        "aweme_id": "like1",
                        "desc": "徒步香港 成长驱动 比赛冲刺",
                        "author": {"nickname": "别人", "uid": "2"},
                    }
                ],
                "collects_raw": [
                    {
                        "aweme_id": "col1",
                        "desc": "露营装备清单 周末出发",
                        "author": {"nickname": "户外", "uid": "3"},
                    }
                ],
                "meta": {
                    "posts": {"pages": 1},
                    "likes": {"pages": 1},
                    "collects": {"pages": 1},
                    "host": "www.douyin.com",
                },
            }

    monkeypatch.setattr(
        "onemore.modules.taste_profile.providers.douyin_http.DouyinHttpCollector",
        FakeCollector,
    )
    response = client.post(
        "/profile/taste/from-link",
        headers=auth_headers,
        json={"share_url": "https://v.douyin.com/72Q4_JwqJxg/", "use_llm": False},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "READY"
    assert data["result"]["primary_tag"]["key"]
    assert data["source_profile"]["nickname"] == "小鹤Timo"
    assert data["collection"]["items_collected"] == 3

    me = client.get("/profile/taste/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["data"]["primary_tag"]["key"] == data["result"]["primary_tag"]["key"]
