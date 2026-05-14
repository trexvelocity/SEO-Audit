"""Render report.html to A4 PDF via WeasyPrint."""
from pathlib import Path
from weasyprint import HTML

here = Path(__file__).parent
html_path = here / "report.html"
pdf_path = here / "FSP-Australia-SEO-Audit-2026.pdf"
HTML(filename=str(html_path)).write_pdf(str(pdf_path))
print(f"PDF written: {pdf_path}  ({pdf_path.stat().st_size/1024:.1f} KB)")
