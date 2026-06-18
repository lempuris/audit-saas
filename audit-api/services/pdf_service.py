"""PDF rendering (ISA reports): HTML via Jinja2 templates, then WeasyPrint
HTML -> PDF. The two steps are separate so the HTML can be unit-tested without
WeasyPrint's native libraries (Pango/Fontconfig), which are installed in the
container image. WeasyPrint is imported lazily for the same reason.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.reports_models import ReportRecord

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_report_html(report: ReportRecord) -> str:
    """Render a report to standalone HTML (no native dependencies)."""
    template = _env.get_template("report.html")
    return template.render(report=report, is_draft=report.status != "final")


def html_to_pdf(html: str) -> bytes:
    # Imported here so the module (and the unit tests) load without WeasyPrint's
    # native libraries present.
    from weasyprint import HTML

    return HTML(string=html).write_pdf()


def render_report_pdf(report: ReportRecord) -> bytes:
    return html_to_pdf(render_report_html(report))


def pdf_filename(report: ReportRecord) -> str:
    slug = report.report_type
    return f"{slug}-{report.id}.pdf"
