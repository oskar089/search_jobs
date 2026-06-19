import { useAuth } from "../context/AuthContext";
import { Card } from "../components/ui/Card";
import { FileText, Globe, TrendingUp, CheckCircle } from "lucide-react";

const stats = [
  { label: "Applications", value: "0", icon: FileText, color: "text-blue-500" },
  { label: "Active Portals", value: "4", icon: Globe, color: "text-green-500" },
  { label: "Match Average", value: "--", icon: TrendingUp, color: "text-purple-500" },
  { label: "Success Rate", value: "--", icon: CheckCircle, color: "text-amber-500" },
];

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">
        Welcome, {user?.name || user?.email}
      </h1>
      <p className="text-slate-400 text-sm mb-6">Here's an overview of your job search activity.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">{stat.label}</p>
                  <p className="text-2xl font-bold text-white mt-1">{stat.value}</p>
                </div>
                <Icon className={`w-8 h-8 ${stat.color} opacity-80`} />
              </div>
            </Card>
          );
        })}
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-white mb-4">Recent Applications</h2>
        <div className="flex flex-col items-center justify-center py-16 text-slate-500">
          <FileText className="w-12 h-12 mb-3 opacity-40" />
          <p className="text-sm font-medium">No applications yet</p>
          <p className="text-xs mt-1 text-slate-600">
            Configure your portals in Portals settings to start scraping jobs
          </p>
        </div>
      </Card>
    </div>
  );
}
