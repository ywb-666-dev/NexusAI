import type { ReactNode } from "react";
export default function PageHeading({
  title,
  subtitle,
  label,
  extra,
}: {
  title: string;
  subtitle: string;
  label: string;
  extra?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{label}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {extra}
    </div>
  );
}
