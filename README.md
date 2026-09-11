# ikas-app-skills

ikas Admin App (Next.js ile geliştirilip OAuth ile mağaza paneline kurulan uygulama)
projelerinde kullanılmak üzere hazırlanmış Claude Code skill kütüphanesi. Skill'ler tek bir
plugin (`ikas-app`) altında toplanır ve Claude Code'un plugin marketplace özelliğiyle
dağıtılır. Tema (Code Components) skill'leri için kardeş repo: `ikascom/ikas-cc-skills`.

## Kurulum

```
/plugin marketplace add ikascom/ikas-app-skills
/plugin install ikas-app@ikas-app-skills
```

Kurulumdan sonra skill'ler otomatik olarak kullanılabilir olur; Claude ilgili bir görevle
karşılaştığında skill'i kendisi devreye alır, `/ikas-app-preflight` gibi komutla elle de
çağrılabilir.

Güncelleme için:

```
/plugin marketplace update ikas-app-skills
```

## Skill Kataloğu

| Skill | Ne zaman kullanılır |
|---|---|
| [ikas-app-preflight](#ikas-app-preflight) | Bir ikas Admin App'i App Store review'ına göndermeden önce ön koşulları ve güvenlik katmanını denetlemek (varsayılan salt-okunur; `fix` argümanıyla tarifli düzeltmeler) |

---

### ikas-app-preflight

Bir ikas Admin App'in **App Store review'ı öncesi ön kontrolü.** Ölçüt, skill ile gelen
`references/app-review.md` kural seti: beş resmi yayın ön koşulu, OAuth / App Bridge /
iframe kontratı, webhook ve app action imza doğrulaması, secret hijyeni, public uç
güvenliği ve gerçek review ret sebepleriyle gerçek düzeltmelerden damıtılmış numaralı
anti-pattern kataloğu. Her bulgu ya ihlal ettiği bölümü zikreder (§2.2, §6.1, §10 #4…)
ya da açıkça "kontrat dışı" etiketlenir. Kod stili, test kapsamı ve iş mantığı kapsam
dışıdır.

**Tetikleyiciler:** "uygulama review'a hazır mı", "app store'a göndermeden önce kontrol
et", "ikas app denetle", "webhook imzası doğru mu", "oauth akışı güvenli mi",
"install/uninstall akışı", "publish checklist".

**Bulgu sınıflandırması:**

| Sınıf | Anlamı |
|---|---|
| Blocker | Review reddi ya da güvenlik açığı — kural setindeki bir MUST ihlali |
| Uyarı | SHOULD ihlali — düzeltilmeli, tek başına ret sebebi değil |
| Beyan gerekli | Koddan görülemeyen ön koşul (partner doğrulama, 2 dev mağaza, reviewer test hesabı) — geliştiriciye sorulur, asla "geçti" sayılmaz |
| Bilgi / Kontrat dışı | Bağlam ve zorunlu olmayan öneriler (maks 5) |

**Altı geçişli prosedür:** (0) `scripts/scan.py` ile deterministik kanıt toplama —
`Math.random` state, imzasız webhook, her durumda 200 dönen handler, `closeLoader`
çağırmayan iframe sayfası, iframe içinde Admin'e redirect, `NEXT_PUBLIC_` secret, public
şemada para alanı…; (1) yüzey envanteri ve **app şekli** tespiti — panel içi dashboard /
harici dashboard / yalnızca action / headless — çünkü "ikas arayüzü" ön koşulu her
şekilde farklı sağlanır; (2) merchant yolculuğu — kurulum → callback → günlük giriş →
aksiyon → plan satın alma → kaldırma; (3) güvenlik katmanı — JWT doğrulayan API rotaları,
tarayıcıdan ikas'a çağrı yok, webhook/action imza + dürüst status kodları, secret
hijyeni, public uçlarda merchant kapsamı ve istemciden para değeri almama; (4) §10
anti-pattern taraması; (5) beyan tablosu.

**Modlar:** argümansız tam denetim (dosya değişmez); `fix` — yalnızca Fix Kataloğu'ndaki
tarifli düzeltmeler (webhook imza doğrulaması, eksik `closeLoader`, CSPRNG state, deploy
URL normalizasyonu, iframe redirect guard'ı, token log temizliği, `NEXT_PUBLIC_` secret
yeniden adlandırma, `Suspense` sarmalama, callback'te `storeName`'i query'den okuma,
`timingSafeEqual` karşılaştırması, mevcut wrapper ile `deleted` token kontrolü) uygulanır,
ardından type-check + lint;
`quick` — yalnızca scanner + anti-pattern; `section <oauth|iframe|webhooks|actions|secrets|public>`.

**Rapor sözleşmesi:** Türkçe; karar cümlesi + app şekli → Blocker tablosu (bulgu, kanıt
dosya:satır, dayanak §) → Uyarılar → Beyan gerekli soruları → Bilgi/kontrat dışı →
öncelikli aksiyon listesi; `fix` modunda uygulanan düzeltmeler + `git diff --stat`.

**İçerik:**

```
skills/ikas-app-preflight/
├── SKILL.md                    # severity taksonomisi, 6 geçişli prosedür, fix kataloğu, rapor sözleşmesi
├── references/app-review.md    # ölçüt kural seti: §1 ön koşullar … §10 anti-pattern kataloğu
└── scripts/scan.py             # deterministik kanıt tarayıcısı (--json destekler)
```

> **Not:** `scan.py` yalnızca kanıt toplar — bir bulgu "okunacak yer", bulgu yokluğu
> "kanıtlanmış" değildir. Nihai karar SKILL.md'deki geçişlerde kod okunarak verilir.

## Lisans

[MIT](LICENSE) © İKAS TEKNOLOJİ A.Ş.
