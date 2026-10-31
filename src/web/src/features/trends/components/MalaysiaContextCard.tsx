import { call, getApi } from "@/lib/api";
import { MalaysiaContextPanel } from "./MalaysiaContextPanel";
import "./malaysia-context.css";

/** National survey context is stored data; it is never presented as a role forecast. */
export async function MalaysiaContextCard() {
  const api = await getApi();
  const result = await call(api.GET("/api/v1/trends/malaysia-context/history"));
  if (!result.ok) return null;
  return <MalaysiaContextPanel observations={result.data} />;
}
