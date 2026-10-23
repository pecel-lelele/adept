import { useMemo, type ComponentType, type ReactNode } from "react";
import { Route, Switch, useLocation, useSearch, Router as WouterRouter } from "wouter";

import { ErrorBoundary } from "@/components/error-boundary";
import { PageSkeleton } from "@/components/shell/PageSkeleton";
import { getAuthMode, getSession } from "@/lib/auth/session";
import { asyncView, FallbackContext } from "@/lib/next-compat/async-view";
import { AppIntlProvider } from "@/lib/next-compat/intl";
import { redirect } from "@/lib/next-compat/router";
import { RouteBoundary } from "@/lib/next-compat/route-boundary";
import type { SearchParams } from "@/lib/scenario";
import NotFound from "@/pages/not-found";

import HomePage from "@/app/page";
import AboutPage from "@/app/about/page";
import TryPage from "@/app/try/page";

import AdminLayout from "@/app/admin/layout";
import AdminPage from "@/app/admin/page";
import AdminSnapshotsPage from "@/app/admin/snapshots/page";
import AdminSourcesPage from "@/app/admin/sources/page";

import AppLayout from "@/app/app/layout";
import AppPage from "@/app/app/page";
import AppCoursesPage from "@/app/app/courses/page";
import AppFundingPage from "@/app/app/funding/page";
import AppJobsPage from "@/app/app/jobs/page";
import AppJoinPage from "@/app/app/join/page";
import AppMatchesPage from "@/app/app/matches/page";
import AppMatchDetailPage from "@/app/app/matches/[roleId]/page";
import AppOnboardingPage from "@/app/app/onboarding/page";
import AppPathwayPage from "@/app/app/pathway/page";
import AppPathwayComparePage from "@/app/app/pathway/compare/page";
import AppProfilePage from "@/app/app/profile/page";
import AppProgressPage from "@/app/app/progress/page";
import AppRadarPage from "@/app/app/radar/page";
import AppSdgPage from "@/app/app/sdg/page";

import AuthLayout from "@/app/auth/layout";
import AuthEntryLayout from "@/app/auth/(entry)/layout";
import AuthLoginPage from "@/app/auth/(entry)/login/page";
import AuthSignupPage from "@/app/auth/(entry)/signup/page";
import AuthConsentPage from "@/app/auth/consent/page";
import AuthJoinPage from "@/app/auth/join/page";

import OrgLayout from "@/app/org/layout";
import OrgPage from "@/app/org/page";
import OrgCoursesPage from "@/app/org/courses/page";
import OrgFundingPage from "@/app/org/funding/page";
import OrgGapsPage from "@/app/org/gaps/page";
import OrgMembersPage from "@/app/org/members/page";
import OrgPlanPage from "@/app/org/plan/page";
import OrgProgrammesPage from "@/app/org/programmes/page";
import OrgProgrammesNewPage from "@/app/org/programmes/new/page";
import OrgRadarPage from "@/app/org/radar/page";
import OrgSdgPage from "@/app/org/sdg/page";
import OrgSetupPage from "@/app/org/setup/page";
import OrgVerifyPage from "@/app/org/verify/page";

import WorkLayout from "@/app/work/layout";
import WorkPage from "@/app/work/page";
import WorkFundingPage from "@/app/work/funding/page";
import WorkPlanPage from "@/app/work/plan/page";
import WorkProgressPage from "@/app/work/progress/page";
import WorkSkillsPage from "@/app/work/skills/page";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyPage = (props: any) => unknown;

function toSearchParams(search: string): SearchParams {
  const out: SearchParams = {};
  new URLSearchParams(search).forEach((value, key) => {
    const prev = out[key];
    out[key] = prev === undefined ? value : Array.isArray(prev) ? [...prev, value] : [prev, value];
  });
  return out;
}

/** Renders a Next page with Promise-wrapped params and searchParams, like the App Router. */
function PageRoute({ page: Page, params }: { page: AnyPage; params?: Record<string, string | undefined> }) {
  const search = useSearch();
  const paramsKey = JSON.stringify(params ?? {});
  const searchParams = useMemo(() => Promise.resolve(toSearchParams(search)), [search]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const routeParams = useMemo(() => Promise.resolve(JSON.parse(paramsKey)), [paramsKey]);
  const C = Page as ComponentType<{ params: unknown; searchParams: unknown }>;
  return <C params={routeParams} searchParams={searchParams} />;
}

function page(path: string, Page: AnyPage) {
  return (
    <Route key={path} path={path}>
      {(params) => <PageRoute page={Page} params={params as Record<string, string | undefined>} />}
    </Route>
  );
}

/** loading.tsx equivalent for a segment. */
function Loading({ children }: { children: ReactNode }) {
  return <FallbackContext.Provider value={<PageSkeleton />}>{children}</FallbackContext.Provider>;
}

/** Port of proxy.ts: workspace pages need a session before rendering. */
const WorkspaceGate = asyncView(async function WorkspaceGateAsync({
  pathname,
  search,
  children,
}: {
  pathname: string;
  search: string;
  children: ReactNode;
}) {
  const session = await getSession();
  if (getAuthMode() !== "supabase" && !session.authenticated) {
    const query = new URLSearchParams({
      mode: pathname.startsWith("/org") ? "organisation" : "individual",
      next: pathname + (search ? `?${search}` : ""),
    });
    redirect(`/auth/login?${query.toString()}`);
  }
  return <>{children}</>;
});

function Gate({ children }: { children: ReactNode }) {
  const [pathname] = useLocation();
  const search = useSearch();
  return (
    <WorkspaceGate pathname={pathname} search={search}>
      {children}
    </WorkspaceGate>
  );
}

function Routes() {
  return (
    <Switch>
      {page("/", HomePage)}
      {page("/about", AboutPage)}
      {page("/try", TryPage)}

      <Route path={/^\/admin(\/.*)?$/}>
        <Gate>
          <AdminLayout>
            <Switch>
              {page("/admin", AdminPage)}
              {page("/admin/snapshots", AdminSnapshotsPage)}
              {page("/admin/sources", AdminSourcesPage)}
              <Route component={NotFound} />
            </Switch>
          </AdminLayout>
        </Gate>
      </Route>

      <Route path={/^\/app(\/.*)?$/}>
        <Gate>
          <AppLayout>
            <Loading>
              <Switch>
                {page("/app", AppPage)}
                {page("/app/courses", AppCoursesPage)}
                {page("/app/funding", AppFundingPage)}
                {page("/app/jobs", AppJobsPage)}
                {page("/app/join", AppJoinPage)}
                {page("/app/matches", AppMatchesPage)}
                {page("/app/matches/:roleId", AppMatchDetailPage)}
                {page("/app/onboarding", AppOnboardingPage)}
                {page("/app/pathway", AppPathwayPage)}
                {page("/app/pathway/compare", AppPathwayComparePage)}
                {page("/app/profile", AppProfilePage)}
                {page("/app/progress", AppProgressPage)}
                {page("/app/radar", AppRadarPage)}
                {page("/app/sdg", AppSdgPage)}
                <Route component={NotFound} />
              </Switch>
            </Loading>
          </AppLayout>
        </Gate>
      </Route>

      <Route path={/^\/auth(\/.*)?$/}>
        <AuthLayout>
          <Switch>
            <Route path={/^\/auth\/(login|signup)$/}>
              <AuthEntryLayout>
                <Switch>
                  {page("/auth/login", AuthLoginPage)}
                  {page("/auth/signup", AuthSignupPage)}
                </Switch>
              </AuthEntryLayout>
            </Route>
            {page("/auth/consent", AuthConsentPage)}
            {page("/auth/join", AuthJoinPage)}
            <Route component={NotFound} />
          </Switch>
        </AuthLayout>
      </Route>

      <Route path={/^\/org(\/.*)?$/}>
        <Gate>
          <OrgLayout>
            <Loading>
              <Switch>
                {page("/org", OrgPage)}
                {page("/org/courses", OrgCoursesPage)}
                {page("/org/funding", OrgFundingPage)}
                {page("/org/gaps", OrgGapsPage)}
                {page("/org/members", OrgMembersPage)}
                {page("/org/plan", OrgPlanPage)}
                {page("/org/programmes", OrgProgrammesPage)}
                {page("/org/programmes/new", OrgProgrammesNewPage)}
                {page("/org/radar", OrgRadarPage)}
                {page("/org/sdg", OrgSdgPage)}
                {page("/org/setup", OrgSetupPage)}
                {page("/org/verify", OrgVerifyPage)}
                <Route component={NotFound} />
              </Switch>
            </Loading>
          </OrgLayout>
        </Gate>
      </Route>

      <Route path={/^\/work(\/.*)?$/}>
        <Gate>
          <WorkLayout>
            <Loading>
              <Switch>
                {page("/work", WorkPage)}
                {page("/work/funding", WorkFundingPage)}
                {page("/work/plan", WorkPlanPage)}
                {page("/work/progress", WorkProgressPage)}
                {page("/work/skills", WorkSkillsPage)}
                <Route component={NotFound} />
              </Switch>
            </Loading>
          </WorkLayout>
        </Gate>
      </Route>

      <Route component={NotFound} />
    </Switch>
  );
}

function Boundaries() {
  const [location] = useLocation();
  return (
    <ErrorBoundary resetKey={location}>
      <RouteBoundary location={location}>
        <Routes />
      </RouteBoundary>
    </ErrorBoundary>
  );
}

function App() {
  return (
    <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <AppIntlProvider>
        <Boundaries />
      </AppIntlProvider>
    </WouterRouter>
  );
}

export default App;
