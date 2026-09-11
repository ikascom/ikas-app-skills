# Report template (Turkish)

The report is written **in Turkish** regardless of the language of SKILL.md, unless the user asks for another language. Use exactly these sections, in this order. Omit a section only when it is empty **and** say so in one line (e.g. "Blocker yok."). Keep prose short; tables carry the substance.

## Contents

- Section layout
- Column rules
- Worked example (abridged)

## Section layout

```markdown
# ikas App Preflight — <uygulama adı> (<proje yolu>)

**Karar:** <tek cümle: review'a gönderilebilir mi; en büyük risk ne>
**Uygulama şekli:** §4 (a|b|c|d) <kısa açıklama> · **Plan:** ücretsiz | ücretli
**Mod:** tam | quick | section <alan> · **Scanner:** <n> route, <n> client page · **Git:** temiz | <n> untracked | commit yok | repo yok

## 0. Bir bakışta
<3–6 madde, teknik olmayan biri için: uygulama ne yapıyor; kurulum/kaldırma/webhook/aksiyon güvenliği ne durumda; göndermeden önce yapılması gereken 1–3 şey; kod dışında kapatılması gereken beyanlar. Madde başına bir cümle, § referansı yok.>

## 1. Blocker'lar
| # | Bulgu | Kanıt | Dayanak | Neden Blocker |
|---|---|---|---|---|
| B1 | … | `dosya:satır` — ne görüldü | §6.1, §10 #2 `[security]` | güvenlik / review / işlevsel |

## 2. Uyarılar
| # | Bulgu | Kanıt | Dayanak |
|---|---|---|---|
| U1 | … | `dosya:satır` — ne görüldü | §2.1, §10 #16 `[docs:admin-app]` |

## 3. Beyan gerekli
| Soru | Neden |
|---|---|
| Partner hesabı oluşturuldu ve uygulama bu hesaba eklendi mi? | §1 #1 |
| … | … |

## 4. Bilgi
- … (clean areas with evidence; scanner hits you merged or downgraded, with the § reason)

## 5. Kontrat dışı (zorunlu değil, en fazla 5)
- …

## 6. Öncelikli aksiyon listesi
1. **`dosya`** — somut değişiklik (B1)
2. …

## 7. Uygulanan düzeltmeler   ← only after the user approved fixes
| Fix | Dosya | Ne değişti |
|---|---|---|
| F1 | `src/app/api/webhooks/ikas/route.ts` | imza doğrulaması + 401/500 yolu eklendi |

Type-check: ✅ geçti | ❌ <ilk hata satırı> | ⏭ atlandı (node_modules yok)
`git diff --stat` çıktısı

Uygulanmayanlar: F4 — ön koşul sağlanmadı (config zaten normalize ediyor)
```

## Column rules

- **Bulgu** — one sentence, what is wrong, no "should consider".
- **Kanıt** — `path:line` plus what you saw there, enough to verify without re-auditing. Quote the scanner line when it *is* the evidence. Mark files that are `untracked` or `gitignored` (`git status --porcelain --ignored`) — they are still in the working tree and will ship if deployed from it.
- **Dayanak** — § reference(s) and the source tag from app-review.md (`[docs:…]`, `[sdk]`, `[security]`, `[observed]`). A finding with no § is **kontrat dışı** and goes to section 5.
- **Neden Blocker** — exactly one of `güvenlik`, `review`, `işlevsel` (see app-review.md §0). When the basis is `[observed]`, say "gözlemlenen ret, dokümante değil".
- **Bir bakışta** — plain Turkish for the developer's manager or the reviewer contact; no §, no file paths, no severity jargon. It summarises, never adds a finding that is not in sections 1–3.
- **Karar** — honest. "Şu iki düzeltmeyle gönderilebilir" is fine when the Blockers are each a small, obvious change. With no Blocker: "Bu kural setine göre Blocker kalmadı; en yüksek öncelikli uyarı: …" (name one). Never say "review'dan geçer".
- Sort: Blockers — güvenlik first, then review, then işlevsel. Uyarılar — by §.
- Do not list Uyarı-level items in the Blocker table to make the report look thorough; do not hide a Blocker in Bilgi to make it look clean.

## Worked example (abridged)

```markdown
# ikas App Preflight — Rush (/Users/x/rush)

**Karar:** İki dosyalık düzeltmeyle gönderilebilir; en büyük risk çalışma ağacında duran imzasız test webhook route'u.
**Uygulama şekli:** §4 (a) panel içi dashboard · **Plan:** ücretsiz
**Mod:** tam · **Scanner:** 16 route, 6 client page · **Git:** 1 untracked

## 0. Bir bakışta
- Rush, mağazaya kampanya ve widget ekleyen panel içi bir uygulama; kurulum ve giriş akışı çalışıyor.
- Çalışma ağacında imzasız bir test webhook route'u var; silinmeden gönderilmemeli.
- Bir admin route'u kaldırılmış mağazaların token'ını reddetmiyor; tek satırlık düzeltme.
- Partner panelinde 4 fazla izin ve uninstall webhook kaydı kontrol edilmeli.

## 1. Blocker'lar
| # | Bulgu | Kanıt | Dayanak | Neden Blocker |
|---|---|---|---|---|
| B1 | Webhook route imza hesaplıyor ama reddetmiyor, koşulsuz 200 dönüyor, imza+header'ları diske yazıyor | `src/app/api/webhooks/capture/route.ts:28-58` — `signatureValid` kullanılmıyor, `appendFileSync(...signature...)`, `return { ok: true }`; dosya **untracked** | §6.1, §10 #2, #19 `[security]` | güvenlik |

## 2. Uyarılar
| # | Bulgu | Kanıt | Dayanak |
|---|---|---|---|
| U1 | `read_orders`, `write_orders`, `read_inventories`, `write_inventories` isteniyor; hiçbir orders/inventory operasyonu çağrılmıyor | `src/globals/config.ts:2-6`; operasyonlar: createCampaign, searchProduct, listStorefront… | §2.1, §10 #16 `[docs:admin-app]` |
| U2 | `get-merchant` route'u `withMerchant` dışında, `deleted` kontrolü yok | `src/app/api/ikas/get-merchant/route.ts:18` | §5.1 `[security]` |

## 3. Beyan gerekli
| Soru | Neden |
|---|---|
| Partner hesabı doğrulandı mı? | §1 #2 |
| Uygulama en az 2 geliştirme mağazasında kurulu mu? Mağaza adları? | §1 #5 |
| Uninstall webhook'u Partner panelinde `<deployUrl>/api/webhooks/ikas` için `store/app/deleted` ile tanımlı mı? (kod `saveWebhooks` çağırmıyor) | §6.2 |

## 4. Bilgi
- Callback: `signature` varsa doğrulanıyor, `state` varsa eşleniyor ve siliniyor, tarayıcıya yalnızca 4 saatlik JWT — §2.2 temiz.
- Widget'ın `api.myikas.com/api/sf/graphql` çağrısı anonim → §5.2 muaf; README'de belirtilmeli.

## 5. Kontrat dışı (zorunlu değil)
- `rate-limit.ts` instance-başı; serverless'ta paylaşımlı store düşünülebilir.

## 6. Öncelikli aksiyon listesi
1. **`src/app/api/webhooks/capture/`** — dizini sil; `.env`'den `WEBHOOK_CAPTURE_*` çıkar (B1)
2. **`src/app/api/ikas/get-merchant/route.ts`** — `withMerchant` ile sar (U2, F10)
3. **`src/globals/config.ts`** — kullanılmayan 4 scope'u çıkar, Partner panelini eşle (U1)
```
