// Shared chart palette + Recharts styling. Values reference the CSS tokens in
// index.css (via var(...)), so charts adapt automatically to light/dark.
// SVG attributes and inline styles both resolve CSS custom properties.
export const SENTIMENT = {
  positive: "var(--positive)",
  negative: "var(--negative)",
  neutral: "var(--neutral)",
  mixed: "var(--mixed)",
};

export const CHART = {
  primary: "var(--primary)",
  primaryMuted: "var(--chart-primary-muted)",
  grid: "var(--chart-grid)",
  axis: "var(--chart-axis)",
  ink: "var(--foreground)",
};

export const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  color: "var(--foreground)",
  boxShadow: "var(--shadow-md)",
  fontSize: 13,
  padding: "8px 12px",
};

export const tooltipLabelStyle = {
  color: "var(--muted-foreground)",
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginBottom: 2,
};

export const axisTick = { fill: "var(--chart-axis)", fontSize: 12 };
