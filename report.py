from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import datetime

def generate_daily_report(filename, mood, outlooks, news):
    """
    Create a one-page PDF market brief:
    – Market mood
    – Outlooks for portfolio tickers
    – Credible headlines
    """
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 750, "Daily Market Brief — Agentic AI")
    c.setFont("Helvetica", 10)
    c.drawString(40, 735, f"Date: {datetime.date.today()}")

    c.drawString(40, 710, f"Market Mood: {mood}/100")
    y = 680
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Ticker Outlooks:")
    y -= 20
    c.setFont("Helvetica", 10)
    for t, msg in outlooks.items():
        c.drawString(50, y, f"{t}: {msg}")
        y -= 15

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Top Headlines:")
    y -= 20
    c.setFont("Helvetica", 10)
    for n in news[:5]:
        c.drawString(50, y, f"• {n['title']} ({n['source']})")
        y -= 15

    c.save()
    return filename
