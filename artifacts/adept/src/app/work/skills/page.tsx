import { asyncView } from "@/lib/next-compat/async-view";
import { SharingView } from "@/features/org/work/components/SharingView";
import { workOrg } from "@/features/org/work/org";

async function PageAsync() {
  return <SharingView org={await workOrg()} />;
}

export default asyncView(PageAsync);
