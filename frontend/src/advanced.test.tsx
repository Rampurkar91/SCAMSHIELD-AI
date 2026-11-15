import React from "react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { UploadScanner, Assistant, Learning, Admin } from "./pages/Advanced";
import { api } from "./api";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const Result = () => <div>Result shown</div>;
describe("advanced file upload forms", () => {
  it("blocks oversized images without contacting backend", async () => {
    const post = vi.spyOn(api, "post");
    render(<UploadScanner kind="image" Result={Result} />);
    const file = new File([new Uint8Array(6 * 1024 * 1024)], "large.png", {
      type: "image/png",
    });
    fireEvent.change(screen.getByLabelText(/Choose file/), {
      target: { files: [file] },
    });
    fireEvent.submit(
      screen.getByRole("button", { name: "Analyze file" }).closest("form")!,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("exceeds 5 MiB");
    expect(post).not.toHaveBeenCalled();
  });
  it("requires explicit voice consent", async () => {
    const post = vi.spyOn(api, "post");
    render(<UploadScanner kind="voice" Result={Result} />);
    fireEvent.change(screen.getByLabelText(/Choose file/), {
      target: { files: [new File(["wav"], "test.wav", { type: "audio/wav" })] },
    });
    fireEvent.submit(
      screen.getByRole("button", { name: "Analyze file" }).closest("form")!,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("consent");
    expect(post).not.toHaveBeenCalled();
  });
  it("shows missing OCR configuration instead of fake success", async () => {
    vi.spyOn(api, "post").mockRejectedValue({
      response: { data: { detail: "OCR is unavailable. Install Tesseract." } },
    });
    render(<UploadScanner kind="image" Result={Result} />);
    fireEvent.change(screen.getByLabelText(/Choose file/), {
      target: { files: [new File(["png"], "test.png", { type: "image/png" })] },
    });
    fireEvent.submit(
      screen.getByRole("button", { name: "Analyze file" }).closest("form")!,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "OCR is unavailable",
    );
    expect(screen.queryByText("Result shown")).not.toBeInTheDocument();
  });
});
describe("assistant and saved learning", () => {
  it("labels a static fallback and sends no context by default", async () => {
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue({
        data: {
          explanation: "Never share a PIN.",
          actions: [],
          uncertainty: "General guidance only",
          source: "Static safety fallback, not an AI answer",
          status: "not_configured",
        },
      });
    render(<Assistant />);
    fireEvent.change(screen.getByLabelText("Your question"), {
      target: { value: "Is a UPI PIN needed for refunds?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask ScamShield" }));
    expect(
      await screen.findByText(/Static safety fallback/),
    ).toBeInTheDocument();
    expect(post).toHaveBeenCalledWith(
      "/assistant/chat",
      expect.objectContaining({ use_ai: false, context: [] }),
      { timeout: 25000 },
    );
  });
  it("persists quiz submissions through backend", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      data: {
        quizzes: [
          {
            id: "upi-pin",
            question: "Need a PIN to receive money?",
            options: ["Yes", "No"],
          },
        ],
        attempts: [],
      },
    });
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue({
        data: { score: 100, explanation: "A PIN authorizes payment." },
      });
    render(<Learning />);
    fireEvent.click(await screen.findByRole("button", { name: "No" }));
    expect(
      await screen.findByText("100/100 · A PIN authorizes payment."),
    ).toBeInTheDocument();
    expect(post).toHaveBeenCalledWith("/awareness/quizzes/upi-pin/submit", {
      answer: 1,
    });
  });
  it("displays denied administrator access", async () => {
    vi.spyOn(api, "get").mockRejectedValue({
      response: { data: { detail: "Administrator access required." } },
    });
    render(<Admin />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Administrator access required.",
    );
  });
});
