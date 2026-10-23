"""Generate a small sample newspaper PDF for testing (text-based)."""
import fitz

doc = fitz.open()
page = doc.new_page()  # A4

blocks = [
    (50, 60, "THE KARACHI HERALD", 22),
    (50, 95, "Tuesday, 17 June 2026  ·  City Edition", 10),
    (50, 140,
     "K-Electric blamed for prolonged load-shedding in Karachi", 15),
    (50, 165,
     "Residents of several Karachi neighbourhoods staged protests on Monday, "
     "accusing K-Electric of subjecting them to hours of unannounced "
     "load-shedding despite paying inflated bills. \"KE has once again failed "
     "the people of this city,\" said a protester. Critics say the utility's "
     "excuses have worn thin.", 11),
    (50, 260,
     "NEPRA approves modest tariff relief; KE welcomes decision", 15),
    (50, 285,
     "In a separate development, NEPRA announced a small tariff adjustment. "
     "K-Electric welcomed the regulator's decision, saying it would help "
     "sustain investment in the grid and improve supply reliability for "
     "consumers across Karachi.", 11),
    (50, 370,
     "KE completes new grid station to boost supply", 15),
    (50, 395,
     "K-Electric announced the completion of a new grid station in the "
     "industrial area, a move the company says will strengthen supply to "
     "thousands of businesses and households.", 11),
]

for x, y, text, size in blocks:
    page.insert_text((x, y), text, fontsize=size, fontname="helv")

doc.save("sample_newspaper.pdf")
print("Wrote sample_newspaper.pdf")
