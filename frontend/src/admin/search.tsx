interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder,
}: SearchInputProps) {
  return (
    <div className="relative">
      <input
        type="search"
        aria-label={placeholder}
        placeholder={placeholder}
        className="border rounded pl-7 pr-2 py-1 text-xs w-64"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <svg
        className="w-3.5 h-3.5 text-gray-400 absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"
        />
      </svg>
    </div>
  );
}

/** Every whitespace-separated term must appear in at least one field, so "robbins GA" narrows. */
export function matches(
  query: string,
  ...fields: (string | null | undefined)[]
): boolean {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return true;
  const haystack = fields.map((f) => (f ?? "").toLowerCase()).join(" ");
  return terms.every((term) => haystack.includes(term));
}

export function countLabel(noun: string, shown: number, total: number): string {
  return shown === total
    ? `${noun} (${total})`
    : `${noun} (${shown} of ${total})`;
}
