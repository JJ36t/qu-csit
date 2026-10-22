import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  InputNumber,
  Switch,
  Select,
  message,
  Space,
  Input,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { absenceRulesApi, academicApi } from "../api/endpoints";

const { Title } = Typography;

export default function AbsenceRulesPage() {
  const [rules, setRules] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [r, t, d] = await Promise.all([
        absenceRulesApi.list(),
        academicApi.listTerms(),
        academicApi.listDepartments(),
      ]);
      setRules(r.data);
      setTerms(t.data);
      setDepartments(d.data);
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
      await absenceRulesApi.upsert(v);
      message.success("تم حفظ القاعدة");
      setModalOpen(false);
      load();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.message_ar || "فشل");
    }
  };

  return (
    <Card>
      <Title level={4}>قواعد الغياب لكل كورس</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            form.setFieldsValue({
              max_absences_per_course: 10,
              late_threshold_minutes: 15,
              late_counts_as_absence: false,
              attendance_warning_threshold: 8,
            });
            setModalOpen(true);
          }}
        >
          إضافة / تعديل قاعدة
        </Button>
        <Button onClick={load}>تحديث</Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={rules}
        pagination={false}
        columns={[
          {
            title: "الكورس",
            dataIndex: "term_id",
            render: (id: string) => terms.find((t) => t.id === id)?.name ?? "—",
          },
          {
            title: "القسم",
            dataIndex: "department_id",
            render: (id: string | null) => (id ? (departments.find((d) => d.id === id)?.code ?? "—") : "كل الأقسام"),
          },
          {
            title: "المرحلة",
            dataIndex: "stage",
            render: (s: number | null) => (s ? `المرحلة ${s}` : "كل المراحل"),
          },
          { title: "حد الغياب", dataIndex: "max_absences_per_course" },
          { title: "حد التأخير (دقيقة)", dataIndex: "late_threshold_minutes" },
          {
            title: "التأخير = غياب؟",
            dataIndex: "late_counts_as_absence",
            render: (v: boolean) => (v ? "نعم" : "لا"),
          },
        ]}
      />

      <Modal
        title="قاعدة غياب"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="حفظ"
        cancelText="إلغاء"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="term_id" label="الكورس" rules={[{ required: true }]}>
            <Select options={terms.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="department_id" label="القسم (اتركه فارغاً لكل الأقسام)">
            <Select
              allowClear
              options={departments.map((d) => ({ value: d.id, label: d.name_ar }))}
            />
          </Form.Item>
          <Form.Item name="stage" label="المرحلة (اتركها فارغة لكل المراحل)">
            <InputNumber min={1} max={8} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="max_absences_per_course" label="حد الغياب لكل مادة" rules={[{ required: true }]}>
            <InputNumber min={1} max={50} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="late_threshold_minutes" label="حد التأخير (دقيقة)" rules={[{ required: true }]}>
            <InputNumber min={1} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="late_counts_as_absence" label="التأخير يعدّ غياباً" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="attendance_warning_threshold" label="حد تنبيه الحضور" rules={[{ required: true }]}>
            <InputNumber min={1} max={50} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="ملاحظات">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
