import type { CampaignStatus } from "@/types";

const LABELS: Record<CampaignStatus, string> = {
  submitted: "Eingereicht",
  in_review: "In Prüfung",
  changes_needed: "Änderungen nötig",
  scheduled: "Geplant",
  approved: "Genehmigt",
  rejected: "Abgelehnt",
  sent: "Versendet",
};

export default function StatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-${status}`}>
      {LABELS[status]}
    </span>
  );
}
