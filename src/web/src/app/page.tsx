import { DataFreshnessBadge, LocaleSwitcher } from "@/components";
import { LandingView } from "@/features/core";

export default function Page() {
  return <LandingView freshness={<DataFreshnessBadge />} localeSwitcher={<LocaleSwitcher />} />;
}
