import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import DiscoveryPage from "./pages/DiscoveryPage";
import ProfilePage from "./pages/ProfilePage";
import WatchPage from "./pages/WatchPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DiscoveryPage />} />
        <Route path="watch/:streamId" element={<WatchPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="profile/:name" element={<ProfilePage />} />
      </Route>
    </Routes>
  );
}
