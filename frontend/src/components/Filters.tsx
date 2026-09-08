export interface FiltersValue {
  sentiment: string;
  startDate: string;
  endDate: string;
}

interface FiltersProps {
  value: FiltersValue;
  onChange: (value: FiltersValue) => void;
}

const inputClasses =
  "rounded border border-black/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-transparent";

export function Filters({ value, onChange }: FiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-black/10 p-4 dark:border-white/10">
      <div className="flex flex-col gap-1">
        <label htmlFor="filter-sentiment" className="text-xs font-medium text-black/60 dark:text-white/60">
          Sentiment
        </label>
        <select
          id="filter-sentiment"
          value={value.sentiment}
          onChange={(event) => onChange({ ...value, sentiment: event.target.value })}
          className={inputClasses}
        >
          <option value="">All</option>
          <option value="POSITIVE">Positive</option>
          <option value="NEGATIVE">Negative</option>
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="filter-start" className="text-xs font-medium text-black/60 dark:text-white/60">
          From
        </label>
        <input
          id="filter-start"
          type="date"
          value={value.startDate}
          onChange={(event) => onChange({ ...value, startDate: event.target.value })}
          className={inputClasses}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="filter-end" className="text-xs font-medium text-black/60 dark:text-white/60">
          To
        </label>
        <input
          id="filter-end"
          type="date"
          value={value.endDate}
          onChange={(event) => onChange({ ...value, endDate: event.target.value })}
          className={inputClasses}
        />
      </div>

      {(value.sentiment || value.startDate || value.endDate) && (
        <button
          type="button"
          onClick={() => onChange({ sentiment: "", startDate: "", endDate: "" })}
          className="rounded border border-black/15 px-3 py-1.5 text-sm dark:border-white/15"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
