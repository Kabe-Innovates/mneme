import { UserCircle, ChevronDown } from "lucide-react";

const ROLES = [
  "Front Office",
  "Admission Desk",
  "Discharge Operations",
  "Billing & Cash Operations",
  "Insurance & TPA",
  "Medical Records",
  "Case Management",
  "Quality & Accreditation",
  "Operations Management",
  "IT & HIS Support",
  "Facility & Maintenance",
  "Biomedical Engineering",
  "Pharmacy",
  "Laboratory",
  "Radiology Operations",
];

interface Props {
  role: string;
  onChange: (role: string) => void;
}

export function RoleSelector({ role, onChange }: Props) {
  return (
    <div className="px-3 py-2">
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-dark-muted">
        <UserCircle className="h-3.5 w-3.5" />
        Your Role
      </label>
      <div className="relative">
        <select
          value={role}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none rounded-lg border border-dark-border bg-dark-surface py-2 pl-2.5 pr-8 text-sm font-medium text-dark-text focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-dark-muted" />
      </div>
      <p className="mt-1 text-xs text-dark-muted">Filters knowledge access by role</p>
    </div>
  );
}
