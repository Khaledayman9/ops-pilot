/**
 * ProfileMenu.test.tsx
 * Component tests for the ProfileMenu — toggle, auth state, theme switch.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ProfileMenu from "../components/ProfileMenu";
import * as apis from "../lib/apis";

// Mock Next.js Link so it renders a plain <a>
jest.mock("next/link", () => {
  const Link = ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  );
  Link.displayName = "Link";
  return Link;
});

jest.mock("../lib/apis", () => ({
  getAccessToken: jest.fn(),
}));

const mockGetAccessToken = apis.getAccessToken as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  // Reset localStorage and document theme
  localStorage.clear();
  document.documentElement.dataset.theme = "";
});

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
describe("ProfileMenu rendering", () => {
  it("renders the Profile button", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("does not show dropdown menu by default", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    expect(screen.queryByText("Login")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Dropdown toggle
// ---------------------------------------------------------------------------
describe("ProfileMenu dropdown", () => {
  it("opens dropdown when Profile button is clicked", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.getByText("Login")).toBeInTheDocument();
    expect(screen.getByText("Register")).toBeInTheDocument();
  });

  it("closes dropdown on second click", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    fireEvent.click(screen.getByText("Profile"));
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.queryByText("Login")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Auth state
// ---------------------------------------------------------------------------
describe("ProfileMenu auth state", () => {
  it("shows Login and Register links when not authenticated", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.getByText("Login")).toBeInTheDocument();
    expect(screen.getByText("Register")).toBeInTheDocument();
    expect(screen.queryByText("View profile")).not.toBeInTheDocument();
  });

  it("shows View profile link when authenticated", () => {
    mockGetAccessToken.mockReturnValue("some-token");
    render(<ProfileMenu />);
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.getByText("View profile")).toBeInTheDocument();
    expect(screen.queryByText("Login")).not.toBeInTheDocument();
  });

  it("always shows Settings link regardless of auth state", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Theme toggle
// ---------------------------------------------------------------------------
describe("ProfileMenu theme toggle", () => {
  it("renders the theme toggle button", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    expect(screen.getByLabelText("Toggle theme")).toBeInTheDocument();
  });

  it("switches theme and persists to localStorage", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    const toggleBtn = screen.getByLabelText("Toggle theme");
    fireEvent.click(toggleBtn);
    expect(localStorage.getItem("ops-pilot-theme")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("toggles back to dark after two clicks", () => {
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    const toggleBtn = screen.getByLabelText("Toggle theme");
    fireEvent.click(toggleBtn); // dark → light
    fireEvent.click(toggleBtn); // light → dark
    expect(localStorage.getItem("ops-pilot-theme")).toBe("dark");
  });

  it("restores saved theme from localStorage on mount", () => {
    localStorage.setItem("ops-pilot-theme", "light");
    mockGetAccessToken.mockReturnValue(undefined);
    render(<ProfileMenu />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
