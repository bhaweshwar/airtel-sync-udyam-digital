// Routes. Phase 0 owns this file; each page lives in src/features/<name>/ and is owned by its workstream.
import { Link, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import Landing from "./Landing";
import { AdvisorPage } from "./features/advisor";
import { QuotePage } from "./features/quote";
import { KycPage } from "./features/kyc";
import { TrackLookupPage, TrackOrderPage } from "./features/track";
import { BackofficePage } from "./features/backoffice";
import { useT } from "./i18n";

function NotFound() {
  const { t } = useT();
  return (
    <div className="py-10 text-center">
      <p className="text-lg font-semibold">404</p>
      <Link to="/" className="text-brand-700 underline">{t("common.back")}</Link>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/advisor" element={<AdvisorPage />} />
        <Route path="/quote" element={<QuotePage />} />
        <Route path="/kyc/:orderId" element={<KycPage />} />
        <Route path="/track" element={<TrackLookupPage />} />
        <Route path="/track/:orderId" element={<TrackOrderPage />} />
        <Route path="/backoffice" element={<BackofficePage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
