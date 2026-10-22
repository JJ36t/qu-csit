import { Card, Col, Row, Statistic, Typography } from "antd";
import { useEffect, useState } from "react";
import { api } from "../api/client";

type Health = { status: string; env: string; app: string };

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Health>("/health")
      .then((r) => setHealth(r.data))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <div>
      <Typography.Title level={3}>لوحة المعلومات</Typography.Title>
      <Typography.Paragraph type="secondary">
        هذه لوحة تحكم ويب لمسؤولي الأقسام وعمادة الكلية. يتم تفعيل الصفحات تدريجياً عبر مراحل
        المشروع.
      </Typography.Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="حالة السيرفر"
              value={health?.status ?? (err ? "خطأ" : "...")}
              valueStyle={{ color: err ? "#cf1322" : "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="البيئة" value={health?.env ?? "..."} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="اسم الخدمة" value={health?.app ?? "..."} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
