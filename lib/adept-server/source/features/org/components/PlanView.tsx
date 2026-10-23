import type { ScenarioId } from "@/lib/api";
import { PackagesView } from "./PackagesView";

export function PlanView(props: { scenario: ScenarioId; roleId?: string; memberIds?: string[] }) {
  return <PackagesView {...props} />;
}
