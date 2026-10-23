import { SharingView } from "@/features/org/work/components/SharingView";
import { workOrg } from "@/features/org/work/org";

export default async function Page() {
  return <SharingView org={await workOrg()} />;
}
