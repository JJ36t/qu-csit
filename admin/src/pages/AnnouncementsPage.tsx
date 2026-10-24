import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Switch,
  message,
  Space,
  Tag,
  InputNumber,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { announcementsApi } from "../api/endpoints";

const { Title } = Typography;
const { TextArea } = Input;

export default function AnnouncementsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const r = await announcementsApi.list(1, 50);
      setItems(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = async () => {
    try {
      const v = await form.validateFields();
      const payload = {
        ...v,
        publish_at: v.publish_at ? v.publish_at.toISOString() : null,
        expires_at: v.expires_at ? v.expires_at.toISOString() : null,
      };
      await announcementsApi.create(payload);
      message.success("تم نشر الإعلان");
      setModalOpen(false);
      form.resetFields();
      load();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.message_ar || "فشل النشر");
    }
  };

  return (
    <Card>
      <Title level={4}>الإعلانات</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            form.setFieldsValue({ scope: "college", priority: 0, pinned: false });
            setModalOpen(true);
          }}
        >
          نشر إعلان
        </Button>
        <Button onClick={load}>تحديث</Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={items}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: "النطاق",
            dataIndex: "scope",
            render: (s: string) => {
              const map: Record<string, { color: string; label: string }> = {
                college: { color: "blue", label: "كلية" },
                department: { color: "green", label: "قسم" },
                stage: { color: "purple", label: "مرحلة" },
                group: { color: "cyan", label: "شعبة" },
                offering: { color: "orange", label: "مادة" },
              };
              const cfg = map[s] ?? { color: "default", label: s };
              return <Tag color={cfg.color}>{cfg.label}</Tag>;
            },
          },
          { title: "العنوان", dataIndex: "title" },
          {
            title: "مثبّت",
            dataIndex: "pinned",
            render: (p: boolean) => (p ? <Tag color="red">مثبّت</Tag> : "—"),
          },
          {
            title: "تاريخ النشر",
            dataIndex: "created_at",
            render: (s: string) => dayjs(s).format("YYYY-MM-DD HH:mm"),
          },
        ]}
      />

      <Modal
        title="نشر إعلان جديد"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="نشر"
        cancelText="إلغاء"
        width={620}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="scope" label="النطاق" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "college", label: "كلية" },
                { value: "department", label: "قسم" },
                { value: "stage", label: "مرحلة" },
                { value: "group", label: "شعبة" },
                { value: "offering", label: "مادة" },
              ]}
            />
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.scope !== cur.scope}
          >
            {({ getFieldValue }) =>
              getFieldValue("scope") !== "college" ? (
                <Form.Item
                  name="scope_id"
                  label="معرّف النطاق (UUID، أو department_id:stage للمرحلة)"
                  rules={[{ required: true, message: "مطلوب لهذا النطاق" }]}
                >
                  <Input placeholder="مثال: 550e8400-e29b-41d4-a716-446655440000 أو dept_id:2" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
          <Form.Item name="title" label="العنوان" rules={[{ required: true }]}>
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="body" label="النص" rules={[{ required: true }]}>
            <TextArea rows={5} />
          </Form.Item>
          <Space style={{ display: "flex" }}>
            <Form.Item name="priority" label="الأولوية (0-10)">
              <InputNumber min={0} max={10} />
            </Form.Item>
            <Form.Item name="pinned" label="مثبّت" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Space style={{ display: "flex" }}>
            <Form.Item name="publish_at" label="وقت النشر (اختياري)">
              <DatePicker showTime format="YYYY-MM-DD HH:mm" />
            </Form.Item>
            <Form.Item name="expires_at" label="انتهاء الصلاحية (اختياري)">
              <DatePicker showTime format="YYYY-MM-DD HH:mm" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
