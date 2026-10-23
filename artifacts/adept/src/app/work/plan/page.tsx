import { WorkPlanView } from "@/features/org/work/components/WorkPlanView";
import { workOrg } from "@/features/org/work/org";

export default async function Page() {
  return <WorkPlanView org={await workOrg()} />;
}
