import { Layout, Typography, Tag } from "antd";

const { Header } = Layout;

export default function AppHeader() {
  return (
    <Header
      style={{
        background: "#fff",
        paddingInline: 24,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <Typography.Title level={4} style={{ margin: 0 }}>
        لوحة تحكم كلية علوم الحاسوب – جامعة القادسية
      </Typography.Title>
      <Tag color="blue">المرحلة 0 — تهيئة</Tag>
    </Header>
  );
}
