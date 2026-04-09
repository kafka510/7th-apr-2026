export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  url?: string;
  tabId?: string;
  target?: '_blank' | '_self';
  rel?: string;
}

export interface MenuGroup {
  id: string;
  label: string;
  icon: string;
  items: MenuItem[];
}

export type MenuSection =
  | { type: 'single'; items: MenuItem[] }
  | { type: 'group'; group: MenuGroup }
  | { type: 'divider' }
  | { type: 'sectionTitle'; sectionTitle: string };

export interface DashboardMenu {
  sections: MenuSection[];
}

export interface UserInfo {
  username: string;
  full_name: string;
  role: string;
  is_superuser: boolean;
}

export interface DashboardData {
  menu: DashboardMenu;
  user: UserInfo;
  timestamp: number;
}

