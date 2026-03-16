import { useEffect, useState } from "react";
import SiteNavbar from "../components/SiteNavbar";
import FeatureCard from "../components/FeatureCard";

const carouselImages = [
  "/assets/carousel-1.png",
  "/assets/carousel-2.png",
  "/assets/carousel-3.png",
  "/assets/carousel-4.png",
  "/assets/carousel-5.png",
];

const teamContent = {
  team: [
    {
      name: "Tran Chanh Hy",
      school: "University of Technology Sydney",
      icons: ["bi-linkedin"],
    },
    {
      name: "Le Quoc Thai",
      school: "Ho Chi Minh University of Technology",
      icons: ["bi-facebook", "bi-linkedin", "bi-github"],
    },
    {
      name: "Dao Dat",
      school: "Ho Chi Minh University of Technology",
      icons: [],
    },
  ],
  goal: {
    image: "/assets/HFDM.png",
    text: "To reduce the HFDM rate in Vietnam in particular and in the world in general; to reduce any delay related from specific symptoms to procedures when checking in a clinic / hospital.",
  },
  laboratory: {
    image: "/assets/logobk.png",
    text: "A student project focused on child healthcare, AI assistance, and smoother patient journeys. Clean, fast, and less headache-inducing than paperwork on a Monday morning.",
  },
};

export default function LandingPage() {
  const [carouselIndex, setCarouselIndex] = useState(1);
  const [teamTab, setTeamTab] = useState("team");

  useEffect(() => {
    const timer = setInterval(() => {
      setCarouselIndex((prev) => (prev + 1) % carouselImages.length);
    }, 2800);
    return () => clearInterval(timer);
  }, []);

  const shiftCarousel = (dir) => {
    setCarouselIndex(
      (prev) => (prev + dir + carouselImages.length) % carouselImages.length,
    );
  };

  return (
    <div className="landing-page">
      <SiteNavbar contactHref="#ourselves" aboutHref="#about-section" />

      <main>
        <section className="hero-section">
          <div className="container-fluid app-container">
            <div className="hero-grid">
              <div className="hero-visual">
                <img
                  src="/assets/hero-robot.png"
                  alt="Healthcare robot"
                  className="hero-robot"
                />
              </div>
              <div className="hero-copy">
                <p className="hero-quote">“Small Patient, Big Heart”</p>
                <h1>
                  A HEALTHCARE
                  <br />
                  SYSTEM FOR
                  <br />
                  <span>YOUR KIDS</span>
                </h1>
              </div>
            </div>
          </div>
        </section>

        <section className="feature-intro">
          <div className="container-fluid app-container text-center">
            <h2>Our Latest Features</h2>
            <p>“Patient to patients”</p>

            <div className="custom-carousel">
              <div className="carousel-stage">
                {carouselImages.map((src, index) => {
                  const total = carouselImages.length;
                  let diff = index - carouselIndex;

                  if (diff > total / 2) diff -= total;
                  if (diff < -total / 2) diff += total;

                  let positionClass = "is-hidden";
                  if (diff === 0) positionClass = "is-active";
                  else if (diff === -1) positionClass = "is-left";
                  else if (diff === 1) positionClass = "is-right";
                  else if (diff === -2) positionClass = "is-far-left";
                  else if (diff === 2) positionClass = "is-far-right";

                  return (
                    <button
                      key={`${src}-${index}`}
                      type="button"
                      className={`carousel-card ${positionClass}`}
                      onClick={() => setCarouselIndex(index)}
                      aria-label={`Go to slide ${index + 1}`}
                    >
                      <img
                        src={src}
                        alt={`Healthcare feature ${index + 1}`}
                        className="carousel-image"
                      />
                    </button>
                  );
                })}
              </div>

              <div className="carousel-controls">
                <button
                  className="carousel-arrow"
                  type="button"
                  onClick={() => shiftCarousel(-1)}
                  aria-label="Previous slide"
                >
                  <i className="bi bi-arrow-left"></i>
                </button>

                <div className="carousel-dots">
                  {carouselImages.map((_, index) => (
                    <button
                      key={index}
                      type="button"
                      className={`carousel-dot ${index === carouselIndex ? "active" : ""}`}
                      onClick={() => setCarouselIndex(index)}
                      aria-label={`Go to slide ${index + 1}`}
                    />
                  ))}
                </div>

                <button
                  className="carousel-arrow"
                  type="button"
                  onClick={() => shiftCarousel(1)}
                  aria-label="Next slide"
                >
                  <i className="bi bi-arrow-right"></i>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="problem-solution-section" id="about-section">
          <div className="container-fluid app-container">
            <div className="section-headings">
              <h2>Your Problem</h2>
              <h2>Our Solution</h2>
            </div>

            <div className="row g-4">
              <div className="col-12 col-lg-6">
                <FeatureCard
                  title="50.000+ HFMD Cases"
                  text="Each year, 60% of the country’s total cases are recorded in Southern Vietnam."
                />
              </div>
              <div className="col-12 col-lg-6">
                <FeatureCard
                  icon="bi-house-door-fill"
                  title="Pre-diagnose HFDM At Home"
                  text="Our AI model learns from HFDM symptoms of 10.000 worldwide kids aged of 1 to 5."
                  button
                />
              </div>
            </div>

            <p className="symptom-line">
              Fever • Sore throat • Mouth ulcers • Painful mouth sores • Skin
              rash • Blister lesions • Red spots • Loss of appetite • Fatigue •
              Irritability (in children) • Drooling (in infants)
            </p>

            <div className="row g-4 mt-1">
              <div className="col-12 col-lg-6">
                <FeatureCard
                  title="25 Minutes On Registration"
                  text="It is a quite long registration procedure in most clinics and hospitals causing frustration."
                />
              </div>
              <div className="col-12 col-lg-6">
                <FeatureCard
                  icon="bi-house-door-fill"
                  title="Online Registration"
                  text="Our integrated register patient form shortens time to make an appointment to doctors."
                  button
                  linkTo="/registration"
                />
              </div>
              <div className="col-12 col-lg-6">
                <FeatureCard
                  title="Scattered Healthcare Info"
                  text="Internet is not a reliable source for first-AIDS with kids whereas you are not stay with doctors."
                />
              </div>
              <div className="col-12 col-lg-6">
                <FeatureCard
                  icon="bi-house-door-fill"
                  title="Post-treatment Multi-agents"
                  text="Our chatbot can help me you give truthful advice on how to treat young patients."
                  button
                />
              </div>
            </div>
          </div>
        </section>

        <section className="ourselves-section" id="ourselves">
          <div className="container-fluid app-container">
            <h2>Ourselves</h2>
            <div className="ourselves-grid">
              <aside className="team-tabs">
                {["team", "goal", "laboratory"].map((tab) => (
                  <button
                    key={tab}
                    className={`team-tab ${teamTab === tab ? "active" : ""}`}
                    onClick={() => setTeamTab(tab)}
                  >
                    {tab === "team"
                      ? "Our Team"
                      : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </aside>

              <div className="team-stage">
                {teamTab === "team" ? (
                  <div className="team-members">
                    {teamContent.team.map((member) => (
                      <div className="member-card" key={member.name}>
                        <div className="member-avatar"></div>
                        <h3>{member.name}</h3>
                        <p>{member.school}</p>
                        <div className="member-socials">
                          {member.icons.map((icon) => (
                            <i className={`bi ${icon}`} key={icon}></i>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="info-panel">
                    <div className="info-illustration">
                      <img
                        src={teamContent[teamTab].image}
                        alt={teamTab}
                        className="info-image"
                      />
                    </div>
                    <p>{teamContent[teamTab].text}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer" id="footer">
        <div className="container-fluid app-container footer-grid">
          <div>
            <h3>Namedly</h3>
            <p>Descriptive line about your company does.</p>
            <div className="footer-socials">
              <i className="bi bi-instagram"></i>
              <i className="bi bi-linkedin"></i>
              <i className="bi bi-twitter-x"></i>
            </div>
          </div>
          <div>
            <h4>Features</h4>
            <a href="#about-section">Core features</a>
            <a href="#about-section">Pro experience</a>
            <a href="#about-section">Integrations</a>
          </div>
          <div>
            <h4>Learn more</h4>
            <a href="#ourselves">Blog</a>
            <a href="#ourselves">Case studies</a>
            <a href="#ourselves">Customer stories</a>
            <a href="#ourselves">Best practices</a>
          </div>
          <div>
            <h4>Support</h4>
            <a href="#ourselves">Contact</a>
            <LinkButton to="/registration" text="Registration form" />
            <LinkButton to="/consent" text="Consent form" />
          </div>
        </div>
      </footer>
    </div>
  );
}

function LinkButton({ to, text }) {
  return <a href={to}>{text}</a>;
}
