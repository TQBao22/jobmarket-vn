export default function Chips({ items, prefix, label }: { items: string[]; prefix?: string; label?: string }) {
  return (
    <ul className="chips" aria-label={label}>
      {items.map((s) => <li key={s}>{prefix}{s}</li>)}
    </ul>
  );
}
