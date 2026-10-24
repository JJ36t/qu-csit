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
  InputNumber,
  Switch,
  Upload,
  message,
  Space,
  Tag,
} from "antd";
import { PlusOutlined, ReloadOutlined, InboxOutlined, FilePdfOutlined, LinkOutlined } from "@ant-design/icons";
import type { UploadProps } from "antd";
import { academicApi, api } from "../api/endpoints";

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

export default function MaterialsPage() {
  const [offerings, setOfferings] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [selectedOffering, setSelectedOffering] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const loadOfferings = async () => {
    try {
      const r = await academicApi.listOfferings();
      setOfferings(r.data);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل تحميل المواد");
    }
  };

  const loadMaterials = async (offeringId: string) => {
    setLoading(true);
    try {
      const r = await api.get(`/offerings/${offeringId}/materials`);
      setMaterials(r.data);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل تحميل المحاضرات");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOfferings();
  }, []);

  useEffect(() => {
    if (selectedOffering) {
      loadMaterials(selectedOffering);
    } else {
      setMaterials([]);
    }
  }, [selectedOffering]);

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    if (!selectedOffering) {
      message.error("اختر تدريس مادة أولاً");
      onError?.(new Error("no offering"));
      return;
    }
    try {
      const fd = new FormData();
      fd.append("file", file as File);
      fd.append("title", form.getFieldValue("title") || (file as any).name);
      fd.append("kind", form.getFieldValue("kind") || "pdf");
      fd.append("is_published", form.getFieldValue("is_published") ?? "false");
      if (form.getFieldValue("week_no")) fd.append("week_no", form.getFieldValue("week_no"));
      if (form.getFieldValue("description")) fd.append("description", form.getFieldValue("description"));
      await api.post(`/offerings/${selectedOffering}/materials`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      message.success("تم رفع المحاضرة");
      onSuccess?.({}, new XMLHttpRequest());
      setModalOpen(false);
      form.resetFields();
      loadMaterials(selectedOffering);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل الرفع");
      onError?.(e);
    }
  };

  const handleAddLink = async () => {
    try {
      const v = await form.validateFields();
      if (!selectedOffering) {
        message.error("اختر تدريس مادة أولاً");
        return;
      }
      const fd = new FormData();
      fd.append("title", v.title);
      fd.append("kind", v.kind);
      fd.append("url", v.url);
      fd.append("is_published", v.is_published ? "true" : "false");
      if (v.week_no) fd.append("week_no", v.week_no);
      if (v.description) fd.append("description", v.description);
      await api.post(`/offerings/${selectedOffering}/materials`, fd);
      message.success("تمت إضافة الرابط");
      setModalOpen(false);
      form.resetFields();
      loadMaterials(selectedOffering);
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.message_ar || "فشل الحفظ");
    }
  };

  const uploadProps: UploadProps = {
    name: "file",
    multiple: false,
    accept: ".pdf,.mp4,.png,.jpg,.jpeg",
    showUploadList: false,
    customRequest: handleUpload,
  };

  return (
    <Card>
      <Title level={4}>المحاضرات</Title>
      <Text type="secondary">
        اختر تدريس مادة لعرض محاضراتها أو إضافة محاضرة جديدة.
      </Text>

      <Space style={{ marginBottom: 16, marginTop: 16, width: "100%" }} direction="vertical">
        <Select
          showSearch
          placeholder="اختر تدريس مادة"
          style={{ width: "100%" }}
          value={selectedOffering}
          onChange={setSelectedOffering}
          optionFilterProp="label"
          options={offerings.map((o) => ({
            value: o.id,
            label: `${o.id.slice(0, 8)}… — ${o.session_kind === "lab" ? "مختبر" : "نظري"}`,
          }))}
        />
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => selectedOffering && loadMaterials(selectedOffering)}
            loading={loading}
            disabled={!selectedOffering}
          >
            تحديث
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!selectedOffering}
            onClick={() => {
              form.resetFields();
              form.setFieldsValue({ kind: "pdf", is_published: false });
              setModalOpen(true);
            }}
          >
            إضافة محاضرة
          </Button>
        </Space>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={materials}
        pagination={{ pageSize: 20 }}
        locale={{ emptyText: selectedOffering ? "لا محاضرات" : "اختر تدريس مادة أولاً" }}
        columns={[
          {
            title: "النوع",
            dataIndex: "kind",
            render: (k: string) =>
              k === "pdf" ? (
                <Tag icon={<FilePdfOutlined />} color="red">PDF</Tag>
              ) : (
                <Tag icon={<LinkOutlined />} color="blue">{k === "video_link" ? "فيديو" : "رابط"}</Tag>
              ),
          },
          { title: "العنوان", dataIndex: "title", render: (s: string) => <strong>{s}</strong> },
          {
            title: "الأسبوع",
            dataIndex: "week_no",
            render: (w: number | null) => (w ? <Tag color="purple">أسبوع {w}</Tag> : "—"),
          },
          {
            title: "النشر",
            dataIndex: "is_published",
            render: (p: boolean) => (p ? <Tag color="green">منشور</Tag> : <Tag>مسودة</Tag>),
          },
          {
            title: "تحميل",
            dataIndex: "download_url",
            render: (url: string | null, row: any) =>
              url ? (
                <a href={url} target="_blank" rel="noreferrer">
                  <Button size="small" type="link" icon={<FilePdfOutlined />}>تنزيل</Button>
                </a>
              ) : row.url ? (
                <a href={row.url} target="_blank" rel="noreferrer">
                  <Button size="small" type="link" icon={<LinkOutlined />}>فتح</Button>
                </a>
              ) : (
                "—"
              ),
          },
        ]}
      />

      <Modal
        title="إضافة محاضرة"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalOpen(false)}>إلغاء</Button>,
          <Button
            key="link"
            type="primary"
            onClick={handleAddLink}
          >
            إضافة كرابط/فيديو
          </Button>,
        ]}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="العنوان" rules={[{ required: true }]}>
            <Input placeholder="مثال: محاضرة 1 — مقدمة" />
          </Form.Item>
          <Form.Item name="kind" label="النوع" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "pdf", label: "PDF (رفع ملف)" },
                { value: "video_link", label: "رابط فيديو" },
                { value: "link", label: "رابط خارجي" },
              ]}
            />
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.kind !== cur.kind}
          >
            {({ getFieldValue }) =>
              getFieldValue("kind") === "pdf" ? (
                <Form.Item label="رفع ملف PDF">
                  <Dragger {...uploadProps}>
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">اسحب ملف PDF هنا أو اضغط للاختيار</p>
                    <p className="ant-upload-hint">PDF / MP4 / PNG / JPG — حتى 50MB</p>
                  </Dragger>
                </Form.Item>
              ) : (
                <Form.Item name="url" label="الرابط" rules={[{ required: true, type: "url" }]}>
                  <Input placeholder="https://…" />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item name="week_no" label="رقم الأسبوع">
            <InputNumber min={1} max={20} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="is_published" label="منشور؟" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="description" label="وصف (اختياري)">
            <TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
