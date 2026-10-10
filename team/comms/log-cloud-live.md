# Cloud live checks (2026-10-10, 23:15 to 23:35 UTC)

- Network: staging-app.freyavoice.ai, freya-bank-mock.freyavoice.workers.dev and trycloudflare.com had to be allowed in the cloud environment; the first two work now.
- PUB-05 re-sim on A+B (agent a5956e85, workflow prep-gen-ab, 1 call): ends with close_call; the only failed check is the hardship note, expected under Brief B rule 8.
- Brief D: build ok in 106 s (new slot brief-d, workflow cbf958f4-5d8e-4ac8-b732-003878c82ac9; the cloud checkout has no .freya-agents.json so a new workflow was created). Trace: traces/cloud-d.log, no keys in it.
- Brief D live sim SKIPPED (Kutay, 23:31): cloudflared cannot open a tunnel from the cloud container (egress is HTTPS through a proxy only). Needs a hosted tunnel service or the PC.
- Workspace holds about 14 workflows; nothing deleted.
