import { API_URL } from "@/lib/api/client";
export async function POST(request: Request) {
  const length = Number(request.headers.get("content-length"));
  if (!Number.isFinite(length) || length <= 0)
    return Response.json(
      { message: "Content length required." },
      { status: 411 },
    );
  if (length > 5 * 1024 * 1024 + 65536)
    return Response.json(
      { message: "Use a file under 5 MB." },
      { status: 413 },
    );
  const publicOrigin = process.env.WEB_ORIGIN ?? "http://localhost:3000";
  if (request.headers.get("origin") !== publicOrigin)
    return new Response(null, { status: 403 });
  try {
    const form = await request.formData(),
      file = form.get("file");
    if (
      !(file instanceof File) ||
      file.size > 5 * 1024 * 1024 ||
      form.get("synthetic_consent") !== "true"
    )
      return Response.json(
        { message: "Choose a synthetic CV and confirm consent." },
        { status: 422 },
      );
    const result = await fetch(API_URL + "/api/v1/preview/cv", {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(20000),
    });
    return new Response(await result.text(), {
      status: result.status,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { message: "Preview unavailable. Try again shortly." },
      { status: 503 },
    );
  }
}
