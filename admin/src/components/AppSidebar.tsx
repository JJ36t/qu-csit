import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  CalendarOutlined,
  TeamOutlined,
  BookOutlined,
  NotificationOutlined,
  DatabaseOutlined,
  ScheduleOutlined,
  BellOutlined,
  AuditOutlined,
  FileExcelOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

const { Sider } = Layout;

const items = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "الرئيسية" },
  { key: "/academic", icon: <DatabaseOutlined />, label: "البنية الأكاديمية" },
  { key: "/groups", icon: <TeamOutlined />, label: "الشعب" },
  { key: "/offerings", icon: <BookOutlined />, label: "تدريس المواد" },
  { key: "/timetable", icon: <CalendarOutlined />, label: "الجدول" },
  { key: "/materials", icon: <FileTextOutlined />, label: "المحاضرات" },
  { key: "/students", icon: <FileExcelOutlined />, label: "استيراد الطلاب" },
  { key: "/announcements", icon: <NotificationOutlined />, label: "الإعلانات" },
  { key: "/absence-rules", icon: <ScheduleOutlined />, label: "قواعد الغياب" },
  { key: "/sessions", icon: <ScheduleOutlined />, label: "الحضور" },
  { key: "/notifications", icon: <BellOutlined />, label: "الإشعارات" },
  { key: "/audit-logs", icon: <AuditOutlined />, label: "سجل التدقيق" },
];

export default function AppSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <Sider width={230} style={{ background: "#fff" }} breakpoint="lg" collapsible>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={items}
        onClick={({ key }) => navigate(key)}
        style={{ height: "100%", borderInlineStart: "1px solid #f0f0f0" }}
      />
    </Sider>
  );
}
