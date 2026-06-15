"""
RDTI Calculator Engine — Australian R&D Tax Incentive Estimator.

SMEs (aggregated turnover < $20M):  43.5¢ refundable per $1 eligible spend
Non-SMEs (turnover $20M-$250M):     30.0¢ non-refundable per $1 eligible spend
Large (turnover > $250M):           30.0¢ non-refundable per $1 eligible spend
                                     (capped at $150M eligible spend)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Eligibility rules (ATO guidelines) ─────────────────────────────────

# Core R&D activities — systematic, experimental, technical
CORE_ELIGIBLE = {
    "software_development",  # building new platforms, novel algorithms
    "hardware_prototyping",   # electronics, mechanical prototypes
    "engineering_design",     # novel engineering solutions
    "scientific_experiments", # lab work, field trials
    "manufacturing_process",  # novel manufacturing methods
    "biotech_pharma",         # drug discovery, medical devices
    "agritech",               # novel agricultural methods
    "cleantech_energy",       # renewable energy innovation
    "mining_tech",            # novel extraction/processing methods
    "defence_aerospace",      # defence and aerospace R&D
}

# Supporting activities — directly related to core R&D
# Up to ~30-40% of core spend typically qualifies for supporting


@dataclass
class RDTCalculation:
    """Complete RDTI calculation with full breakdown."""

    # Inputs
    technical_staff_count: int = 0
    avg_staff_salary: float = 0.0
    cloud_infra_spend: float = 0.0
    contractor_spend: float = 0.0
    consumables_spend: float = 0.0
    software_licenses: float = 0.0
    business_type: str = "software_development"
    annual_turnover: float = 0.0

    # Computed
    total_eligible_spend: float = 0.0
    refundable_offset: float = 0.0
    fee: float = 0.0
    core_rd_spend: float = 0.0
    supporting_spend: float = 0.0
    is_sme: bool = True
    industry_benchmark: dict = field(default_factory=dict)
    gap_analysis: dict = field(default_factory=dict)

    def calculate(self) -> "RDTCalculation":
        """Run the full RDTI calculation."""
        # Staff wages (60-90% of technical staff time typically qualifies)
        staff_wages = self.technical_staff_count * self.avg_staff_salary
        staff_eligible = staff_wages * 0.80  # 80% assumption

        # Cloud/infra — if building novel software, 60-80% qualifies
        cloud_eligible = self.cloud_infra_spend * 0.70

        # Contractors — directly related to R&D
        contractor_eligible = self.contractor_spend * 0.75

        # Consumables — materials used in experiments/prototypes
        consumables_eligible = self.consumables_spend * 0.80

        # Software licenses — tools used for R&D
        licenses_eligible = self.software_licenses * 0.60

        # Total
        self.core_rd_spend = staff_eligible + contractor_eligible
        self.supporting_spend = cloud_eligible + consumables_eligible + licenses_eligible
        self.total_eligible_spend = self.core_rd_spend + self.supporting_spend

        # SME check
        self.is_sme = self.annual_turnover < 20_000_000 or self.annual_turnover == 0

        # Tax offset
        if self.is_sme:
            self.refundable_offset = self.total_eligible_spend * 0.435
        else:
            self.refundable_offset = self.total_eligible_spend * 0.30

        # Fee (20% of refund, capped reasonably)
        self.fee = min(self.refundable_offset * 0.20, 50_000)

        # Industry benchmarks
        self._compute_benchmarks(staff_wages)
        self._compute_gap_analysis(staff_wages)

        return self

    def _compute_benchmarks(self, staff_wages: float):
        """Compare against industry averages."""
        # Based on ATO public data + industry surveys
        benchmarks = {
            "software_development": {
                "label": "SaaS / Software",
                "typical_rd_pct": 0.75,   # 75% of staff cost is R&D
                "cloud_utilization": 0.80,
                "avg_refund_per_staff": 42_000,
            },
            "hardware_prototyping": {
                "label": "Hardware / Electronics",
                "typical_rd_pct": 0.85,
                "cloud_utilization": 0.20,
                "avg_refund_per_staff": 55_000,
            },
            "engineering_design": {
                "label": "Engineering",
                "typical_rd_pct": 0.70,
                "cloud_utilization": 0.15,
                "avg_refund_per_staff": 48_000,
            },
            "mining_tech": {
                "label": "Mining Tech",
                "typical_rd_pct": 0.65,
                "cloud_utilization": 0.10,
                "avg_refund_per_staff": 60_000,
            },
            "cleantech_energy": {
                "label": "CleanTech / Energy",
                "typical_rd_pct": 0.80,
                "cloud_utilization": 0.15,
                "avg_refund_per_staff": 52_000,
            },
            "manufacturing_process": {
                "label": "Manufacturing",
                "typical_rd_pct": 0.60,
                "cloud_utilization": 0.05,
                "avg_refund_per_staff": 38_000,
            },
            "biotech_pharma": {
                "label": "Biotech / Pharma",
                "typical_rd_pct": 0.90,
                "cloud_utilization": 0.10,
                "avg_refund_per_staff": 65_000,
            },
            "agritech": {
                "label": "AgriTech",
                "typical_rd_pct": 0.70,
                "cloud_utilization": 0.05,
                "avg_refund_per_staff": 40_000,
            },
        }

        bench = benchmarks.get(self.business_type, benchmarks["software_development"])

        if self.technical_staff_count > 0:
            refund_per_staff = self.refundable_offset / self.technical_staff_count
        else:
            refund_per_staff = 0

        self.industry_benchmark = {
            "sector": bench["label"],
            "benchmark_refund_per_staff": bench["avg_refund_per_staff"],
            "your_refund_per_staff": round(refund_per_staff, 0),
            "typical_rd_pct": bench["typical_rd_pct"],
            "message": "",
        }

        # Generate comparison message
        if refund_per_staff > bench["avg_refund_per_staff"] * 1.2:
            self.industry_benchmark["message"] = "✅ Above industry average — you're capturing well."
        elif refund_per_staff > bench["avg_refund_per_staff"] * 0.8:
            self.industry_benchmark["message"] = "👍 In line with industry average."
        else:
            self.industry_benchmark["message"] = "⚠️ Below industry average — likely missing eligible spend."

    def _compute_gap_analysis(self, staff_wages: float):
        """Estimate how much eligible spend is being missed."""
        if self.technical_staff_count == 0:
            self.gap_analysis = {"total_gap": 0, "potential_refund_gap": 0, "notes": []}
            return

        notes = []
        gap = 0

        # Staff time not claimed
        if staff_wages > 0:
            # If they entered a salary, assume 80% eligible
            pass  # already included above

        # Consumables gap
        if self.consumables_spend < staff_wages * 0.05:
            est_gap = staff_wages * 0.10
            gap += est_gap
            notes.append(f"Consumables (~\${est_gap:,.0f} in materials/devices might qualify)")

        # Cloud gap  
        if self.cloud_infra_spend < staff_wages * 0.10 and self.business_type == "software_development":
            est_gap = staff_wages * 0.15
            gap += est_gap
            notes.append(f"Cloud infrastructure (~\${est_gap:,.0f} in AWS/Azure is often eligible)")

        # Software licenses gap
        if self.software_licenses < staff_wages * 0.03:
            est_gap = staff_wages * 0.05
            gap += est_gap
            notes.append(f"Software licenses (~\${est_gap:,.0f} in dev tools could qualify)")

        self.gap_analysis = {
            "total_gap": round(gap, 0),
            "potential_refund_gap": round(gap * 0.435, 0),
            "notes": notes,
        }

    def to_dict(self) -> dict:
        """Serialise to dict for JSON response."""
        return {
            "inputs": {
                "technical_staff_count": self.technical_staff_count,
                "avg_staff_salary": self.avg_staff_salary,
                "cloud_infra_spend": self.cloud_infra_spend,
                "contractor_spend": self.contractor_spend,
                "consumables_spend": self.consumables_spend,
                "software_licenses": self.software_licenses,
                "business_type": self.business_type,
                "annual_turnover": self.annual_turnover,
            },
            "results": {
                "total_eligible_spend": round(self.total_eligible_spend, 2),
                "refundable_offset": round(self.refundable_offset, 2),
                "core_rd_spend": round(self.core_rd_spend, 2),
                "supporting_spend": round(self.supporting_spend, 2),
                "is_sme": self.is_sme,
                "refund_rate_pct": 43.5 if self.is_sme else 30.0,
                "estimated_fee": round(self.fee, 2),
            },
            "benchmark": self.industry_benchmark,
            "gap_analysis": self.gap_analysis,
        }

    def to_report_text(self) -> str:
        """Generate full report text for PDF."""
        d = self.to_dict()
        r = d["results"]
        inp = d["inputs"]

        lines = []
        lines.append("=" * 60)
        lines.append("  R&D TAX INCENTIVE — ESTIMATED CLAIM REPORT")
        lines.append("  Prepared for: [Client Name]")
        lines.append(f"  Date: {__import__('datetime').datetime.now().strftime('%d %B %Y')}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("YOUR ESTIMATED REFUND")
        lines.append("-" * 40)
        lines.append(f"  Total Eligible R&D Spend:  ${r['total_eligible_spend']:>10,.2f}")
        lines.append(f"  Refund Rate:                    {r['refund_rate_pct']}%")
        lines.append(f"  Estimated ATO Refund:     ${r['refundable_offset']:>10,.2f}")
        lines.append("")
        lines.append("BREAKDOWN")
        lines.append("-" * 40)
        lines.append(f"  Core R&D Activities:       ${r['core_rd_spend']:>10,.2f}")
        lines.append(f"  Supporting Activities:     ${r['supporting_spend']:>10,.2f}")
        lines.append("")
        lines.append(f"  Staff ({inp['technical_staff_count']} × \${inp['avg_staff_salary']:,.0f}):      "
                      f"${inp['technical_staff_count'] * inp['avg_staff_salary'] * 0.80:>10,.2f}")
        lines.append(f"  Cloud/Infrastructure:      ${inp['cloud_infra_spend'] * 0.70:>10,.2f}")
        lines.append(f"  Contractors:               ${inp['contractor_spend'] * 0.75:>10,.2f}")
        lines.append(f"  Consumables:               ${inp['consumables_spend'] * 0.80:>10,.2f}")
        lines.append(f"  Software Licenses:         ${inp['software_licenses'] * 0.60:>10,.2f}")
        lines.append("")
        lines.append("INDUSTRY COMPARISON")
        lines.append("-" * 40)
        b = self.industry_benchmark
        lines.append(f"  Sector:                    {b['sector']}")
        lines.append(f"  Industry Avg Refund/Staff: \${b['benchmark_refund_per_staff']:>8,.0f}")
        lines.append(f"  Your Refund/Staff:         \${b['your_refund_per_staff']:>8,.0f}")
        lines.append(f"  Verdict:                   {b['message']}")
        lines.append("")
        if self.gap_analysis.get("notes"):
            lines.append("POTENTIAL OVERLOOKED SPEND")
            lines.append("-" * 40)
            for note in self.gap_analysis["notes"]:
                lines.append(f"  • {note}")
            g = self.gap_analysis
            lines.append("")
            lines.append(f"  Potential missed refund:   \${g['potential_refund_gap']:>8,.0f}")
        lines.append("")
        lines.append("DISCLAIMER")
        lines.append("-" * 40)
        lines.append("  This is an estimate only. A registered tax agent or")
        lines.append("  R&D consultant should prepare the final application.")
        lines.append("  Refund amounts depend on ATO assessment of eligibility.")
        lines.append("")
        lines.append("=" * 60)
        lines.append("  Generated by rdtcalculator.com.au")
        lines.append("  [Barry Marshall — 1st4 Group]")
        lines.append("=" * 60)
        return "\n".join(lines)


def calculate(inputs: dict) -> dict:
    """Run calculation from a dict of inputs (API endpoint)."""
    calc = RDTCalculation(
        technical_staff_count=int(inputs.get("staff_count", 0)),
        avg_staff_salary=float(inputs.get("avg_salary", 0)),
        cloud_infra_spend=float(inputs.get("cloud_spend", 0)),
        contractor_spend=float(inputs.get("contractor_spend", 0)),
        consumables_spend=float(inputs.get("consumables_spend", 0)),
        software_licenses=float(inputs.get("licenses_spend", 0)),
        business_type=inputs.get("business_type", "software_development"),
        annual_turnover=float(inputs.get("turnover", 0)),
    )
    calc.calculate()
    return calc.to_dict()
