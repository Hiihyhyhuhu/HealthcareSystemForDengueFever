import { Link, NavLink, useLocation } from "react-router-dom";

export default function SiteNavbar({
  contactHref = "#ourselves",
  aboutHref = "#about-section",
  showAbout = true,
}) {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  const linkClass = ({ isActive }) =>
    `nav-link custom-nav-link ${isActive ? "active" : ""}`;

  return (
    <nav className="navbar navbar-expand-lg fixed-top app-navbar">
      <div className="container-fluid app-container px-3 px-lg-4">
        <Link className="navbar-brand brand-logo" to="/">
          NAME{isLanding ? "HERE" : ""}
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#mainNavbar"
          aria-controls="mainNavbar"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div
          className="collapse navbar-collapse justify-content-end"
          id="mainNavbar"
        >
          <ul className="navbar-nav align-items-lg-center gap-lg-3">
            {isLanding ? (
              <>
                <li className="nav-item">
                  <a className="nav-link custom-nav-link" href={contactHref}>
                    Contact
                  </a>
                </li>
                {showAbout && (
                  <li className="nav-item">
                    <a className="nav-link custom-nav-link" href={aboutHref}>
                      About
                    </a>
                  </li>
                )}
              </>
            ) : (
              <>
                <li className="nav-item">
                  <NavLink className={linkClass} to="/">
                    Home
                  </NavLink>
                </li>
                <li className="nav-item">
                  <NavLink className={linkClass} to="/registration">
                    Registration
                  </NavLink>
                </li>
                <li className="nav-item">
                  <NavLink className={linkClass} to="/consent">
                    Consent
                  </NavLink>
                </li>
                <li className="nav-item">
                  <a
                    className="nav-link custom-nav-link"
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      window.print();
                    }}
                  >
                    Download
                  </a>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
}
