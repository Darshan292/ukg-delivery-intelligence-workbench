// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { NeighbourhoodResponse } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const UNREACHABLE = "The API is not reachable. Start the backend and reload.";

function messageFor(status: number, entity: string): string {
  if (status === 404) return `No entity with key ${entity}. Check the key in the address (?entity=...).`;
  if (status === 422)
    return "Entity keys use letters, digits, dot, underscore and hyphen, up to 100 characters.";
  return UNREACHABLE;
}

export async function fetchNeighbourhood(entity: string, signal?: AbortSignal): Promise<NeighbourhoodResponse> {
  let res: Response;
  try {
    res = await fetch(`/api/neighbourhood?entity=${encodeURIComponent(entity)}`, { signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(503, UNREACHABLE);
  }
  if (!res.ok) throw new ApiError(res.status, messageFor(res.status, entity));
  try {
    return (await res.json()) as NeighbourhoodResponse;
  } catch {
    throw new ApiError(503, UNREACHABLE);
  }
}
