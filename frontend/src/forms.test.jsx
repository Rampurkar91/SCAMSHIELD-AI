import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthPage, Auth, Scanner, Recovery } from "./main";
import { api } from "./api";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  sessionStorage.clear();
});
function view(component, user = null) {
  return render(
    <Auth.Provider value={{ user, setUser: vi.fn() }}>
      <MemoryRouter>{component}</MemoryRouter>
    </Auth.Provider>,
  );
}
describe("account forms", () => {
  it("validates registration without calling backend", async () => {
    const post = vi.spyOn(api, "post");
    view(<AuthPage register />);
    fireEvent.click(screen.getByRole("button", { name: /Create account/ }));
    expect(
      await screen.findByText("Enter at least two characters."),
    ).toBeInTheDocument();
    expect(screen.getByText("Use at least 12 characters.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });
  it("toggles password visibility", () => {
    view(<AuthPage />);
    const input = screen.getByPlaceholderText("Your password");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByLabelText("Show password"));
    expect(input).toHaveAttribute("type", "text");
  });
  it("shows backend login errors", async () => {
    vi.spyOn(api, "post").mockRejectedValue({
      response: { data: { detail: "Invalid email or password." } },
    });
    view(<AuthPage />);
    fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
      target: { value: "person@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Your password"), {
      target: { value: "nottherightpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in securely/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password.",
    );
  });
  it("does not simulate email reset when SMTP is missing", async () => {
    vi.spyOn(api, "post").mockRejectedValue({
      response: { data: { detail: "Password reset email is not configured." } },
    });
    view(<Recovery />);
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "person@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "not configured",
    );
  });
});
describe("scanner", () => {
  it("requires login, rather than faking guest scan results", async () => {
    const post = vi.spyOn(api, "post");
    view(<Scanner />);
    fireEvent.change(screen.getByLabelText("Website address"), {
      target: { value: "https://example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Analyze URL/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Please sign in",
    );
    expect(post).not.toHaveBeenCalled();
  });
  it("sends actual content to the selected endpoint and shows errors", async () => {
    const post = vi
      .spyOn(api, "post")
      .mockRejectedValue({
        response: { data: { detail: "Service unavailable" } },
      });
    view(<Scanner />, { name: "Tester" });
    fireEvent.click(screen.getByRole("button", { name: "UPI" }));
    fireEvent.change(screen.getByLabelText("Content to analyze"), {
      target: { value: "Send a PIN to receive money" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Analyze content/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Service unavailable",
    );
    expect(post).toHaveBeenCalledWith(
      "/scans/upi",
      { content: "Send a PIN to receive money" },
      { timeout: 120000 },
    );
  });
});
