import { asyncView } from "@/lib/next-compat/async-view";
import { WorkHomeView } from "@/features/org/work/components/WorkHomeView";
import { workOrg } from "@/features/org/work/org";

async function PageAsync() {
  return <WorkHomeView org={await workOrg()} />;
}

export default asyncView(PageAsync);
