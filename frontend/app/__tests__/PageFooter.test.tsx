/**
 * PageFooter.test.tsx
 * Tests for the shared PageFooter component — link visibility per pathname.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import PageFooter from "../components/PageFooter";

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

const mockUsePathname = jest.fn();
jest.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

beforeEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Default pages (not help or contact)
// ---------------------------------------------------------------------------
describe("PageFooter on a generic page", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/");
    render(<PageFooter />);
  });

  it("renders Help link", () => {
    expect(screen.getByText("Help").closest("a")).toHaveAttribute(
      "href",
      "/help",
    );
  });

  it("renders Contact link", () => {
    expect(screen.getByText("Contact").closest("a")).toHaveAttribute(
      "href",
      "/contact",
    );
  });

  it("renders the version string", () => {
    expect(screen.getByText(/ops-pilot v0\.1\.0/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Help page — hide Help link
// ---------------------------------------------------------------------------
describe("PageFooter on /help", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/help");
    render(<PageFooter />);
  });

  it("hides the Help link", () => {
    expect(screen.queryByText("Help")).not.toBeInTheDocument();
  });

  it("still shows the Contact link", () => {
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Contact page — hide Contact link
// ---------------------------------------------------------------------------
describe("PageFooter on /contact", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/contact");
    render(<PageFooter />);
  });

  it("hides the Contact link", () => {
    expect(screen.queryByText("Contact")).not.toBeInTheDocument();
  });

  it("still shows the Help link", () => {
    expect(screen.getByText("Help")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Other inner pages
// ---------------------------------------------------------------------------
describe("PageFooter on /settings", () => {
  it("shows both Help and Contact", () => {
    mockUsePathname.mockReturnValue("/settings");
    render(<PageFooter />);
    expect(screen.getByText("Help")).toBeInTheDocument();
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });
});

describe("PageFooter on /chat", () => {
  it("shows both Help and Contact", () => {
    mockUsePathname.mockReturnValue("/chat");
    render(<PageFooter />);
    expect(screen.getByText("Help")).toBeInTheDocument();
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });
});
