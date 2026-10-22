// Type-checks translation keys against the English messages.
import type common from "../../../messages/en/common.json";
import type guardrails from "../../../messages/en/guardrails.json";
import type matching from "../../../messages/en/matching.json";
import type org from "../../../messages/en/org.json";
import type pathway from "../../../messages/en/pathway.json";
import type profile from "../../../messages/en/profile.json";
import type scenarios from "../../../messages/en/scenarios.json";
import type sdg from "../../../messages/en/sdg.json";
import type trends from "../../../messages/en/trends.json";
import type ui from "../../../messages/en/ui.json";

import type { Locale } from "./config";

declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: {
      common: typeof common;
      trends: typeof trends;
      scenarios: typeof scenarios;
      profile: typeof profile;
      matching: typeof matching;
      pathway: typeof pathway;
      sdg: typeof sdg;
      org: typeof org;
      guardrails: typeof guardrails;
      ui: typeof ui;
    };
  }
}
