import { WorkHomeView } from "@/features/org/work/components/WorkHomeView";
import { workOrg } from "@/features/org/work/org";

export default async function Page() {
  return <WorkHomeView org={await workOrg()} />;
}
