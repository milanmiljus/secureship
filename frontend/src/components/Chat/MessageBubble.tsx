import React from "react";
import type { ShipmentOut } from "../../api/secureship";

const STATUS_STYLES: Record<
  string,
  { label: string; color: string; dot: string }
> = {
  exception: {
    label: "Exception",
    color: "bg-red-100 text-red-700 border-red-200",
    dot: "bg-red-500",
  },
  out_for_delivery: {
    label: "Out for Delivery",
    color: "bg-amber-100 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
  },
  in_transit: {
    label: "In Transit",
    color: "bg-blue-100 text-blue-700 border-blue-200",
    dot: "bg-blue-500",
  },
  delivered: {
    label: "Delivered",
    color: "bg-green-100 text-green-700 border-green-200",
    dot: "bg-green-500",
  },
  label_created: {
    label: "Label Created",
    color: "bg-gray-100 text-gray-600 border-gray-200",
    dot: "bg-gray-400",
  },
};

const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

// estimated_delivery is date-only (YYYY-MM-DD); force UTC so it does not shift a day locally.
function formatDate(value: string | null | undefined): string {
  if (!value) return "\u2014";
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00Z` : value;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? value : DATE_FORMAT.format(date);
}

function ShipmentCard({ data }: { data: ShipmentOut }) {
  const style = STATUS_STYLES[data.status] ?? STATUS_STYLES.label_created;

  return (
    <div className="mt-1 space-y-2">
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm text-sm">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
              Tracking
            </p>
            <p className="font-mono font-semibold text-gray-800">
              {data.tracking_number}
            </p>
          </div>
          <span
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${style.color}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
            {style.label}
          </span>
        </div>

        {/* Route */}
        <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-3">
          <div className="flex-1">
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
              From
            </p>
            <p className="text-gray-700">{data.origin}</p>
          </div>
          <svg
            className="w-4 h-4 text-gray-300 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 8l4 4m0 0l-4 4m4-4H3"
            />
          </svg>
          <div className="flex-1 text-right">
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
              To
            </p>
            <p className="text-gray-700">{data.destination}</p>
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 gap-px bg-gray-100">
          {[
            { label: "Carrier", value: data.carrier },
            {
              label: "Est. Delivery",
              value: formatDate(data.estimated_delivery),
            },
            { label: "Last Update", value: formatDate(data.last_update) },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white px-4 py-2.5">
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
                {label}
              </p>
              <p className="text-gray-700 mt-0.5">{value}</p>
            </div>
          ))}
        </div>

        {/* Packages */}
        {!!data.packages?.length && (
          <div className="border-t border-gray-100">
            <p className="px-4 pt-3 pb-1 text-xs text-gray-400 uppercase tracking-wide font-medium">
              Packages ({data.packages.length})
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-1.5 text-left text-xs text-gray-400 font-medium">
                    Description
                  </th>
                  <th className="px-4 py-1.5 text-right text-xs text-gray-400 font-medium">
                    Weight
                  </th>
                  <th className="px-4 py-1.5 text-right text-xs text-gray-400 font-medium">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.packages.map((pkg, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2 text-gray-700">
                      {pkg.description}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500">
                      {pkg.weight_kg} kg
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500">
                      ${pkg.declared_value.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="h-3" />
          </div>
        )}
      </div>
    </div>
  );
}

function RobotAvatar() {
  return (
    <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 self-end">
      <svg
        className="w-5 h-5 text-gray-500"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M9 11a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2m6 0a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2z" />
      </svg>
    </div>
  );
}

function HumanAvatar() {
  return (
    <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 self-end">
      <svg
        className="w-5 h-5 text-blue-500"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
      </svg>
    </div>
  );
}

function renderMarkdown(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

interface Props {
  role: "user" | "assistant";
  content: string;
  avatar?: "robot" | "human" | "banner";
  shipments?: ShipmentOut[];
}

export default function MessageBubble({
  role,
  content,
  avatar,
  shipments,
}: Props) {
  const isUser = role === "user";

  if (avatar === "banner") {
    let lines: string[] = [];
    try {
      lines = JSON.parse(content);
    } catch {
      lines = [content];
    }
    return (
      <div className="mx-1 p-3 bg-blue-50 border border-blue-200 rounded-xl text-sm space-y-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
            Support Chat
          </span>
        </div>
        {lines.map((line, i) => (
          <p key={i} className="text-gray-700">
            {line}
          </p>
        ))}
      </div>
    );
  }

  if (!isUser) {
    const Icon = avatar === "human" ? <HumanAvatar /> : <RobotAvatar />;
    if (shipments?.length) {
      return (
        <div className="flex justify-start items-end gap-2">
          {Icon}
          <div className="max-w-[85%] space-y-2">
            {content && (
              <div className="rounded-2xl px-4 py-2.5 text-sm leading-relaxed bg-gray-100 text-gray-800 rounded-bl-sm">
                {renderMarkdown(content)}
              </div>
            )}
            {shipments.map((s) => (
              <ShipmentCard key={s.id} data={s} />
            ))}
          </div>
        </div>
      );
    }
    return (
      <div className="flex justify-start items-end gap-2">
        {Icon}
        <div className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed bg-gray-100 text-gray-800 rounded-bl-sm">
          {renderMarkdown(content)}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed bg-blue-600 text-white rounded-br-sm">
        {content}
      </div>
    </div>
  );
}
