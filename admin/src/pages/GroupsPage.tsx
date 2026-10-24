import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  InputNumber,
  Select,
  message,
  Space,
  Tag,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { academicApi } from "../api/endpoints";

const { Title } = Typography;

export default function GroupsPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState<{ dept?: string; stage?: number }>({});

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filters.dept) params.department_id = filters.dept;
      if (filters.stage) params.stage = filters.stage;
      const [g, d, t] = await Promise.all([
        academicApi.listGroups(),
        academicApi.listDepartments(),
        academicApi.listTerms(),
      ]);
      setGroups(g.data);
      setDepartments(d.data);
      setTerms(t.data);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل التحميل");
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
      await academicApi.createGroup(v);
      message.success("تمت إضافة الشعبة");
      setModalOpen(false);
      form.resetFields();
      load();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.message_ar || "فشل الحفظ");
    }
  };

  return (
    <Card>
      <Title level={4}>الشعب</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          placeholder="تصفية حسب القسم"
          style={{ width: 200 }}
          value={filters.dept}
          onChange={(v) => setFilters((f) => ({ ...f, dept: v }))}
          options={departments.map((d) => ({ value: d.id, label: d.name_ar }))}
        />
        <Select
          allowClear
          placeholder="تصفية حسب المرحلة"
          style={{ width: 150 }}
          value={filters.stage}
          onChange={(v) => setFilters((f) => ({ ...f, stage: v }))}
          options={[1, 2, 3, 4, 5, 6, 7, 8].map((n) => ({ value: n, label: `المرحلة ${n}` }))}
        />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          تحديث
        </Button>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            setModalOpen(true);
          }}
        >
          إضافة شعبة
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={groups.filter((g) => {
          if (filters.dept && g.department_id !== filters.dept) return false;
          if (filters.stage && g.stage !== filters.stage) return false;
          return true;
        })}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: "القسم",
            dataIndex: "department_id",
            render: (id: string) => departments.find((d) => d.id === id)?.code ?? "—",
          },
          { title: "المرحلة", dataIndex: "stage", render: (s: number) => <Tag color="blue">المرحلة {s}</Tag> },
          { title: "الاسم", dataIndex: "name", render: (s: string) => <strong>{s}</strong> },
          {
            title: "النوع",
            dataIndex: "study_type",
            render: (s: string) => (
              <Tag color={s === "morning" ? "green" : "purple"}>
                {s === "morning" ? "صباحي" : "مسائي"}
              </Tag>
            ),
          },
        ]}
      />

      <Modal
        title="إضافة شعبة"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="حفظ"
        cancelText="إلغاء"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="department_id" label="القسم" rules={[{ required: true }]}>
            <Select options={departments.map((d) => ({ value: d.id, label: d.name_ar }))} />
          </Form.Item>
          <Form.Item name="stage" label="المرحلة" rules={[{ required: true }]}>
            <InputNumber min={1} max={8} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="name" label="اسم الشعبة (مثل A)" rules={[{ required: true }]}>
            <Select
              options={["A", "B", "C", "D"].map((n) => ({ value: n, label: n }))}
            />
          </Form.Item>
          <Form.Item name="study_type" label="النوع" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "morning", label: "صباحي" },
                { value: "evening", label: "مسائي" },
              ]}
            />
          </Form.Item>
          <Form.Item name="term_id" label="الكورس" rules={[{ required: true }]}>
            <Select options={terms.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
