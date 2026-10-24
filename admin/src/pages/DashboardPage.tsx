import { Card, Col, Row, Statistic, Typography, Tag, Alert, Button, Space } from "antd";
import { useEffect, useState } from "react";
import { ReloadOutlined, ApiOutlined, DashboardOutlined } from "@ant-design/icons";
import axios from "axios";

type Health = { status: string; env: string; app: string };

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<{ students: number; instructors: number; courses: number; departments: number } | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      // /health is at the API origin (no /api/v1 prefix). Use a raw axios call
      // to the configured proxy target. The Vite dev server proxies /health
      // and /api to the backend.
      const r = await axios.get<Health>("/health");
      setHealth(r.data);
      // Also fetch public stats (no auth required)
      try {
        const s = await axios.get("/api/v1/public/stats");
        setStats(s.data);
      } catch {
        setStats(null);
      }
    } catch (e: any) {
      setErr(e?.message || "تعذّر الاتصال بالسيرفر");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <Typography.Title level={3}>لوحة المعلومات</Typography.Title>
      <Typography.Paragraph type="secondary">
        هذه لوحة تحكم ويب لمسؤولي الأقسام وعمادة الكلية. يتم تفعيل الصفحات تدريجياً عبر مراحل المشروع.
      </Typography.Paragraph>

      {err && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="تعذّر الاتصال بالسيرفر"
          description={
            <Space direction="vertical">
              <span>{err}</span>
              <span>
                تأكد أن السيرفر يعمل على <Typography.Text code>http://localhost:8000</Typography.Text>
              </span>
              <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>
                إعادة المحاولة
              </Button>
            </Space>
          }
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="حالة السيرفر"
              value={health?.status ?? (err ? "خطأ" : "...")}
              valueStyle={{ color: err ? "#cf1322" : "#3f8600" }}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="البيئة"
              value={health?.env ?? "..."}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="اسم الخدمة"
              value={health?.app ?? "..."}
            />
          </Card>
        </Col>
      </Row>

      {stats && (
        <>
          <Typography.Title level={4} style={{ marginTop: 32 }}>
            إحصائيات الكلية
          </Typography.Title>
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Card>
                <Statistic title="الطلاب" value={stats.students} />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic title="التدريسيون" value={stats.instructors} />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic title="المواد" value={stats.courses} />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic title="الأقسام" value={stats.departments} />
              </Card>
            </Col>
          </Row>
        </>
      )}

      <Card style={{ marginTop: 32 }}>
        <Typography.Title level={5}>روابط سريعة</Typography.Title>
        <Space wrap>
          <Tag color="blue">
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
              Swagger UI (API docs)
            </a>
          </Tag>
          <Tag color="green">
            <a href="http://localhost:8000/api/v1/public/privacy" target="_blank" rel="noreferrer">
              سياسة الخصوصية
            </a>
          </Tag>
          <Tag color="purple">
            <a href="http://localhost:8000/api/v1/public/stats" target="_blank" rel="noreferrer">
              إحصائيات عامة
            </a>
          </Tag>
          <Tag color="orange">
            <a href="http://localhost:8000/api/v1/public/maintenance" target="_blank" rel="noreferrer">
              حالة الصيانة
            </a>
          </Tag>
        </Space>
      </Card>
    </div>
  );
}
