import Foundation
import UIKit
import XCTest
@testable import ONE_MORE

final class ContractCoverageTests: XCTestCase {
    func testExactlySeventyFourFormalNodesPlusTwoComposites() {
        XCTAssertEqual(PrototypeScreenID.formalNodes.count, 74)
        XCTAssertEqual(PrototypeScreenID.allCases.count, 76)
        XCTAssertEqual(PrototypeScreenID.returnedReferences.count, 36)
        XCTAssertEqual(PrototypeScreenID.missingReturnedReferences.count, 40)
        XCTAssertEqual(Set(ScreenCatalog.all), Set(PrototypeScreenID.formalNodes.map(\.rawValue)))
        XCTAssertEqual(Set(PrototypeScreenID.allCases.map(\.route)).count, 76)
    }

    func testEveryFormalNodeHasTitleRouteAndGroup() {
        for node in PrototypeScreenID.formalNodes {
            XCTAssertFalse(node.title.isEmpty, node.rawValue)
            XCTAssertFalse(node.route.isEmpty, node.rawValue)
            XCTAssertNotEqual(node.group, .composite, node.rawValue)
        }
        XCTAssertEqual(PrototypeScreenID.b122.group, .composite)
        XCTAssertEqual(PrototypeScreenID.msg.group, .composite)
    }

    func testIntentCompileContractDecodesServerOwnedFields() throws {
        let json = #"{"data":{"card":{"id":"c1","status":"Draft","gathering_type":"competition","mode":"offline","goal":"完成作品","capabilities":[{"key":"backend","source":"verified"}],"required_roles":["frontend"],"intensity":"high","available_windows":[{"start_at":"2026-08-12T11:00:00Z","end_at":"2026-08-12T13:00:00Z","stability":0.9}],"campus":"east","min_size":2,"target_size":4,"social_mode":"reveal_after_confirm","competition_id":"comp-1","expires_at":"2026-08-14T15:59:00Z","field_sources":{"campus":"profile"},"clarification_rounds":1},"needs_clarification":true,"questions":[{"key":"availability","prompt":"时间？","input_type":"datetime_range"}],"max_rounds":2},"meta":{}}"#
        let value = try JSONDecoder.oneMore.decode(APIEnvelope<IntentCompileResult>.self, from: Data(json.utf8)).data
        XCTAssertTrue(value.needsClarification)
        XCTAssertEqual(value.maxRounds, 2)
        XCTAssertEqual(value.card.requiredRoles, ["frontend"])
        XCTAssertEqual(value.card.availableWindows.first?.stability, 0.9)
        XCTAssertEqual(value.card.fieldSources["campus"], "profile")
    }

    func testTasteQuestionsRequireSingleOptionIdentifiers() throws {
        let json = #"{"schema_version":"taste-quiz-v1","import_id":"taste-1","candidate_tags":[{"key":"sports","label":"运动","score":0.8}],"questions":[{"id":"q1","prompt":"更喜欢？","options":[{"id":"o1","label":"羽毛球"},{"id":"o2","label":"跑步"}],"required":true,"type":"single_choice"}],"optional":true,"calibrated":false,"min_answers":3,"max_answers":5,"intro":"答几题让画像更准","submit_path":"/profile/imports/taste-1/answers"}"#
        let value = try JSONDecoder.oneMore.decode(TasteQuestionSet.self, from: Data(json.utf8))
        XCTAssertEqual(value.questions.count, 1)
        XCTAssertEqual(value.questions[0].type, "single_choice")
        XCTAssertEqual(value.questions[0].options.map(\.id), ["o1", "o2"])
        XCTAssertEqual(value.optional, true)
        XCTAssertEqual(value.schemaVersion, "taste-quiz-v1")
        XCTAssertEqual(value.minimumSelections, 3)
        XCTAssertEqual(value.submitPath, "/profile/imports/taste-1/answers")
    }

    func testTasteProfileResultDecodesUnifiedShape() throws {
        let json = #"{"status":"READY","primary_tag":{"key":"explorer_builder","label":"探索型 Builder","score":0.3},"secondary_tags":[{"key":"knowledge_curator","label":"知识策展人","score":0.2}],"interest_domains":[{"key":"ai_programming","label":"AI / 编程","score":0.4}],"interest_facets":[{"domain":"ai_programming","facet":"hackathon","label":"黑客松","source":"llm"}],"dimensions":{"openness":0.4},"summary":"一句话","persona":"长文案","matching_hints":["一起做项目"],"confidence":0.65,"calibrated":false,"sample":{"items":100,"generation":"llm","llm_model":"deepseek-v4-flash"},"source":"douyin","model_version":"taste-v2","visibility":"private"}"#
        let value = try JSONDecoder.oneMore.decode(TasteProfileResult.self, from: Data(json.utf8))
        XCTAssertEqual(value.primaryTag.key, "explorer_builder")
        XCTAssertEqual(value.matchingHints, ["一起做项目"])
        XCTAssertEqual(value.sample?.generation, "llm")
        XCTAssertFalse(value.calibrated)
        XCTAssertEqual(value.interestFacets.first?.label, "黑客松")
    }

    func testTastePhoneLoginDecodesOnlyMaskedPhone() throws {
        let json = #"{"import_id":"taste-1","status":"WAITING_SMS_CODE","phone_masked":"138****8000","code_sent":true,"verified":false,"authenticated_at":null,"submit_code":"/profile/imports/taste-1/phone/verify","verify":"/profile/imports/taste-1/verify","error":null}"#
        let value = try JSONDecoder.oneMore.decode(TastePhoneLoginStatus.self, from: Data(json.utf8))
        XCTAssertEqual(value.phoneMasked, "138****8000")
        XCTAssertTrue(value.codeSent)
        XCTAssertFalse(value.verified)
    }

    func testTextImageAndLocationRequestsRemainDistinct() throws {
        let encoder = JSONEncoder.oneMore
        let text = try JSONSerialization.jsonObject(with: encoder.encode(TextMessageCreate(content: "hello"))) as! [String: Any]
        let image = try JSONSerialization.jsonObject(with: encoder.encode(ImageMessageCreate(image: .init(mediaId: "m1", caption: nil)))) as! [String: Any]
        let location = try JSONSerialization.jsonObject(with: encoder.encode(LocationMessageCreate(location: .init(latitude: 23.1, longitude: 113.3, label: "东校园", address: nil)))) as! [String: Any]
        XCTAssertEqual(text["content_type"] as? String, "text")
        XCTAssertEqual(image["content_type"] as? String, "image")
        XCTAssertEqual(location["content_type"] as? String, "location")
        XCTAssertNil(text["image"]); XCTAssertNil(image["location"]); XCTAssertNil(location["content"])
    }

    func testAllFiftySevenBundledFramesHaveProvenanceAndDecode() throws {
        struct Manifest: Decodable {
            struct State: Decodable {
                struct Frame: Decodable { let index: Int; let sha256: String }
                let state: String; let frames: [Frame]
            }
            let frameCount: Int; let states: [State]
        }
        let url = Bundle.main.url(forResource: "azou-frames-manifest", withExtension: "json")!
        let manifest = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: url))
        XCTAssertEqual(manifest.frameCount, 57)
        var checked = 0
        var provenance = Set<String>()
        for state in manifest.states {
            for frame in state.frames {
                let resource = "azou_\(state.state.replacingOccurrences(of: "-", with: "_"))_\(String(format: "%02d", frame.index))"
                let frameURL = Bundle.main.url(forResource: resource, withExtension: "png")!
                let data = try Data(contentsOf: frameURL)
                XCTAssertNotNil(UIImage(data: data), resource)
                XCTAssertFalse(data.isEmpty, resource)
                XCTAssertEqual(frame.sha256.count, 64, resource)
                XCTAssertNotNil(frame.sha256.range(of: "^[0-9a-f]{64}$", options: .regularExpression), resource)
                provenance.insert(frame.sha256)
                checked += 1
            }
        }
        XCTAssertEqual(checked, 57)
        XCTAssertEqual(provenance.count, 57)
    }

    func testAllRuntimeStateEvidenceKindsAreStableAndUnique() {
        XCTAssertEqual(RuntimeStateEvidence.allCases.count, 8)
        XCTAssertEqual(Set(RuntimeStateEvidence.allCases.map(\.rawValue)).count, 8)
        XCTAssertTrue(RuntimeStateEvidence.allCases.allSatisfy { !$0.title.isEmpty })
    }
}
