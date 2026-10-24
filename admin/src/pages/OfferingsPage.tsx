import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Select,
  message,
  Space,
  Tag,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { academicApi } from "../api/endpoints";

const { Title } = Typography;

export default function OfferingsPage() {
  const [offerings, setOfferings] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [o, c, g, t] = await Promise.all([
        academicApi.listOfferings(),
        academicApi.listCourses(),
        academicApi.listGroups(),
        academicApi.listTerms(),
      ]);
      setOfferings(o.data);
      setCourses(c.data);
      setGroups(g.data);
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
      await academicApi.createOffering(v);
      message.success("تمت إضافة تدريس المادة");
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
      <Title level={4}>تدريس المواد</Title>

      <Space style={{ marginBottom: 16 }}>
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
          إضافة تدريس
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={offerings}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: "المادة",
            dataIndex: "course_id",
            render: (id: string) => {
              const c = courses.find((x) => x.id === id);
              return c ? `${c.code} — ${c.name_ar}` : "—";
            },
          },
          {
            title: "الشعبة",
            dataIndex: "group_id",
            render: (id: string) => {
              const g = groups.find((x) => x.id === id);
              return g ? (
                <Space>
                  <Tag color="blue">المرحلة {g.stage}</Tag>
                  <Tag>{g.name}</Tag>
                  <Tag color={g.study_type === "morning" ? "green" : "purple"}>
                    {g.study_type === "morning" ? "صباحي" : "مسائي"}
                  </Tag>
                </Space>
              ) : (
                "—"
              );
            },
          },
          {
            title: "النوع",
            dataIndex: "session_kind",
            render: (s: string) => (
              <Tag color={s === "lab" ? "orange" : "blue"}>
                {s === "lab" ? "مختبر" : "نظري"}
              </Tag>
            ),
          },
          {
            title: "التدريسي",
            dataIndex: "instructor_id",
            render: (id: string | null) => (id ? <span style={{ fontFamily: "monospace", fontSize: 12 }}>{id.slice(0, 8)}…</span> : <Tag>غير معيّن</Tag>),
          },
        ]}
      />

      <Modal
        title="إضافة تدريس مادة"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="حفظ"
        cancelText="إلغاء"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="course_id" label="المادة" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={courses.map((c) => ({
                value: c.id,
                label: `${c.code} — ${c.name_ar} (مرحلة ${c.stage})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="term_id" label="الكورس" rules={[{ required: true }]}>
            <Select options={terms.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="group_id" label="الشعبة" rules={[{ required: true }]}>
            <Select
              options={groups.map((g) => ({
                value: g.id,
                label: `مرحلة ${g.stage} — ${g.name} (${g.study_type === "morning" ? "صباحي" : "مسائي"})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="session_kind" label="النوع">
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
