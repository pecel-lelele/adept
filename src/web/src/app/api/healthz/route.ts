import { proxyRequest } from "@/lib/api/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
function handle(request: Request) { return proxyRequest(request); }

export const GET = handle;
export const HEAD = handle;
