import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "antd";
import AppHeader from "./components/AppHeader";
import AppSidebar from "./components/AppSidebar";
import DashboardPage from "./pages/DashboardPage";
import AcademicStructurePage from "./pages/AcademicStructurePage";
import TimetablePage from "./pages/TimetablePage";
import AnnouncementsPage from "./pages/AnnouncementsPage";
import StudentsImportPage from "./pages/StudentsImportPage";
import AbsenceRulesPage from "./pages/AbsenceRulesPage";
import PlaceholderPage from "./pages/PlaceholderPage";

const { Content } = Layout;

export default function App() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader />
      <Layout>
        <AppSidebar />
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/academic" element={<AcademicStructurePage />} />
            <Route path="/timetable" element={<TimetablePage />} />
            <Route path="/students" element={<StudentsImportPage />} />
            <Route path="/announcements" element={<AnnouncementsPage />} />
            <Route path="/absence-rules" element={<AbsenceRulesPage />} />
            <Route path="*" element={<PlaceholderPage title="غير موجود" phase="" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
