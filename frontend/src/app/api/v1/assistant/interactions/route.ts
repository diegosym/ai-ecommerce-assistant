import { NextResponse } from "next/server";

const BACKEND_URL = process.env.ASSISTANT_API_URL ?? "http://127.0.0.1:8000/api/v1";

export async function POST(request: Request): Promise<NextResponse> {
  try {
    const body = (await request.json()) as unknown;
    const upstream = await fetch(`${BACKEND_URL}/assistant/interactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const responseBody = await upstream.text();
    return new NextResponse(responseBody, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "catalog_unavailable",
          message: "The shopping assistant is temporarily unavailable. Please try again.",
          retryable: true,
        },
        interactionId: null,
      },
      { status: 503 },
    );
  }
}
