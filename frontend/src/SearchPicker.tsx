import { useState } from "react";

/**
 * 通用可搜索下拉选择器：同时支持下拉选择与手动输入关键词过滤，
 * 避免“下拉框 + 搜索框”同时出现造成的操作冲突。
 */
export function SearchPicker<T extends { id: number }>({
  items,
  value,
  onChange,
  placeholder,
  display,
  filter,
  includeAll,
  allLabel,
}: {
  items: T[];
  value: number;
  onChange: (id: number) => void;
  placeholder?: string;
  display: (item: T) => string;
  filter?: (item: T, query: string) => boolean;
  includeAll?: boolean;
  allLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = items.find((it) => it.id === value);
  const q = query.trim().toLowerCase();
  const matches = (it: T) =>
    !q || (filter ? filter(it, q) : display(it).toLowerCase().includes(q));
  const filtered = q ? items.filter(matches) : items;

  return (
    <div
      className="relative"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setOpen(false);
      }}
    >
      <input
        value={
          open
            ? query
            : query || (selected ? display(selected) : includeAll && !value ? allLabel || "全部" : "")
        }
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        placeholder={placeholder || "输入关键词搜索..."}
        className="field"
      />
      {open && (
        <div className="absolute z-30 w-full picker-dropdown max-h-48 overflow-auto mt-1">
          {includeAll && (
            <button
              type="button"
              onClick={() => {
                onChange(0);
                setOpen(false);
                setQuery("");
              }}
              className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                value === 0 ? "text-indigo-300 bg-white/10" : "text-white/90 hover:bg-white/10"
              }`}
            >
              {allLabel || "全部"}
            </button>
          )}
          {filtered.map((it) => (
            <button
              key={it.id}
              type="button"
              onClick={() => {
                onChange(it.id);
                setOpen(false);
                setQuery("");
              }}
              className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                it.id === value ? "text-indigo-300 bg-white/10" : "text-white/90 hover:bg-white/10"
              }`}
            >
              {display(it)}
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="px-3 py-2 text-xs text-white/50">无匹配项</div>
          )}
        </div>
      )}
    </div>
  );
}
