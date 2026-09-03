import { Route, Routes } from "react-router-dom"
import { HomePage } from "./pages/HomePage"
import { PlantsPage } from "./pages/PlantsPage"
import { PlantArticlePage } from "./pages/PlantArticlePage"
import { DiscoveriesPage } from "./pages/DiscoveriesPage"
import { DiscoveryArticlePage } from "./pages/DiscoveryArticlePage"
import { LoginPage } from "./pages/LoginPage"
import { AdminApp } from "./pages/admin/AdminApp"
import { NotFoundPage } from "./pages/NotFoundPage"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/plants" element={<PlantsPage />} />
      <Route path="/plants/:slug" element={<PlantArticlePage />} />
      <Route path="/discoveries" element={<DiscoveriesPage />} />
      <Route path="/discoveries/:slug" element={<DiscoveryArticlePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/admin/*" element={<AdminApp />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}