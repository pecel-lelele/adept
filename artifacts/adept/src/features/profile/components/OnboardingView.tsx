import { asyncView } from "@/lib/next-compat/async-view";
import { ErrorState } from "@/components/ErrorState";
import { getAccount } from "@/lib/auth/account";

import { fetchMyProfile, fetchSkillCatalogue } from "../api";
import { IntakeWizard } from "./IntakeWizard";

/** Step 1 of the journey: a four-step intake that saves to the learner's profile. */
async function OnboardingViewAsync() {
  const [account, catalogue, profile] = await Promise.all([
    getAccount(),
    fetchSkillCatalogue(),
    fetchMyProfile(),
  ]);
  if (!catalogue.ok) return <ErrorState failure={catalogue} />;
  return (
    <IntakeWizard
      catalogue={catalogue.data.skills}
      interests={catalogue.data.interests ?? []}
      initial={account?.has_profile && profile.ok ? profile.data : null}
    />
  );
}

export const OnboardingView = asyncView(OnboardingViewAsync);
