# Corpus design notes (not indexed; used to write eval questions)

## Unique facts per doc (escalation = L2 / next level)
| id | team | threshold | escalation | key commands |
|---|---|---|---|---|
| RB-001 | Core Signalling | reject >4.5% for 10 min; AuC queue >2,000 | 15 / 40 min | hlrctl show subscriber, hsscfg restart-peer, hsscfg failover --target pod-b |
| RB-002 | Revenue Assurance | <70% by 03:00; deadline 05:30 | 30 min Billing Ops L3 / 60 min Finance | billctl batch resume --from-checkpoint |
| RB-003 | Messaging Platform | queue >50,000; delivery <92% | 10 / 25 min | smsgwctl rate set --mps 400, route failover |
| RB-004 | Care Apps | threads >190/200 for 5 min | 20 / 45 min | crmadm pool recycle, scale to 6 nodes |
| RB-005 | Payments Engineering | success <96% over 5 min; acquirer >3 s | 10 / 30 min | paygwctl route set --acquirer secondary |
| RB-006 | Platform Edge | 5xx >2% over 3 min | 15 / 35 min | gwctl breaker show, upstream failover to eu-west-b |
| RB-007 | Porting Ops | PENDING_DONOR >4 business hours; 2 working-day limit | 60 min / 4 h | portctl request resend (once only) |
| RB-008 | Provisioning | oldest msg >8 min | 12 / 50 min | provctl queue quarantine, drain --concurrency 5 |
| RB-009 | Roaming Partnerships | attach <85% / 30 min; TAP >36 h | 30 min / 2 h | roamctl partner status, sor exclude |
| RB-010 | Value Added Services | deposit failures >1.5%; storage >85% | 20 / 90 min | vmctl purge |
| RB-011 | Network Services | (superseded) TTL 300 s | 30 min / 2 h | dnsctl flush --zone |
| RB-012 | Network Services | SERVFAIL >1% / 5 min; TTL 60 s during incident | 10 / 30 min | dnsctl site withdraw, cache purge |

## Traps
- Different words for symptoms: "application unresponsive under high load" (RB-004), "provisioning queue stalls" (RB-008), "attach/location-update rejects" (RB-001).
- Overlap: RB-004 vs RB-006 (slow under load; thread pool vs upstream breaker). PM-005 links both.
- Superseded: RB-011 -> RB-012 (TTL 300 vs 60/900, timers 30 vs 10 min, flush vs site withdraw).
- Postmortem-only lessons: PM-001 radio-restart storm and admission control; PM-002 notify Finance at 04:30; PM-003 weekly synthetic test of secondary acquirer; PM-004 `gwctl cert chain --check` and chain expiry; PM-005 replica lag alert metric, check lag before recycling pools; PM-006 launch-day load test, quarantine first.
- No runbook for certificate expiry or replication lag; only postmortems cover them.
