# Telecom IT Change Management Policy (synthetic)

Synthetic policy for learning purposes. All values are invented.

## 1. Change types
- **Standard change**: pre-approved, repeatable, low-risk and fully documented (for example a routine SIM provisioning template refresh or a scheduled certificate renewal). It needs no CAB review. Raise it from the approved standard-change catalogue.
- **Normal change**: anything not in the catalogue. It needs a full change request (CR), a risk assessment and CAB approval before implementation.
- **Emergency change**: only for something that is broken right now, meaning an active outage or incident (for example a P1/P2) that needs a fix immediately. See section 4.
- **Choosing a type**: if it is in the catalogue, use Standard. If it is planned work, use Normal. Use Emergency only when a live incident requires the change. Business urgency or deadline pressure is never a reason for an emergency change.

## 2. Lead times and maintenance windows
- A normal change must be submitted at least **5 working days** before implementation. Changes to the core network (packet core, IMS, HLR/HSS) need **7 working days**.
- Standard changes need 1 working day of notice.
- Maintenance windows are **Tuesday and Thursday, 00:00-04:00** for core network and **Monday to Friday, 00:00-05:00** for other systems. Weekend windows are allowed for normal changes that meet lead time and have service-owner agreement.
- A change raised the same day cannot enter that night's window as a normal change.
- A **late or expedited normal change** (the work is ready late, or the business wants it sooner) is still a normal change. Ask the CAB chair for expedited review. It is not an emergency, and it needs a documented reason and the usual approvals.
- To avoid emergency handling, submit a normal change by the lead time above.

## 3. CAB schedule and approvers
- The Change Advisory Board (CAB) meets **every Wednesday at 10:00**. There is no CAB meeting on Saturday or Sunday.
- The agenda cutoff is **Monday 12:00**. A CR submitted after the cutoff goes to the following week's CAB, unless the CAB chair accepts it for expedited review.
- Every normal change needs CAB approval. Standard changes do not. Low-risk normal changes may be approved by the CAB chair between meetings.
- Before CAB, a change needs sign-off from the **technical owner** and the **service owner**. The **CAB chair** gives the final approval.
- Approvers reject any change without test evidence. Untested code must not go to production.

## 4. Emergency changes
- An emergency change is allowed **only while an active outage or incident is in progress**. Urgency, deadlines, executive requests or a wish to avoid lead times do not qualify.
- Raise it in the CR tool as type Emergency and link the incident number. Phone the on-call duty manager.
- Approval comes from the **Emergency CAB (ECAB)**: the on-call duty manager plus one service owner. If the usual approvers cannot be reached, the on-call duty manager alone may approve out of hours and must record the reason.
- A backout plan is still required, even if brief.
- A retrospective review is held within **2 working days**.

## 5. Freezes and blackouts
- **Quarter-end freeze**: the last 5 working days of each quarter, covering billing, charging and customer-facing systems.
- **Holiday blackout**: **20 December to 3 January**, covering all production systems, including RAN software upgrades.
- During a freeze or blackout only emergency changes (active incident) are allowed, approved by ECAB. A non-emergency exception needs written approval from the VP of Technology, submitted at least 3 working days ahead.
- A billing defect found during a freeze that is not causing an active outage waits until the freeze ends, or goes through the VP exception route.

## 6. Rollback and backout plans
- Every normal and emergency change must include a backout plan before approval. Standard changes use the backout plan built into their catalogue entry.
- A backout plan states: the trigger (what failure makes us roll back), the steps, the owner, the time needed, and how success is verified. It must have been tested in pre-production where possible.
- **Rollback or fix forward**: roll back if the change has not passed the point of no return, or if a fix cannot be completed in the time left in the window. Fix forward only if the fix is known, tested and fits inside the window. If unsure, roll back.
- The decision is made by the change implementer with the service owner and logged on the CR.

## 7. CR forms and mandatory fields
- The latest CR template is in the Change Management portal under **Templates > Change Request**.
- **Mandatory fields**: summary, change type, affected service and CI, risk and impact, implementation plan, **backout plan**, test evidence, planned start and end (window), technical owner and service owner. A CR with a blank mandatory field is returned automatically.
- Backout instructions go in the **Backout Plan** field on the CR form, on the Plan tab.
- If a change fails validation or is abandoned, do not raise a new CR. Open the original CR, set the status to **Failed**, add closure notes describing what failed, and link any incident.
