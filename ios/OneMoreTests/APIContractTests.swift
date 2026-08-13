import XCTest
@testable import ONE_MORE

final class APIContractTests: XCTestCase {
    func testCampusDayCodecKeepsShanghaiCivilDayAtEveryBoundary() throws {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        let midnight = try XCTUnwrap(formatter.date(from: "2026-08-12T16:00:00Z"))
        let earlyMorning = try XCTUnwrap(formatter.date(from: "2026-08-12T21:30:00Z"))
        let lateNight = try XCTUnwrap(formatter.date(from: "2026-08-13T15:59:00Z"))
        XCTAssertEqual(CampusDayCodec.string(from: midnight), "2026-08-13")
        XCTAssertEqual(CampusDayCodec.string(from: earlyMorning), "2026-08-13")
        XCTAssertEqual(CampusDayCodec.string(from: lateNight), "2026-08-13")
    }

    func testHTTP200FailedCampusActionNeverMapsToSuccess() {
        XCTAssertEqual(
            CampusActionExecutionDisposition.resolve(
                status: "failed", errorCategory: "resource_conflict"
            ),
            .chooseAnotherResource
        )
        XCTAssertEqual(
            CampusActionExecutionDisposition.resolve(
                status: "failed", errorCategory: "login_expired"
            ),
            .reauthenticate
        )
        XCTAssertEqual(
            CampusActionExecutionDisposition.resolve(
                status: "succeeded", errorCategory: nil
            ),
            .succeeded
        )
        XCTAssertEqual(
            CampusActionExecutionDisposition.recoveryScreen(
                actionName: "room.reserve_preview"
            ),
            "B6"
        )
        XCTAssertEqual(
            CampusActionExecutionDisposition.recoveryScreen(
                actionName: "gym.book_preview"
            ),
            "B5"
        )
    }

    func testCampusEventAcceptsNullableSchedule() throws {
        let json = #"{"id":"e-null","type":"lecture","title":"时间待定活动","starts_at":null,"ends_at":null,"location":null,"official_url":null,"details":{},"registration_mode":"official_link_only"}"#
        let event = try JSONDecoder.oneMore.decode(CampusEvent.self, from: Data(json.utf8))
        XCTAssertNil(event.startsAt)
        XCTAssertNil(event.endsAt)
        XCTAssertEqual(event.title, "时间待定活动")
        XCTAssertEqual(event.displayType, "讲座")
    }

    func testCampusEventMapsLegacyEnglishTypesToChinese() throws {
        let json = #"{"id":"e-teachin","type":"teachin","title":"校招宣讲","starts_at":null,"ends_at":null,"location":null,"official_url":null,"details":{},"registration_mode":"official_link_only"}"#
        let event = try JSONDecoder.oneMore.decode(CampusEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.displayType, "宣讲")
    }

    func testLeaveEndpointMinimalAuthoritativeResultDecodes() throws {
        let payload = #"{"id":"g-1","status":"Dissolved"}"#.data(using: .utf8)!
        let result = try JSONDecoder.oneMore.decode(GatheringLeaveResult.self, from: payload)
        XCTAssertEqual(result.id, "g-1")
        XCTAssertEqual(result.status, .dissolved)
    }

    func testSuccessEnvelopeSnakeCaseAndFractionalUTCDate() throws {
        let data = #"{"data":{"id":"m1","channel_id":"c1","sender_id":"u1","sender_type":"human","content_type":"text","content":"你好","image":null,"location":null,"sent_at":"2026-08-11T14:08:35.089313Z"},"meta":{"source":"live"}}"#.data(using: .utf8)!
        let envelope = try JSONDecoder.oneMore.decode(APIEnvelope<MessagePayload>.self, from: data)
        XCTAssertEqual(envelope.data.channelId, "c1")
        XCTAssertEqual(envelope.data.content, "你好")
        XCTAssertNotNil(envelope.data.sentAt)
        XCTAssertEqual(envelope.meta["source"], .string("live"))
    }

    func testErrorEnvelopePreservesRequestIDAndDetails() throws {
        let data = #"{"error":{"code":"INTENT_NOT_EDITABLE","message":"当前意图不可编辑","details":{"status":"Pooling"},"request_id":"req-123"}}"#.data(using: .utf8)!
        let value = try JSONDecoder.oneMore.decode(APIErrorEnvelope.self, from: data).error
        XCTAssertEqual(value.code, "INTENT_NOT_EDITABLE")
        XCTAssertEqual(value.requestId, "req-123")
        XCTAssertEqual(value.details["status"], .string("Pooling"))
    }

    func testUnknownGatheringEnumFallsBackWithoutDecodeFailure() throws {
        let data = Data(#""future_server_state""#.utf8)
        XCTAssertEqual(try JSONDecoder().decode(GatheringStatus.self, from: data), .unknown)
    }

    func testNotificationPreferenceRoundTripUsesSnakeCase() throws {
        let value = NotificationPreferences(
            overallEnabled: true,
            calendarSyncEnabled: false,
            categories: .init(gatheringUpdates: true, actionUpdates: false, chatMessages: true, trustUpdates: true, competitionDeadlines: false, scheduleReminders: true),
            systemSettingsManagedLocally: ["focus_mode"]
        )
        let data = try JSONEncoder.oneMore.encode(value)
        let string = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(string.contains("calendar_sync_enabled"))
        XCTAssertEqual(try JSONDecoder.oneMore.decode(NotificationPreferences.self, from: data).categories.actionUpdates, false)
        XCTAssertEqual(try JSONDecoder.oneMore.decode(NotificationPreferences.self, from: data).categories.scheduleReminders, true)
        let legacy = #"{"overall_enabled":true,"calendar_sync_enabled":false,"categories":{"gathering_updates":true,"action_updates":true,"chat_messages":true,"trust_updates":true,"competition_deadlines":true},"system_settings_managed_locally":[]}"#.data(using: .utf8)!
        XCTAssertEqual(try JSONDecoder.oneMore.decode(NotificationPreferences.self, from: legacy).categories.scheduleReminders, true)
        let inbox = try JSONDecoder.oneMore.decode(
            InboxNotification.self,
            from: Data(#"{"id":"n1","type":"schedule_reminder","category":"schedule_reminders","title":"课表快到了","payload":{"summary":"「高数」还有 30 分钟就要上课","deep_link":"onemore://screen/B3"},"created_at":"2026-08-13T01:00:00Z","delivered_at":null}"#.utf8)
        )
        XCTAssertEqual(inbox.summary.contains("高数"), true)
        XCTAssertEqual(inbox.categoryLabel, "日程")
        XCTAssertEqual(inbox.resolvedCategory, "schedule_reminders")
    }

    func testSharedGoalDecodesAutomaticProgressContract() throws {
        let payload = #"{"id":"goal-1","relation_id":"rel-1","definition":"一起自习","period_start":"2026-08-01","period_end":"2026-08-31","target_value":4,"current_value":1,"unit":"次","status":"active","milestones":[{"fraction":0.25,"target_value":1,"reached":true,"reached_at":"2026-08-11T12:00:00Z"}],"member_progress":[{"user_id":"u1","display_name":"小林","current_value":2,"last_progress_at":"2026-08-11T12:00:00Z"}],"next_action":"周五图书馆见","last_broadcast":"已自动更新","last_progress_at":"2026-08-11T12:00:00Z","progress_source":"attendance_and_completion"}"#.data(using: .utf8)!
        let goal = try JSONDecoder.oneMore.decode(SharedGoal.self, from: payload)
        XCTAssertEqual(goal.currentValue, 1)
        XCTAssertEqual(goal.milestones.first?.reached, true)
        XCTAssertEqual(goal.memberProgress.first?.currentValue, 2)
        XCTAssertEqual(goal.nextAction, "周五图书馆见")
        XCTAssertEqual(goal.progressSource, "attendance_and_completion")
    }

    func testAnonymousRescheduleProposalContractDecodesWithoutVoterIdentities() throws {
        let payload = #"{"proposal_id":"rp-1","gathering_id":"g-1","status":"open","start_at":"2026-08-18T11:00:00Z","end_at":"2026-08-18T13:00:00Z","feasible_count":4,"accepted_count":2,"required_count":4,"my_vote":"accepted","expires_at":"2026-08-11T13:00:00Z","decided_at":null}"#.data(using: .utf8)!
        let proposal = try JSONDecoder.oneMore.decode(RescheduleProposal.self, from: payload)
        XCTAssertEqual(proposal.id, "rp-1")
        XCTAssertEqual(proposal.acceptedCount, 2)
        XCTAssertEqual(proposal.requiredCount, 4)
        XCTAssertEqual(proposal.myVote, "accepted")
    }

    func testPrivateRecurrenceDecisionContractDecodesCloneRoute() throws {
        let payload = #"{"decision":"partial","kept_user_ids":["u1","u2"],"clone_gathering_id":"g-next"}"#.data(using: .utf8)!
        let decision = try JSONDecoder.oneMore.decode(
            GatheringSummary.RecurrenceDecision.self, from: payload
        )
        XCTAssertEqual(decision.decision, "partial")
        XCTAssertEqual(decision.keptUserIds, ["u1", "u2"])
        XCTAssertEqual(decision.cloneGatheringId, "g-next")
    }

    func testCompetitionTeamGapCopyUsesMissingRolesAndSeatCount() throws {
        let json = """
        {"id":"t-1","title":"数模组队差建模","gathering_type":"比赛组队","status":"Pooling","location":null,"campus":"东校园","start_at":null,"target_size":3,"member_count":2,"required_roles":["modeling"],"expires_at":null,"goal":"差一个建模","missing_count":1,"missing_roles":["modeling"],"filled_roles":["编程","写作"]}
        """
        let team = try JSONDecoder.oneMore.decode(CompetitionTeam.self, from: Data(json.utf8))
        XCTAssertEqual(team.filled, 2)
        XCTAssertEqual(team.resolvedMissingCount, 1)
        XCTAssertEqual(team.gapDescription, "差一个建模")
        XCTAssertEqual(team.filledRoles, ["编程", "写作"])
    }

    func testCampusActionCopyTurnsGymPreviewIntoChineseCard() throws {
        let copy = try XCTUnwrap(
            CampusActionCopy.make(
                actionName: "gym.book_preview",
                params: [
                    "date": .string("2026-08-13"),
                    "end": .string("21:00"),
                    "start": .string("19:00"),
                    "venue": .string("珠海校区"),
                    "venue_type": .string("篮球"),
                    "next": .string("/actions/preview"),
                ],
                status: "previewed"
            )
        )
        XCTAssertEqual(copy.title, "预约篮球")
        XCTAssertEqual(copy.headline, "珠海校区 · 篮球")
        XCTAssertEqual(copy.sticker, "basketball.png")
        XCTAssertEqual(copy.statusLabel, "待确认")
        XCTAssertEqual(copy.facts.map(\.label), ["地点", "时段"])
        XCTAssertEqual(copy.facts.first { $0.label == "地点" }?.value, "珠海校区")
        XCTAssertEqual(copy.facts.first { $0.label == "时段" }?.value, "19:00 – 21:00")
        XCTAssertTrue(copy.timeLine?.contains("19:00") == true)
        let blob = ([copy.title, copy.headline] + copy.facts.flatMap { [$0.label, $0.value] }).joined()
        XCTAssertFalse(blob.contains("gym.book_preview"))
        XCTAssertFalse(blob.contains("params."))
        XCTAssertFalse(blob.contains("venue_type"))
        XCTAssertFalse(blob.contains("/actions/preview"))
    }

    func testCampusActionCopyReadsHermesPreviewPayload() throws {
        let result = HermesAskResult(
            kind: "action_preview",
            action: "gym.book_preview",
            cardType: "action_preview",
            data: .object([
                "next": .string("/actions/preview"),
                "message": .string("今晚可以约"),
                "params": .object([
                    "venue_type": .string("篮球"),
                    "venue": .string("珠海校区"),
                    "date": .string("2026-08-13"),
                    "start": .string("19:00"),
                    "end": .string("21:00"),
                ]),
            ]),
            requiresPreview: true,
            toolTrace: nil
        )
        let copy = try XCTUnwrap(CampusActionCopy.make(from: result))
        XCTAssertEqual(copy.title, "预约篮球")
        XCTAssertFalse(copy.facts.contains(where: { $0.value.contains("preview") }))
    }
}
