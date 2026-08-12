import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { PhoneFrame } from "./components/shell/PhoneFrame";
import { TabBar } from "./components/shell/TabBar";
import { useApp } from "./app/AppContext";
import {
  AuthFactsScreen,
  AuthGrantsScreen,
  AuthIntroScreen,
  AuthScanScreen,
  AuthSocialScreen,
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

          <Route path="/today" element={<TodayScreen />} />
          <Route path="/today/ask" element={<HermesAskScreen />} />
          <Route path="/today/timetable" element={<TimetableScreen />} />
          <Route path="/today/course/:courseId" element={<CourseDetailScreen />} />
          <Route path="/today/assignments" element={<AssignmentsScreen />} />
          <Route
            path="/today/assignment/:assignmentId"
            element={<AssignmentDetailScreen />}
          />
          <Route path="/today/gym" element={<GymScreen />} />
          <Route path="/today/room" element={<RoomScreen />} />
          <Route path="/today/events" element={<EventsScreen />} />
          <Route path="/today/event/:eventId" element={<EventDetailScreen />} />
          <Route path="/today/research" element={<ResearchScreen />} />
          <Route path="/today/transit" element={<TransitScreen />} />
          <Route path="/today/scene" element={<SceneTriggerScreen />} />
          <Route
            path="/today/action-preview"
            element={<PersonalActionPreviewScreen />}
          />

          <Route path="/competitions" element={<CompetitionsScreen />} />
          <Route
            path="/competition/:competitionId"
            element={<CompetitionDetailScreen />}
          />
          <Route
            path="/competition/:competitionId/table"
            element={<CompetitionTableScreen />}
          />

          <Route path="/intent" element={<IntentComposerScreen />} />
          <Route path="/intent/capabilities" element={<IntentCapabilitiesScreen />} />
          <Route path="/intent/availability" element={<IntentAvailabilityScreen />} />
          <Route path="/intent/roles" element={<IntentRolesScreen />} />
          <Route path="/intent/safety" element={<IntentSafetyScreen />} />

          <Route path="/gatherings/open" element={<OpenGatheringsScreen />} />
          <Route path="/gatherings/mine" element={<MyGatheringsScreen />} />
          <Route path="/gatherings/initiate" element={<InitiateGatheringScreen />} />
          <Route path="/gathering/:gatheringId" element={<GatheringDetailScreen />} />
          <Route
            path="/gathering/:gatheringId/trust"
            element={<TrustRequirementScreen />}
          />
          <Route path="/g/:shareToken" element={<ShareLandingScreen />} />

          <Route path="/messages" element={<MessagesScreen />} />
          <Route path="/channel/:channelId" element={<ChannelScreen />} />

          <Route path="/me" element={<ProfileScreen />} />
          <Route path="/me/profile" element={<ProfileEditorScreen />} />
          <Route path="/me/trust" element={<TrustScreen />} />
          <Route path="/me/grants" element={<GrantsScreen />} />
          <Route path="/me/privacy" element={<PrivacyScreen />} />
          <Route path="/me/preferences" element={<MatchingPreferencesScreen />} />
          <Route path="/me/notifications" element={<NotificationSettingsScreen />} />
          <Route path="/me/blocks" element={<BlockListScreen />} />
          <Route path="/me/appeals" element={<AppealsScreen />} />
          <Route path="/me/account" element={<AccountScreen />} />
          <Route path="/me/taste" element={<TasteImportScreen />} />
          <Route path="/me/safety-history" element={<SafetyHistoryScreen />} />
          <Route path="/me/recap" element={<RecapScreen />} />

          <Route path="/relations" element={<RelationsScreen />} />
          <Route path="/relation/:relationId" element={<RelationDetailScreen />} />
          <Route path="/goal/:relationId" element={<SharedGoalsScreen />} />

          <Route path="/organizer" element={<OrganizerScreen />} />
          <Route path="/organizer/create" element={<OrganizerCreateScreen />} />
          <Route
            path="/organizer/gatherings/:gatheringId/dashboard"
            element={<OrganizerDashboardScreen />}
          />
          <Route path="/organizer/templates" element={<OrganizerTemplatesScreen />} />

          <Route path="/states" element={<StatesLibraryScreen />} />
          <Route path="/permission" element={<PermissionNoticeScreen />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        {showTabs ? <TabBar /> : null}
      </div>
    </PhoneFrame>
  );
}
