import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Input,
  message,
} from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api/endpoints";

const { Title } = Typography;

const ACTION_COLORS: Record<string, string> = {
  login: "blue",
  logout: "default",
  change_password: "orange",
  create_department: "green",
  create_academic_year: "green",
  create_term: "green",
  create_group: "green",
  create_course: "green",
  create_offering: "green",
  create_slot: "blue",
  update_slot: "blue",
  delete_slot: "red",
  create_timetable_change: "orange",
  create_announcement: "purple",
  open_session: "green",
  close_session: "volcano",
  patch_attendance: "orange",
  create_material: "cyan",
  update_material: "cyan",
  student_import_commit: "green",
  reset_password: "red",
  toggle_user_status: "orange",
  unbind_device: "orange",
  term_absence_rule_upsert: "blue",
};

export default function AuditLogsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [entityFilter, setEntityFilter] = useState<string | undefined>(undefined);
  const [actionFilter, setActionFilter] = useState<string>("");

  const load = async () => {
    setLoading(true);
    try {
      const params: any = { page: 1, limit: 100 };
      if (entityFilter) params.entity = entityFilter;
      const r = await api.get("/admin/audit-logs", { params });
      let data = r.data;
      if (actionFilter) {
        data = data.filter((d: any) => d.action?.toLowerCase().includes(actionFilter.toLowerCase()));
      }
      setItems(data);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل التحميل");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [entityFilter]);

  const entities = [
    "user", "department", "academic_year", "term", "group", "course",
    "course_offering", "timetable_slot", "timetable_change", "announcement",
    "lecture_session", "attendance_record", "material", "term_absence_rule",
  ];

  return (
    <Card>
      <Title level={4}>سجل التدقيق</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          placeholder="تصفية حسب الكيان"
          style={{ width: 200 }}
          value={entityFilter}
          onChange={(v) => setEntityFilter(v)}
          options={entities.map((e) => ({ value: e, label: e }))}
        />
        <Input
          allowClear
          placeholder="بحث في الإجراء..."
          prefix={<SearchOutlined />}
          style={{ width: 200 }}
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          تحديث
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 50 }}
        scroll={{ x: "max-content" }}
        columns={[
          {
            title: "الوقت",
            dataIndex: "created_at",
            render: (s: string) => dayjs(s).format("YYYY-MM-DD HH:mm:ss"),
            width: 180,
          },
          {
            title: "الكيان",
            dataIndex: "entity",
            render: (s: string) => <Tag>{s}</Tag>,
            width: 150,
          },
          {
            title: "الإجراء",
            dataIndex: "action",
            render: (s: string) => (
              <Tag color={ACTION_COLORS[s] ?? "default"}>{s}</Tag>
            ),
            width: 200,
          },
          {
            title: "المعرّف",
            dataIndex: "entity_id",
            render: (s: string) => (s ? <span style={{ fontFamily: "monospace", fontSize: 12 }}>{s.slice(0, 8)}…</span> : "—"),
            width: 100,
          },
          {
            title: "الفاعل",
            dataIndex: "actor_id",
            render: (s: string) => (s ? <span style={{ fontFamily: "monospace", fontSize: 12 }}>{s.slice(0, 8)}…</span> : "—"),
            width: 100,
          },
          {
            title: "IP",
            dataIndex: "ip",
            render: (s: string) => s ?? "—",
            width: 120,
          },
        ]}
      />
    </Card>
  );
}
