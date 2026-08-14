from portrait_evolve.taxonomy import infer_domains, infer_scene, normalize_role


def test_intent_text_maps_to_domains_and_scene():
    text = "想找两个人报名智能应用开发大赛，我做后端和数据，缺前端和产品"
    assert infer_scene(text) == "比赛组队"
    assert "ai_programming" in infer_domains(text)


def test_role_aliases():
    assert normalize_role("前端") == "frontend"
    assert normalize_role("建模") == "research"
    assert normalize_role("论文") == "writing"
