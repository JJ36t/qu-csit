import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Select,
  TimePicker,
  message,
  Space,
  Tag,
  Popconfirm,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { academicApi, timetableApi } from "../api/endpoints";

const { Title } = Typography;
const WEEKDAYS = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];

export default function TimetablePage() {
  const [offerings, setOfferings] = useState<any[]>([]);
  const [slots, setSlots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState<any | null>(null);
  const [form] = Form.useForm();

  const loadOfferings = async () => {
    const r = await academicApi.listOfferings();
    setOfferings(r.data);
  };

  const loadSlots = async () => {
    setLoading(true);
    try {
      const today = dayjs();
      const r = await timetableApi.getMy(
        today.subtract(7, "day").format("YYYY-MM-DD"),
        today.add(30, "day").format("YYYY-MM-DD")
      );
      // Flatten the date-grouped response into a list of (date, slot) entries
      const flat: any[] = [];
      for (const day of r.data) {
        for (const entry of day.entries) {
          flat.push({ ...entry.slot, date: day.date, is_cancelled: entry.is_cancelled });
        }
      }
      // Deduplicate by slot id
      const seen = new Set<string>();
      const unique = flat.filter((s) => {
        if (seen.has(s.id)) return false;
        seen.add(s.id);
        return true;
      });
      setSlots(unique);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOfferings();
    loadSlots();
  }, []);

  const openCreate = () => {
    setEditingSlot(null);
    form.resetFields();
    form.setFieldsValue({ weekday: 0, kind: "theory" });
    setModalOpen(true);
  };

  const openEdit = (slot: any) => {
    setEditingSlot(slot);
    form.setFieldsValue({
      offering_id: slot.offering_id,
      weekday: slot.weekday,
      start_time: dayjs(slot.start_time, "HH:mm:ss"),
      end_time: dayjs(slot.end_time, "HH:mm:ss"),
      kind: slot.kind,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const v = await form.validateFields();
      const payload = {
        ...v,
        start_time: v.start_time.format("HH:mm:ss"),
        end_time: v.end_time.format("HH:mm:ss"),
      };
      if (editingSlot) {
        await timetableApi.updateSlot(editingSlot.id, payload);
        message.success("تم تعديل الحصة");
      } else {
        await timetableApi.createSlot(payload);
        message.success("تمت إضافة الحصة");
      }
      setModalOpen(false);
      loadSlots();
    } catch (e: any) {
      if (e?.response?.data?.code?.includes("CONFLICT")) {
        message.error(e.response.data.message_ar || "تعارض في الجدول");
      } else if (e?.errorFields) {
        // validation
      } else {
        message.error(e?.response?.data?.message_ar || "فشل الحفظ");
      }
    }
  };

  const handleDelete = async (id: string) => {
    await timetableApi.deleteSlot(id);
    message.success("تم حذف الحصة");
    loadSlots();
  };

  return (
    <Card>
      <Title level={4}>محرر الجدول الأسبوعي</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          إضافة حصة
        </Button>
        <Button onClick={loadSlots}>تحديث</Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={slots}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: "المادة (تدريس)",
            dataIndex: "offering_id",
            render: (id) => {
              const o = offerings.find((x) => x.id === id);
              return o ? o.course_id?.slice(0, 8) + "…" : id.slice(0, 8) + "…";
            },
          },
          { title: "اليوم", dataIndex: "weekday", render: (d) => WEEKDAYS[d] ?? d },
          {
            title: "البداية",
            dataIndex: "start_time",
            render: (s: string) => s?.slice(0, 5),
          },
          { title: "النهاية", dataIndex: "end_time", render: (s: string) => s?.slice(0, 5) },
          {
            title: "النوع",
            dataIndex: "kind",
            render: (k: string) => (k === "lab" ? <Tag color="orange">مختبر</Tag> : <Tag color="blue">نظري</Tag>),
          },
          {
            title: "إجراءات",
            render: (_, row) => (
              <Space>
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)} />
                <Popconfirm
                  title="حذف الحصة؟"
                  onConfirm={() => handleDelete(row.id)}
                  okText="نعم"
                  cancelText="لا"
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editingSlot ? "تعديل حصة" : "إضافة حصة"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="حفظ"
        cancelText="إلغاء"
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="offering_id" label="تدريس المادة" rules={[{ required: true }]}>
            <Select
              placeholder="اختر تدريس المادة"
              showSearch
              optionFilterProp="label"
              options={offerings.map((o) => ({ value: o.id, label: o.id.slice(0, 8) }))}
              disabled={!!editingSlot}
            />
          </Form.Item>
          <Form.Item name="weekday" label="اليوم" rules={[{ required: true }]}>
            <Select
              options={WEEKDAYS.map((label, value) => ({ value, label }))}
            />
          </Form.Item>
          <Space style={{ display: "flex" }}>
            <Form.Item name="start_time" label="البداية" rules={[{ required: true }]}>
              <TimePicker format="HH:mm:ss" />
            </Form.Item>
            <Form.Item name="end_time" label="النهاية" rules={[{ required: true }]}>
              <TimePicker format="HH:mm:ss" />
            </Form.Item>
          </Space>
          <Form.Item name="kind" label="النوع">
            <Select
              options={[
                { value: "theory", label: "نظري" },
                { value: "lab", label: "مختبر" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
