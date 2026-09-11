# broken-app fixture

`starter-app` from ikascom/ikas-app-examples with defects injected on purpose. Every injected defect maps to a rule in
`references/app-review.md` and, where one exists, a recipe in `references/fix-catalogue.md`. Used by `tests/run.sh`.

| Defect | File | Rule | Recipe |
|---|---|---|---|
| Unsigned uninstall webhook, deletes token, 200 from catch, no `deleted` short-circuit | `src/app/api/webhooks/ikas/route.ts` | §6.1, §6.2, §10 #2 #3 | F1, F11 |
| Unsigned payment webhook grants on any status | `src/app/api/webhooks/payment/route.ts` | §6.1, §6.4 | F1, F13 |
| API action without signature | `src/app/api/actions/order-detail/route.ts` | §7.2 | F1 |
| Iframe action page: no `closeLoader`, `useSearchParams` outside `<Suspense>` | `src/app/actions/order-list/page.tsx` | §3.1, §3.3, §10 #4 #14 | F2, F8 |
| Admin route with no JWT, `authorizedAppId` from query | `src/app/api/ikas/list-products/route.ts` | §5.1 | — (action list) |
| Shared wrapper checks only `!authToken` | `src/lib/with-merchant.ts` | §5.1 | F14 |
| `NEXT_PUBLIC_SECRET_COOKIE_PASSWORD` | `src/globals/config.ts`, `.env.example` | §8 | F7 |
| Client component calls the Admin API | `src/components/home-page/direct-call.tsx` | §5.2, §10 #18 | — (action list) |
| `console.log(access_token)` server-side | `src/app/api/oauth/callback/ikas/route.ts` | §8, §10 #10 | F6 |
| `ikas.config.json` action URL with no route | `ikas.config.json` | §7 | — |
| Inherited from the starter: `Math.random` state, unnormalized deploy URL, `===` signature compare, browser-console param log, unconditional Admin redirect, `\|\| ''` secrets, unused scopes | various | §2.1, §2.2, §3.3, §8, §10 #1 #5 #6 #16 | F3, F4, F5, F6, F9 |
| `.env.production` with real-looking values, not in `.gitignore` (created by `tests/run.sh`, untracked) | `.env.production` | §8 | F12 |
