# Northwind Mobile: Runbook and Postmortem Index

Synthetic corpus (fictional operator, no real company data). 12 runbooks + 6 postmortems.

| id | title | type | summary |
|---|---|---|---|
| RB-001 | HLR/HSS Subscriber Attach and Authentication Failures | runbook | Location-update rejects and AuC queue saturation; restart peer or fail over to HSS pod B. |
| RB-002 | Nightly Billing Rating Batch Delayed or Stalled | runbook | Rating batch behind schedule for the 05:30 deadline; locks, bad tariff tables, resume from checkpoint. |
| RB-003 | SMS Gateway Message Queue Backlog and Delivery Degradation | runbook | Outbound queue over 50,000 or delivery under 92%; throttle campaigns, fail over aggregator. |
| RB-004 | CRM and Customer-Care Application Unresponsive Under High Load | runbook | Agent UI thread pool saturated with low CPU; recycle pool and scale to 6 nodes. |
| RB-005 | Payment Gateway Authorisation Failures and Acquirer Timeouts | runbook | Auth success under 96%; route to the secondary acquirer, recycle connection pool. |
| RB-006 | API Gateway Elevated 5xx Errors and Open Circuit Breakers | runbook | 5xx above 2% from open upstream breakers; probe, fail over region, rotate certificates. |
| RB-007 | Number Porting Requests Stuck Between Operators | runbook | Port-in stuck in PENDING_DONOR or rejected P14; resend, amend, manual routing. |
| RB-008 | SIM and eSIM Activation Provisioning Queue Stall | runbook | Activation queue oldest message over 8 minutes; quarantine poison message, drain lane. |
| RB-009 | Roaming Partner Signalling Failures and Late TAP Files | runbook | One visited network failing or TAP files over 36 hours late; link restart, GT update, steering exclusion. |
| RB-010 | Voicemail Deposit and Retrieval Failures | runbook | Deposit failures over 1.5% or storage over 85%; purge, restart node, check forwarding. |
| RB-011 | DNS Resolution Failures (Version 1) | runbook | SUPERSEDED by RB-012. Old resolver platform; kept for audit only. |
| RB-012 | DNS Resolution Failures (Version 2, Current) | runbook | Anycast resolver SERVFAIL over 1%; withdraw site, purge cache, lower TTL to 60 s. |
| PM-001 | Attach Storm After Regional Power Event | postmortem | HSS overwhelmed by synchronised re-attach; links RB-001. |
| PM-002 | Billing Batch Overran Into Business Hours | postmortem | Ad-hoc report lock slowed rating batch; links RB-002. |
| PM-003 | Payment Authorisation Failures During Acquirer Degradation | postmortem | Slow acquirer plus untested secondary route; links RB-005. |
| PM-004 | Expired Intermediate Certificate Broke API and SMS Traffic | postmortem | Chain certificate expired before leaf; links RB-006. |
| PM-005 | Database Replication Lag Slowed CRM Lookups | postmortem | Bulk job lagged replica, wrong alert metric; links RB-004. |
| PM-006 | eSIM Activation Backlog on Launch Weekend | postmortem | Poison message blocked ordered lane; links RB-008. |
