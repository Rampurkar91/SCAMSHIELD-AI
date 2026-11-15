import { describe, it, expect, vi, afterEach } from "vitest";
import { api, errorText, download } from "./api";
describe("API error handling", () => {
  it("shows backend errors", () =>
    expect(
      errorText({ response: { data: { detail: "Session expired." } } }),
    ).toBe("Session expired."));
  it("formats validation errors", () =>
    expect(
      errorText({ response: { data: { detail: [{ msg: "Invalid URL" }] } } }),
    ).toBe("Invalid URL"));
  it("handles connection failure", () =>
    expect(errorText({})).toMatch("Unable to connect"));
  it("uses relative API requests in the preview", () =>
    expect(api.defaults.baseURL).toBe("/api"));
});
