import { asyncView } from "@/lib/next-compat/async-view";
import { WorkPlanView } from "@/features/org/work/components/WorkPlanView";
import { workOrg } from "@/features/org/work/org";

async function PageAsync() {
  return <WorkPlanView org={await workOrg()} />;
}

export default asyncView(PageAsync);
