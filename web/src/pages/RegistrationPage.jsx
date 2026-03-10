import PageShell from "../components/PageShell";

const familyHistory = [
  ["Diabetes", "Asthma", "Thyroid disorder"],
  ["Stroke", "COPD", "Heart attack under age of 60"],
  [
    "High blood pressure",
    {
      label: "Any other important family illness. Please state:",
      whoLabel: "Who:",
      colSpan: 2,
    },
  ],
];

export default function RegistrationPage() {
  return (
    <PageShell title="Registration Form">
      <form className="medical-form registration-form">
        <section className="registration-section">
          <h2 className="section-title form-block-title mb-1">Patient</h2>

          <div className="row g-3 align-items-start">
            <div className="col-12 col-lg-8">
              <label className="field-label">Patient’s Name</label>
              <div className="row g-2">
                <div className="col-12 col-md-6">
                  <input
                    className="form-control custom-input compact-input"
                    placeholder="Enter input"
                  />
                  <small>First name</small>
                </div>
                <div className="col-12 col-md-6">
                  <input
                    className="form-control custom-input compact-input"
                    placeholder="Enter input"
                  />
                  <small>Last name</small>
                </div>
              </div>
            </div>

            <div className="col-12 col-lg-4">
              <label className="field-label">Sex</label>
              <select
                className="form-select custom-input compact-input registration-select"
                defaultValue=""
              >
                <option value="" disabled>
                  Please select
                </option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="others">Others</option>
              </select>
            </div>

            <div className="col-12 col-lg-4">
              <label className="field-label">Date of Birth</label>
              <input
                className="form-control custom-input compact-input"
                placeholder="Enter input"
                type="date"
              />
            </div>

            <div className="col-12 col-lg-8">
              <label className="field-label">
                Province/City and Country of Birth
              </label>
              <input
                className="form-control custom-input compact-input"
                placeholder="e.g. Da Nang Province, Vietnam"
              />
            </div>

            <div className="col-12 col-lg-8">
              <label className="field-label">Address</label>
              <input
                className="form-control custom-input compact-input"
                placeholder="28 Tan Son St., ward Tan Son"
              />
            </div>
          </div>
        </section>

        <hr className="section-rule" />

        <section className="registration-section">
          <h2 className="section-title form-block-title mb-2">
            Parent’s / Guardian’s
          </h2>
          <div className="row g-3 g-lg-4 align-items-start guardian-grid">
            <div className="col-12 col-lg-7">
              <label className="field-label">Name</label>
              <input
                className="form-control custom-input compact-input"
                placeholder="Enter input"
              />
            </div>
            <div className="col-12 col-lg-5">
              <label className="field-label">Phone Number</label>
              <input
                className="form-control custom-input compact-input"
                placeholder="Enter input"
              />
            </div>
            <div className="col-12 col-lg-7">
              <label className="field-label">Email</label>
              <input
                className="form-control custom-input compact-input"
                placeholder="Enter input"
              />
            </div>
            <div className="col-12 col-lg-5 relationship-field">
              <label className="field-label relationship-label">
                Relationship to the child
              </label>
              <select
                className="form-select custom-input compact-input rounded-pill relationship-select"
                defaultValue=""
              >
                <option>Select an option</option>
                <option value="mother">Mom / Mother</option>
                <option value="father">Dad / Father</option>
                <option value="guardian">Guardian</option>
                <option value="others">Others</option>
              </select>
            </div>
          </div>
        </section>

        <hr className="section-rule" />

        <section className="medical-section">
          <h2 className="section-title">Medical Background of Patient</h2>
          <p className="medical-intro">
            Are there any serious diseases that affect your child’s{" "}
            <strong>parents, brothers or sisters?</strong> Tick all that apply{" "}
            <strong>
              <u>and</u>
            </strong>{" "}
            state <strong>family member</strong>:
          </p>

          <div className="medical-grid">
            {/* Row 1 */}
            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>Diabetes</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>Asthma</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>Thyroid disorder</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            {/* Row 2 */}
            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>Stroke</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>COPD</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>Heart attack under age of 60</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            {/* Row 3 */}
            <div className="medical-cell history-cell">
              <div className="history-head">
                <span>High blood pressure</span>
                <input type="checkbox" />
              </div>
              <label>Who:</label>
              <input
                className="form-control custom-input thin"
                placeholder="name"
              />
            </div>

            <div className="medical-cell merged-cell span-2">
              <div className="merged-grid">
                <div className="merged-left">
                  <div className="history-head">
                    <span>
                      Any other important family illness. <em>Please state:</em>
                    </span>
                    <input type="checkbox" />
                  </div>
                  <input
                    className="form-control custom-input thin"
                    placeholder="Enter"
                  />
                </div>

                <div className="merged-right">
                  <label>Who:</label>
                  <input
                    className="form-control custom-input thin"
                    placeholder="name"
                  />
                </div>
              </div>
            </div>

            {/* Row 4 */}
            <div className="medical-cell wide-label">
              <span>
                Please state any allergies and sensitivities that your child has
                to medicines, food &amp; dressings:
              </span>
            </div>
            <div className="medical-cell wide-input span-2">
              <input
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>

            {/* Row 5 */}
            <div className="medical-cell wide-label">
              <span>Please state any mental disabilities your child has:</span>
            </div>
            <div className="medical-cell wide-input span-2">
              <input
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>

            {/* Row 6 */}
            <div className="medical-cell question-cell medicine-question-span">
              <span>Does your child have any problems taking medicines?</span>
            </div>

            <div className="medical-cell radio-cell medicine-radio-span">
              <label className="radio-line">
                <span>Yes</span>
                <input type="radio" name="medicineProblem" />
              </label>
              <label className="radio-line">
                <span>No</span>
                <input type="radio" name="medicineProblem" />
              </label>
            </div>

            <div className="medical-cell detail-cell medicine-detail-span">
              <span>If yes, please give details, e.g. swallowing</span>
              <input
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>

            {/* Row 7 */}
            <div className="medical-cell half-split-cell">
              <span>What chronic medical conditions has your child had?</span>
              <input
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>

            <div className="medical-cell half-split-cell span-2 half-right-reset">
              <span>Date of Diagnosis:</span>
                <textarea
                  className="form-control custom-input tall textarea-input"
                  placeholder="Enter"
                />
            </div>

            {/* Row 8 */}
            <div className="medical-cell half-split-cell span-2 half-right-reset">
              <span>What injuries has your child had?</span>
              <textarea
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>

            <div className="medical-cell half-cell span-2">
              <div className="two-col-split">
                <div className="split-block">
                  <span>Date of injury/s</span>
                  <input
                    className="form-control custom-input tall textarea-input"
                    placeholder="Enter"
                  />
                </div>
              </div>
            </div>

            {/* Row 9 */}
            <div className="medical-cell full-row span-3">
              <span>
                Please list any tablets, medicines or other treatments your
                child is currently taking / undertaking:
              </span>
              <input
                className="form-control custom-input tall textarea-input"
                placeholder="Enter"
              />
            </div>
          </div>
        </section>

        <hr className="section-rule" />

        <section className="registration-section">
          <h2 className="section-title">Sharing your child’s medical record</h2>
          <p>
            <strong>Medical Record Sharing</strong> allows your child's complete
            GP medical record to be made available to authorised healthcare
            professionals involved in your care. You will always be asked your
            permission before anybody looks at your child’s shared medical
            record.
          </p>
          <div className="tick-line">
            <strong>
              If you don’t want to share your child’s GP record tick here:
            </strong>{" "}
            <input type="checkbox" />
          </div>
          <p>
            <strong>Summary Care Records</strong> contains details of your
            child’s key health information – medications, allergies and adverse
            reactions. They are accessible to authorised healthcare staff in
            A&amp;E Departments throughout England. You will always be asked
            your permission before anybody looks at your child’s Summary Care
            Record.
          </p>
          <div className="tick-line">
            <strong>
              If you don’t want your child to have a Summary Care Record tick
              here:
            </strong>{" "}
            <input type="checkbox" />
          </div>
          <p>
            <strong>The Care.data Programme</strong> collates information about
            your child and the care they receive. It links information from all
            the different places where your child receives care, such as their
            GP, hospital and community services, to help them provide a full
            picture of your child’s medical needs and the care they are
            receiving. This data is made available to NHS Commissioners so that
            they can design integrated services and is shared with third parties
            for research purposes.
          </p>
          <div className="tick-line">
            <strong>
              I wish to OPT OUT from my child’s Personal Confidential Data being
              shared outside their GP practice:
            </strong>{" "}
            <input type="checkbox" />
          </div>
          <div className="tick-line">
            <strong>
              I wish to OPT OUT from my child’s Personal Confidential Data being
              shared with third parties:
            </strong>{" "}
            <input type="checkbox" />
          </div>
        </section>

        <hr className="section-rule" />
        <section className="registration-section signature-section">
          <h2 className="section-title">Signature</h2>
          <div className="row g-4 text-center signature-row">
            <div className="col-12 col-md-6">
              <div className="signature-box">Doctor’s signature</div>
              <p>Ho Chi Minh City, ..., .../.../....</p>
            </div>
            <div className="col-12 col-md-6">
              <div className="signature-box">Parent’s/ Guardian signature</div>
              <p>Ho Chi Minh City, ..., .../.../....</p>
            </div>
          </div>
        </section>
      </form>
    </PageShell>
  );
}
