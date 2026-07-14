from playwright.sync_api import sync_playwright
HTML=str(__import__("pathlib").Path(__file__).resolve().parent / "manuscript_combined_v1.html")
PDF=str(__import__("pathlib").Path(__file__).resolve().parent / "manuscript_combined_v1.pdf")
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page()
    pg.goto("file://"+HTML, wait_until="load")
    pg.wait_for_timeout(600)
    pg.emulate_media(media="print")
    pg.pdf(path=PDF, format="A4", print_background=True, prefer_css_page_size=False,
           margin={"top":"16mm","bottom":"15mm","left":"15mm","right":"15mm"})
    b.close()
print("PDF written:", PDF)
