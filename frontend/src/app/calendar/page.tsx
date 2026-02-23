"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin, { type EventDropArg } from "@fullcalendar/interaction";
import type { EventInput, EventApi, DatesSetArg } from "@fullcalendar/core";
import { getCampaigns, getMoveOptions, updateCampaignStatus } from "@/lib/api";
import type { CampaignListItem, CampaignStatus } from "@/types";
import Link from "next/link";

const STATUS_COLORS: Record<CampaignStatus, string> = {
  submitted: "#6b7280",
  in_review: "#3b82f6",
  changes_needed: "#f59e0b",
  scheduled: "#8b5cf6",
  approved: "#22c55e",
  rejected: "#ef4444",
  sent: "#10b981",
};

function toEvents(campaigns: CampaignListItem[]): EventInput[] {
  return campaigns
    .filter((c) => c.send_at)
    .map((c) => ({
      id: String(c.id),
      title: c.title,
      start: c.send_at!.slice(0, 10),
      allDay: true,
      backgroundColor: STATUS_COLORS[c.status],
      borderColor: STATUS_COLORS[c.status],
      extendedProps: { status: c.status, department: c.department.name, color: STATUS_COLORS[c.status] },
    }));
}

export default function CalendarPage() {
  const calRef = useRef<FullCalendar>(null);
  const [events, setEvents] = useState<EventInput[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [validDates, setValidDates] = useState<Set<string>>(new Set());
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [currentRange, setCurrentRange] = useState<{ start: string; end: string } | null>(null);

  async function load() {
    try {
      const campaigns = await getCampaigns();
      setEvents(toEvents(campaigns));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Laden");
    }
  }

  useEffect(() => { load(); }, []);

  const handleDatesSet = useCallback((arg: DatesSetArg) => {
    const start = arg.startStr.slice(0, 10);
    const end = arg.endStr.slice(0, 10);
    setCurrentRange({ start, end });
  }, []);

  async function loadMoveOptions(campaignId: number, start: string, end: string) {
    try {
      const res = await getMoveOptions(campaignId, start, end);
      setValidDates(new Set(res.valid_dates));
    } catch {
      setValidDates(new Set());
    }
  }

  function handleEventDragStart(info: { event: EventApi }) {
    const id = parseInt(info.event.id);
    setDraggingId(id);
    if (currentRange) {
      loadMoveOptions(id, currentRange.start, currentRange.end);
    }
  }

  async function handleEventDrop(arg: EventDropArg) {
    const id = parseInt(arg.event.id);
    const newDate = arg.event.startStr.slice(0, 10);

    if (!validDates.has(newDate)) {
      arg.revert();
      setError("Dieser Termin verstößt gegen den Mindestabstand. Bitte wähle einen anderen Tag.");
      setDraggingId(null);
      setValidDates(new Set());
      return;
    }

    try {
      const sendAt = `${newDate}T09:00:00+02:00`;
      await updateCampaignStatus(id, { send_at: sendAt });
      setError(null);
      await load();
    } catch (e: unknown) {
      arg.revert();
      setError(e instanceof Error ? e.message : "Fehler beim Verschieben");
    }
    setDraggingId(null);
    setValidDates(new Set());
  }

  // Force FullCalendar to re-render day cells whenever validDates changes.
  // setTimeout defers the call out of React's render cycle to avoid the
  // flushSync-inside-lifecycle error in React 18.
  useEffect(() => {
    const id = setTimeout(() => calRef.current?.getApi().render(), 0);
    return () => clearTimeout(id);
  }, [validDates, draggingId]);

  // Colour calendar days by validity during drag
  function dayCellClassNames(arg: { date: Date }) {
    if (!draggingId || validDates.size === 0) return [];
    const d = arg.date.toISOString().slice(0, 10);
    return validDates.has(d) ? ["sh-valid-slot"] : ["sh-invalid-slot"];
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Kampagnen-Kalender</h1>
        <Link
          href="/requests/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + Neue Anfrage
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex justify-between">
          {error}
          <button onClick={() => setError(null)} className="font-bold ml-2">×</button>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-4 text-xs">
        {(Object.entries(STATUS_COLORS) as [CampaignStatus, string][]).map(([s, c]) => (
          <span key={s} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: c }} />
            {s}
          </span>
        ))}
      </div>

      <style>{`
        .sh-valid-slot { background-color: rgba(134, 239, 172, 0.35) !important; }
        .sh-invalid-slot { background-color: rgba(252, 165, 165, 0.25) !important; opacity: 0.6; }
      `}</style>

      <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-100">
        <FullCalendar
          ref={calRef}
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          locale="de"
          events={events}
          editable={true}
          eventDrop={handleEventDrop}
          eventDragStart={handleEventDragStart}
          datesSet={handleDatesSet}
          dayCellClassNames={dayCellClassNames}
          eventClick={(info) => {
            window.location.href = `/campaigns/${info.event.id}`;
          }}
          eventContent={(arg) => (
            <div
              className="px-1 py-0.5 overflow-hidden rounded w-full"
              style={{ backgroundColor: arg.event.extendedProps.color }}
            >
              <div className="font-medium text-white truncate text-xs leading-tight">
                {arg.event.title}
              </div>
              <div className="text-white/80 text-xs">{arg.event.extendedProps.department}</div>
            </div>
          )}
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,dayGridWeek",
          }}
          height="auto"
        />
      </div>

      <p className="mt-2 text-xs text-gray-400">
        Drag &amp; Drop zum Verschieben von Kampagnen. Grüne Tage sind regelkonform.
      </p>
    </div>
  );
}
