"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, ListTodo, ChevronLeft, ChevronRight, Home } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/admin/memory", label: "Vector Memory", icon: Database },
  { href: "/admin/tasks", label: "Task History", icon: ListTodo },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "fixed right-0 top-0 h-screen bg-slate-900/95 border-l border-slate-800 transition-all duration-300 z-40 flex flex-col",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex flex-col h-full p-4">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center p-2 mb-4 rounded-lg hover:bg-slate-800 text-slate-400 transition-colors"
        >
          {collapsed ? (
            <ChevronLeft className="h-5 w-5" />
          ) : (
            <ChevronRight className="h-5 w-5" />
          )}
        </button>

        <nav className="space-y-2 flex-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg transition-colors",
                  isActive
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                )}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!collapsed && (
                  <span className="text-sm font-medium">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        <Link
          href="/"
          className="flex items-center gap-3 p-3 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <Home className="h-5 w-5 flex-shrink-0" />
          {!collapsed && <span className="text-sm font-medium">Back to App</span>}
        </Link>
      </div>
    </aside>
  );
}
