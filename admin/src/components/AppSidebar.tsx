import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  CalendarOutlined,
  TeamOutlined,
  BookOutlined,
  ScheduleOutlined,
  NotificationOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

const { Sider } = Layout;

const items = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "الرئيسية" },
  { key: "/academic-years", icon: <DatabaseOutlined />, label: "السنوات والكورسات" },
  { key: "/groups", icon: <TeamOutlined />, label: "الشعب" },
  { key: "/offerings", icon: <BookOutlined />, label: "تدريس المواد" },
  { key: "/timetable", icon: <CalendarOutlined />, label: "الجدول" },
  { key: "/students", icon: <TeamOutlined />, label: "استيراد الطلاب" },
  { key: "/announcements", icon: <NotificationOutlined />, label: "الإعلانات" },
  { key: "/sessions", icon: <ScheduleOutlined />, label: "الحضور" },
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
