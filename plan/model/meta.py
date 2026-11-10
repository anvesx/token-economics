# Group blurbs and cross-cutting pages. Plain text, house style.
GT = {
 'edge':('Every request passes this gateway. It resolves who is calling, copies the stream and applies the failure mode.','A front desk that every request walks past. It notes who you are and what you took, then lets you through.'),
 'adapt':('One adapter per harness, each with eight capability flags. Missing flags downgrade control to observation.','One translator per tool. Each says what it can and cannot be told to do.'),
 'sig':('Hooks, OpenTelemetry and transcripts add detail. They are never the enforcement path.','Extra notes the tools send about themselves. Useful, but a developer can switch them off.'),
 'api':('Provider connectors that speak each vendor API and report usage in one normalised shape.','One plug per vendor, all returning the same kind of receipt.'),
 'cli':('CLI agents run headless as backends with budget, turn and schema flags.','Command-line agents that Token Economics starts and watches, with limits set on the command.'),
 'health':('Model catalogue, rate-limit tracking and a priced fallback chain.','A list of what exists, what is blocked right now, and what to try next.'),
 'price':('Append-only price rows with a lifecycle, plus a separate plan-units table.','The price list, never edited in place, only added to.'),
 'meter':('Raw usage becomes five exclusive token buckets, then one cost row per provider response.','Turns a vendor receipt into one clean line in the ledger.'),
 'recon':('Estimated cost is checked against invoices weekly, and plan quota is tracked in native units.','A weekly check of our sums against the real bill.'),
 'bud':('Virtual-key budgets with a worst-case reservation before dispatch and a true-up after.','A hold on the card before the purchase, then the final charge.'),
 'run':('Turn cap, loop guard, session stickiness and switch pricing keep a run from burning money.','Stops an agent from going in circles or changing model at a bad moment.'),
 'route':('Rules first, a static router second, cascade only with measured acceptance.','Picks the model for each request, cheapest first, with a safe default.'),
 'tier':('Cache planner, tier selector and cache-hit monitor.','Chooses how long to cache and which price tier to buy.'),
 'ctx':('Eight controls on what enters the prompt.','Keeps the prompt small without losing the facts the agent needs.'),
 'store':('Metadata-only store, spend attribution and the content-logging policy.','Where usage facts live, with no prompt text kept.'),
 'view':('Dashboards and one flagged anomaly detector.','Charts and alerts for people.'),
 'eval':('Eval harness, private task set, paired statistics and cost per successful task.','Tests whether a saving cost any quality.'),
 'roll':('Shadow runs, canaries, kill-switches and rollback triggers.','Ways to try a change safely and undo it fast.'),
 'admin':('Admin API, versioned policy, tenant keys and audit log.','Where operators change settings, with a record of every change.'),
 'sec':('Secrets vault, admin authorisation and retention rules.','Locks, roles and expiry dates.'),
}
STAGE_CHIP = {}
XC = [
 {'id':'security','title':'Security','blurb':'Keys, fail-closed budgets, metadata-only logs.','intro':'The gateway holds real credentials, so it is the highest-value target in the system. Controls below apply to every stage.',
  'sections':[
   {'h':'Rules','rows':['Enforce budgets at the gateway. A client hook can be disabled, so it never carries enforcement (research note R4, adapter rules).','Fail closed for budget decisions and open for observation. A dead metering path must not block work, a dead budget path must not allow spend.','Log metadata only. Prompt and tool content logging stays off unless a tenant opts in (OTEL_LOG_* flags).','Never store OAuth tokens. Forward the auth header and the anthropic-beta header unchanged.','Provider keys live in the vault and are fetched at call time. Project-local Codex config ignores provider keys, so keys go in user config.','Reject usage objects with unknown extra keys, so a spoofed upstream cannot inject fields.','Cap the strong-model share per tenant to blunt router attacks.','Every policy, budget and key change writes an audit row before it applies.']},
   {'h':'Still open','rows':['Claude Code behaviour on an HTTP 402 is not in the corpus. Test it before relying on 402 for hard caps.','Soft-budget overshoot size is not in the corpus. Pick a margin in the shadow phase.']}]},
 {'id':'reliability','title':'Reliability','blurb':'Failure modes, fallback, kill-switch.','intro':'Reliability here means the gateway never becomes the reason a developer cannot work, and never lets spend run unmetered.',
  'sections':[
   {'h':'Failure behaviour','kind':'table','cols':['Failure','Observation path','Budget path'],'rows':[
    ['Ledger write fails','Fail open, queue and retry','Fail closed after the hold expires'],
    ['Price row stale','Estimate flagged low confidence','Billing decisions blocked'],
    ['Provider 429','Priced fallback hop','Priced fallback hop'],
    ['Policy bundle unreadable','Keep last good bundle','Keep last good bundle, deny if none'],
    ['Router unavailable','Use best-single baseline','Use best-single baseline'],
    ['Kill-switch flipped','Optimisations off, default path','Budgets stay on']]},
   {'h':'Not in corpus','rows':['Disaster-recovery targets, multi-region design and gateway latency budgets. Each is a DevX proposal to be set in phase P3.']}]},
 {'id':'performance','title':'Performance','blurb':'Where latency can come from.','intro':'The corpus has no gateway latency measurements. Targets below are DevX proposals to be measured in phase P0.',
  'sections':[
   {'h':'Latency budget (DevX proposal)','kind':'table','cols':['Step','Target','Note'],'rows':[
    ['Key resolve and policy read','under 5 ms','In-memory, refreshed from the signed bundle'],
    ['Reservation','under 10 ms','Single atomic counter'],
    ['Stream tee','0 ms added','Copy, never buffer the stream'],
    ['Ledger write','Async','Off the request path']]},
   {'h':'Rules','rows':['Never buffer a streaming response before forwarding it.','Keep the cache key stable per session. A change in tool set or model invalidates the cache.','Cap about 15 requests per minute per prefix on OpenAI to keep cache routing stable.']}]},
 {'id':'cost','title':'Cost','blurb':'Where Token Economics saves money, and what it costs.','intro':'Every lever is gated by the eval harness. Savings ranges are vendor or author claims in the corpus, not Token Economics results.',
  'sections':[
   {'h':'Levers in ship order','kind':'table','cols':['Lever','Phase','Evidence status'],'rows':[
    ['Per-key hard budgets, turn caps, loop guard','P1','Sourced; 51 percent of spend falls after the first repeated failure (research note R2)'],
    ['Cache planner and stickiness','P2','Sourced; blanket 1h TTL made one bill 8.6 percent worse'],
    ['Context guard','P2','Sourced; output compressors flip sign by harness, so off by default'],
    ['Static router','P2','Sourced; savings range from ties to 53 percent, measure first'],
    ['Cascade, bandits','P3 or later','Only with measured acceptance']]},
   {'h':'Cost of Token Economics itself','rows':['Charge the optimisation overhead to the task when measuring cost per successful task.','Probe-based prediction adds one probe call plus a 1.9x multiplier.']}]},
 {'id':'quality','title':'Quality','blurb':'How we know a saving did not hurt.','intro':'A cheaper run that fails more often is not a saving. The headline metric is cost per successful task, failures included.',
  'sections':[
   {'h':'Rules','rows':['Declare the success non-inferiority bound before the test.','Use paired, task-clustered bootstrap intervals.','Isolate cache state per arm.','Keep a private eval set with hard cases plus a Lite subset (80 tasks tracked 350 within 0.81 percentage points).','Report median and P95 per user.','Track failed-run waste share (baseline 32 percent), spend after first repeated failure (51 percent), geometric SD (x1.34), probe error and reconciliation ratio.']}]},
 {'id':'limits','title':'What this plan does not know','blurb':'Evidence limits, stated up front.','intro':'The plan rests on a research set that was summarised by models. Read these limits before trusting any number.',
  'sections':[
   {'h':'Evidence','rows':['All 423 sources and 411 notes are model-written. Six agents extracted the requirements from notes plus corpus text. The plan does not rest on a first-hand read of every paper.','Codex stopped early and contributed none of the notes used.','Many figures are vendor or author claims. Model names such as Fable 5.1 are quoted as the corpus gives them and some cannot be checked.']},
   {'h':'Not in corpus','rows':['Measured cache loss on a model switch.','Claude Code behaviour on HTTP 402.','Soft-budget overshoot size.','A measured subagent multiplier. The 7x agent-team figure is quoted, not measured.','Production shadow results.','Power formulas, anomaly detection method and reconciliation tolerance.','Default GPU utilisation for self-hosting.']},
   {'h':'Unresolved conflicts, labelled DevX proposal','rows':['Gemini cache discount 75 percent against 90 percent, and minimum prefix sizes: take the larger until tested.','Auto-compact thresholds: 50 percent, about 90 percent, or window minus 33k.','MCP schema size 8k to 55k.','Budget visibility: some sources say it helps, one says agents ignore it. Enforce outside the agent.','Error-price break-even $0.01 against $0.20.','Together H100 $3 against $5.49 per hour.','Batch plus cache stacking differs by vendor, so it is a price-book flag.']}]},
]
