import { useNavigate } from "react-router-dom";

export default function FeatureCard({
  icon = "bi-heart-pulse-fill",
  title,
  text,
  button,
  linkTo,
}) {
  const navigate = useNavigate();
  return (
    <article className="feature-card h-100">
      <div className="icon-wrap">
        <i className={`bi ${icon}`}></i>
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {button ? (
        <button
          className="btn demo-btn"
          onClick={() => {
            if (linkTo) navigate(linkTo);
          }}
        >
          Try Our Demo
        </button>
      ) : null}
    </article>
  );
}
