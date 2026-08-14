import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { PhoneFrame } from "./components/shell/PhoneFrame";
import { TabBar } from "./components/shell/TabBar";
import {
  AuthOnly,
  SocialAccessGate,
} from "./components/shell/SocialAccessGate";
import { useApp } from "./app/AppContext";
import {
  AuthFactsScreen,
  AuthGrantsScreen,
  AuthIntroScreen,
  AuthScanScreen,
  AuthSocialScreen,
  AuthTasteScreen,
  BootScreen,
  OnboardingGuideScreen,
  PhoneAuthScreen,
} from "./screens/auth/AuthScreens";
import {
  AssignmentDetailScreen,
  AssignmentsScreen,
  CourseDetailScreen,
  EventDetailScreen,
  EventsScreen,
  GymScreen,
  HermesAskScreen,
  PersonalActionPreviewScreen,
  ResearchScreen,
  RoomScreen,
  SceneTriggerScreen,
  TimetableScreen,
  TodayScreen,
  TransitScreen,
} from "./screens/today/TodayScreens";
import {
  CompetitionDetailScreen,
  CompetitionTableScreen,
  CompetitionTeamDetailScreen,
  CompetitionsScreen,
} from "./screens/competitions/CompetitionsScreens";
import {
  IntentAvailabilityScreen,
  IntentCapabilitiesScreen,
  IntentComposerScreen,
  IntentRolesScreen,
  IntentSafetyScreen,
} from "./screens/intent/IntentScreens";
import {
  GatheringDetailScreen,
  InitiateGatheringScreen,
  MyGatheringsScreen,
  OpenGatheringsScreen,
  SafetyHistoryScreen,
  ShareLandingScreen,
  TrustRequirementScreen,
} from "./screens/gatherings/GatheringScreens";
import { ChannelScreen, MessagesScreen } from "./screens/messages/MessagesScreens";
import {
  AccountScreen,
  AppealsScreen,
  BlockListScreen,
  GrantsScreen,
  MatchingPreferencesScreen,
  NotificationSettingsScreen,
  PrivacyScreen,
  ProfileEditorScreen,
  ProfileScreen,
  RecapScreen,
  DisplayNameScreen,
  TrustScreen,
} from "./screens/profile/ProfileScreens";
import {
  RelationDetailScreen,
  RelationsScreen,
  SharedGoalsScreen,
} from "./screens/relations/RelationsScreens";
import {
  OrganizerCreateScreen,
  OrganizerDashboardScreen,
  OrganizerScreen,
  OrganizerTemplatesScreen,
} from "./screens/organizer/OrganizerScreens";
import { DemoTasteScreen } from "./screens/taste/DemoTasteScreen";
import { TasteImportScreen } from "./screens/taste/TasteImportScreen";
import {
  PermissionNoticeScreen,
  StatesLibraryScreen,
} from "./screens/shared/SharedScreens";
import { LandingScreen } from "./screens/landing/LandingScreen";
import {
  PrivacyPolicyScreen,
  TermsScreen,
} from "./screens/landing/LegalScreens";

const TAB_PREFIXES = [
  "/today",
  "/competitions",
  "/intent",
  "/messages",
  "/me",
];

/** 营销页（Landing / 法律文档）：全宽文档流，不套手机壳。 */
function isMarketingRoute(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname === "/legal" ||
    pathname.startsWith("/legal/")
  );
}

/** 评委公开体验：免登录，独立全页，不套 App 壳。 */
function isPublicDemoRoute(pathname: string): boolean {
  return pathname === "/demo/taste" || pathname.startsWith("/demo/taste/");
}

function usesTabBar(pathname: string): boolean {
  if (
    pathname.startsWith("/auth") ||
    pathname === "/" ||
    pathname === "/app" ||
    pathname.startsWith("/g/")
  ) {
    return false;
  }
  if (pathname.startsWith("/channel/")) return false;
  if (TAB_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return true;
  }
  if (
    pathname.startsWith("/gatherings") ||
    pathname.startsWith("/gathering") ||
    pathname.startsWith("/relations") ||
    pathname.startsWith("/relation") ||
    pathname.startsWith("/organizer") ||
    pathname.startsWith("/competition") ||
    pathname.startsWith("/goal")
  ) {
    return true;
  }
  return false;
}

export default function App() {
  const { shellMode } = useApp();
  const location = useLocation();
  const showTabs = usesTabBar(location.pathname);

  if (isMarketingRoute(location.pathname)) {
    return (
      <Routes>
        <Route path="/" element={<LandingScreen />} />
        <Route path="/legal/privacy" element={<PrivacyPolicyScreen />} />
        <Route path="/legal/terms" element={<TermsScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  if (isPublicDemoRoute(location.pathname)) {
    return (
      <Routes>
        <Route path="/demo/taste" element={<DemoTasteScreen />} />
        <Route path="*" element={<Navigate to="/demo/taste" replace />} />
      </Routes>
    );
  }

  return (
    <PhoneFrame mode={shellMode}>
      <div
        className={`app-main ${showTabs ? "has-tabs" : ""}`}
        data-od-id="app-root"
        data-screen="app-root"
      >
        <Routes>
          <Route path="/app" element={<BootScreen />} />
          <Route path="/onboarding" element={<OnboardingGuideScreen />} />
          <Route path="/auth" element={<AuthIntroScreen />} />
          <Route path="/auth/phone" element={<PhoneAuthScreen />} />
          <Route path="/auth/scan" element={<AuthScanScreen />} />
          <Route path="/auth/grants" element={<AuthGrantsScreen />} />
          <Route path="/auth/facts" element={<AuthFactsScreen />} />
          <Route path="/auth/social" element={<AuthSocialScreen />} />
          <Route path="/auth/taste" element={<AuthTasteScreen />} />

          <Route path="/today" element={<TodayScreen />} />
          <Route
            path="/today/ask"
            element={
              <AuthOnly title="登录后才能问噜噜">
                <HermesAskScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/timetable"
            element={
              <AuthOnly title="登录后才能看课表">
                <TimetableScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/course/:courseId"
            element={
              <AuthOnly title="登录后才能看课程">
                <CourseDetailScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/assignments"
            element={
              <AuthOnly title="登录后才能看作业">
                <AssignmentsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/assignment/:assignmentId"
            element={
              <AuthOnly title="登录后才能看作业">
                <AssignmentDetailScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/gym"
            element={
              <AuthOnly title="登录后才能订场">
                <GymScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/room"
            element={
              <AuthOnly title="登录后才能订研讨室">
                <RoomScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/events"
            element={
              <AuthOnly title="登录后才能看校园活动">
                <EventsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/event/:eventId"
            element={
              <AuthOnly title="登录后才能看活动详情">
                <EventDetailScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/research"
            element={
              <AuthOnly title="登录后才能看组会课题">
                <ResearchScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/transit"
            element={
              <AuthOnly title="登录后才能查班车">
                <TransitScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/scene"
            element={
              <AuthOnly title="登录后才能看场景提醒">
                <SceneTriggerScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/today/action-preview"
            element={
              <AuthOnly title="登录后才能预览行动">
                <PersonalActionPreviewScreen />
              </AuthOnly>
            }
          />

          <Route
            path="/competitions"
            element={
              <AuthOnly
                title="登录后才能看活动"
                subtitle="比赛组队、公开局和校园活动报名都需要先登录。"
              >
                <CompetitionsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/competition/:competitionId"
            element={
              <AuthOnly title="登录后才能看赛事">
                <CompetitionDetailScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/competition/:competitionId/table"
            element={
              <AuthOnly title="登录后才能组队">
                <CompetitionTableScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/competition/:competitionId/team/:teamId"
            element={
              <AuthOnly title="登录后才能看队伍">
                <CompetitionTeamDetailScreen />
              </AuthOnly>
            }
          />

          <Route
            path="/intent"
            element={
              <SocialAccessGate
                title="登录后才能发布意图"
                subtitle="差一个、加入局和找搭子都需要先登录。"
              >
                <IntentComposerScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/intent/capabilities"
            element={
              <SocialAccessGate title="登录后才能发布意图">
                <IntentCapabilitiesScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/intent/availability"
            element={
              <SocialAccessGate title="登录后才能发布意图">
                <IntentAvailabilityScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/intent/roles"
            element={
              <SocialAccessGate title="登录后才能发布意图">
                <IntentRolesScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/intent/safety"
            element={
              <SocialAccessGate title="登录后才能发布意图">
                <IntentSafetyScreen />
              </SocialAccessGate>
            }
          />

          <Route
            path="/gatherings/open"
            element={
              <AuthOnly title="登录后才能看公开局">
                <OpenGatheringsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/gatherings/mine"
            element={
              <AuthOnly title="登录后才能看我的局">
                <MyGatheringsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/gatherings/initiate"
            element={
              <AuthOnly title="登录后才能发起局">
                <InitiateGatheringScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/gathering/:gatheringId"
            element={
              <AuthOnly title="登录后才能进入局">
                <GatheringDetailScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/gathering/:gatheringId/trust"
            element={
              <AuthOnly title="登录后才能查看信任门槛">
                <TrustRequirementScreen />
              </AuthOnly>
            }
          />
          <Route path="/g/:shareToken" element={<ShareLandingScreen />} />

          <Route
            path="/messages"
            element={
              <SocialAccessGate
                title="登录后才能看消息"
                subtitle="局内聊天和系统通知都需要先登录。"
              >
                <MessagesScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/channel/:channelId"
            element={
              <SocialAccessGate title="登录后才能进群聊">
                <ChannelScreen />
              </SocialAccessGate>
            }
          />

          <Route
            path="/me"
            element={
              <AuthOnly
                title="登录后打开「我的」"
                subtitle="画像、授权和设置都需要先登录。"
              >
                <ProfileScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/profile"
            element={
              <AuthOnly title="登录后才能编辑资料">
                <ProfileEditorScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/nickname"
            element={
              <AuthOnly title="登录后才能改昵称">
                <DisplayNameScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/trust"
            element={
              <AuthOnly title="登录后才能看信任进度">
                <TrustScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/grants"
            element={
              <AuthOnly title="登录后才能管理授权">
                <GrantsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/privacy"
            element={
              <AuthOnly title="登录后才能管理社交开关">
                <PrivacyScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/preferences"
            element={
              <AuthOnly title="登录后才能设置匹配偏好">
                <MatchingPreferencesScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/notifications"
            element={
              <AuthOnly title="登录后才能设置通知">
                <NotificationSettingsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/blocks"
            element={
              <AuthOnly title="登录后才能管理拉黑">
                <BlockListScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/appeals"
            element={
              <AuthOnly title="登录后才能看申诉">
                <AppealsScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/account"
            element={
              <AuthOnly title="登录后才能管理账号">
                <AccountScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/taste"
            element={
              <AuthOnly title="登录后才能导入兴趣画像">
                <TasteImportScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/safety-history"
            element={
              <AuthOnly title="登录后才能看安全记录">
                <SafetyHistoryScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/me/recap"
            element={
              <AuthOnly title="登录后才能看复盘">
                <RecapScreen />
              </AuthOnly>
            }
          />

          <Route
            path="/relations"
            element={
              <SocialAccessGate title="登录后才能看搭子关系">
                <RelationsScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/relation/:relationId"
            element={
              <SocialAccessGate title="登录后才能看搭子关系">
                <RelationDetailScreen />
              </SocialAccessGate>
            }
          />
          <Route
            path="/goal/:relationId"
            element={
              <SocialAccessGate title="登录后才能看共同目标">
                <SharedGoalsScreen />
              </SocialAccessGate>
            }
          />

          <Route
            path="/organizer"
            element={
              <AuthOnly title="登录后才能打开主理人台">
                <OrganizerScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/organizer/create"
            element={
              <AuthOnly title="登录后才能创建官方局">
                <OrganizerCreateScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/organizer/gatherings/:gatheringId/dashboard"
            element={
              <AuthOnly title="登录后才能打开主理人台">
                <OrganizerDashboardScreen />
              </AuthOnly>
            }
          />
          <Route
            path="/organizer/templates"
            element={
              <AuthOnly title="登录后才能使用官方模板">
                <OrganizerTemplatesScreen />
              </AuthOnly>
            }
          />

          <Route path="/states" element={<StatesLibraryScreen />} />
          <Route path="/permission" element={<PermissionNoticeScreen />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        {showTabs ? <TabBar /> : null}
      </div>
    </PhoneFrame>
  );
}
