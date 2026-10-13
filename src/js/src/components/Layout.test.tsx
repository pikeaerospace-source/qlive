/**
 * Tests for the application shell (`Layout`).
 *
 * An SPA needs explicit accessibility scaffolding: landmarks, a skip link, an
 * exposed current page, and focus moving to the main region after a route change
 * so assistive technology announces the new page.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import Layout from "./Layout";

function renderLayout(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<h1>Discover</h1>} />
          <Route path="dashboard" element={<h1>Dashboard</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  it("renders banner, navigation and main landmarks", () => {
    renderLayout();

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "QLive home" }),
    ).toBeInTheDocument();

    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getAllByRole("link")).toHaveLength(2);
  });

  it("exposes a skip link that targets the main region", () => {
    renderLayout();

    expect(
      screen.getByRole("link", { name: "Skip to content" }),
    ).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });

  it("exposes the current page and follows navigation", () => {
    renderLayout();

    expect(screen.getByRole("link", { name: "Discover" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute(
      "aria-current",
    );

    fireEvent.click(screen.getByRole("link", { name: "Dashboard" }));

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Discover" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("leaves focus alone on first render", () => {
    renderLayout();

    expect(screen.getByRole("main")).not.toHaveFocus();
  });

  it("moves focus to the main region after navigating", () => {
    renderLayout();

    fireEvent.click(screen.getByRole("link", { name: "Dashboard" }));

    expect(screen.getByRole("main")).toHaveFocus();
    expect(screen.getByRole("main")).toHaveAttribute("tabindex", "-1");
  });

  it("keeps focus on the main region across repeat visits", () => {
    renderLayout();

    fireEvent.click(screen.getByRole("link", { name: "Dashboard" }));
    fireEvent.click(screen.getByRole("link", { name: "Discover" }));

    expect(screen.getByRole("main")).toHaveFocus();
  });
});
