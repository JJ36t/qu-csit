import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Table,
  Tag,
  Space,
  Button,
  message,
  Modal,
  Descriptions,
} from "antd";
import { ReloadOutlined, StopOutlined, EyeOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api/endpoints";

const { Title, Text } = Typography;

export default function SessionsPage() {
  const [, setOfferings] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [liveModal, setLiveModal] = useState<{ open: boolean; session: any; data: any }>({
    open: false,
    session: null,
    data: null,
  });

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/offerings");
      setOfferings(r.data);
      // Collect sessions for all offerings (admin view)
      const allSessions: any[] = [];
      for (const o of r.data) {
        try {
          const sr = await api.get(`/offerings/${o.id}/attendance/report`);
          // No direct "list sessions" endpoint — we use the offering report
          // which contains summary data per student. For a session list we'd
          // need a /sessions endpoint; for now we just show offerings.
          allSessions.push({ offering: o, report: sr.data });
        } catch {}
      }
      setSessions(allSessions);
    } catch (e: any) {
      message.error(e?.response?.data?.message_ar || "فشل التحميل");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const closeSession = async (sessionId: string) => {
    Modal.confirm({
      title: "إغلاق الجلسة؟",
      content: "سيتم تعليم جميع الطلاب غير المسجّلين كغائبين.",
      okText: "إغلاق",
      cancelText: "إلغاء",
      onOk: async () => {
        try {
          await api.post(`/sessions/${sessionId}/close`);
          message.success("تم إغلاق الجلسة");
          load();
        } catch (e: any) {
          message.error(e?.response?.data?.message_ar || "فشل الإغلاق");
        }
      },
    });
  };

  return (
    <Card>
      <Title level={4}>الحضور — الجلسات</Title>
      <Text type="secondary">
        عرض تدريس المواد وتقارير الحضور لكل مادة. اضغط "تقرير" لعرض تفاصيل الطلاب.
      </Text>

      <Space style={{ marginBottom: 16, marginTop: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          تحديث
        </Button>
      </Space>

      <Table
        rowKey={(r) => r.offering.id}
        loading={loading}
        dataSource={sessions}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: "المادة", dataIndex: ["offering", "course_id"], render: (id) => id?.slice(0, 8) + "…" },
          { title: "الشعبة", dataIndex: ["offering", "group_id"], render: (id) => id?.slice(0, 8) + "…" },
          { title: "التدريسي", dataIndex: ["offering", "instructor_id"], render: (id) => id ? id.slice(0, 8) + "…" : "—" },
          {
            title: "الطلاب",
            render: (_, row) => row.report?.students?.length ?? 0,
          },
          {
            title: "إجراءات",
            render: (_, row) => (
              <Space>
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => {
                    Modal.info({
                      title: "تقرير الحضور",
                      width: 800,
                      content: (
                        <Table
                          size="small"
                          rowKey={(r: any) => r.student_id}
                          pagination={{ pageSize: 10 }}
                          dataSource={row.report?.students ?? []}
                          columns={[
                            { title: "الطالب", dataIndex: "student_name" },
                            {
                              title: "الحضور",
                              render: (_, s: any) => {
                                const sm = s.summary;
                                if (!sm) return "—";
                                return (
                                  <Space>
                                    <Tag color="green">حاضر: {sm.present}</Tag>
                                    <Tag color="orange">متأخر: {sm.late}</Tag>
                                    <Tag color="red">غائب: {sm.absent}</Tag>
                                    <Tag color="blue">{(sm.attendance_percent * 100).toFixed(0)}%</Tag>
                                    {sm.is_warning && <Tag color="volcano">⚠️ تنبيه</Tag>}
                                  </Space>
                                );
                              },
                            },
                          ]}
                        />
                      ),
                    });
                  }}
                >
                  تقرير
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={liveModal.open}
        title="الحضور اللحظي للجلسة"
        onCancel={() => setLiveModal({ open: false, session: null, data: null })}
        footer={[
          <Button key="close" danger onClick={() => closeSession(liveModal.session?.id)}>
            <StopOutlined /> إغلاق الجلسة
          </Button>,
          <Button key="ok" onClick={() => setLiveModal({ open: false, session: null, data: null })}>
            إغلاق
          </Button>,
        ]}
        width={900}
      >
        {liveModal.data && (
          <>
            <Descriptions size="small" bordered column={3} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="الحاضرين">
                <Tag color="green">{liveModal.data.present_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="المتأخرين">
                <Tag color="orange">{liveModal.data.late_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="المسجّلون">
                <Tag color="blue">{liveModal.data.enrolled_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="الغائبون">
                <Tag color="red">{liveModal.data.absent_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="مُعلّم">
                <Tag color="volcano">{liveModal.data.flagged_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="الحالة">
                <Tag>{liveModal.data.status}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <Table
              size="small"
              rowKey={(r: any) => r.student_id}
              pagination={{ pageSize: 10 }}
              dataSource={liveModal.data.records ?? []}
              columns={[
                { title: "الطالب", dataIndex: "full_name_ar" },
                {
                  title: "الحالة",
                  dataIndex: "status",
                  render: (s: string) => {
                    const map: Record<string, string> = {
                      present: "green",
                      late: "orange",
                      absent: "red",
                      excused: "purple",
                    };
                    return <Tag color={map[s] ?? "default"}>{s}</Tag>;
                  },
                },
                { title: "الطريقة", dataIndex: "method" },
                {
                  title: "الوقت",
                  dataIndex: "scanned_at",
                  render: (s: string) => (s ? dayjs(s).format("HH:mm:ss") : "—"),
                },
                {
                  title: "مُعلّم؟",
                  dataIndex: "flagged",
                  render: (f: boolean, r: any) =>
                    f ? <Tag color="volcano">{r.flag_reason || "مشبوه"}</Tag> : "—",
                },
              ]}
            />
          </>
        )}
      </Modal>
    </Card>
  );
}
