# Doctor console

The physician-facing app for MediKiosk (SIH26047). React + Vite, no router,
no component library, no state manager — two runtime dependencies total.

## Run it

```bash
cd frontend-doctor
npm install
npm run dev
```

Opens on <http://localhost:5174>.

It runs entirely on fixtures, so it needs no backend and no API keys. To
point it at the real API once that exists, copy `.env.example` to `.env` and
set `VITE_USE_MOCKS=0`; `vite.config.js` already proxies `/api` to
`http://localhost:8000`. No component changes are needed — the fixture
shapes are identical to `shared/snapshot-contract.json`.

## What is here

| Screen | File | What it is |
|---|---|---|
| Home | `src/screens/Home.jsx` | Launcher. One dominant action, the flagged patient as a card, next in queue, due back |
| Queue | `src/screens/Queue.jsx` | Today's clinic. Priority band, intake state per row, throughput stats. Second tab is Due back |
| Encounter | `src/screens/Encounter.jsx` | The consultation. Four zones on one route |
| Patients | `src/screens/Patients.jsx` | Everyone on file. Search, filter, sort |
| Patient record | `src/screens/PatientDetail.jsx` | History, appointments, conditions |
| Settings | `src/screens/Settings.jsx` | Profile, practitioner view, modules, terminology |

The encounter screen is built to one constraint: **the doctor's eyes are on
it for about ten seconds before they must look at the patient.** Zone 1 never
scrolls. Everything else is one click away, not one navigation away.

## Two demo patients

Only `Rahul Verma` and `Anjali Deshmukh` have full snapshot fixtures.

That is deliberate — Rahul is Ayurveda OPD and Anjali is General Medicine, so
switching between them shows the Dashavidha panel appearing and disappearing
without a toggle, which is the framework-agnostic claim demonstrated rather
than asserted. The other four are selectable and land on a clear empty state.

## Conventions

- **No hardcoded colours.** Everything comes from `shared/tokens.css`. A hex
  value in a component is a bug — add the token instead.
- **No bare clinical strings.** Every clinical value carries `source` and
  `status` so click-to-source works at every field. See the contract.
- **Alerts are separate from content.** They arrive as their own top-level
  array because they come from deterministic rules, not the model.

## Known stubs

- `Edit summary` and consult templates are not built.
- The QR on the patient sheet is a drawn placeholder. It needs the ABHA
  deep-link endpoint and a QR library. **Do not demo it as scannable.**
- NAMASTE codes come from a public mirror, not the official portal — see
  `shared/terminology.json` before quoting any code.
