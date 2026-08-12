from __future__ import annotations

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures/competition_snapshot_2026-08-11.json"
OUTPUT = ROOT / "fixtures/competition_snapshot_2026-08-11_v1.1.json"
QUALITY_REVIEW = ROOT / "data/competitions/quality_review_2026-08-11.csv"
CHECKSUM = ROOT / "fixtures/competition_snapshot_2026-08-11_v1.1.sha256"
VERIFIED_AT = "2026-08-11T20:27:06+08:00"


META: dict[str, dict[str, str | int]] = {
    "cumcm_guangdong_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "school_notice",
        "registration_instructions": "打开中山大学数学学院通知，按通知准备报名表和参赛承诺书；由校内负责老师汇总报名及缴费。",
        "fee_note": "广东赛区报名费300元/队。",
        "recommendation_tier": "A",
        "priority": 98,
        "quality_note": "中山大学官方通知；已将操作入口从全国平台改为校内通知。",
    },
    "cnmc_guangdong_2026": {
        "participation_mode": "individual",
        "registration_mode": "school_coordinated",
        "registration_instructions": "广东赛区要求学校统一汇总报名；中大学生先联系学院教务或数学学院确认校内收集方式。",
        "fee_note": "报名费100元/人，由学校统一汇款。",
        "recommendation_tier": "A",
        "priority": 90,
        "quality_note": "广东省数学会通知可信；报名不是学生直报，需学校统一组织。",
    },
    "ncccu_office_2026": {
        "participation_mode": "individual",
        "registration_mode": "direct",
        "registration_instructions": "在赛项官网选择科目并由学生本人报名、缴费。",
        "fee_note": "区域赛个人赛80元/科，国赛不再另收费。",
        "recommendation_tier": "B",
        "priority": 70,
        "quality_note": "主办方赛项页字段完整；个人赛仅开放备赛搭子，不作为正式组队。",
    },
    "ncccu_programming_2026": {
        "participation_mode": "individual",
        "registration_mode": "direct",
        "registration_instructions": "在赛项官网选择C、C++、Java或Python科目并由学生本人报名、缴费。",
        "fee_note": "区域赛个人赛80元/科，国赛不再另收费。",
        "recommendation_tier": "B",
        "priority": 74,
        "quality_note": "修正奖金口径：前三名学生600元/名，而非队伍1000元/队。",
    },
    "ncccu_ai_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "由队长在赛项官网报名并填写队员信息；允许跨校组队。",
        "fee_note": "区域赛团队赛200元/队，国赛不再另收费。",
        "recommendation_tier": "B",
        "priority": 78,
        "quality_note": "主办方赛项页的时间、队伍和奖金字段完整，可直接组队。",
    },
    "ncccu_bigdata_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "由队长在赛项官网报名并填写队员信息；允许跨校组队。",
        "fee_note": "区域赛团队赛200元/队，国赛不再另收费。",
        "recommendation_tier": "B",
        "priority": 78,
        "quality_note": "主办方赛项页的时间、队伍和奖金字段完整，可直接组队。",
    },
    "aiadc_smart_application_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "在AIADC报名系统填报负责人、成员和项目；团队原则上不超过10人，特殊项目放宽需审核。",
        "fee_note": "官网赛程提及缴费，金额以报名系统和后续正式通知为准。",
        "recommendation_tier": "B",
        "priority": 80,
        "quality_note": "官网规则完整，但组织与费用信息透明度低于A档，保留B档观察。",
    },
    "aic_algorithm_application_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "先确认中山大学校赛或赛区组织方式，再由队伍通过AIC报名系统完成赛区报名。",
        "fee_note": "参加省赛/区域赛的队伍按官方通知缴纳500元/队。",
        "recommendation_tier": "A",
        "priority": 90,
        "quality_note": "官方赛道通知完整；存在校赛前置步骤，需学校/赛区协调。",
    },
    "aic_digital_economy_decision_2026": {
        "participation_mode": "team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "2至3名中大同校学生组队，先确认校内初赛与推荐方式，再由队长在AIC报名系统填报；不得跨校组队。",
        "fee_note": "晋级复赛的队伍按官方通知缴纳500元/队。",
        "recommendation_tier": "A",
        "priority": 92,
        "quality_note": "官方专项赛通知字段完整；存在校内初赛与推荐前置步骤。",
    },
    "aic_indoor_agriculture_transplant_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "在AIC报名系统选择室内农业主题赛和对应任务，填报1至3名参赛学生。",
        "fee_note": "参赛队伍按官方通知缴纳500元/队。",
        "recommendation_tier": "A",
        "priority": 90,
        "quality_note": "官方主题赛通知含选拔和山东线下总决赛信息。",
    },
    "aic_indoor_agriculture_harvest_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "在AIC报名系统选择室内农业主题赛和对应任务，填报1至3名参赛学生。",
        "fee_note": "参赛队伍按官方通知缴纳500元/队。",
        "recommendation_tier": "A",
        "priority": 90,
        "quality_note": "官方主题赛通知含选拔和山东线下总决赛信息。",
    },
    "cubec_circulation_simulation_2026": {
        "participation_mode": "team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "先组成3至5人的中大同校队伍，再联系学院竞赛负责人；平台院校登记须由学校负责教师完成。",
        "fee_note": "收费及知识赛安排以中山大学组织通知和赛事平台为准。",
        "recommendation_tier": "A",
        "priority": 93,
        "quality_note": "中国贸促会商业行业委员会官方通知；学生不能绕过院校负责人直报。",
    },
    "cubec_marketing_decision_2026": {
        "participation_mode": "team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "先组成3至5人的中大同校队伍，再联系学院竞赛负责人；平台院校注册须由学校负责教师完成。",
        "fee_note": "收费及知识赛安排以中山大学组织通知和赛事平台为准。",
        "recommendation_tier": "A",
        "priority": 92,
        "quality_note": "中国贸促会商业行业委员会官方通知；学生不能绕过院校负责人直报。",
    },
    "cubec_entrepreneurship_research_2026": {
        "participation_mode": "team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "先组成3至5人的中大同校队伍并准备专题论文，再联系学院竞赛负责人统一组织。",
        "fee_note": "收费及知识赛安排以中山大学组织通知和赛事平台为准。",
        "recommendation_tier": "A",
        "priority": 91,
        "quality_note": "中国贸促会商业行业委员会官方通知；学生不能绕过院校负责人直报。",
    },
    "cubec_data_agent_2026": {
        "participation_mode": "team",
        "registration_mode": "school_coordinated",
        "registration_instructions": "先组成3至5人的中大同校队伍，再联系学院竞赛负责人；平台院校登记须由学校负责教师完成。",
        "fee_note": "收费及知识赛安排以中山大学组织通知和赛事平台为准。",
        "recommendation_tier": "A",
        "priority": 94,
        "quality_note": "中国贸促会商业行业委员会官方通知；学生不能绕过院校负责人直报。",
    },
    "jingkaibei_smart_innovation_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "可由个人负责人直接在创赛云平台报名，也可通过院校通道；团队不超过8人。",
        "fee_note": "智能创新、青年创业赛道免费。",
        "recommendation_tier": "C",
        "priority": 55,
        "quality_note": "信息可核验但主办方为商业机构；作为补充赛事展示，降低推荐权重。",
    },
    "jingkaibei_youth_entrepreneurship_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "可由个人负责人直接在创赛云平台报名，也可通过院校通道；团队不超过8人。",
        "fee_note": "智能创新、青年创业赛道免费。",
        "recommendation_tier": "C",
        "priority": 55,
        "quality_note": "信息可核验但主办方为商业机构；作为补充赛事展示，降低推荐权重。",
    },
    "jingkaibei_innovation_entrepreneurship_ability_2026": {
        "participation_mode": "individual",
        "registration_mode": "direct",
        "registration_instructions": "由学生本人在创赛云平台参加测试赛或付费正式赛。",
        "fee_note": "测试赛免费；正式赛50元/项；与英语词汇赛联报80元；纸质证书另付费。",
        "recommendation_tier": "C",
        "priority": 20,
        "quality_note": "商业主办、付费、按固定分数段发证；仅作补充信息，不进入正式组队列表。",
    },
    "jingkaibei_english_vocabulary_2026": {
        "participation_mode": "individual",
        "registration_mode": "direct",
        "registration_instructions": "由学生本人在创赛云平台报名并参加线上闭卷答题。",
        "fee_note": "正式赛50元/项；与双创能力赛联报80元；纸质证书另付费。",
        "recommendation_tier": "C",
        "priority": 18,
        "quality_note": "商业主办、付费、按固定分数段发证；仅作补充信息，不进入正式组队列表。",
    },
    "shuzhilian_application_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "direct",
        "registration_instructions": "1至5名学生组成队伍后，在大赛官网报名并提交作品；允许跨校组队。",
        "fee_note": "官方学校通知明确不收报名费、参赛费。",
        "recommendation_tier": "B",
        "priority": 80,
        "quality_note": "学校官方转载通知和赛事官网相互印证；赛事为第3届，列B档持续观察。",
    },
    "waiyanshe_international_communication_sysu_2026": {
        "participation_mode": "individual",
        "registration_mode": "school_notice",
        "registration_instructions": "9月13日23:59前在大赛官网同时报名综合能力与演讲赛项；9月20日参加iTEST初赛并按中大通知上传演讲视频和稿件。",
        "fee_note": "中山大学校选赛通知未说明收费。",
        "recommendation_tier": "A",
        "priority": 85,
        "quality_note": "修正报名截止：官网报名为9月13日，9月20日是初赛/视频提交日。",
    },
    "waiyanshe_short_video_sysu_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "school_notice",
        "registration_instructions": "个人或不超过5人的团队先完成作品，再由队长于9月13日23:59前在官网报名并按中大通知提交。",
        "fee_note": "中山大学校选赛通知未说明收费。",
        "recommendation_tier": "A",
        "priority": 88,
        "quality_note": "中山大学官方通知；团队规模、校内提交和官网报名动作明确。",
    },
    "waiyanshe_four_new_sysu_2026": {
        "participation_mode": "individual_or_team",
        "registration_mode": "school_notice",
        "registration_instructions": "个人或不超过5人的中大同校团队于9月13日23:59前在官网报名，并提交英文研究报告和在线回答。",
        "fee_note": "中山大学校选赛通知未说明收费。",
        "recommendation_tier": "A",
        "priority": 86,
        "quality_note": "中山大学通知与大赛官网规则相互印证，适合跨专业同校组队。",
    },
    "waiyanshe_multilingual_sysu_2026": {
        "participation_mode": "individual",
        "registration_mode": "school_notice",
        "registration_instructions": "9月13日23:59前在大赛官网完成个人报名，并按中大通知将定题演讲视频和稿件上传至公务云盘。",
        "fee_note": "中山大学校选赛通知未说明收费。",
        "recommendation_tier": "A",
        "priority": 80,
        "quality_note": "中山大学官方通知；个人赛仅开放备赛搭子，不作为正式组队。",
    },
}


def apply_factual_fixes(item: dict) -> None:
    key = item["external_key"]
    if key == "cumcm_guangdong_2026":
        item["registration_url"] = item["source_url"]
    elif key == "ncccu_programming_2026":
        item["rewards"] = (
            "区域赛/省赛和国赛按科目评定一、二、三等奖并颁发电子荣誉证书；"
            "各科目前三名获奖学生税前奖金600元/名。"
        )
        item["required_skills"] = ["backend"]
    elif key == "waiyanshe_international_communication_sysu_2026":
        item["registration_deadline"] = "2026-09-13T23:59:00+08:00"
        item["stages"].insert(
            0,
            {
                "name": "中山大学官网报名",
                "start_at": "2026-07-13T00:00:00+08:00",
                "end_at": "2026-09-13T23:59:00+08:00",
                "mode": "online",
                "location": "外研社大赛官网",
                "note": "须同时报名综合能力赛项与演讲赛项",
            },
        )


def build() -> dict:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    output = deepcopy(source)
    output["snapshot_version"] = "competition-radar-cn-v1.1-2026-08-11"
    output["generated_at"] = VERIFIED_AT

    keys = {item["external_key"] for item in output["items"]}
    if keys != set(META):
        raise RuntimeError(
            f"QA metadata coverage mismatch: missing={sorted(keys - set(META))}, "
            f"extra={sorted(set(META) - keys)}"
        )

    rows: list[dict[str, str | int]] = []
    for item in output["items"]:
        meta = META[item["external_key"]]
        apply_factual_fixes(item)
        for field in (
            "participation_mode",
            "registration_mode",
            "registration_instructions",
            "fee_note",
            "recommendation_tier",
            "priority",
        ):
            item[field] = meta[field]
        item["verified_at"] = VERIFIED_AT
        rows.append(
            {
                "external_key": item["external_key"],
                "赛事名称": item["name"],
                "推荐等级": meta["recommendation_tier"],
                "参赛形态": meta["participation_mode"],
                "报名方式": meta["registration_mode"],
                "正式组队": "是" if item["team_size_max"] > 1 else "否（备赛搭子）",
                "优先级": meta["priority"],
                "官方来源": item["source_url"],
                "行动入口": item["registration_url"],
                "费用说明": meta["fee_note"],
                "核验时间": VERIFIED_AT,
                "验收结论": meta["quality_note"],
            }
        )

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    QUALITY_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with QUALITY_REVIEW.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{digest}  fixtures/{OUTPUT.name}\n", encoding="utf-8")
    return {
        "output": str(OUTPUT),
        "items": len(output["items"]),
        "tiers": {
            tier: sum(1 for row in rows if row["推荐等级"] == tier) for tier in "ABC"
        },
        "official_team": sum(1 for item in output["items"] if item["team_size_max"] > 1),
        "prep_partner": sum(1 for item in output["items"] if item["team_size_max"] == 1),
        "sha256": digest,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
