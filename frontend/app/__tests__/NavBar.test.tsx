/**
 * NavBar.test.tsx
 * Tests for the shared NavBar component across all three variants.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import NavBar from "../components/NavBar";

jest.mock("next/link", () => {
  const Link = ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>;
  Link.displayName = "Link";
  return Link;
});

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/",
}));

// ---------------------------------------------------------------------------
// Brand
// ---------------------------------------------------------------------------
describe("NavBar brand", () => {
  it("always renders the ops-pilot logo linking to /", () => {
    render(<NavBar variant="home" />);
    const logo = screen.getByText("ops");
    expect(logo.closest("a")).toHaveAttribute("href", "/");
  });
});

// ---------------------------------------------------------------------------
// home variant
// ---------------------------------------------------------------------------
describe("NavBar home variant", () => {
  beforeEach(() => render(<NavBar variant="home" />));

  it("renders Orchestration anchor", () => {
    expect(screen.getByText("Orchestration")).toBeInTheDocument();
  });

  it("renders Help link", () => {
    expect(screen.getByText("Help")).toBeInTheDocument();
  });

  it("renders Contact link", () => {
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });

  it("renders Settings link", () => {
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders LAUNCH button linking to /chat", () => {
    const launch = screen.getByText("LAUNCH");
    expect(launch.closest("a")).toHaveAttribute("href", "/chat");
  });

  it("does not render Home or Chat nav links", () => {
    expect(screen.queryByText("Home")).not.toBeInTheDocument();
    expect(screen.queryByText("Chat")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// inner variant
// ---------------------------------------------------------------------------
describe("NavBar inner variant", () => {
  beforeEach(() => render(<NavBar variant="inner" />));

  it("renders Home link to /", () => {
    expect(screen.getByText("Home").closest("a")).toHaveAttribute("href", "/");
  });

  it("renders Chat link to /chat", () => {
    expect(screen.getByText("Chat").closest("a")).toHaveAttribute(
      "href",
      "/chat",
    );
  });

  it("renders Settings link to /settings", () => {
    expect(screen.getByText("Settings").closest("a")).toHaveAttribute(
      "href",
      "/settings",
    );
  });

  it("does not render LAUNCH or Orchestration", () => {
    expect(screen.queryByText("LAUNCH")).not.toBeInTheDocument();
    expect(screen.queryByText("Orchestration")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// auth variant
// ---------------------------------------------------------------------------
describe("NavBar auth variant", () => {
  beforeEach(() => render(<NavBar variant="auth" />));

  it("renders Home, Chat, Settings links", () => {
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("does not render LAUNCH or Orchestration", () => {
    expect(screen.queryByText("LAUNCH")).not.toBeInTheDocument();
    expect(screen.queryByText("Orchestration")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// default variant
// ---------------------------------------------------------------------------
describe("NavBar default variant", () => {
  it("defaults to inner variant when no variant prop passed", () => {
    render(<NavBar />);
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});
