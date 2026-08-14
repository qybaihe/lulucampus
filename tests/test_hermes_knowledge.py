from __future__ import annotations

from onemore.core.database import SessionLocal
from onemore.hermes.campus_mcp import CAMPUS_TOOLS, dispatch_tool, mint_tool_session
from onemore.modules.campus.ima_kb import (
    KnowledgeChunk,
    _rank_chunks,
    answer_campus_knowledge,
    search_campus_knowledge,
)


FIXTURE_CHUNKS = [
    KnowledgeChunk(
        title="宿舍晚上会断电断网吗",
        question="宿舍晚上会断电断网吗",
        text="珠海校区宿舍夜间不断电，校园网一般也不中断。个别楼栋维修时会提前通知。",
        source="迎新智能体QA合集.md",
        media_id="md-qa",
    ),
    KnowledgeChunk(
        title="转专业难吗？",
        question="转专业难吗？",
        text="做好准备的话还好，难度还要看学院热度。可以先去转专业群问学长。",
        source="迎新智能体QA合集.md",
        media_id="md-qa",
    ),
    KnowledgeChunk(
        title="校园卡如何充值",
        question="校园卡如何充值",
        text="可以用企业微信里的逸仙卡入口充值，实体卡和虚拟卡余额互通。",
        source="迎新智能体QA合集.md",
        media_id="md-qa",
    ),
    KnowledgeChunk(
        title="校内食堂介绍",
        question="校内食堂介绍",
        text="各校区都有食堂。珠海学五、南校园学一学五最常去。",
        source="迎新智能体QA合集.md",
        media_id="md-qa",
    ),
]


def _patch_knowledge(monkeypatch) -> None:
    monkeypatch.setattr("onemore.modules.campus.ima_kb.ima_configured", lambda: True)
    monkeypatch.setattr("onemore.modules.campus.ima_kb._load_chunks", lambda: list(FIXTURE_CHUNKS))
    monkeypatch.setattr("onemore.modules.campus.ima_kb._chunks_from_title_matches", lambda _q: [])


def test_rank_prefers_exact_campus_question():
    ranked = _rank_chunks("宿舍晚上会断电吗？", FIXTURE_CHUNKS)
    assert ranked
    assert ranked[0].question == "宿舍晚上会断电断网吗"


def test_campus_card_alias_finds_yixian_card():
    ranked = _rank_chunks("逸仙卡怎么充值", FIXTURE_CHUNKS)
    assert ranked
    assert "校园卡" in ranked[0].question


def test_answer_campus_knowledge_returns_card(monkeypatch):
    _patch_knowledge(monkeypatch)
    result = answer_campus_knowledge("宿舍晚上会断电吗？")
    assert result is not None
    assert result["card_type"] == "knowledge_answer"
    assert result["action"] == "campus.knowledge"
    message = result["data"]["message"]
    assert "断电" in message
    assert "ima.qq.com" not in message
    assert "openapi" not in message.lower()
    hits = result["data"]["hits"]
    assert hits
    assert "url" not in hits[0]
    assert "media_id" not in hits[0]


def test_hermes_ask_uses_campus_knowledge(client, auth_headers, monkeypatch):
    _patch_knowledge(monkeypatch)
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "宿舍晚上会断电吗？"},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["card_type"] == "knowledge_answer"
    assert "断电" in (body["data"].get("message") or "")
    blob = response.text.lower()
    assert "ima-openapi" not in blob
    assert "apikey" not in blob


def test_hermes_ask_still_routes_courses_not_knowledge(client, auth_headers, monkeypatch):
    _patch_knowledge(monkeypatch)
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "今天有什么课？"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["card_type"] == "course_list"


def test_campus_knowledge_search_tool(client, auth_headers, monkeypatch):
    _patch_knowledge(monkeypatch)
    with SessionLocal() as db:
        token = mint_tool_session(db, "u_demo_1", question="转专业难吗")
        result = dispatch_tool(
            "campus_knowledge_search",
            {"question": "转专业难吗"},
            tool_session=token,
            db=db,
        )
    assert result["ok"] is True
    assert result["card_type"] == "knowledge_answer"
    assert "转专业" in (result["data"].get("message") or "")
    names = {tool.name for tool in CAMPUS_TOOLS}
    assert "campus_knowledge_search" in names


def test_search_skips_greetings(monkeypatch):
    _patch_knowledge(monkeypatch)
    assert answer_campus_knowledge("你好") is None
    assert search_campus_knowledge("转专业难吗")["hits"]
