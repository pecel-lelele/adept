import Link from "next/link";
import { getTranslations } from "next-intl/server";

import {
  buttonVariants,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StubBanner,
} from "@/components";

type AuthPage = "login" | "signup" | "consent" | "join";

/** Auth stubs. AUTH_MODE=demo uses /demo/*; real auth (Supabase) comes later. */
export async function AuthView({ page }: { page: AuthPage }) {
  const t = await getTranslations("common");
  const title = {
    login: t("auth.loginTitle"),
    signup: t("auth.signupTitle"),
    consent: t("auth.consentTitle"),
    join: t("auth.joinTitle"),
  }[page];

  return (
    <main className="mx-auto max-w-md px-4 py-10">
      <StubBanner feature="Core auth" />
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {page === "consent" ? t("auth.consentBody") : t("auth.notImplemented")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <a href="/demo/learner" className={buttonVariants()}>
            {t("landing.individualDemo")}
          </a>
          <a href="/demo/org" className={buttonVariants({ variant: "outline" })}>
            {t("landing.organisationDemo")}
          </a>
          <Link href="/" className="pt-2 text-center text-sm underline">
            {t("appName")}
          </Link>
        </CardContent>
      </Card>
    </main>
  );
}
