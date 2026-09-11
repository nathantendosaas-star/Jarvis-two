---
name: lead-research-kampala
description: Researches and identifies real business leads in Kampala/Greater Kampala (and wider Uganda on request) for ANY niche and ANY specified price point. Triggers whenever the user gives a niche/industry AND a target price for a product or service (e.g. "find roofing companies in Kampala willing to pay $2000 for a website", "find schools I can charge $1500 for social media management"). Does not dictate the niche — it is a general-purpose research method. Strictly gates every lead against evidenced ability-to-pay for the stated price; never substitutes smaller/cheaper businesses to pad the result count.
---

# Lead Research — Kampala

A general-purpose skill for finding real, contactable businesses/organizations in Kampala (and Greater Kampala — Wakiso, Mukono, Entebbe — unless the user narrows it further) that plausibly match BOTH a stated niche AND a stated price point for a product or service.

This skill has no opinion on what niche to search. The user supplies the niche. What this skill enforces is discipline: **the price point is a hard filter, not a target to be approximated.**

---

## 1. Required Inputs Before Starting

Do not begin researching until you have:

1. **Niche/industry** — whatever the user names (roofing companies, private schools, salons, clinics, law firms, whatever). No restriction on category.
2. **What's being sold** — the product/service and a one-line value proposition, so you can judge relevance of signals.
3. **Exact price point** — a number, with currency. This is the single most important input in the whole task.
4. **Area** (optional) — default to Greater Kampala metro if not specified.
5. **Number of leads wanted** (optional) — default to 10, but see Section 6: quantity is always subordinate to quality.

**If the price point is missing or vague ("a good amount," "whatever they can afford"), ask for it before doing anything else.** Every downstream filter in this skill depends on having a real number to check leads against. This is the one clarifying question worth stopping for.

---

## 2. Core Principle: The Price Point Is a Hard Filter

The most common failure mode for a skill like this is *quota-filling* — searching for the niche, finding 10-ish businesses that exist, and calling it done regardless of whether they can plausibly pay what was asked. That failure mode is explicitly banned here.

**Rules:**
- A lead only qualifies if there's real evidence it operates at or above the requested price tier (see Section 4).
- It is always better to return 4 well-evidenced leads than 10 padded ones.
- Never quietly downgrade the target (e.g., user asks for $2,000-capable roofing companies, you can't find enough, so you start including small roadside roofing vendors). If you can't find enough qualified leads, say so explicitly and report how many were rejected and why.
- Niche stereotypes are not evidence. Don't assume "it's a school, so it must be budget-constrained" or "it's real estate, so it must be wealthy." Check each business on its own signals.

---

## 3. Kampala Budget Tiers (Reference Anchors)

Use these as calibration anchors, not rigid boundaries. They exist so you have a consistent mental model of what different price points imply about the kind of business you should be looking for.

| Tier | USD | UGX (approx.) | Typical profile |
|---|---|---|---|
| Micro / street-level | Under $50 | Under 180,000 | Hawkers, single-person kiosks, boda riders, roadside vendors |
| Small local business | $50–$300 | 180,000–1.1M | Single-location shop/salon/restaurant, small tailor, one-branch service business |
| Established SME | $300–$1,500 | 1.1M–5.5M | Multi-staff, known local brand, storefront in a commercial zone, some paid promotion, several years operating |
| Mid-market | $1,500–$8,000 | 5.5M–29M | Multi-branch chains, corporate/NGO/expat-serving clients, import/export, private schools with real scale, mid-size clinics, 3-star+ hotels, active digital ad spend |
| Upper-market / institutional | $8,000+ | 29M+ | Large enterprises, franchise/multinational operations, banks/insurance/telecom-adjacent vendors, large hospital groups, big real estate developers, large NGOs/INGOs, 4–5 star hospitality, government-adjacent contractors |

**USD vs. UGX signal — treat this as a real filter, not just a currency conversion:**
If the user's price point is quoted in USD, that's a signal about *who* the buyer should be, not just *how much*. A business that only transacts in UGX cash retail may have an equivalent shilling amount that "fits," but pitching it in USD is a mismatch — it reads as out of touch with how that business thinks about value, and tanks close probability. Favor businesses that already have a reason to think in USD: tourism/hospitality serving foreigners, export/import trade, NGOs/INGOs, forex bureaus, real estate targeting diaspora or expats, professional firms (law, audit, consulting) with international clients, businesses that invoice abroad. If the user's price is in UGX, this constraint relaxes — normal local SMEs are fair game at the appropriate tier.

---

## 4. Capacity Evidence — What Actually Counts as Proof

This is the core of the strictness requirement. Do not qualify a lead for a tier based on a single plausible-sounding signal or a vibe about the neighborhood. **Require at least 3 independent, corroborating signals pointing at or above the target tier before marking a lead "Qualified."** Fewer than 3, or signals that conflict with each other, means the lead gets marked **"Unverified — needs manual check,"** not silently included and not silently dropped.

**Physical / location signals**
- Location tier (Kololo, Nakasero, Bugolobi, Muyenga tend to skew higher; Kikuubo/downtown wholesale is cash-heavy but variable; industrial area indicates manufacturing scale; outskirts generally lower) — one signal among several, never sufficient alone, don't stereotype
- Number of branches/locations
- Quality of premises — signage, storefront condition, parking, visible security
- Staff count (job listings, visible team size, LinkedIn presence)

**Digital / behavioral signals**
- Active paid advertising (running Facebook/Instagram/Google ads — a strong, checkable signal of existing marketing spend)
- Existing professional website or brand identity (signals prior spend on similar services)
- Job postings requiring paid tools/software (e.g. "must know Salesforce/HubSpot" implies budget)
- Social media following *and* engagement quality/posting consistency (raw follower count alone is weak — check if it's actually active)
- Volume and recency of Google reviews (proxy for transaction volume)

**Financial / structural signals**
- Registered company (URSB-registered, VAT-registered businesses skew larger)
- Franchise or multinational affiliation
- Clientele type — B2B, corporate, NGO, expat, or government-facing tends to mean higher budget than pure walk-in retail
- Import/export activity or forex dealings
- Funding, investment, or expansion news
- Membership in trade associations or chambers of commerce (PSFU, Uganda Manufacturers Association, private schools associations, etc.)
- Years in operation / establishment age (Facebook page creation date, Google listing "since" date)
- Active hiring (growth signal = spending capacity)

---

## 5. Search Execution

1. Use `places_search` for physical business discovery in the specified area(s) — pull multiple queries covering the niche plus adjacent terms, and note ratings/review counts/addresses returned.
2. Use `web_search` to find association listings, directories, news mentions, and social presence not covered by Places data.
3. Use `web_fetch` on each candidate's actual website or social page directly — don't infer capacity from a search snippet alone when you can check the source.
4. Cross-reference: a strong lead usually shows up in more than one of the above. If a business only appears once and you can't verify it independently, that itself is a data point toward "Unverified."
5. Do not stop at the first batch that "sounds right" — actively look for disconfirming evidence too (e.g., a defunct-looking Facebook page, no reviews in 2+ years) before finalizing a tier assignment.

---

## 6. Scoring and Gating

For each candidate:

1. **Budget-fit gate first.** Assign: Qualified / Unverified / Rejected (below tier). Rejected leads are dropped from the deliverable list but counted in the summary — never silently omitted without explanation.
2. Only Qualified and Unverified leads proceed to scoring.
3. **Niche fit** (1–10): how squarely does this business match the requested niche, not an adjacent category.
4. **Reachability** (1–10): can you actually find a real phone number, WhatsApp, email, or social handle to contact them through?
5. Overall priority ranking = budget-fit confidence first, then niche fit, then reachability. Do not let a high niche-fit score compensate for a weak budget-fit gate.

---

## 7. Output Format

**Summary block first:**
- Niche + price point + area as understood
- Total candidates researched
- Qualified count
- Unverified (needs manual check) count
- Rejected-for-budget count (this transparency is mandatory — it's the proof the filter was actually applied)

**Per lead:**
```
## [Business Name]
Area: [neighborhood/location]
Niche match: [confirmed / notes if partial]
Budget tier assigned: [tier] — Confidence: Qualified / Unverified
Price-point verdict: [why this business plausibly can/cannot pay the requested price]

Evidence (tag each signal by type):
- [Physical] ...
- [Digital] ...
- [Financial/structural] ...

Contact info found:
- Phone: [...]
- WhatsApp: [...]
- Email: [...]
- Social: [...]
(mark any as "not found" rather than guessing)

Decision maker to target: [role — realistic for a business this size]
Suggested first-touch approach: [in-person visit / WhatsApp / call / social DM — matched to how this business actually operates, not a generic cold-email default]
```

---

## 8. Never Do This

- Never swap in lower-budget businesses just to hit the requested lead count.
- Never treat a neighborhood, business category, or "it looks nice" as sufficient proof of budget on its own.
- Never present an unverifiable lead as confidently qualified — flag it.
- Never invent phone numbers, emails, or social handles. "Not found" is a valid, honest answer.
- Never let niche stereotypes override actual evidence in either direction.

---

## 9. Handoff

Treat this skill's output as a **draft list**, not a finished CRM-ready result. Every lead produced here should be run through the `lead-reviewer-kampala` skill before anything gets added to the CRM.
