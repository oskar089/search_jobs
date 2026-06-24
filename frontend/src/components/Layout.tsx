import { useEffect } from "react";
import { Outlet, useNavigate, useLocation, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { cn } from "../lib/utils";
import { listNotifications } from "../lib/notifications";
import { LayoutDashboard, User, Globe, Briefcase, Bell, LogOut } from "lucide-react";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, disabled: false },
  { label: "Profile", path: "/profile", icon: User, disabled: false },
  { label: "Portals", path: "/portals", icon: Globe, disabled: false },
  { label: "Applications", path: "/applications", icon: Briefcase, disabled: false },
  { label: "Notifications", path: "/notifications", icon: Bell, disabled: false },
];

export function Layout() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Unread notification count
  const { data: notifs } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    enabled: isAuthenticated,
    refetchInterval: 30_000,
  });
  const unreadCount = notifs?.filter((n) => !n.is_read).length ?? 0;

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/login", { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900">
        <div className="text-slate-400 text-sm">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-slate-900">
      <aside className="hidden md:flex w-64 flex-col bg-slate-800 border-r border-slate-700">
        <div className="flex h-16 items-center px-6 border-b border-slate-700">
          <h1 className="text-lg font-bold text-white">Search Jobs</h1>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            if (item.disabled) {
              return (
                <div
                  key={item.label}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 cursor-not-allowed"
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </div>
              );
            }
            return (
              <Link
                key={item.label}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  location.pathname === item.path
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-700",
                )}
              >
                <Icon className="w-5 h-5" />
                {item.label}
                {item.label === "Notifications" && unreadCount > 0 && (
                  <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-blue-600 px-1.5 text-xs font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-slate-700">
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Logout
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-slate-700 bg-slate-800 px-6">
          <div className="flex items-center gap-3 md:hidden">
            <h1 className="text-lg font-bold text-white">Search Jobs</h1>
          </div>
          <h2 className="text-sm text-slate-300 md:text-base">
            Welcome, <span className="font-semibold text-white">{user?.name || user?.email}</span>
          </h2>
          <button
            onClick={logout}
            className="md:hidden text-sm text-slate-400 hover:text-white"
          >
            Logout
          </button>
        </header>

        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
