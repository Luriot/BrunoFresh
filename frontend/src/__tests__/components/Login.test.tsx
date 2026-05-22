import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render, screen, fireEvent } from "@testing-library/react";
import { Login } from "../../components/Login";

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders username and password inputs", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.getByPlaceholderText("auth.usernameLabel")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("auth.passwordLabel")).toBeInTheDocument();
  });

  it("renders the sign-in button", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.getByRole("button", { name: "auth.signIn" })).toBeInTheDocument();
  });

  it("sign-in button is not disabled by default", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.getByRole("button", { name: "auth.signIn" })).not.toBeDisabled();
  });

  it("does not call onLogin when submitted with both fields empty", () => {
    const onLogin = vi.fn();
    render(<Login onLogin={onLogin} error={null} />);

    const form = screen.getByRole("button", { name: "auth.signIn" }).closest("form")!;
    fireEvent.submit(form);
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("does not call onLogin when submitted with whitespace-only username", () => {
    const onLogin = vi.fn();
    render(<Login onLogin={onLogin} error={null} />);

    fireEvent.change(screen.getByPlaceholderText("auth.usernameLabel"), { target: { value: "   " } });
    const form = screen.getByPlaceholderText("auth.usernameLabel").closest("form")!;
    fireEvent.submit(form);
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("calls onLogin with username and password on submit", async () => {
    const onLogin = vi.fn().mockResolvedValueOnce(undefined);
    render(<Login onLogin={onLogin} error={null} />);

    fireEvent.change(screen.getByPlaceholderText("auth.usernameLabel"), { target: { value: "alice" } });
    fireEvent.change(screen.getByPlaceholderText("auth.passwordLabel"), { target: { value: "secret" } });

    const form = screen.getByPlaceholderText("auth.usernameLabel").closest("form")!;
    await act(async () => {
      fireEvent.submit(form);
    });

    expect(onLogin).toHaveBeenCalledOnce();
    expect(onLogin).toHaveBeenCalledWith("alice", "secret");
  });

  it("displays error message when error prop is provided", () => {
    render(<Login onLogin={vi.fn()} error="Invalid credentials" />);
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
  });

  it("does not display an error element when error prop is null", () => {
    render(<Login onLogin={vi.fn()} error={null} />);
    expect(screen.queryByText("Invalid credentials")).not.toBeInTheDocument();
  });
});

