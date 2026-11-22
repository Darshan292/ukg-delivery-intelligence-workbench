// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "./__fixtures__/neighbourhood.json";
import { ApiError, fetchNeighbourhood } from "./api";

function mockFetch(status: number, body: unknown = {}) {
  const f = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }),
  );
  vi.stubGlobal("fetch", f);
  return f;
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchNeighbourhood", () => {
  it("requests the encoded entity and returns the body", async () => {
    const f = mockFetch(200, fixture);
    await expect(fetchNeighbourhood("A B/1")).resolves.toEqual(fixture);
    expect(f.mock.calls[0][0]).toBe("/api/neighbourhood?entity=A%20B%2F1");
  });

  it.each([
    [404, "No entity with key NOPE. Check the key in the address (?entity=...)."],
    [409, "More than one entity has the key NOPE; add entity_type or product_profile."],
    [422, "Entity keys use letters, digits, dot, underscore and hyphen, up to 100 characters."],
    [503, "The API is not reachable. Start the backend and reload."],
  ])("maps %i to ApiError", async (status, message) => {
    mockFetch(status, { detail: "x" });
    const err = await fetchNeighbourhood("NOPE").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(status);
    expect((err as ApiError).message).toBe(message);
  });

  it("maps a network failure to ApiError 503", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    const err = await fetchNeighbourhood("X").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(503);
  });

  it("rethrows aborts untouched", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("a", "AbortError")));
    await expect(fetchNeighbourhood("X")).rejects.toMatchObject({ name: "AbortError" });
  });
});
