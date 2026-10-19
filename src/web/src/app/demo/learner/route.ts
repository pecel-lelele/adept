import type { NextRequest } from "next/server";

import { demoSignIn } from "@/lib/auth/demo";

export function GET(request: NextRequest) {
  return demoSignIn(request, "learner");
}
