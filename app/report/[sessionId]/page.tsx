import { Dashboard } from "@/app/components/dashboard";

type ReportPageProps = { params: Promise<{ sessionId: string }> };

export default async function ReportPage({ params }: ReportPageProps) {
  const { sessionId } = await params;
  const api = process.env.NEXT_PUBLIC_CHANGESTORY_API ?? "http://127.0.0.1:8000";
  const response = await fetch(`${api}/api/v1/reports/${sessionId}`, { cache: "no-store" });
  const initialReport = response.ok ? await response.json() : undefined;
  return <Dashboard initialReport={initialReport} />;
}
