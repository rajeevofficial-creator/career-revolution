import os
import asyncio
from typing import Dict, Any, Optional
from jinja2 import Template
import logging
from datetime import datetime
import markdown

logger = logging.getLogger(__name__)

class PDFService:
    """Service for rendering HTML to PDF using Playwright."""
    
    def __init__(self, templates_dir: str = "app/templates"):
        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)

    async def render_html(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with context."""
        template_path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template {template_name} not found in {self.templates_dir}")
            
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
            
        template = Template(template_content)
        return template.render(**context)

    def _generate_pdf_sync(self, html_content: str, output_path: str) -> bool:
        """Synchronous version of PDF generation to be run in a separate thread."""
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_content, wait_until="load", timeout=60000)
                page.pdf(
                    path=output_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
                )
                browser.close()
                return True
        except Exception as e:
            logger.error(f"Sync PDF Error: {e}")
            import traceback
            with open("c:\\Users\\rajeev\\career_revolution\\debug_pdf_error.log", "a") as f:
                f.write(f"\n--- Sync PDF Error at {datetime.now()} ---\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
            return False

    async def generate_pdf(self, html_content: str, output_path: str) -> bool:
        """Generate a PDF from HTML content by offloading to a sync thread (Windows fix)."""
        return await asyncio.to_thread(self._generate_pdf_sync, html_content, output_path)

    async def create_cv_pdf(self, context: Dict[str, Any], output_path: str) -> bool:
        """Helper to create a CV PDF from the modern template."""
        html = await self.render_html("cv_template_modern.html", context)
        return await self.generate_pdf(html, output_path)

    async def create_cl_pdf(self, context: Dict[str, Any], output_path: str) -> bool:
        """Helper to create a Cover Letter PDF from the modern template."""
        # Convert content from markdown to HTML for proper PDF rendering
        raw_content = context.get('content', '')
        if raw_content:
            context['content'] = markdown.markdown(raw_content)

        # Add basic formatting like today's date if not present
        if 'date' not in context:
            from datetime import datetime
            context['date'] = datetime.now().strftime("%B %d, %Y")
            
        html = await self.render_html("cl_template_modern.html", context)
        return await self.generate_pdf(html, output_path)
