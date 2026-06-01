import PageShell from '../components/PageShell';

export default function ConsentPage() {
  return (
    <PageShell title="Consent for Surgery, Procedure, and Anesthesia">
      <form className="medical-form consent-form">
        <div className="checkbox-row top-options">
          {['Emergency', 'Urgent', 'Scheduled / Elective'].map((item) => (
            <label key={item}><input type="checkbox" /> <span>{item}</span></label>
          ))}
        </div>

        <p>We under the names below agree to the commitment forum as followed:</p>
        <h2 className="section-title">I. Surgeon / Anesthesiologist.</h2>

        <div className="row g-3 align-items-end">
          <div className="col-12 col-lg-3"><label className="field-label">My name is</label></div>
          <div className="col-12 col-lg-9"><input className="form-control custom-input rounded-pill" defaultValue="D. Ho Quang" /></div>
          <div className="col-12 col-md-4"><label className="field-label">Position</label><input className="form-control custom-input rounded-pill" defaultValue="Head" /></div>
          <div className="col-12 col-md-8"><label className="field-label">Department</label><input className="form-control custom-input rounded-pill" defaultValue="Surgery" /></div>
          <div className="col-12 col-lg-3"><label className="field-label">and Doctor</label></div>
          <div className="col-12 col-lg-9"><input className="form-control custom-input rounded-pill" defaultValue="H. Truong Anh" /></div>
          <div className="col-12 col-md-4"><label className="field-label">Position</label><input className="form-control custom-input rounded-pill" defaultValue="Specialist" /></div>
          <div className="col-12 col-md-8 d-flex align-items-center"><div className="plain-note">(Department of Anesthesia)</div></div>
        </div>

        <div className="stacked-fields mt-4">
          <label>Assigned to perform the surgery/procedure/anesthesia for the patient: <input className="inline-input" placeholder="Enter" /></label>
          <label>Diagnosed: <input className="inline-input" placeholder="Enter" /></label>
        </div>

        <p className="mt-4">
          We have fully and clearly explained and provided counseling to the patient/the patient’s family regarding the surgery / procedure / anesthesia and resuscitation, including the following matters:
        </p>

        <div className="check-list">
          {[
            'Diagnosis',
            'Indication for surgery/procedure.',
            'Risks and potential consequences of not undergoing the surgery/procedure.',
            'Results after surgery/procedure (expectation)',
          ].map((text) => (
            <label key={text}><input type="checkbox" /> <span>{text}</span></label>
          ))}
        </div>

        <section className="mt-4">
          <h3 className="mini-title">Planned surgical / procedural method</h3>
          <div className="checkbox-row three-col">
            {['Open surgery', 'Laparoscopic surgery', 'Procedure'].map((item) => (
              <label key={item}><input type="checkbox" /> <span>{item}</span></label>
            ))}
          </div>
        </section>

        <section className="mt-3">
          <h3 className="mini-title">Planned anesthesia and resuscitation method</h3>
          <div className="checkbox-row grid-options">
            {[
              'Endotracheal anesthesia', 'Laryngeal mask anesthesia (LMA)', 'Intravenous anesthesia',
              'Spinal anesthesia', 'Epidural anesthesia', 'Nerve plexus block',
              'Premedication + Local anesthesia', 'Others',
            ].map((item) => (
              <label key={item}><input type="checkbox" /> <span>{item}</span></label>
            ))}
          </div>
        </section>

        <section className="mt-3">
          <h3 className="mini-title">Alternative treatment options other than surgery/procedure:</h3>
          <div className="checkbox-row three-col">
            {['No', 'Yes, specifically'].map((item) => (
              <label key={item}><input type="checkbox" /> <span>{item}</span></label>
            ))}
          </div>
        </section>

        <section className="mt-4 risk-box">
          <h3 className="mini-title">Possible risks and complications during and after surgery/procedure:</h3>
          <textarea className="form-control custom-input risk-area" rows="10"></textarea>
        </section>
      </form>
    </PageShell>
  );
}
