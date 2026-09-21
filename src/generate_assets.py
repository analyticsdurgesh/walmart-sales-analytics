# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# Path makes folders and writes files.
from pathlib import Path


# A hand-drawn mock-up of the dashboard, written as SVG. SVG is a text format for pictures:
# every tag is one shape. <rect> is a rectangle, <text> is a label, <polyline> is a bent line.
# Reading it top to bottom: a grey background, a green title bar, four white cards with a
# label and a number each, a "Monthly Sales Trend" box with a green line, and a
# "Store Ranking" box with three coloured bars.
# The numbers in the cards are typed in by hand. They are not calculated from the CSV.
DASHBOARD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
<rect width="1200" height="720" fill="#f7f9fb"/>
<rect x="40" y="40" width="1120" height="84" rx="8" fill="#1f5e46"/>
<text x="72" y="92" font-family="Arial" font-size="34" fill="white">Walmart Sales Analytics Dashboard</text>
<rect x="40" y="152" width="250" height="120" rx="8" fill="white" stroke="#d8dee4"/>
<rect x="320" y="152" width="250" height="120" rx="8" fill="white" stroke="#d8dee4"/>
<rect x="600" y="152" width="250" height="120" rx="8" fill="white" stroke="#d8dee4"/>
<rect x="880" y="152" width="280" height="120" rx="8" fill="white" stroke="#d8dee4"/>
<text x="68" y="195" font-family="Arial" font-size="18" fill="#57606a">Total sales</text>
<text x="68" y="238" font-family="Arial" font-size="34" fill="#1f2328">$85.2M</text>
<text x="348" y="195" font-family="Arial" font-size="18" fill="#57606a">Average week</text>
<text x="348" y="238" font-family="Arial" font-size="34" fill="#1f2328">$1.05M</text>
<text x="628" y="195" font-family="Arial" font-size="18" fill="#57606a">Stores</text>
<text x="628" y="238" font-family="Arial" font-size="34" fill="#1f2328">45</text>
<text x="908" y="195" font-family="Arial" font-size="18" fill="#57606a">Holiday uplift</text>
<text x="908" y="238" font-family="Arial" font-size="34" fill="#1f2328">+7.8%</text>
<rect x="40" y="310" width="720" height="350" rx="8" fill="white" stroke="#d8dee4"/>
<text x="72" y="350" font-family="Arial" font-size="22" fill="#1f2328">Monthly Sales Trend</text>
<polyline points="90,590 180,540 270,560 360,470 450,500 540,410 630,430 720,350" fill="none" stroke="#247a5d" stroke-width="5"/>
<rect x="800" y="310" width="360" height="350" rx="8" fill="white" stroke="#d8dee4"/>
<text x="832" y="350" font-family="Arial" font-size="22" fill="#1f2328">Store Ranking</text>
<rect x="850" y="390" width="250" height="34" fill="#2f80ed"/>
<rect x="850" y="450" width="210" height="34" fill="#27ae60"/>
<rect x="850" y="510" width="170" height="34" fill="#f2c94c"/>
</svg>"""

# A second SVG: five labelled boxes joined by arrows.
# CSV / Dataset -> ETL -> SQL Warehouse on the top row, Analytics and Streamlit App below.
# <g> groups shapes so they share a font or a colour. <marker> defines the arrow head,
# and each <line> is one arrow.
ARCHITECTURE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
<rect width="1200" height="720" fill="#f7f9fb"/>
<text x="60" y="78" font-family="Arial" font-size="36" fill="#1f2328">Project Architecture</text>
<g font-family="Arial" font-size="22" fill="#1f2328">
<rect x="70" y="150" width="230" height="110" rx="8" fill="white" stroke="#d8dee4"/><text x="115" y="213">CSV / Dataset</text>
<rect x="380" y="150" width="230" height="110" rx="8" fill="white" stroke="#d8dee4"/><text x="450" y="213">ETL</text>
<rect x="690" y="150" width="230" height="110" rx="8" fill="white" stroke="#d8dee4"/><text x="735" y="213">SQL Warehouse</text>
<rect x="380" y="380" width="230" height="110" rx="8" fill="white" stroke="#d8dee4"/><text x="430" y="443">Analytics</text>
<rect x="690" y="380" width="230" height="110" rx="8" fill="white" stroke="#d8dee4"/><text x="725" y="443">Streamlit App</text>
</g>
<g stroke="#1f5e46" stroke-width="5" marker-end="url(#arrow)">
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1f5e46"/></marker></defs>
<line x1="300" y1="205" x2="380" y2="205"/><line x1="610" y1="205" x2="690" y2="205"/>
<line x1="805" y1="260" x2="805" y2="380"/><line x1="690" y1="435" x2="610" y2="435"/>
<line x1="610" y1="435" x2="690" y2="435"/>
</g>
</svg>"""


# Saves the two SVG pictures into docs/.
def write_svg_assets() -> None:
    # The docs folder, relative to where the command is run.
    docs = Path("docs")
    # Make the folder. No error if it is already there.
    docs.mkdir(exist_ok=True)
    # "docs / name" joins folder and file name. write_text saves the string as a file.
    (docs / "dashboard_overview.svg").write_text(DASHBOARD_SVG, encoding="utf-8")
    # Same for the architecture picture.
    (docs / "project_architecture.svg").write_text(ARCHITECTURE_SVG, encoding="utf-8")


# Saves two PNG pictures into docs/screenshots/.
# They are placeholder charts with made-up points, not screenshots of the running app.
def write_png_assets() -> None:
    # Imported here and not at the top, so the SVG step still works on a machine without plotly.
    import plotly.graph_objects as go

    # Folder for the PNG files.
    screenshots = Path("docs/screenshots")
    # parents=True makes docs/ too if needed.
    screenshots.mkdir(parents=True, exist_ok=True)
    # Start an empty chart.
    fig = go.Figure()
    # Draw four made-up points joined by a line. The name shows in the legend.
    fig.add_scatter(x=[1, 2, 3, 4], y=[12, 15, 13, 18], mode="lines+markers", name="Sales")
    # Title, a white theme, and the size in pixels.
    fig.update_layout(title="Dashboard Overview", template="plotly_white", width=1200, height=720)
    # Save as PNG. plotly needs the kaleido package for this step.
    fig.write_image(screenshots / "dashboard_overview.png")

    # A second empty chart. The name fig is reused because the first chart is already saved.
    fig = go.Figure()
    # Four bars of equal height, one per project stage.
    fig.add_bar(x=["Data", "ETL", "SQL", "Dashboard"], y=[1, 1, 1, 1])
    # Title, theme and size.
    fig.update_layout(title="Project Architecture", template="plotly_white", width=1200, height=720)
    # Save as PNG.
    fig.write_image(screenshots / "project_architecture.png")


# Saves a four-slide PowerPoint file into reports/.
def write_presentation() -> None:
    # python-pptx is optional, so try the import.
    try:
        # Presentation is the class that stands for one .pptx file.
        from pptx import Presentation
    # Not installed: leave without making a deck. Nothing is printed about it.
    except ImportError:
        # Go back to main() with nothing written.
        return

    # A new empty presentation.
    prs = Presentation()
    # Each pair is (slide title, slide text). The loop makes one slide per pair.
    for title, body in [
        # Slide 1: the title slide.
        ("Walmart Sales Analytics", "SQL, ETL, dashboarding, and forecasting"),
        # Slide 2: the questions the project answers.
        ("Business Questions", "Store ranking, holiday uplift, trends, and economic signals"),
        # Slide 3: how the database tables are laid out.
        ("Data Model", "Normalized POS tables plus weekly store sales fact table"),
        # Slide 4: the dashboard tabs.
        ("Dashboard", "Overview, stores, signals, forecast, insights, and data tabs"),
    ]:
        # Layout 1 is PowerPoint's "Title and Content" layout.
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        # Fill the title box.
        slide.shapes.title.text = title
        # Placeholder 1 is the content box under the title.
        slide.placeholders[1].text = body
    # Make the reports folder if it is missing.
    Path("reports").mkdir(exist_ok=True)
    # Save the file.
    prs.save("reports/walmart_sales_analytics.pptx")


# Runs the three steps one after the other.
def main() -> None:
    # Two SVG files.
    write_svg_assets()
    # Two PNG files.
    write_png_assets()
    # One PowerPoint file, if python-pptx is installed.
    write_presentation()
    # This message prints even when the PowerPoint step was skipped.
    print("Generated dashboard, architecture, screenshot, and presentation assets.")


# True when started with: python -m src.generate_assets
if __name__ == "__main__":
    # Make the files.
    main()
