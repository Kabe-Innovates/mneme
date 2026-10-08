import { UserCircle } from "lucide-react";

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
      <label className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
        <UserCircle className="h-3.5 w-3.5" />
        Your Role
      </label>
      <select
        value={role}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm font-medium text-slate-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-slate-400">
        Filters knowledge access by role
      </p>
    </div>
  );
}
