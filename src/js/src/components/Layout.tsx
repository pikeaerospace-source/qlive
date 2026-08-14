import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "nav-link active" : "nav-link";

export default function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          Q<span className="brand-accent">Live</span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end className={linkClass}>
            Discover
          </NavLink>
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
