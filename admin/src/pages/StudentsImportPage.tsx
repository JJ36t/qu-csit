import { useState } from "react";
import {
  Card,
  Typography,
  Table,
  Upload,
  message,
  Modal,
  Tag,
  Space,
} from "antd";
import { InboxOutlined } from "@ant-design/icons";
import type { UploadProps } from "antd";
import { usersApi } from "../api/endpoints";

const { Title, Text } = Typography;
const { Dragger } = Upload;

export default function StudentsImportPage() {
  const [preview, setPreview] = useState<any | null>(null);
  const [committing, setCommitting] = useState(false);

  const uploadProps: UploadProps = {
    name: "file",
    multiple: false,
    accept: ".xlsx",
    showUploadList: true,
    beforeUpload: () => true, // we handle upload manually via customRequest
    customRequest: async (options) => {
      const { file, onSuccess, onError } = options;
      try {
        const r = await usersApi.importStudents(file as File, true);
        setPreview(r.data);
        onSuccess?.({}, new XMLHttpRequest());
      } catch (e: any) {
        message.error(e?.response?.data?.message_ar || "فشل الرفع");
        onError?.(e);
      }
    },
  };

  const handleCommit = async () => {
    if (!preview) return;
    setCommitting(true);
    try {
      const r = await usersApi.commitStudentImport(preview.batch_id);
      message.success(`تم إنشاء ${r.data.created} حساب طالب. كلمة المرور الأولية: ${r.data.initial_password}`);
      setPreview(null);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل التثبيت");
    } finally {
      setCommitting(false);
    }
  };

  return (
    <Card>
      <Title level={4}>استيراد قوائم الطلاب</Title>
      <Text type="secondary">
        ارفع ملف Excel بالأعمدة: university_id | full_name_ar | email | phone | department_code | stage | study_type | group_name
      </Text>
      <div style={{ marginTop: 16, marginBottom: 16 }}>
        <Dragger {...uploadProps} style={{ padding: 24 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">اسحب ملف Excel هنا أو اضغط للاختيار</p>
          <p className="ant-upload-hint">يدعم ملفات .xlsx فقط</p>
        </Dragger>
      </div>

      {preview && (
        <Modal
          title="معاينة الاستيراد"
          open={!!preview}
          onCancel={() => setPreview(null)}
          onOk={handleCommit}
          okText={`تثبيت (${preview.valid_rows} طالب)`}
          cancelText="إلغاء"
          okButtonProps={{ loading: committing, disabled: preview.valid_rows === 0 }}
          width={800}
        >
          <Space direction="vertical" style={{ width: "100%" }}>
            <div>
              <Tag color="green">{preview.valid_rows} صالح</Tag>
              <Tag color="red">{preview.error_rows} خطأ</Tag>
              <Tag color="blue">كلمة المرور الأولية: {preview.initial_password}</Tag>
            </div>
            <Table
              size="small"
              rowKey={(_, idx) => String(idx)}
              pagination={{ pageSize: 10 }}
              dataSource={preview.rows}
              columns={[
                { title: "الصف", dataIndex: "row", width: 60 },
                {
                  title: "الحالة",
                  dataIndex: "ok",
                  render: (ok: boolean) => (ok ? <Tag color="green">صالح</Tag> : <Tag color="red">خطأ</Tag>),
                },
                { title: "الرقم الجامعي", dataIndex: "university_id" },
                { title: "الاسم", dataIndex: "full_name_ar" },
                { title: "السبب", dataIndex: "error" },
              ]}
            />
          </Space>
        </Modal>
      )}
    </Card>
  );
}
