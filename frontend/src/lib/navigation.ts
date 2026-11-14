import {
  Bell,
  Bot,
  ClipboardCheck,
  Database,
  FileBarChart,
  FlaskConical,
  Gem,
  LayoutDashboard,
  type LucideIcon,
  Search,
  Settings,
  ShieldCheck,
  User,
  Users,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "AI Assistant", href: "/assistant", icon: Bot },
  { label: "Find Indian Standards", href: "/standards", icon: Search },
  { label: "Certification Guide", href: "/certification", icon: ShieldCheck },
  { label: "Laboratory Finder", href: "/laboratories", icon: FlaskConical },
  { label: "Hallmarking", href: "/hallmarking", icon: Gem },
  { label: "Consumer Help", href: "/consumer-help", icon: Users },
  { label: "Compliance Workspace", href: "/compliance", icon: ClipboardCheck },
  { label: "My Reports", href: "/reports", icon: FileBarChart },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Profile", href: "/profile", icon: User },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Knowledge Base", href: "/admin/documents", icon: Database, adminOnly: true },
];

export const PENDING_QUERY_KEY = "bis_saathi_pending_query";

export const POPULAR_QUERIES = [
  "Which Indian Standard applies to domestic pressure cookers?",
  "How can a foreign manufacturer obtain BIS certification?",
  "How do I verify the HUID on hallmarked gold jewellery?",
  "What documents are needed for a BIS product licence?",
  "How can I check whether an ISI mark is genuine?",
  "What tests are required for packaged drinking water?",
];
