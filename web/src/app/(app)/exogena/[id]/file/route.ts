import { NextResponse } from "next/server";

import { exogenaApi } from "@/lib/api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const generation = Number(id);

  if (!Number.isInteger(generation) || generation < 1) {
    return new NextResponse("Not found", { status: 404 });
  }

  const upstream = await exogenaApi.file(generation);
  if (!upstream.ok) {
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
    });
  }

  return new NextResponse(upstream.body, {
    headers: {
      "Content-Type": "application/xml",
      "Content-Disposition":
        upstream.headers.get("content-disposition") ??
        `attachment; filename="exogena-${generation}.xml"`,
    },
  });
}
