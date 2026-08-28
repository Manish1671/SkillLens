export function SectionHeader({
  eyebrow,
  title,
  description,
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
}) {
  const alignClass = align === "center" ? "text-center mx-auto max-w-2xl" : "max-w-2xl";

  return (
    <header className={`space-y-3 ${alignClass}`}>
      {eyebrow ? <p className="sl-eyebrow">{eyebrow}</p> : null}
      <h2 className="sl-section-title">{title}</h2>
      {description ? (
        <p className="text-base leading-relaxed text-muted">{description}</p>
      ) : null}
    </header>
  );
}
