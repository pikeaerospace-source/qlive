import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "nav-link active" : "nav-link";

export default function Layout() {
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
      <main id="main" className="content">
        <Outlet />
      </main>
    </div>
  );
}

