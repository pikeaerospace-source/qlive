/**
 * QLive — application shell: skip link, top bar, primary nav and main region.
 *
 * `header` / `nav` / `main` landmarks plus the skip link let keyboard and
 * screen-reader users move through the chrome. Client-side routing swaps the
 * page in place without a document load, so focus is moved to `main` after each
 * navigation to announce the new page.
 */

import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "nav-link active" : "nav-link";

export default function Layout() {
  const { pathname } = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const previousPath = useRef(pathname);

  // An SPA navigation replaces the page without a document load, so assistive
  // technology keeps reporting the page the user arrived from. Focusing the main
  // region (which also scrolls it into view) resets that context. Skipped on the
  // first render, so a fresh load keeps its natural focus and scroll position.
  useEffect(() => {
    if (previousPath.current === pathname) return;
    previousPath.current = pathname;
    mainRef.current?.focus();
  }, [pathname]);

  return (
    <div className="app">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="QLive home">
          Q<span className="brand-accent">Live</span>
        </NavLink>
        <nav className="nav" aria-label="Primary">
          <NavLink to="/" end className={linkClass}>
            Discover
          </NavLink>
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
        </nav>
      </header>
      <main id="main" className="content" ref={mainRef} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
