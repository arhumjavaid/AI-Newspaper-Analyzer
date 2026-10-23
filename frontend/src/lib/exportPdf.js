import html2canvas from "html2canvas-pro";
import { jsPDF } from "jspdf";

// A4 portrait, millimetres.
const PAGE_W = 210;
const PAGE_H = 297;
const MARGIN = 12;
const HEADER_H = 17;
const FOOTER_H = 11;
const BLOCK_GAP = 5;

const CONTENT_W = PAGE_W - MARGIN * 2;
const CONTENT_TOP = MARGIN + HEADER_H;
const CONTENT_BOTTOM = PAGE_H - FOOTER_H;
const USABLE_H = CONTENT_BOTTOM - CONTENT_TOP;

// Brand colours (hex approximations of the oklch design tokens).
const INK = "#1f2430";
const MUTED = "#6b7280";
const LINE = "#e4e6eb";
const BRAND = "#f5d000";

// Load /logo.png as a data URL once, tolerating failure (header still renders).
async function loadLogo() {
  try {
    const res = await fetch("/logo.png");
    const blob = await res.blob();
    return await new Promise((resolve) => {
      const r = new FileReader();
      r.onloadend = () => resolve(r.result);
      r.onerror = () => resolve(null);
      r.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

function drawHeader(pdf, logo, { title, subtitle }) {
  if (logo) {
    pdf.setFillColor(BRAND);
    pdf.roundedRect(MARGIN, MARGIN, 9, 9, 2, 2, "F");
    try {
      pdf.addImage(logo, "PNG", MARGIN, MARGIN, 9, 9);
    } catch {
      /* keep the brand square if the logo can't be embedded */
    }
  }
  const x = MARGIN + (logo ? 12 : 0);
  pdf.setTextColor(INK);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(12);
  pdf.text(title, x, MARGIN + 4.2);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(MUTED);
  pdf.text(subtitle, x, MARGIN + 8.6);

  pdf.setDrawColor(LINE);
  pdf.setLineWidth(0.3);
  pdf.line(MARGIN, CONTENT_TOP - 4, PAGE_W - MARGIN, CONTENT_TOP - 4);
}

function drawHeaderMeta(pdf, { publication, date }) {
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(MUTED);
  if (publication) pdf.text(publication, PAGE_W - MARGIN, MARGIN + 4.2, { align: "right" });
  if (date) pdf.text(date, PAGE_W - MARGIN, MARGIN + 8.6, { align: "right" });
}

function drawFooter(pdf, page, total) {
  const y = PAGE_H - FOOTER_H + 4;
  pdf.setDrawColor(LINE);
  pdf.setLineWidth(0.3);
  pdf.line(MARGIN, y - 3, PAGE_W - MARGIN, y - 3);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(MUTED);
  pdf.text(`Page ${page} of ${total}`, PAGE_W - MARGIN, y + 1, { align: "right" });
}

// Crop a horizontal band out of a source canvas and return it as a PNG data URL.
function sliceCanvas(source, startPx, heightPx) {
  const c = document.createElement("canvas");
  c.width = source.width;
  c.height = heightPx;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.drawImage(source, 0, startPx, source.width, heightPx, 0, 0, source.width, heightPx);
  return c.toDataURL("image/png");
}

/**
 * Render a report container to a branded, paginated PDF.
 * Each direct child of `container` is treated as an atomic block and is never
 * split across a page boundary — unless it is taller than a full page, in which
 * case it is sliced. Browser print chrome (URL, title, page numbers) is absent
 * because we build the document ourselves.
 */
export async function exportReportPdf(container, meta = {}) {
  const {
    title = "Media Intelligence Report",
    subtitle = "",
    publication = "",
    date = "",
    filename = "media-intelligence-report.pdf",
  } = meta;

  const root = document.documentElement;
  const wasDark = root.classList.contains("dark");
  const prevWidth = container.style.width;

  // Light mode + a fixed desktop width give a clean, consistent two-column deck.
  if (wasDark) root.classList.remove("dark");
  root.setAttribute("data-pdf-exporting", "");
  const style = document.createElement("style");
  style.textContent = "[data-pdf-exporting] .print\\:hidden{display:none !important}";
  document.head.appendChild(style);
  container.style.width = "1180px";

  // Let layout + charts settle after the style changes.
  await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 180)));

  try {
    const logo = await loadLogo();
    const pdf = new jsPDF("p", "mm", "a4");
    let firstPage = true;
    let y = CONTENT_TOP;

    const newPage = () => {
      if (!firstPage) pdf.addPage();
      firstPage = false;
      y = CONTENT_TOP;
    };
    newPage();

    const blocks = Array.from(container.children).filter(
      (el) => el.offsetHeight > 0 && !el.classList.contains("print:hidden")
    );

    for (const el of blocks) {
      const canvas = await html2canvas(el, {
        scale: 2,
        backgroundColor: "#ffffff",
        useCORS: true,
        logging: false,
        windowWidth: 1180,
      });
      const mmPerPx = CONTENT_W / canvas.width;
      const fullH = canvas.height * mmPerPx;

      if (fullH <= USABLE_H) {
        // Whole block on one page — never split.
        if (y + fullH > CONTENT_BOTTOM) newPage();
        pdf.addImage(canvas.toDataURL("image/png"), "PNG", MARGIN, y, CONTENT_W, fullH);
        y += fullH + BLOCK_GAP;
      } else {
        // Block taller than a page — slice it across pages.
        if (y > CONTENT_TOP + 1) newPage();
        let remaining = canvas.height;
        let srcY = 0;
        while (remaining > 0) {
          const availPx = Math.floor((CONTENT_BOTTOM - y) / mmPerPx);
          const slicePx = Math.min(availPx, remaining);
          const dataUrl = sliceCanvas(canvas, srcY, slicePx);
          pdf.addImage(dataUrl, "PNG", MARGIN, y, CONTENT_W, slicePx * mmPerPx);
          srcY += slicePx;
          remaining -= slicePx;
          y += slicePx * mmPerPx;
          if (remaining > 0) newPage();
        }
        y += BLOCK_GAP;
      }
    }

    const total = pdf.getNumberOfPages();
    for (let i = 1; i <= total; i++) {
      pdf.setPage(i);
      drawHeader(pdf, logo, { title, subtitle });
      drawHeaderMeta(pdf, { publication, date });
      drawFooter(pdf, i, total);
    }

    pdf.save(filename);
  } finally {
    container.style.width = prevWidth;
    style.remove();
    root.removeAttribute("data-pdf-exporting");
    if (wasDark) root.classList.add("dark");
  }
}
