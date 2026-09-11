# external-dashboard fixture

A shape (b) app (external product, ikas is one integration) written the way the R1–R4 rejections describe:

| Defect | File | Rejection | Rule |
|---|---|---|---|
| Root page never calls `closeLoader()`, bounces to the external login — panel spinner forever | `src/app/page.tsx` | R2, R3 | §3.1, §10 #4 |
| No in-iframe link/instruction, no "installed" screen | `src/app/page.tsx` | R2, R3 | §4 (b), §10 #12 |
| Callback requires `state` + an app session; otherwise `error=missing_code` / "install link has expired" | `src/app/api/oauth/callback/ikas/route.ts` | R1, R4 | §2.2, §10 #20 |
| Token parked in the browser session, tenant linked by hand later; ikas token in a cookie | same | R3 | §2.2 auto-bind, §10 #21, §2.3 |
| Inherited from the starter: `Math.random` state, unnormalized deploy URL, unused scopes | various | — | Uyarı |

Expected: at least four Blockers (§2.2 state, §2.3 token in cookie, §3.1 spinner, §4 (b) no link) and the §4 (b) test-account Beyan row.
