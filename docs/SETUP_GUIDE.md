# Your step-by-step RiskGraph setup

You do not need to use Mila. Codex can build and test the code here. Anthropic runs the AI model; Render will run the small website/API.

Participant progress, October 18: source is published at [farzana0/riskgraph](https://github.com/farzana0/riskgraph), GitHub's automated checks passed, and [RiskGraph is live on Render](https://riskgraph-fa98.onrender.com). The deployed app detects both provider configurations and requires operator access. The next step is to enter the generated operator token privately in the app and run small real integration checks. Real provider calls, hosted memory read/write, and restart persistence are still pending. Render's GitHub connection is sufficient for deployment; connecting Render to this chat is optional.

Do one step at a time. You do not need to create every account today.

## Step 1 — Make the GitHub repository

1. Open [GitHub](https://github.com/) and sign in or create your account.
2. Choose **New repository** (also available at [github.com/new](https://github.com/new)).
3. Repository name: **riskgraph**.
4. Description: **Risk and safety monitoring for AI refund agents, with uncertainty estimates for small samples.**
5. Choose **Public**. The hackathon requires a public code repository.
6. Leave “Add a README”, “Add .gitignore”, and the license selector unset: the prepared project already contains its README and ignore rules. You can decide a license later.
7. Choose **Create repository**.
8. Copy the repository's ordinary web address, such as `https://github.com/YOUR-NAME/riskgraph`, and send it to Codex. This is not a secret.

**Stop here for the first session.** Codex can help with the upload once this repository exists. There is no need to write the code yourself. Do not upload the project ZIP as one file: Render needs the extracted source files. The repository root must contain `README.md`, `render.yaml`, `requirements.txt`, `app/`, `tests/`, and `docs/`.

## Step 2 — Check Anthropic credits before October 21

1. Sign in to [Claude Console](https://platform.claude.com/).
2. Open your organisation's billing/credits view. Confirm the $100 credit was actually applied and note the exact expiry shown there. October 21 is participant-provided, not independently verified from the console.
3. If credits fail, the supplied Discord announcements report a known activation issue. Do not assume it is an app bug.
4. Configure an API key privately in the app's server environment when Codex walks you through it. Do not paste the key into chat, GitHub, screenshots, or Devpost.
5. We will run a small Claude evaluation first, inspect the evidence and usage, then run the held-out evaluation. Aim to finish by October 20 to avoid an unknown October 21 cutoff time.

There is no need to spend all $100. Save useful evaluation evidence while the credits are available. The app stores input/output token counts and limits attempted API calls.

## Step 3 — Set up Render to put it online

1. Create/sign in to [Render](https://dashboard.render.com/), ideally using GitHub.
2. Redeem the $50 through the [official Build North Render credit form](https://credits-portal-mmdm.onrender.com/claim/build-north-georgian). Confirm the credit appears before enabling paid hosting.
3. From the dashboard create a **Blueprint**, connect your GitHub `riskgraph` repository, and use `render.yaml` at the root.
4. Review the displayed costs. The configuration uses one small paid Python web service and a 1 GB persistent disk. Credits do not automatically mean spending is capped or the service becomes free forever.
5. The provider secret fields are optional for the offline demo; leave all three SurrealDB values empty until connecting it. Add the Anthropic key privately in Render when ready.
6. Create the service. Wait for deployment success and copy the actual Render app URL.
7. In the service's Environment page, find `RISKGRAPH_ADMIN_TOKEN` and copy its full value. Enter that value in the app's **Connections → Operator access** field and click **Verify operator access**. Continue when the app confirms access is verified. If you changed the value in Render, save and deploy that environment change before using it. Never publish the token.
8. Check that the initial synthetic dashboard loads, a new evaluation completes, a blocked action opens, evidence downloads, and data remains after a service restart.

Codex can guide each screen. Account creation, credit redemption, and any billing agreement stay under your control.

## Step 4 — Add SurrealDB Agent Memory

1. Sign in/create your account at [SurrealDB Studio](https://studio.surrealdb.com/).
2. Redeem **BUILDNORTH50**, the $50 Agent Memory credit listed on the hackathon resources page. Verify the balance and access to **Contexts**.
3. Create an **Agent Memory Context**, not just a generic database instance. If access is unavailable, use the sponsor office hours or resource pack for help.
4. Register a scope such as `org/riskgraph/demo`. Create a key with only the read/write grants needed for that scope. Follow the official [hosted quickstart](https://surrealdb.com/docs/agent-memory/quickstarts/hosted).
5. In Render set `SURREAL_MEMORY_URL` (the HTTPS Context host), `SURREAL_MEMORY_CONTEXT`, `SURREAL_MEMORY_API_KEY`, and `SURREAL_MEMORY_SCOPE`. Enter the actual values privately; Codex does not need them in chat.
6. Redeploy/restart. Run one evaluation with memory off and another with memory on. Inspect the decision trace for successful recall and remembered incidents.
7. Save the actual `recall_trace_id` and `turn_id` evidence. Demonstrate prior incidents being retrieved into later agent decisions. Do not claim the SurrealDB prize integration from the local fallback alone.

The public sponsor resource pack returned a 404 during verification. Official Agent Memory documentation was available; account-specific entitlement still needs confirmation.

## Step 5 — Prepare Devpost

1. Sign in to [Build North on Devpost](https://build-north.devpost.com/) and join the hackathon if you have not already.
2. Start a project called **RiskGraph**.
3. Tagline: **Know the cost of an AI agent's mistakes before they happen.**
4. Add your actual public GitHub URL and successful Render live URL.
5. Use `docs/DEVPOST_DRAFT.md` as a draft, revising sponsor and result claims after live tests.
6. Add all team members (maximum four) and disclose AI tools/prior work.
7. Optional: record a video of at most four minutes, without a login requirement. Suggested walkthrough is in the draft.
8. Submit by **October 25, 2026, 11:59 p.m. Toronto time**. Do not wait for the header's October 26 midnight wording.

The detailed rules require Canadian residence and age 18+. The overview's generic eligibility summary is broader; use the specific rules and ask the organisers if uncertain. Top-ten demo attendance requires at least one team member in Toronto on October 29.

## Optional — Eon Era

Era can provide a realistic simulated company and agent benchmarking. It is a separate optional integration; this version does not claim it. Once access is granted, follow the organiser's setup guide and adapt actual exported cases with explicit ground-truth labels and a declared loss cap. Do not invent an Era API or count local scenarios as Era usage.

## What to send Codex next

Only the public GitHub repository URL. Later, send the public Render URL and describe which setup screen you are on. Keep keys and operator tokens out of chat.
