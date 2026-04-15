# Settlement Layer Advisory

Licensed RWA Compliance & Investor Onboarding
for Tokenized Asset Protocols.

---

## Directory

```
services/
  service_overview.md     — full service menu and pricing

outreach/
  linkedin_templates.md   — personalized outreach for Ondo,
                            Circle, Backed Finance, Fireblocks

legal/
  disclosures.md          — standard disclaimers and
                            methodology disclosures

funnel/
  intake_form_spec.md     — Tally.so form specification
                            (build before first outreach)
```

## Before First Outreach

1. Build the Tally intake form (spec: funnel/intake_form_spec.md)
2. Add the intake form link to services/service_overview.md
3. Review and personalize linkedin_templates.md with any
   new regulatory developments specific to each target
4. Run a field probe on the target entity before reaching out:

   python3 ~/Desktop/GENIUSFLOW_OS/workspace/geniusflow/run.py probe ONDO
   python3 ~/Desktop/GENIUSFLOW_OS/workspace/geniusflow/run.py probe CIRCLE

   Probe output is saved to ~/EIGENSTATE_ADVISORY/probes/
   Reference the current Φ_S reading in the outreach message.

## Field Probe Command

The probe command reads live regulatory pressure from the
Eigenstate engine without running a full observation cycle.

Output: Φ_S reading, settlement position, cascade neighbors,
ΔI this cycle, peer comparison, on-chain proof (Base mainnet).

Each probe saves to: ~/EIGENSTATE_ADVISORY/probes/
