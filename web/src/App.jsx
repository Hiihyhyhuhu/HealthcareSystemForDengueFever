import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Registration from "./pages/RegistrationPage";
import Consent from "./pages/ConsentPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/registration" element={<Registration />} />
      <Route path="/consent" element={<Consent />} />
    </Routes>
  );
}
