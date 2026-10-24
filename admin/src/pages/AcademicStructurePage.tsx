import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Switch,
  Select,
  message,
  Space,
  Tag,
} from "antd";
import { PlusOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { academicApi } from "../api/endpoints";

const { Title } = Typography;

export default function AcademicStructurePage() {
  const [years, setYears] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [offerings, setOfferings] = useState<any[]>([]);
  const [yearModalOpen, setYearModalOpen] = useState(false);
  const [termModalOpen, setTermModalOpen] = useState(false);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [courseModalOpen, setCourseModalOpen] = useState(false);
  const [offeringModalOpen, setOfferingModalOpen] = useState(false);
  const [yearForm] = Form.useForm();
  const [termForm] = Form.useForm();
  const [groupForm] = Form.useForm();
  const [courseForm] = Form.useForm();
  const [offeringForm] = Form.useForm();

  const loadAll = async () => {
    const [y, t, g, d, c, o] = await Promise.all([
      academicApi.listAcademicYears(),
      academicApi.listTerms(),
      academicApi.listGroups(),
      academicApi.listDepartments(),
      academicApi.listCourses(),
      academicApi.listOfferings(),
    ]);
    setYears(y.data);
    setTerms(t.data);
    setGroups(g.data);
    setDepartments(d.data);
    setCourses(c.data);
    setOfferings(o.data);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleGenerateSessions = async (termId: string) => {
    const r = await academicApi.generateSessions(termId);
    message.success(`تم توليد ${r.data.created} جلسة محاضرات`);
  };

  return (
    <div>
      <Title level={3}>البنية الأكاديمية</Title>

      <Card title="السنوات الدراسية" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Button icon={<PlusOutlined />} onClick={() => { yearForm.resetFields(); setYearModalOpen(true); }}>
            إضافة سنة
          </Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={years}
          columns={[
            { title: "السنة", dataIndex: "label" },
            {
              title: "الحالية",
              dataIndex: "is_current",
              render: (c: boolean) => (c ? <Tag color="green">نعم</Tag> : "—"),
            },
          ]}
        />
      </Card>

      <Card title="الكورسات (الفصول الدراسية)" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Button icon={<PlusOutlined />} onClick={() => { termForm.resetFields(); setTermModalOpen(true); }}>
            إضافة كورس
          </Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={terms}
          columns={[
            { title: "الاسم", dataIndex: "name" },
            { title: "البداية", dataIndex: "start_date" },
            { title: "النهاية", dataIndex: "end_date" },
            {
              title: "الحالي",
              dataIndex: "is_current",
              render: (c: boolean) => (c ? <Tag color="green">نعم</Tag> : "—"),
            },
            {
              title: "إجراءات",
              render: (_, row) => (
                <Button
                  size="small"
                  icon={<ThunderboltOutlined />}
                  onClick={() => handleGenerateSessions(row.id)}
                >
                  توليد الجلسات
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Card title="الأقسام" style={{ marginBottom: 16 }}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={departments}
          columns={[
            { title: "الاسم", dataIndex: "name_ar" },
            { title: "الرمز", dataIndex: "code" },
            { title: "عدد المراحل", dataIndex: "stages_count" },
          ]}
        />
      </Card>

      <Card title="الشعب" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Button icon={<PlusOutlined />} onClick={() => { groupForm.resetFields(); setGroupModalOpen(true); }}>
            إضافة شعبة
          </Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          dataSource={groups}
          columns={[
            { title: "القسم", dataIndex: "department_id", render: (id: string) => departments.find((d) => d.id === id)?.code ?? "—" },
            { title: "المرحلة", dataIndex: "stage" },
            { title: "الاسم", dataIndex: "name" },
            { title: "النوع", dataIndex: "study_type", render: (t: string) => (t === "morning" ? "صباحي" : "مسائي") },
          ]}
        />
      </Card>

      <Card title="المواد" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Button icon={<PlusOutlined />} onClick={() => { courseForm.resetFields(); setCourseModalOpen(true); }}>
            إضافة مادة
          </Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          dataSource={courses}
          columns={[
            { title: "الرمز", dataIndex: "code" },
            { title: "الاسم", dataIndex: "name_ar" },
            { title: "المرحلة", dataIndex: "stage" },
            { title: "الوحدات", dataIndex: "units" },
            { title: "النوع", dataIndex: "kind", render: (k: string) => (k === "lab" ? "مختبر" : "نظري") },
          ]}
        />
      </Card>

      <Card title="تدريس المواد">
        <Space style={{ marginBottom: 12 }}>
          <Button icon={<PlusOutlined />} onClick={() => { offeringForm.resetFields(); setOfferingModalOpen(true); }}>
            إضافة تدريس
          </Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          dataSource={offerings}
          columns={[
            { title: "المادة", dataIndex: "course_id", render: (id: string) => courses.find((c) => c.id === id)?.code ?? "—" },
            { title: "الشعبة", dataIndex: "group_id", render: (id: string) => groups.find((g) => g.id === id)?.name ?? "—" },
            { title: "النوع", dataIndex: "session_kind" },
            { title: "التدريسي", dataIndex: "instructor_id", render: (id: string | null) => (id ? id.slice(0, 8) + "…" : "—") },
          ]}
        />
      </Card>

      {/* Year modal */}
      <Modal
        title="إضافة سنة دراسية"
        open={yearModalOpen}
        onOk={async () => {
          try {
            const v = await yearForm.validateFields();
            await academicApi.createAcademicYear(v);
            message.success("تمت الإضافة");
            setYearModalOpen(false);
            loadAll();
          } catch (e: any) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.message_ar || "فشل");
          }
        }}
        onCancel={() => setYearModalOpen(false)}
      >
        <Form form={yearForm} layout="vertical">
          <Form.Item name="label" label="السنة (مثل 2025/2026)" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_current" label="الحالية" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Term modal */}
      <Modal
        title="إضافة كورس"
        open={termModalOpen}
        onOk={async () => {
          try {
            const v = await termForm.validateFields();
            await academicApi.createTerm({
              ...v,
              start_date: v.start_date.format("YYYY-MM-DD"),
              end_date: v.end_date.format("YYYY-MM-DD"),
            });
            message.success("تمت الإضافة");
            setTermModalOpen(false);
            loadAll();
          } catch (e: any) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.message_ar || "فشل");
          }
        }}
        onCancel={() => setTermModalOpen(false)}
      >
        <Form form={termForm} layout="vertical">
          <Form.Item name="academic_year_id" label="السنة الدراسية" rules={[{ required: true }]}>
            <Select options={years.map((y) => ({ value: y.id, label: y.label }))} />
          </Form.Item>
          <Form.Item name="name" label="اسم الكورس" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="start_date" label="تاريخ البداية" rules={[{ required: true }]}>
            <DatePicker />
          </Form.Item>
          <Form.Item name="end_date" label="تاريخ النهاية" rules={[{ required: true }]}>
            <DatePicker />
          </Form.Item>
          <Form.Item name="is_current" label="الحالي" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Group modal */}
      <Modal
        title="إضافة شعبة"
        open={groupModalOpen}
        onOk={async () => {
          try {
            const v = await groupForm.validateFields();
            await academicApi.createGroup(v);
            message.success("تمت الإضافة");
            setGroupModalOpen(false);
            loadAll();
          } catch (e: any) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.message_ar || "فشل");
          }
        }}
        onCancel={() => setGroupModalOpen(false)}
      >
        <Form form={groupForm} layout="vertical">
          <Form.Item name="department_id" label="القسم" rules={[{ required: true }]}>
            <Select options={departments.map((d) => ({ value: d.id, label: d.name_ar }))} />
          </Form.Item>
          <Form.Item name="stage" label="المرحلة" rules={[{ required: true }]}>
            <InputNumber min={1} max={8} />
          </Form.Item>
          <Form.Item name="name" label="اسم الشعبة" rules={[{ required: true }]}>
            <Input placeholder="مثل A" />
          </Form.Item>
          <Form.Item name="study_type" label="النوع">
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

      {/* Course modal */}
      <Modal
        title="إضافة مادة"
        open={courseModalOpen}
        onOk={async () => {
          try {
            const v = await courseForm.validateFields();
            await academicApi.createCourse(v);
            message.success("تمت الإضافة");
            setCourseModalOpen(false);
            loadAll();
          } catch (e: any) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.message_ar || "فشل");
          }
        }}
        onCancel={() => setCourseModalOpen(false)}
      >
        <Form form={courseForm} layout="vertical">
          <Form.Item name="code" label="الرمز" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name_ar" label="الاسم بالعربي" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department_id" label="القسم" rules={[{ required: true }]}>
            <Select options={departments.map((d) => ({ value: d.id, label: d.name_ar }))} />
          </Form.Item>
          <Form.Item name="stage" label="المرحلة" rules={[{ required: true }]}>
            <InputNumber min={1} max={8} />
          </Form.Item>
          <Form.Item name="units" label="الوحدات">
            <InputNumber min={1} max={10} />
          </Form.Item>
          <Form.Item name="kind" label="النوع">
            <Select options={[{ value: "theory", label: "نظري" }, { value: "lab", label: "مختبر" }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Offering modal */}
      <Modal
        title="إضافة تدريس مادة"
        open={offeringModalOpen}
        onOk={async () => {
          try {
            const v = await offeringForm.validateFields();
            await academicApi.createOffering(v);
            message.success("تمت الإضافة");
            setOfferingModalOpen(false);
            loadAll();
          } catch (e: any) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.message_ar || "فشل");
          }
        }}
        onCancel={() => setOfferingModalOpen(false)}
      >
        <Form form={offeringForm} layout="vertical">
          <Form.Item name="course_id" label="المادة" rules={[{ required: true }]}>
            <Select options={courses.map((c) => ({ value: c.id, label: `${c.code} — ${c.name_ar}` }))} />
          </Form.Item>
          <Form.Item name="term_id" label="الكورس" rules={[{ required: true }]}>
            <Select options={terms.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="group_id" label="الشعبة" rules={[{ required: true }]}>
            <Select options={groups.map((g) => ({ value: g.id, label: `${g.name} (${g.stage})` }))} />
          </Form.Item>
          <Form.Item name="session_kind" label="النوع">
            <Select options={[{ value: "theory", label: "نظري" }, { value: "lab", label: "مختبر" }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
