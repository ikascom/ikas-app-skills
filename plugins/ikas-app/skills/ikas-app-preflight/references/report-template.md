# Report template (Turkish)

The report is written **in Turkish** regardless of the language of SKILL.md, unless the user asks for another language. Use exactly these sections, in this order. Omit a section only when it is empty **and** say so in one line (e.g. "Blocker yok."). Keep prose short.

**The report is read in a terminal by a developer who has never opened app-review.md.** Three consequences:

1. **What to do comes first.** The action list sits right under Karar; the detailed sections justify it below.
2. **Plain names before § numbers.** Every finding header starts with the area in Turkish, the § in parentheses: `OAuth callback (§2.2)`. Never a bare `§2.2`. Area names:

   | § | Alan adı |
   |---|---|
   | §1 | Yayın ön koşulları |
   | §2.1 / §2.2 / §2.3 | OAuth başlatma / OAuth callback / Token yenileme |
   | §3 | Panel içi yükleme (App Bridge) |
   | §4 | Panel ekranı |
   | §5 | Backend API (JWT) |
   | §6.1 / §6.2 / §6.4 | Webhook imzası / Kaldırma / Ödeme |
   | §7 | Aksiyonlar |
   | §8 | Gizli anahtarlar ve ayar |
   | §9 | Storefront uçları |
   | §10 #n | Bilinen hata kalıbı #n |

3. **Narrow tables for indexes, blocks for detail.** A table is fine when every cell is short (≤ 40 chars, ≤ 4 columns): the *Bulgu özeti* index, the "kod dışında" table, the §10 sweep. Findings themselves are blocks (Bulgu / Kanıt / Düzeltme) — a table cell cannot hold a `path:line` plus what was seen without the terminal re-flowing it into a key/value wall. Bilgi and öneri bullets are one line each, path first.

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

## Bir bakışta
<3–6 madde, teknik olmayan biri için: uygulama ne yapıyor; kurulum/kaldırma/webhook/aksiyon güvenliği ne durumda; göndermeden önce yapılması gereken 1–3 şey; kod dışında kapatılması gereken beyanlar. Madde başına bir cümle, § yok.>

## Yapılacaklar (öncelik sırasıyla)
1. **`dosya:satır`** — somut değişiklik, tek cümle → B1 · katalogda F<n> var / elle
2. **`dosya`** — … → U1 · elle
3. **Partner paneli** — … → kod dışında
<Blocker'lar önce, sonra Uyarılar, sonra kod dışı işler. Her madde: nerede, ne değişecek, hangi bulguya bağlı, katalogda hazır tarif var mı.>

## Bulgu özeti
| # | Şiddet | Alan | Dosya |
|---|---|---|---|
| B1 | güvenlik | Webhook imzası | `api/webhooks/capture/route.ts` |
| U1 | uyarı | OAuth callback | `lib/signatures.ts:11` |
<Bir satır = bir bulgu; sıra Yapılacaklar ile aynı. Dosya `src/` öneki olmadan, tek satır. Bulgu yoksa bölümü atla.>

## 1. Blocker'lar
**B1 · güvenlik · Webhook imzası (§6.1, §10 #2) `[security]`**
Bulgu: <tek cümle, ne yanlış>
Kanıt: `dosya:satır` — ne görüldü (untracked/gitignored ise belirt)
Düzeltme: <tek cümle, ne yapılacak>

**B2 · işlevsel · Panel içi yükleme (§3.1) `[observed]` R2**
…

## 2. Uyarılar
**U1 · OAuth başlatma (§2.1, §10 #16) `[docs:admin-app]`**
Bulgu: …
Kanıt: `dosya:satır` — …
Düzeltme: …

## 3. Kod dışında doğrulanacaklar
| Soru | Neden |
|---|---|
| Partner hesabı oluşturuldu ve uygulama bu hesaba eklendi mi? | Yayın ön koşulu (§1 #1) |
| … | … |

## 4. Temiz alanlar ve notlar
- `dosya:satır` — tek satır, tek gerçek (temiz alan kanıtı; birleştirilen/düşürülen scanner hit'i ve gerekçesi)
- §10 taraması: ✓ 1, 2, 3, 4, 6, 10, 11 · n/a 5, 9, 12 · bulgu 8→U2, 15→U3, 17→U5   ← tek satır, üç grup; "#1 ✓ #2 ✓ …" dizisi yazma

## 5. İsteğe bağlı öneriler (kural gerektirmiyor, en fazla 5)
- …

## 7. Uygulanan düzeltmeler   ← only after the user approved fixes
- **F1** `src/app/api/webhooks/ikas/route.ts` — imza doğrulaması + 401/500 yolu eklendi

Type-check: ✅ geçti | ❌ <ilk hata satırı> | ⏭ atlandı (node_modules yok)
`git diff --stat` çıktısı

Uygulanmayanlar: F4 — ön koşul sağlanmadı (config zaten normalize ediyor)
```

## Column rules

- **Header line** — `**B1 · <neden> · <Alan adı> (<§>) <kaynak etiketi>**` for Blockers, `**U1 · <Alan adı> (<§>) <kaynak etiketi>**` for Uyarılar; area names from the table above. Neden is exactly one of `güvenlik`, `review`, `işlevsel` (app-review.md §0). Source tags: `[docs:…]`, `[sdk]`, `[schema]`, `[mcp]`, `[partner-panel]`, `[security]`, `[observed] R<n>` (cite the rejection number). A finding with no § is **kontrat dışı** and goes to section 5.
- **Bulgu** — one sentence, what is wrong, no "should consider".
- **Kanıt** — `path:line` plus what you saw there, enough to verify without re-auditing. Quote the scanner line when it *is* the evidence. Mark files that are `untracked` or `gitignored` (`git status --porcelain --ignored`) — they are still in the working tree and will ship if deployed from it.
- **Düzeltme** — one sentence, imperative, concrete ("`state` karşılaştırmasını `state && session.state` koşuluna al"). Same text feeds the Yapılacaklar list.
- **Length** — Bulgu ≤ 1 line, Kanıt ≤ 2 lines, Düzeltme ≤ 1 line, every note bullet ≤ 1 line. Long reasoning goes nowhere; the evidence column is what the developer opens.
- **Bir bakışta** — plain Turkish for the developer's manager or the reviewer contact; no §, no file paths, no severity jargon. It summarises, never adds a finding that is not in sections 1–3.
- **Bulgu özeti** — one row per finding, same order as Yapılacaklar, four short cells; it is the index a reader scans before opening a block. Never put Bulgu/Kanıt text in it.
- **Karar** — honest. "Şu iki düzeltmeyle gönderilebilir" is fine when the Blockers are each a small, obvious change. With no Blocker: "Bu kural setine göre Blocker kalmadı; en yüksek öncelikli uyarı: …" (name one). Never say "review'dan geçer".
- Sort: Blockers — güvenlik first, then review, then işlevsel. Uyarılar — by §.
- Do not list Uyarı-level items in the Blocker table to make the report look thorough; do not hide a Blocker in Bilgi to make it look clean.

## Worked example (abridged)

```markdown
# ikas App Preflight — Rush (/Users/x/rush)

**Karar:** İki dosyalık düzeltmeyle gönderilebilir; en büyük risk çalışma ağacında duran imzasız test webhook route'u.
**Uygulama şekli:** §4 (a) panel içi dashboard · **Plan:** ücretsiz
**Mod:** tam · **Scanner:** 16 route, 6 client page · **Git:** 1 untracked

## Bir bakışta
- Rush, mağazaya kampanya ve widget ekleyen panel içi bir uygulama; kurulum ve giriş akışı çalışıyor.
- Çalışma ağacında imzasız bir test webhook route'u var; silinmeden gönderilmemeli.
- Bir admin route'u kaldırılmış mağazaların token'ını reddetmiyor; tek satırlık düzeltme.
- Partner panelinde 4 fazla izin ve uninstall webhook kaydı kontrol edilmeli.

## Yapılacaklar (öncelik sırasıyla)
1. **`src/app/api/webhooks/capture/`** — dizini sil; `.env`'den `WEBHOOK_CAPTURE_*` çıkar → B1 · elle
2. **`src/app/api/oauth/callback/ikas/route.ts`** — token kaydından sonra `installScript` çağır → B2 · elle
3. **`src/app/api/ikas/get-merchant/route.ts`** — `withMerchant` ile sar → U2 · katalogda F10 var
4. **`src/globals/config.ts`** — kullanılmayan 4 scope'u çıkar, Partner panelini eşle → U1 · elle (re-authorize gerektirir)
5. **Partner paneli** — Bildirim Adresi'ni `<deployUrl>/api/webhooks/ikas` yap; 2 dev mağazayı İzin Verilen Mağazalar'a ekle → kod dışında

## Bulgu özeti
| # | Şiddet | Alan | Dosya |
|---|---|---|---|
| B1 | güvenlik | Webhook imzası | `api/webhooks/capture/route.ts` |
| B2 | review | Kaldırma / storefront script | `lib/storefront-script.ts:68` |
| U1 | uyarı | OAuth başlatma | `globals/config.ts:2` |
| U2 | uyarı | Backend API | `api/ikas/get-merchant/route.ts:18` |

## 1. Blocker'lar
**B1 · güvenlik · Webhook imzası (§6.1, §10 #2, #19) `[security]`**
Bulgu: Webhook route imza hesaplıyor ama reddetmiyor, koşulsuz 200 dönüyor, imza+header'ları diske yazıyor.
Kanıt: `src/app/api/webhooks/capture/route.ts:28-58` — `signatureValid` kullanılmıyor, `appendFileSync(...signature...)`, `return { ok: true }`; dosya **untracked**.
Düzeltme: Dizini sil; test için gerekiyorsa aynı imza zincirinin arkasına al.

**B2 · review · Kaldırma / storefront script (§6.2, §10 #17) `[observed]` R5**
Bulgu: Storefront script kurulumda otomatik eklenmiyor; yalnızca ayarlar düğmesi ve kampanya publish ile.
Kanıt: `src/lib/storefront-script.ts:68` `installScript` — çağıranlar `api/ikas/script`, `campaigns/[id]/publish`; callback'te yok.
Düzeltme: Callback'te token kaydedildikten sonra `installScript` çağır; reviewer kurunca vitrinde script'i görmeli.

## 2. Uyarılar
**U1 · OAuth başlatma (§2.1, §10 #16) `[docs:admin-app]`**
Bulgu: `read_orders`, `write_orders`, `read_inventories`, `write_inventories` isteniyor; hiçbir orders/inventory operasyonu çağrılmıyor.
Kanıt: `src/globals/config.ts:2-6`; operasyonlar: createCampaign, searchProduct, listStorefront…
Düzeltme: 4 scope'u çıkar; Partner panel › Uygulama Yetkileri'ni aynı listeye indir (mevcut kurulumlar yeniden yetki ister).

**U2 · Backend API (§5.1) `[security]`**
Bulgu: `get-merchant` route'u `withMerchant` dışında, `deleted` kontrolü yok.
Kanıt: `src/app/api/ikas/get-merchant/route.ts:18`
Düzeltme: Handler'ı `withMerchant` ile sar (F10).

## 3. Kod dışında doğrulanacaklar
| Soru | Neden |
|---|---|
| Partner hesabı doğrulandı mı? | Yayın ön koşulu (§1 #2) |
| Uygulama en az 2 geliştirme mağazasında kurulu mu? Partner panel › İzin Verilen Mağazalar'daki adlar? | Yayın ön koşulu (§1 #5), ret R7 |
| Partner panel › Bildirim Adresi `<deployUrl>/api/webhooks/ikas` mi? (`store/app/deleted` yalnız oradan gelir) | Kaldırma (§6.2) |

## 4. Temiz alanlar ve notlar
- `api/oauth/callback/ikas/route.ts:46-60` — signature varsa doğrulanıyor, state varsa eşleniyor ve siliniyor; tarayıcıya yalnız 4 saatlik JWT (OAuth callback temiz).
- `public/widget.js:12` — `api.myikas.com/api/sf/graphql` anonim çağrı → Backend API kuralından muaf; README'de belirtilmeli.

## 5. İsteğe bağlı öneriler
- `rate-limit.ts` instance-başı; serverless'ta paylaşımlı store düşünülebilir.
```
