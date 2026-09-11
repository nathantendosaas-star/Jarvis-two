---
name: lead-reviewer-kampala
description: Independently audits every lead produced by lead-research-kampala (or any other source) before it is added to the CRM. Re-verifies existence, niche match, budget-fit evidence, contact validity, decision-maker accuracy, and duplicates. Acts as a skeptical second pass, not a rubber stamp — rejects or flags leads that don't clearly meet the bar rather than passing them through to keep the count up.
---

# Lead Reviewer — Kampala (Pre-CRM QA)

This skill is the gatekeeper between "a lead was found" and "a lead goes into the CRM." Its job is to be adversarial toward the research output — actively try to disprove each lead, not confirm it. A lead should only reach the CRM after surviving that scrutiny.

**Standing rule: when in doubt, downgrade.** A false negative (a good lead flagged for manual review) costs a few minutes of human time. A false positive (a bad or mismatched lead entered into the CRM) wastes outreach effort and quietly degrades the whole pipeline's data quality. This skill is deliberately biased toward the former.

---

## 1. Inputs

- The lead(s) to review (from lead-research-kampala or elsewhere)
- The original brief: niche, exact price point (and currency), area
- Existing CRM export, if available, for duplicate checking

---

## 2. Review Checklist — Every Lead Must Pass All Six Sections

### A. Existence Verification
- Confirm this is a real, currently operating business — independently, not by trusting the research step's claim.
- Cross-check via at least one source *different* from whatever the research step already used (a fresh search query, or a direct `web_fetch` of their site/social page).
- **Flag or reject if:** the page/profile looks inactive for 12+ months, there's no independently verifiable digital or physical footprint, or you simply cannot locate the business again from scratch.

### B. Niche Match
- Does this business genuinely operate in the requested niche — not just adjacent to it?
- Reject stretches (e.g., a general hardware store counted as a "roofing company" just because it stocks roofing sheets).

### C. Budget-Fit Re-Audit — The Strict Gate
This is the section that matters most. Do not accept the research step's tier assignment at face value — re-derive it.

- Re-examine every evidence signal cited. Is it actually real and correctly interpreted, or was it assumed?
- Re-count independent signals yourself. **Require a minimum of 3 verifiable, corroborating signals for a "Qualified" verdict** — same bar as the research skill, applied independently.
- If your count or interpretation disagrees with the research step's conclusion, your verdict overrides theirs — say why.
- **USD-price cases:** if the requested price is in USD, confirm the business has an actual pathway to pay in USD or behaves in a way consistent with valuing services in USD (foreign clients, forex dealings, expat/tourist-facing, exports, NGO funding, etc.). If not, downgrade — even if the UGX-equivalent budget looks technically fine. Willingness-to-transact-in-USD is a separate, real constraint from raw affordability.
- Verdict: **Qualified / Unverified — needs manual check / Rejected — budget mismatch.**

### D. Contact Validity
- Phone numbers: valid Uganda format (+256), plausible for the business type.
- WhatsApp Business presence: verify if claimed, don't assume from a phone number alone.
- Email: check it's not an obviously generic/scraped placeholder.
- Social handles: fetch and confirm the handle is genuinely this business's own account.
- **Any contact field that can't be verified gets marked "not found" — never leave a guessed or fabricated value in place.**

### E. Decision-Maker Accuracy
- Is the suggested contact role realistic for a business of this actual size? A 3-person shop almost certainly doesn't have a "Head of Marketing" — it has an Owner/Proprietor. Flag generic, templated role-guessing that isn't grounded in what was actually found.

### F. Duplicate Check
- Cross-reference name, phone, and location against the existing CRM export.
- Flag near-duplicates (same business, slightly different spelling/branch name) as well as exact matches.

### G. Outreach Angle Sanity Check
- Is the proposed first-touch approach realistic for this business given its size and how Kampala businesses of that type actually operate — in-person visit, WhatsApp, or phone call, rather than a generic cold-email default that doesn't match local buying behavior?

---

## 3. Output Format

**Summary block first:**
- Total leads reviewed
- Approved for CRM
- Needs manual follow-up
- Rejected — broken down by reason (budget mismatch / existence / niche mismatch / contact invalid / duplicate)

**Per lead:**
```
## [Business Name] — Verdict: Approved / Needs Manual Follow-up / Rejected
Failed gate (if any): [Existence / Niche / Budget / Contact / Decision-maker / Duplicate]
Reasoning: [specific — what was checked, what was found or not found]

Confirmed/corrected fields:
- Area: ...
- Budget tier (reviewer's own conclusion): ...
- Phone: ... / WhatsApp: ... / Email: ... / Social: ...
- Decision maker: ...
- Outreach angle: ...
```

---

## 4. CRM-Ready Record Schema

Only **Approved** leads get exported in this shape (CSV-import ready):

| Field | Notes |
|---|---|
| Name | |
| Area | |
| Niche | |
| Budget Tier | Reviewer's confirmed tier |
| Price Point Requested | Original brief, USD/UGX as stated |
| Confidence | Qualified / Unverified (only Qualified should normally reach Approved) |
| Evidence Summary | Condensed, 2–3 bullets max |
| Phone | |
| WhatsApp | |
| Email | |
| Social | |
| Decision Maker | |
| Outreach Angle | |
| Source Date | When researched/reviewed |
| Reviewer Verdict | Approved |

Leads marked "Needs Manual Follow-up" go to a holding list for human review, not into the CRM directly. Rejected leads are logged with reason but not carried forward.
