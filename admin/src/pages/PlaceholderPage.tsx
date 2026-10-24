import { Card, Typography, Tag } from "antd";

export default function PlaceholderPage({
  title,
  phase,
}: {
  title: string;
  phase?: string;
}) {
  return (
    <Card>
      <Typography.Title level={4}>{title}</Typography.Title>
      <Typography.Paragraph type="secondary">
        هذه الصفحة تُنفّذ في المرحلة القادمة.
      </Typography.Paragraph>
      {phase && <Tag color="processing">{phase}</Tag>}
    </Card>
  );
}
