"""
RDTI Calculator — Flask Backend
Handles API, Stripe checkout, PDF generation, and webhooks.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime

import stripe
from flask import Flask, jsonify, request, send_file, render_template, abort
from functools import wraps
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from engine import calculate
from analytics import log_event, get_stats

# ── Config ────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "price_rdti_report")
DOMAIN = os.environ.get("DOMAIN", "http://localhost:5000")
DASHBOARD_CODE = os.environ.get("DASHBOARD_CODE", "0794")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# ── Routes ────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the landing page."""
    log_event("page_view")
    return render_template("index.html")


# ── Blog ───────────────────────────────────────────────────────────────

BLOG_POSTS = [
    {
        "slug": "rdti-software-startups-australia-2025",
        "title": "R&D Tax Incentive for Software Startups in Australia: The Complete Guide",
        "date": "2026-06-16",
        "author": "1st4 Group",
        "summary": "How Australian software startups can claim the 43.5% ATO refund on development costs — eligibility criteria, qualifying activities, and common mistakes.",
        "tags": ["RDTI", "SaaS", "Australian Startups", "ATO", "R&D Tax"],
        "content": """
<h2>What Is the R&D Tax Incentive?</h2>
<p>Australia's R&D Tax Incentive (RDTI) is a government program that gives cash back for eligible R&D activities. For SMEs (turnover under $20M), the refundable tax offset is <strong>43.5%</strong> of eligible spend — meaning for every $100,000 you spend on qualifying software development, you can get up to $43,500 back in cash.</p>

<h2>Do Software Development Activities Qualify?</h2>
<p>Yes — if they involve technical uncertainty. The ATO and AusIndustry look for:</p>
<ul>
    <li><strong>Novelty:</strong> Can't know the outcome in advance (or how to achieve it)</li>
    <li><strong>Systematic progression:</strong> Methodical experimentation, not trial-and-error</li>
    <li><strong>Technical uncertainty:</strong> The answer isn't already known or publicly available</li>
</ul>
<p>Building routine business software does NOT qualify. But building a new recommendation engine, optimising a trading algorithm, or developing novel infrastructure — that often does.</p>

<h2>The 43.5% SME Rate</h2>
<p>If your aggregated turnover is under $20M, you can claim the <strong>refundable</strong> 43.5% rate. This means the ATO sends you a cash cheque — you don't need to owe tax to benefit. Non-SME companies can claim a <strong>non-refundable</strong> 38.5% offset that offsets tax payable.</p>

<h2>What's Eligible?</h2>
<ul>
    <li><strong>Technical staff wages</strong> — developers, engineers, data scientists (80% of time typically deemed eligible)</li>
    <li><strong>Cloud infrastructure</strong> — AWS, Azure, GCP costs directly supporting R&D (70% typically)</li>
    <li><strong>Contractors</strong> — external developers doing R&D work (75% typical)</li>
    <li><strong>Software licenses</strong> — tools used directly in development (60% typical)</li>
</ul>

<h2>Common Mistakes</h2>
<ul>
    <li><strong>Not documenting uncertainty</strong> — you need records showing you didn't know the answer upfront</li>
    <li><strong>Claiming 100%</strong> — most activities mix R&D and routine work; apportionment is expected</li>
    <li><strong>Missing the deadline</strong> — R&D application due to AusIndustry by 30 April after year end</li>
</ul>

<h2>How Much Could You Get?</h2>
<p><a href="/">Use our free RDTI Calculator</a> — enter your staff count, cloud spend, and other costs for an instant estimate. No email, no signup.</p>
"""
    },
    {
        "slug": "ato-43-percent-software-development-refund",
        "title": "The ATO's 43.5% Software Development Refund: What Every Aussie Founder Should Know",
        "date": "2026-06-16",
        "author": "1st4 Group",
        "summary": "Most Australian tech founders don't realise their software development costs qualify for the ATO's 43.5% refundable R&D offset. Here's what you're leaving on the table.",
        "tags": ["ATO", "43.5%", "Software Development", "R&D", "Tax Refund"],
        "content": """
<h2>You're Probably Leaving $50K+ on the Table</h2>
<p>Most Australian SaaS founders think R&D means lab coats and petri dishes. In reality, the ATO's R&D Tax Incentive covers software development — and most bootstrapped startups qualify for the 43.5% <strong>refundable</strong> cash offset.</p>

<p>For a team of 5 engineers averaging $150K salary with $50K in cloud costs, the eligible refund is approximately <strong>$150K+ per year</strong>. In cash. From the ATO.</p>

<h2>Who Qualifies?</h2>
<p>The key test: did your development involve <strong>technical uncertainty</strong> that was resolved through <strong>systematic progression</strong>? If you built something where you didn't know the outcome in advance, and you approached it methodically, you likely qualify.</p>

<p>Examples of qualifying activities:</p>
<ul>
    <li>Building a novel recommendation or matching algorithm</li>
    <li>Optimising real-time data processing at scale</li>
    <li>Developing proprietary machine learning models</li>
    <li>Creating new cryptographic or security protocols</li>
</ul>

<h2>The Numbers Don't Lie</h2>
<p>The ATO dishes out over <strong>$3 billion annually</strong> through the RDTI program. Yet AusIndustry estimates that <strong>40% of eligible startups don't claim</strong> — because they don't know they qualify.</p>

<h2>Quick Estimate Tool</h2>
<p><a href="/">Check your eligibility in 30 seconds</a> — free calculator, no email required.</p>
"""
    },
    {
        "slug": "bootstrapped-saas-rdti-maximise-refund",
        "title": "How Bootstrapped SaaS Founders Can Maximise Their RDTI Refund",
        "date": "2026-06-16",
        "author": "1st4 Group",
        "summary": "Practical strategies for bootstrapped Australian SaaS companies to maximise their R&D Tax Incentive claim — from cost tracking to documentation.",
        "tags": ["Bootstrapped", "SaaS", "RDTI", "Tax Strategy", "Startup Finance"],
        "content": """
<h2>Why Bootstrapped Founders Have an Advantage</h2>
<p>Bootstrapped SaaS companies are <strong>perfect RDTI candidates</strong>. Without VC funding, every dollar counts — and the 43.5% refundable offset is essentially the government co-investing in your R&D at nearly half the cost.</p>

<h2>Strategy 1: Track Time Accurately</h2>
<p>The most common reason RDTI claims get reduced? Poor time tracking. The ATO expects reasonable apportionment — if a developer spends 60% of their time on novel work and 40% on routine maintenance, claim 60%. Track this monthly, not retrospectively.</p>

<h2>Strategy 2: Include All Cloud Costs</h2>
<p>AWS, Azure, GCP, DigitalOcean — the infrastructure that supports your R&D is eligible. Keep detailed invoices showing which instances/servers supported development vs production.</p>

<h2>Strategy 3: Don't Forget Contractors</h2>
<p>External developers, designers, and engineers doing R&D work are eligible at typically 75% of their cost. If you're using freelance talent for novel development work, include them in your claim.</p>

<h2>Strategy 4: Document the Uncertainty</h2>
<p>This is the most important requirement and the most commonly missed. Keep records showing what you <em>didn't know</em> before you started: research notes, experiment results, failed approaches. GitHub commit history, technical design docs, and architecture RFCs all count.</p>

<h2>Strategy 5: Lodge on Time</h2>
<p>R&D registration with AusIndustry must be submitted by <strong>30 April</strong> after the financial year ends. Mark your calendar now. Late registration means zero refund for that year.</p>

<h2>How Much Are You Leaving on the Table?</h2>
<p><a href="/">Use our calculator</a> to estimate your refund in 30 seconds.</p>
"""
    },
]


@app.route("/blog")
def blog_index():
    """Blog listing page."""
    return render_template("blog.html", posts=BLOG_POSTS)


@app.route("/blog/<slug>")
def blog_post(slug):
    """Individual blog post."""
    post = next((p for p in BLOG_POSTS if p["slug"] == slug), None)
    if post is None:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/sitemap.xml")
def sitemap():
    """Basic XML sitemap for SEO."""
    pages = [
        {"loc": "", "priority": "1.0"},
        {"loc": "/blog", "priority": "0.8"},
    ]
    for p in BLOG_POSTS:
        pages.append({"loc": f"/blog/{p['slug']}", "priority": "0.7"})

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '  <url><loc>https://rdtcalculator.1st4.mobi/</loc><priority>1.0</priority></url>\n'
    xml += '  <url><loc>https://rdtcalculator.1st4.mobi/blog</loc><priority>0.8</priority></url>\n'
    for p in BLOG_POSTS:
        xml += f'  <url><loc>https://rdtcalculator.1st4.mobi/blog/{p["slug"]}</loc><priority>0.7</priority></url>\n'
    xml += '</urlset>'
    return xml, 200, {"Content-Type": "application/xml"}


@app.route("/robots.txt")
def robots():
    """Robots.txt for search engines."""
    return "User-agent: *\nAllow: /\nSitemap: https://rdtcalculator.1st4.mobi/sitemap.xml\n", 200, {"Content-Type": "text/plain"}


# ── API Routes ─────────────────────────────────────────────────────────

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """Calculate RDTI estimate from form data."""
    data = request.get_json() or {}
    result = calculate(data)
    log_event("calculation", {
        "business_type": data.get("business_type", ""),
        "staff_count": data.get("staff_count", 0),
        "refund_amount": result.get("results", {}).get("refundable_offset", 0),
    })
    return jsonify(result)


@app.route("/api/create-checkout", methods=["POST"])
def create_checkout():
    """Create Stripe Checkout Session for the full report."""
    data = request.get_json() or {}
    discount = data.get("discount", False)

    if not STRIPE_SECRET_KEY:
        # Dev mode — redirect to PDF directly
        return jsonify({"url": f"{DOMAIN}/api/report?{_encode_params(data)}"})

    try:
        if discount:
            # 50% off — dynamic pricing
            line_items = [{
                "price_data": {
                    "currency": "aud",
                    "product_data": {"name": "RDTI Full Report (50% off)"},
                    "unit_amount": 950,
                },
                "quantity": 1,
            }]
        else:
            line_items = [{"price": STRIPE_PRICE_ID, "quantity": 1}]

        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode="payment",
            success_url=f"{DOMAIN}/api/report?session_id={{CHECKOUT_SESSION_ID}}&{_encode_params(data)}",
            cancel_url=f"{DOMAIN}/",
            metadata=data,
        )
        log_event("checkout", {"discount": discount, "amount_cents": 950 if discount else 1900})
        return jsonify({"url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/report")
def download_report():
    """Generate and return the PDF report."""
    data = {
        "staff_count": request.args.get("staff_count", 0, type=int),
        "avg_salary": request.args.get("avg_salary", 0, type=float),
        "cloud_spend": request.args.get("cloud_spend", 0, type=float),
        "contractor_spend": request.args.get("contractor_spend", 0, type=float),
        "consumables_spend": request.args.get("consumables_spend", 0, type=float),
        "licenses_spend": request.args.get("licenses_spend", 0, type=float),
        "business_type": request.args.get("business_type", "software_development"),
        "turnover": request.args.get("turnover", 0, type=float),
    }

    # Calculate
    result = calculate(data)
    r = result["results"]
    inp = result["inputs"]

    # Generate PDF
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    margin = 50

    y = h - margin

    # Title
    pdf.setFont("Helvetica-Bold", 24)
    pdf.setFillColorRGB(0.02, 0.37, 0.20)  # dark green
    pdf.drawString(margin, y, "R&D Tax Incentive")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(margin, y - 30, "Estimated Claim Report")
    y -= 60

    # Date
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(margin, y, f"Generated: {datetime.now().strftime('%d %B %Y')}")
    y -= 40

    # ── Your Refund ──
    pdf.setFillColorRGB(0.02, 0.37, 0.20)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, "Your Estimated Refund")
    y -= 30

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, f"ATO Refund: ${r['refundable_offset']:>,.2f}")
    y -= 20
    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, y, f"Total Eligible R&D Spend: ${r['total_eligible_spend']:>,.2f}")
    y -= 16
    pdf.drawString(margin, y, f"Refund Rate: {r['refund_rate_pct']}% ({'SME' if r['is_sme'] else 'Standard'})")
    y -= 30

    # ── Breakdown ──
    pdf.setFillColorRGB(0.02, 0.37, 0.20)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, "Spend Breakdown")
    y -= 24
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 10)

    staff_wages = inp["technical_staff_count"] * inp["avg_staff_salary"]
    labels_values = [
        (f"Staff ({inp['technical_staff_count']} × ${inp['avg_staff_salary']:>,.0f})",
         staff_wages * 0.80, "80% of staff time"),
        ("Cloud/Infrastructure", inp["cloud_infra_spend"] * 0.70, "70% of cloud spend"),
        ("Contractors", inp["contractor_spend"] * 0.75, "75% of contractor spend"),
        ("Consumables", inp["consumables_spend"] * 0.80, "80% of materials"),
        ("Software Licenses", inp["software_licenses"] * 0.60, "60% of license costs"),
    ]

    for label, val, note in labels_values:
        if val > 0:
            pdf.drawString(margin + 10, y, f"  {label}:")
            pdf.drawRightString(w - margin, y, f"${val:>10,.2f}")
            y -= 14
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawString(margin + 20, y, note)
            pdf.setFillColorRGB(0, 0, 0)
            y -= 16

    y -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "  Total Eligible:")
    pdf.drawRightString(w - margin, y, f"${r['total_eligible_spend']:>10,.2f}")
    y -= 30

    # ── Industry Comparison ──
    if y < 120:
        pdf.showPage()
        y = h - margin

    pdf.setFillColorRGB(0.02, 0.37, 0.20)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, "Industry Comparison")
    y -= 24
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 10)
    b = result["benchmark"]
    pdf.drawString(margin, y, f"  Sector: {b['sector']}")
    y -= 14
    pdf.drawString(margin, y, f"  Industry Avg Refund/Staff: ${b['benchmark_refund_per_staff']:>8,.0f}")
    y -= 14
    pdf.drawString(margin, y, f"  Your Refund/Staff:         ${b['your_refund_per_staff']:>8,.0f}")
    y -= 14
    pdf.drawString(margin, y, f"  Verdict: {b['message']}")
    y -= 30

    # ── Gap Analysis ──
    gap = result.get("gap_analysis", {})
    if gap.get("notes"):
        if y < 100:
            pdf.showPage()
            y = h - margin
        pdf.setFillColorRGB(0.92, 0.62, 0.07)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin, y, "Potential Overlooked Spend")
        y -= 24
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica", 10)
        for note in gap["notes"]:
            pdf.drawString(margin + 10, y, f"  • {note}")
            y -= 14
        y -= 6
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin, y, f"  Potential additional refund: ${gap['potential_refund_gap']:>8,.0f}")
        y -= 30

    # ── Next Steps ──
    if y < 120:
        pdf.showPage()
        y = h - margin
    pdf.setFillColorRGB(0.02, 0.37, 0.20)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, "Next Steps")
    y -= 24
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 10)
    steps = [
        "1. Gather payroll records for technical staff",
        "2. Compile cloud/infrastructure invoices (AWS, Azure, GCP)",
        "3. Collect contractor agreements and invoices",
        "4. Document R&D activities — what was novel/experimental?",
        "5. Engage an R&D consultant or registered tax agent",
        "6. Lodge R&D Application with AusIndustry (by 30 April after year end)",
        "7. Lodge amended tax return with ATO (43.5% refund within 28 days)",
    ]
    for step_text in steps:
        pdf.drawString(margin + 10, y, step_text)
        y -= 14

    # ── Footer ──
    y = margin + 20
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin, y, "Disclaimer: This is an estimate only. "
                  "Engage a registered tax agent or R&D consultant for your actual application.")
    pdf.drawString(margin, y - 10,
                   f"Generated by rdtcalculator.com.au | 1st4 Group | {datetime.now().strftime('%Y')}")

    # ── Referral Upsell (page 2) ──
    pdf.showPage()
    y = h - margin
    pdf.setFillColorRGB(0.02, 0.37, 0.20)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin, y, "Want Us to File This for You?")
    y -= 30
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 11)
    lines = [
        "We partner with certified R&D tax accountants who handle the entire",
        "AusIndustry and ATO filing on your behalf.",
        "",
        "What you get:",
        "  ✅ Full R&D activity documentation",
        "  ✅ AusIndustry registration (due 30 April)",
        "  ✅ ATO refund filing (43.5% — paid in ~28 days)",
        "  ✅ Maximised claim — we find what you missed",
        "  ✅ Success-fee basis — you pay nothing unless you get your refund",
        "",
        "Ready to claim?",
        "  → Reply to this PDF or email barry@1st4.mobi",
        "  → Include your estimated refund amount and staff count",
        "  → We'll connect you with the right accountant in 24 hours",
        "",
        "No obligation. Free initial consultation.",
        "",
        "1st4 Group — R&D Tax Incentive Specialists",
    ]
    for line in lines:
        pdf.drawString(margin, y, line)
        y -= 16
        if y < 60:
            pdf.showPage()
            y = h - margin

    pdf.save()
    buf.seek(0)

    log_event("purchase", {
        "business_type": data.get("business_type", ""),
        "staff_count": data.get("staff_count", 0),
        "refund_amount": r.get("refundable_offset", 0),
        "revenue_cents": 950 if data.get("discount") else 1900,
    })

    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"RDTI_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
    )


@app.route("/api/referral-lead", methods=["POST"])
def referral_lead():
    """Capture referral opt-in leads."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"status": "ignored", "reason": "invalid email"}), 400

    # Write to a simple JSONL file
    lead = {
        "timestamp": datetime.utcnow().isoformat(),
        "email": email,
        "staff_count": data.get("staff_count", 0),
        "refund_amount": data.get("refund_amount", "0"),
        "business_type": data.get("business_type", ""),
        "claimed": False,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/referral_leads.jsonl", "a") as f:
        f.write(json.dumps(lead) + "\n")

    log_event("referral_lead", {
        "email": email,
        "refund_amount": data.get("refund_amount", "0"),
        "business_type": data.get("business_type", ""),
    })

    return jsonify({"status": "captured"})


@app.route("/api/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe payment confirmation."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if endpoint_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return jsonify({"error": "Invalid signature"}), 400
    else:
        event = json.loads(payload)

    if event.get("type") == "checkout.session.completed":
        # Payment successful — the user will be redirected to /api/report with session_id
        # The report is generated on-the-fly, so no processing needed here
        pass

    return jsonify({"status": "ok"})


def _encode_params(data: dict) -> str:
    """Convert calculation inputs to URL query params."""
    mapping = {
        "staff_count": "staff_count",
        "avg_salary": "avg_salary",
        "cloud_spend": "cloud_spend",
        "contractor_spend": "contractor_spend",
        "consumables_spend": "consumables_spend",
        "licenses_spend": "licenses_spend",
        "business_type": "business_type",
        "turnover": "turnover",
    }
    parts = []
    for our_key, req_key in mapping.items():
        val = data.get(our_key, data.get(req_key, ""))
        if val:
            parts.append(f"{req_key}={val}")
    return "&".join(parts)


# ── Dashboard ─────────────────────────────────────────────────────────


def require_code(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        code = request.args.get("code", "")
        if code != DASHBOARD_CODE:
            return render_template("login.html", error=None)
        return f(*args, **kwargs)
    return decorated


@app.route("/dashboard")
@require_code
def dashboard():
    """Serve the analytics dashboard."""
    return render_template("dashboard.html")


@app.route("/api/dashboard-stats")
@require_code
def api_dashboard_stats():
    """Return JSON dashboard stats."""
    days = request.args.get("days", 30, type=int)
    return jsonify(get_stats(days=days))


# ── Main ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)