import type { Metadata } from "next";
import Sidebar from "./Sidebar";

export const metadata: Metadata = {
  title: "Svitch Dashboard",
  description: "AI compliance control plane for regulated enterprises",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#F4F4F2" }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0 }}>{children}</main>
    </div>
  );
}
