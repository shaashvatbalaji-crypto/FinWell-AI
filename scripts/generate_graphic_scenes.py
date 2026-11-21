import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = r"C:\Users\shaas\OneDrive\Desktop\FinWell_AI\FinWell_AI\docs\assets\video"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 1920, 1080

def get_font(name="segoeui.ttf", size=24, bold=False):
    font_file = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = os.path.join(r"C:\Windows\Fonts", font_file)
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_rounded_rect(draw, bbox, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def create_radial_gradient(w, h, center_color, outer_color, center=None, radius=None):
    if center is None:
        center = (w // 2, h // 2)
    if radius is None:
        radius = math.hypot(w // 2, h // 2)
    
    img = Image.new("RGB", (w, h), outer_color)
    draw = ImageDraw.Draw(img)
    cx, cy = center
    
    steps = 40
    for i in range(steps, 0, -1):
        r = radius * (i / steps)
        t = i / steps
        r_c = int(outer_color[0] * t + center_color[0] * (1 - t))
        g_c = int(outer_color[1] * t + center_color[1] * (1 - t))
        b_c = int(outer_color[2] * t + center_color[2] * (1 - t))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(r_c, g_c, b_c))
    
    return img.filter(ImageFilter.GaussianBlur(radius=15))

# ==============================================================================
# SCENE 3B: Dense, Confusing Bank Statement (The Problem)
# ==============================================================================
def generate_scene3b():
    img = create_radial_gradient(W, H, (18, 24, 38), (8, 11, 18))
    draw = ImageDraw.Draw(img)

    # Header Bar
    draw_rounded_rect(draw, (80, 60, 1840, 140), 12, fill=(15, 23, 42), outline=(30, 41, 59), width=2)
    draw.text((120, 85), "ACCOUNT STATEMENT • MONTH-END CLOSE-UP", fill=(148, 163, 184), font=get_font(size=22, bold=True))
    draw.text((1450, 85), "STATUS: UNRECONCILED (142 TXNS)", fill=(239, 68, 68), font=get_font(size=20, bold=True))

    # Big alert banner
    draw_rounded_rect(draw, (80, 160, 1840, 240), 12, fill=(69, 10, 10), outline=(185, 28, 28), width=2)
    draw.text((120, 185), "WHERE DID YOUR MONEY GO?  •  Hundreds of unorganized, cryptic debits accumulating silently", fill=(254, 202, 202), font=get_font(size=26, bold=True))

    # Statement Table
    table_top = 260
    draw_rounded_rect(draw, (80, table_top, 1840, 960), 16, fill=(13, 19, 33), outline=(30, 41, 59), width=2)

    # Column Headers
    cols = [(110, "DATE"), (260, "TRANSACTION DESCRIPTION"), (1050, "CHQ / REF NO"), (1330, "DEBIT"), (1540, "CREDIT"), (1720, "TAG")]
    draw.line([(80, table_top + 50), (1840, table_top + 50)], fill=(51, 65, 85), width=2)
    for x, title in cols:
        draw.text((x, table_top + 16), title, fill=(148, 163, 184), font=get_font(size=18, bold=True))

    rows = [
        ("2024-03-28", "UPI/4092819028/ZOMATO-PAY/BLR", "UPI-4092819", "Rs. 480.00", "-", "UNSORTED"),
        ("2024-03-27", "POS 401928 CAFE COFFEE DAY KORAMANGALA", "POS-889124", "Rs. 250.00", "-", "UNSORTED"),
        ("2024-03-27", "POS 401928 CAFE COFFEE DAY KORAMANGALA (DUPLICATE?)", "POS-889124", "Rs. 250.00", "-", "ALERT !"),
        ("2024-03-26", "ACH DR NETFLIX ENTERTAINMENT IN", "ACH-991028", "Rs. 649.00", "-", "RECURRING"),
        ("2024-03-25", "NEFT DR/HDFC0000410/SELF-TRANSFER-TO-ICICI", "NEFT-77192", "Rs. 10,000.00", "-", "TRANSFER ?"),
        ("2024-03-24", "UPI/4081928391/AMAZON-PAY-GROCERY", "UPI-881920", "Rs. 1,840.00", "-", "UNSORTED"),
        ("2024-03-22", "CR REFUND AMAZON SELLER SERVICES RET-019", "REF-401928", "-", "Rs. 1,499.00", "REFUND ?"),
        ("2024-03-20", "IMPS/P2A/409182/SPLIT-WEEKEND-DINNER", "IMPS-2819", "-", "Rs. 1,200.00", "PEER CR"),
        ("2024-03-18", "AUTO-DEBIT SIP MUTUAL FUND GROWW", "MF-991823", "Rs. 5,000.00", "-", "INVESTMENT"),
        ("2024-03-15", "CHG ANNUAL DEBIT CARD MAINTENANCE + GST", "FEE-00192", "Rs. 590.00", "-", "BANK FEE"),
        ("2024-03-12", "CREDIT CARD BILL PAYMENT DESK AUTO-SWEEP", "CC-881923", "Rs. 24,650.00", "-", "MANUAL CHK")
    ]

    y = table_top + 65
    for date, desc, ref, dr, cr, tag in rows:
        is_highlight = "ALERT" in tag or "TRANSFER" in tag or "REFUND" in tag
        if is_highlight:
            draw_rounded_rect(draw, (95, y - 5, 1825, y + 42), 6, fill=(30, 20, 25) if "ALERT" in tag else (20, 30, 45))
        
        draw.text((110, y + 4), date, fill=(148, 163, 184), font=get_font(size=18))
        draw.text((260, y + 4), desc[:52], fill=(241, 245, 249) if not is_highlight else (251, 191, 36), font=get_font(size=18, bold=is_highlight))
        draw.text((1050, y + 4), ref, fill=(100, 116, 139), font=get_font(size=18))
        draw.text((1330, y + 4), dr, fill=(248, 113, 113) if dr != "-" else (100, 116, 139), font=get_font(size=18, bold=(dr != "-")))
        draw.text((1540, y + 4), cr, fill=(52, 211, 153) if cr != "-" else (100, 116, 139), font=get_font(size=18, bold=(cr != "-")))
        
        # Tag badge
        badge_fill = (239, 68, 68) if "ALERT" in tag else ((59, 130, 246) if "TRANSFER" in tag else ((16, 185, 129) if "REFUND" in tag else (71, 85, 105)))
        draw_rounded_rect(draw, (1710, y, 1815, y + 30), 4, fill=badge_fill)
        draw.text((1722, y + 4), tag, fill=(255, 255, 255), font=get_font(size=14, bold=True))
        
        draw.line([(95, y + 50), (1825, y + 50)], fill=(30, 41, 59), width=1)
        y += 58

    # Bottom watermark/summary
    draw.text((110, 985), "Total Monthly Volume: Rs. 1,42,850.00 across 3 accounts  •  Net Cashflow: Unclear without automated reconciliation", fill=(148, 163, 184), font=get_font(size=20))
    
    path = os.path.join(OUTPUT_DIR, "scene3b_confusing_statement.png")
    img.save(path)
    print("Saved:", path)

# ==============================================================================
# SCENE 4A: FinWell AI Ingestion & Extraction Engine
# ==============================================================================
def generate_scene4a():
    img = create_radial_gradient(W, H, (10, 24, 45), (5, 10, 20))
    draw = ImageDraw.Draw(img)

    # Top Brand Header
    draw_rounded_rect(draw, (80, 50, 1840, 130), 12, fill=(15, 23, 42), outline=(37, 99, 235), width=2)
    draw.text((120, 72), "FINWELL AI  •  STAGE 1: STATEMENT EXTRACTION & NORMALIZATION", fill=(255, 255, 255), font=get_font(size=26, bold=True))
    draw_rounded_rect(draw, (1480, 68, 1800, 112), 20, fill=(6, 78, 59), outline=(16, 185, 129), width=1)
    draw.text((1510, 78), "PyMuPDF + ChromaDB", fill=(52, 211, 153), font=get_font(size=18, bold=True))

    # 3 Pipeline Columns
    card_w = 540
    # Left Card: Statement Upload & PDF Parsing
    draw_rounded_rect(draw, (80, 160, 80 + card_w, 980), 16, fill=(13, 20, 36), outline=(30, 58, 138), width=2)
    draw_rounded_rect(draw, (100, 180, 80 + card_w - 20, 230), 8, fill=(30, 58, 138))
    draw.text((120, 192), "1. PDF Ingestion & Stream Parser", fill=(255, 255, 255), font=get_font(size=20, bold=True))
    
    draw.text((120, 260), "Source: Bank_Statement_Mar2024.pdf", fill=(148, 163, 184), font=get_font(size=18))
    draw.text((120, 295), "Parser: PyMuPDF High-Precision Stream", fill=(56, 189, 248), font=get_font(size=18))
    
    # Fake visual pdf preview
    draw_rounded_rect(draw, (110, 340, 590, 850), 10, fill=(19, 29, 51), outline=(51, 65, 85))
    draw.text((140, 360), "[HDFC BANK STATEMENT]", fill=(226, 232, 240), font=get_font(size=18, bold=True))
    draw.line([(140, 395), (560, 395)], fill=(71, 85, 105), width=2)
    for idx, sample_text in enumerate([
        "28/03/24 UPI-ZOMATO-BLR        Dr 480.00",
        "27/03/24 POS-CCD-KORAMANGALA   Dr 250.00",
        "26/03/24 NETFLIX COM ACH       Dr 649.00",
        "25/03/24 NEFT SELF TFR ICICI   Dr 10,000.00",
        "22/03/24 AMAZON RET CR         Cr 1,499.00",
        "18/03/24 GROWW SIP MF          Dr 5,000.00",
        "15/03/24 CARD MAINT FEE        Dr 590.00"
    ]):
        draw.text((140, 420 + idx * 55), sample_text, fill=(148, 163, 184), font=get_font("consola.ttf", size=15))
        if idx == 3:
            draw_rounded_rect(draw, (130, 415 + idx * 55, 570, 445 + idx * 55), 4, fill=(14, 165, 233), outline=(56, 189, 248), width=2)

    draw_rounded_rect(draw, (110, 880, 590, 940), 8, fill=(16, 185, 129))
    draw.text((180, 895), "142 ROWS EXTRACTED (100%)", fill=(255, 255, 255), font=get_font(size=18, bold=True))

    # Center Card: Normalization & Vector Embeddings
    cx1 = 660
    draw_rounded_rect(draw, (cx1, 160, cx1 + card_w, 980), 16, fill=(13, 20, 36), outline=(13, 148, 136), width=2)
    draw_rounded_rect(draw, (cx1 + 20, 180, cx1 + card_w - 20, 230), 8, fill=(13, 148, 136))
    draw.text((cx1 + 40, 192), "2. Normalization & AI Embedding", fill=(255, 255, 255), font=get_font(size=20, bold=True))
    
    draw.text((cx1 + 40, 260), "Clean Merchant Entity Resolution", fill=(148, 163, 184), font=get_font(size=18))
    draw.text((cx1 + 40, 295), "Vector Store: ChromaDB Semantic Match", fill=(52, 211, 153), font=get_font(size=18))

    # Step cards in middle
    steps = [
        ("Raw Text", "UPI/4092819028/ZOMATO-PAY/BLR"),
        ("Clean Merchant", "Zomato India (Online Dining)"),
        ("Semantic Category", "Food & Dining  [Confidence: 99.1%]"),
        ("Raw Text", "NEFT DR/HDFC0000410/SELF-TRANSFER"),
        ("Clean Merchant", "HDFC to ICICI Self-Transfer"),
        ("Semantic Category", "Internal Transfer [Flag: Pairing Req.]")
    ]
    sy = 350
    for label, val in steps:
        is_cat = "Category" in label or "Clean" in label
        draw_rounded_rect(draw, (cx1 + 30, sy, cx1 + card_w - 30, sy + 70), 8, fill=(20, 30, 48) if is_cat else (15, 23, 42), outline=(52, 211, 153) if is_cat else (71, 85, 105))
        draw.text((cx1 + 50, sy + 10), label.upper(), fill=(52, 211, 153) if is_cat else (148, 163, 184), font=get_font(size=14, bold=True))
        draw.text((cx1 + 50, sy + 35), val, fill=(241, 245, 249), font=get_font(size=17, bold=is_cat))
        sy += 85

    draw_rounded_rect(draw, (cx1 + 30, 880, cx1 + card_w - 30, 940), 8, fill=(13, 148, 136))
    draw.text((cx1 + 100, 895), "SEMANTIC CATEGORIZATION READY", fill=(255, 255, 255), font=get_font(size=18, bold=True))

    # Right Card: Structured Unified Ledger (MySQL)
    rx1 = 1240
    draw_rounded_rect(draw, (rx1, 160, rx1 + card_w, 980), 16, fill=(13, 20, 36), outline=(99, 102, 241), width=2)
    draw_rounded_rect(draw, (rx1 + 20, 180, rx1 + card_w - 20, 230), 8, fill=(99, 102, 241))
    draw.text((rx1 + 40, 192), "3. Unified Financial Schema", fill=(255, 255, 255), font=get_font(size=20, bold=True))
    
    draw.text((rx1 + 40, 260), "Database: MySQL Production Ledger", fill=(148, 163, 184), font=get_font(size=18))
    draw.text((rx1 + 40, 295), "Schema: UUID • Amount • Net Cashflow", fill=(165, 180, 252), font=get_font(size=18))

    # JSON code block view
    draw_rounded_rect(draw, (rx1 + 30, 340, rx1 + card_w - 30, 850), 10, fill=(10, 15, 26), outline=(51, 65, 85))
    json_lines = [
        "// Normalized Transaction Object",
        "{",
        '  "txn_id": "f8a92b41-38c0",',
        '  "account_id": 4108,',
        '  "date": "2024-03-25",',
        '  "type": "TRANSFER_OUT",',
        '  "amount": 10000.00,',
        '  "counterparty": "ICICI_8921",',
        '  "recon_status": "PENDING_PAIR",',
        '  "vector_score": 0.9842',
        "}"
    ]
    for idx, l in enumerate(json_lines):
        color = (148, 163, 184) if "//" in l else ((56, 189, 248) if ":" in l else (241, 245, 249))
        draw.text((rx1 + 50, 370 + idx * 42), l, fill=color, font=get_font("consola.ttf", size=18))

    draw_rounded_rect(draw, (rx1 + 30, 880, rx1 + card_w - 30, 940), 8, fill=(99, 102, 241))
    draw.text((rx1 + 100, 895), "INGESTION LATENCY: 420 ms", fill=(255, 255, 255), font=get_font(size=18, bold=True))

    path = os.path.join(OUTPUT_DIR, "scene4a_ingestion_extraction.png")
    img.save(path)
    print("Saved:", path)

# ==============================================================================
# SCENE 4B: FinWell AI Multi-Engine Reconciliation Matrix
# ==============================================================================
def generate_scene4b():
    img = create_radial_gradient(W, H, (10, 30, 35), (5, 15, 18))
    draw = ImageDraw.Draw(img)

    # Top Brand Header
    draw_rounded_rect(draw, (80, 50, 1840, 130), 12, fill=(15, 23, 42), outline=(16, 185, 129), width=2)
    draw.text((120, 72), "FINWELL AI  •  STAGE 2: MULTI-ENGINE TRANSACTION RECONCILIATION", fill=(255, 255, 255), font=get_font(size=26, bold=True))
    draw_rounded_rect(draw, (1420, 68, 1800, 112), 20, fill=(6, 78, 59), outline=(52, 211, 153), width=1)
    draw.text((1445, 78), "98.6% RECONCILED", fill=(52, 211, 153), font=get_font(size=18, bold=True))

    # 3 Horizontal Reconciliation Matching Modules
    engines = [
        {
            "engine": "1. INTER-ACCOUNT TRANSFER PAIRING ENGINE (TransferDetector)",
            "sub": "Eliminates double-counting between multiple user bank accounts",
            "left_title": "HDFC Primary Checking (A/c #4108)",
            "left_val": "2024-03-25 • DEBIT Rs. 10,000.00",
            "arrow": "<-> LINKED & RECONCILED <->",
            "right_title": "ICICI Savings Account (A/c #8921)",
            "right_val": "2024-03-25 • CREDIT Rs. 10,000.00",
            "result": "NET EXPENSE IMPACT: Rs. 0.00 (Self-Transfer Verified)",
            "badge": "100% CONFIDENCE",
            "color": (16, 185, 129)
        },
        {
            "engine": "2. REFUND TO PURCHASE LINKING ENGINE (RefundMatcher)",
            "sub": "Links credit refunds directly back to original debit purchases",
            "left_title": "Original Amazon Purchase",
            "left_val": "2024-03-08 • DEBIT Rs. 1,499.00",
            "arrow": "<-> DIRECT REFUND MATCH <->",
            "right_title": "Amazon Seller Return Credit",
            "right_val": "2024-03-22 • CREDIT Rs. 1,499.00",
            "result": "NET EXPENSE CANCELLED: Rs. 0.00 (Category Adjusted)",
            "badge": "MATCHED [0.984 SCORE]",
            "color": (6, 182, 212)
        },
        {
            "engine": "3. SLIDING-WINDOW DUPLICATE DETECTION ENGINE (DuplicateDetector)",
            "sub": "Detects accidental double-swipes & gateway duplicate charges",
            "left_title": "Coffee Shop Terminal Tap #1",
            "left_val": "10:14:02 AM • DEBIT Rs. 250.00",
            "arrow": "<!> DUPLICATE IDENTIFIED <!>",
            "right_title": "Coffee Shop Terminal Tap #2",
            "right_val": "10:14:15 AM • DEBIT Rs. 250.00",
            "result": "FLAGGED TO USER: Discrepancy Resolved, Prevented False Expense",
            "badge": "SLIDING WINDOW (48H)",
            "color": (245, 158, 11)
        }
    ]

    card_y = 160
    for eng in engines:
        draw_rounded_rect(draw, (80, card_y, 1840, card_y + 240), 16, fill=(12, 22, 36), outline=(30, 48, 70), width=2)
        
        # Engine Title Bar
        draw.text((110, card_y + 18), eng["engine"], fill=eng["color"], font=get_font(size=20, bold=True))
        draw.text((110, card_y + 46), eng["sub"], fill=(148, 163, 184), font=get_font(size=16))
        
        # Badge
        draw_rounded_rect(draw, (1580, card_y + 18, 1810, card_y + 54), 8, fill=(20, 35, 55), outline=eng["color"], width=1)
        draw.text((1600, card_y + 24), eng["badge"], fill=eng["color"], font=get_font(size=14, bold=True))

        # Left Node
        draw_rounded_rect(draw, (110, card_y + 80, 700, card_y + 165), 10, fill=(19, 31, 50), outline=(51, 65, 85))
        draw.text((130, card_y + 92), eng["left_title"], fill=(241, 245, 249), font=get_font(size=18, bold=True))
        draw.text((130, card_y + 125), eng["left_val"], fill=(248, 113, 113), font=get_font(size=18, bold=True))

        # Arrow Center
        draw_rounded_rect(draw, (730, card_y + 100, 1190, card_y + 145), 8, fill=(24, 40, 64), outline=eng["color"], width=1)
        draw.text((750, card_y + 112), eng["arrow"], fill=(255, 255, 255), font=get_font(size=18, bold=True))

        # Right Node
        draw_rounded_rect(draw, (1220, card_y + 80, 1810, card_y + 165), 10, fill=(19, 31, 50), outline=(51, 65, 85))
        draw.text((1240, card_y + 92), eng["right_title"], fill=(241, 245, 249), font=get_font(size=18, bold=True))
        draw.text((1240, card_y + 125), eng["right_val"], fill=(52, 211, 153), font=get_font(size=18, bold=True))

        # Result line
        draw_rounded_rect(draw, (110, card_y + 180, 1810, card_y + 225), 6, fill=(16, 28, 44))
        draw.text((130, card_y + 190), "-> " + eng["result"], fill=(226, 232, 240), font=get_font(size=17, bold=True))

        card_y += 265

    # Bottom metric strip
    draw_rounded_rect(draw, (80, 970, 1840, 1035), 10, fill=(6, 78, 59))
    draw.text((120, 985), "RECONCILIATION RESULT: 139 / 142 TRANSACTIONS VERIFIED (98.6%)  •  ACCURATE NET CASHFLOW GUARANTEED", fill=(255, 255, 255), font=get_font(size=19, bold=True))

    path = os.path.join(OUTPUT_DIR, "scene4b_reconciliation_matrix.png")
    img.save(path)
    print("Saved:", path)

# ==============================================================================
# SCENE 5B: FinWell AI Master Title Card & Brand Outro
# ==============================================================================
def generate_scene5b():
    img = create_radial_gradient(W, H, (10, 25, 45), (4, 8, 16))
    draw = ImageDraw.Draw(img)

    # Decorative tech grid dots
    for x in range(100, W, 100):
        for y in range(100, H, 100):
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(20, 45, 75))

    # Center Logo Shield Icon
    cx, cy = W // 2, 330
    shield_pts = [
        (cx, cy - 90),
        (cx + 80, cy - 45),
        (cx + 80, cy + 40),
        (cx, cy + 105),
        (cx - 80, cy + 40),
        (cx - 80, cy - 45)
    ]
    draw.polygon(shield_pts, fill=(16, 185, 129), outline=(52, 211, 153))
    # Inner checkmark
    draw.line([(cx - 35, cy), (cx - 10, cy + 28), (cx + 35, cy - 30)], fill=(255, 255, 255), width=10)

    # Title
    title = "FinWell AI"
    draw.text((cx - 240, 470), title, fill=(255, 255, 255), font=get_font(size=96, bold=True))

    # Subtitle
    sub = "Personal Finance Intelligence & Transaction Reconciliation Platform"
    draw.text((cx - 480, 590), sub, fill=(148, 163, 184), font=get_font(size=28))

    # Core Capabilities Badges
    pills = [
        "PyMuPDF Statement Extraction",
        "ChromaDB Semantic Search",
        "Tri-Engine Reconciliation Matrix",
        "Real-Time Analytics"
    ]
    total_w = len(pills) * 280
    px = cx - (total_w // 2)
    for p in pills:
        draw_rounded_rect(draw, (px, 660, px + 260, 715), 25, fill=(15, 28, 48), outline=(56, 189, 248), width=1)
        draw.text((px + 20, 678), p, fill=(226, 232, 240), font=get_font(size=16, bold=True))
        px += 280

    # Tagline Banner
    draw_rounded_rect(draw, (cx - 450, 770, cx + 450, 850), 16, fill=(6, 78, 59), outline=(52, 211, 153), width=2)
    tagline = "Extract.  Understand.  Reconcile.  Take Control."
    draw.text((cx - 360, 792), tagline, fill=(255, 255, 255), font=get_font(size=30, bold=True))

    # Bottom github repo url
    draw.text((cx - 300, 930), "github.com/shaashvatbalaji-crypto/FinWell-AI", fill=(100, 116, 139), font=get_font(size=22))

    path = os.path.join(OUTPUT_DIR, "scene5b_title_card.png")
    img.save(path)
    print("Saved:", path)

if __name__ == "__main__":
    generate_scene3b()
    generate_scene4a()
    generate_scene4b()
    generate_scene5b()
    print("All graphic scenes generated successfully!")
