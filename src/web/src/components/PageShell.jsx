import SiteNavbar from './SiteNavbar';

export default function PageShell({ title, children }) {
  return (
    <div className="page-shell">
      <SiteNavbar showAbout={false} />
      <main className="form-page-main">
        <header className="form-hero text-center">
          <h1>{title}</h1>
        </header>
        <section className="form-sheet">{children}</section>
      </main>
    </div>
  );
}
