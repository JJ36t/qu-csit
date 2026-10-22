import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "antd";
import AppHeader from "./components/AppHeader";
import AppSidebar from "./components/AppSidebar";
import DashboardPage from "./pages/DashboardPage";
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
            <Route
              path="/academic-years"
              element={<PlaceholderPage title="السنوات الدراسية والكورسات" phase="Phase 2" />}
            />
            <Route
              path="/groups"
              element={<PlaceholderPage title="الشعب" phase="Phase 2" />}
            />
            <Route
              path="/offerings"
              element={<PlaceholderPage title="تدريس المواد" phase="Phase 2" />}
            />
            <Route
              path="/timetable"
              element={<PlaceholderPage title="الجدول" phase="Phase 2" />}
            />
            <Route
              path="/students"
              element={<PlaceholderPage title="استيراد الطلاب" phase="Phase 1" />}
            />
            <Route
              path="/announcements"
              element={<PlaceholderPage title="الإعلانات" phase="Phase 2" />}
            />
            <Route path="*" element={<PlaceholderPage title="غير موجود" phase="" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
