import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Login } from "../../components/Login";

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the passcode input", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.getByPlaceholderText("auth.passcodePlaceholder")).toBeInTheDocument();
  });

  it("renders the sign-in button", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.getByRole("button", { name: "auth.signIn" })).toBeInTheDocument();
  });

  it("sign-in button is not disabled when passcode is typed", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    const input = screen.getByPlaceholderText("auth.passcodePlaceholder");
    const button = screen.getByRole("button", { name: "auth.signIn" });

    fireEvent.change(input, { target: { value: "secret" } });
    expect(button).not.toBeDisabled();
  });

  it("does not call onLogin when submitted with empty passcode", () => {
    const onLogin = vi.fn();
    render(<Login onLogin={onLogin} error={null} />);

    const form = screen.getByRole("button", { name: "auth.signIn" }).closest("form")!;
    fireEvent.submit(form);
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("does not call onLogin when submitted with whitespace-only passcode", () => {
    const onLogin = vi.fn();
    render(<Login onLogin={onLogin} error={null} />);
    const input = screen.getByPlaceholderText("auth.passcodePlaceholder");

    fireEvent.change(input, { target: { value: "   " } });
    const form = input.closest("form")!;
    fireEvent.submit(form);
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("calls onLogin with the typed passcode on submit", async () => {
    const onLogin = vi.fn().mockResolvedValueOnce(undefined);
    render(<Login onLogin={onLogin} error={null} />);

    const input = screen.getByPlaceholderText("auth.passcodePlaceholder");
    fireEvent.change(input, { target: { value: "my-passcode" } });

    const form = input.closest("form")!;
    fireEvent.submit(form);

    expect(onLogin).toHaveBeenCalledOnce();
    expect(onLogin).toHaveBeenCalledWith("my-passcode");
  });

  it("displays error message when error prop is provided", () => {
    render(<Login onLogin={vi.fn()} error="Invalid passcode" />);
    expect(screen.getByText("Invalid passcode")).toBeInTheDocument();
  });

  it("does not display an error element when error prop is null", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.queryByText("Invalid passcode")).not.toBeInTheDocument();
  });
});
