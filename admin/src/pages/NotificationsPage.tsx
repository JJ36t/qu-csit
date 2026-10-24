import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Tag,
  Button,
  Space,
  message,
  Switch,
} from "antd";
import { ReloadOutlined, CheckOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api/endpoints";

const { Title } = Typography;

const TYPE_LABELS: Record<string, { color: string; label: string }> = {
  timetable_change: { color: "blue", label: "تغيير جدول" },
  attendance_open: { color: "green", label: "فتح حضور" },
  announcement: { color: "purple", label: "إعلان" },
  new_material: { color: "orange", label: "محاضرة جديدة" },
  absence_warning: { color: "red", label: "تحذير غياب" },
  grade_published: { color: "cyan", label: "نشر درجات" },
  excuse_reviewed: { color: "gold", label: "مراجعة عذر" },
  request_updated: { color: "magenta", label: "تحديث طلب" },
};

export default function NotificationsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/notifications", {
        params: { unread_only: unreadOnly, page: 1, limit: 50 },
      });
      setItems(r.data.items);
      setTotal(r.data.total);
      setUnread(r.data.unread);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل التحميل");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [unreadOnly]);

  const markAllRead = async () => {
    try {
      await api.post("/notifications/read-all");
      message.success("تم تعليم الكل كمقروء");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل");
    }
  };

  const markOneRead = async (id: string) => {
    try {
      await api.post(`/notifications/${id}/read`);
      load();
    } catch {}
  };

  return (
    <Card>
      <Title level={4}>صندوق الإشعارات</Title>

      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          تحديث
        </Button>
        <Button icon={<CheckOutlined />} onClick={markAllRead} disabled={unread === 0}>
          تعليم الكل كمقروء ({unread})
        </Button>
        <span>عرض غير المقروء فقط:</span>
        <Switch checked={unreadOnly} onChange={setUnreadOnly} />
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 20, total }}
        columns={[
          {
            title: "النوع",
            dataIndex: "type",
            render: (t: string) => {
              const cfg = TYPE_LABELS[t] ?? { color: "default", label: t };
              return <Tag color={cfg.color}>{cfg.label}</Tag>;
            },
          },
          {
            title: "العنوان",
            dataIndex: "title",
            render: (s: string, row: any) => (
              <strong style={{ fontWeight: row.read_at ? "normal" : "bold" }}>{s}</strong>
            ),
          },
          { title: "النص", dataIndex: "body", ellipsis: true },
          {
            title: "الوقت",
            dataIndex: "created_at",
            render: (s: string) => dayjs(s).format("YYYY-MM-DD HH:mm"),
          },
          {
            title: "الحالة",
            dataIndex: "read_at",
            render: (s: string | null, row: any) =>
              s ? (
                <Tag>مقروء</Tag>
              ) : (
                <Button size="small" type="link" onClick={() => markOneRead(row.id)}>
                  تعليم كمقروء
                </Button>
              ),
          },
        ]}
      />
    </Card>
  );
}
