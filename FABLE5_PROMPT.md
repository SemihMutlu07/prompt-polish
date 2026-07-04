# Prompt Improver — Fable 5 Build Prompt

Bu prompt, Fable 5 orchestrator'a Prompt Improver (pi) aracını build ettirmek içindir. Tüm kararlar prompt içinde verilmiştir — Fable hiçbir şey sormaz, direkt kod yazar.

---

## 1. Product Concept (Tek Cümle)

**"AI kullanırken İngilizceni geliştiren terminal aracı."** — Prompt engineering asistanı değil, dil öğrenme arkadaşı.

Kullanıcı bir AI'a prompt yazdığında, cevap gelmeden önce terminalde küçük bir kart gösterir: orijinal prompt, daha iyi İngilizce versiyonu, yapılan iyileştirmeler ve kelime alternatifleri. Kartı okur, dilini geliştirir, sonra AI cevabını alır.

**Konumlandırma (competitive gap):**
- PromptDC, PromptForge, Boost My PrompT gibi 10 rakip var — hepsi "AI'dan daha iyi cevap al" için
- Hiçbiri "İngilizceni geliştir" pozisyonunda değil
- Hiçbiri orijinal vs revize'yi yan yana öğretme amaçlı göstermiyor
- Bu mavi okyanus: 1.5 milyar ESL × 180M ChatGPT kullanıcısı

---

## 2. Build Edilecek Şey

### 2.1 CLI Tool (`pi`)

Python CLI, terminal-first. Kullanım:

```bash
pi "write code for sort algorithm"         # argüman olarak
echo "explain recursion" | pi              # pipe ile
pi                                          # interactive mode (Ctrl+D)
pi --setup                                  # API key config
```

### 2.2 Hermes Hook (opsiyonel, sonra)

pre-llm_call hook'u olarak Hermes'e entegre. Bu adımda **CLI tool build edilir**, hook sonra.

---

## 3. Architecture

### Flow

```
┌─ Kullanıcı prompt yazar ─────────────────────────────┐
│                                                        │
│  1. Kullanıcı: "write code for sort algorithm"         │
│                                                        │
│  2. pi aracı prompt'u alır                             │
│     → gpt-4o-mini'e (veya benzeri ucuz model) gönderir│
│     → system prompt: "improve English, teach user"     │
│                                                        │
│  3. LLM'den JSON döner:                               │
│     { revised, improvements[], vocabulary[] }          │
│                                                        │
│  4. Terminal'de kutu çizilir:                          │
│     ╭─ Prompt Improver ─────────────────────────╮      │
│     │ Original: write code for sort algorithm    │      │
│     │ ✓ Revised: Could you help me write code   │      │
│     │   for implementing a sorting algorithm?   │      │
│     │                                            │      │
│     │ 📝 Improvements:                          │      │
│     │   • word choice                           │      │
│     │     ✗ "write code for"                    │      │
│     │     ✓ "help me write code for"            │      │
│     │                                            │      │
│     │ 📖 Vocabulary:                            │      │
│     │   • "implementing" → uygulamak            │      │
│     │     ↩ alternative: "building"             │      │
│     │                                            │      │
│     │ Use revised? [Y/n] _                       │      │
│     ╰────────────────────────────────────────────╯      │
│                                                        │
│  5. Kullanıcı Y girerse → revised prompt çıktı olarak  │
│     Kullanıcı n girerse → orijinal prompt çıktı olarak  │
│                                                        │
│  6. Çıktı stdout'a yazılır → pipe ile başka araca     │
│     gidebilir veya Hermes'e gider                      │
│                                                        │
│  7. Kart tamamen stderr'de — stdout temiz              │
└────────────────────────────────────────────────────────┘
```

### Output Convention

| Kanal | Ne gider |
|-------|----------|
| **stdout** | Sadece seçilen prompt (revised veya original). Pipe edilebilir. |
| **stderr** | Kart, hata mesajları, interactive prompt. Terminal UI. |

```bash
pi "write code" | hermes ask         # revised prompt direkt Hermes'e
pi "write code" > prompt.txt         # dosyaya kaydet
```

### Config File

`~/.config/pi/config.json` (0600 permissions):
```json
{
  "api_key": "sk-or-...",
  "base_url": "https://openrouter.ai/api/v1",
  "model": "openai/gpt-4o-mini"
}
```

Env var override: `PI_API_KEY`, `PI_BASE_URL`, `PI_MODEL`

LLM provider: OpenAI-compatible API (OpenRouter, OpenAI, etc.)

---

## 4. LLM System Prompt

```
You are an English improvement assistant. Your task is to help non-native 
speakers write better English prompts for AI.

Given a user's prompt, return a JSON object with these fields:
1. "revised": rewritten version in more fluent, natural English. 
   Keep same intent. Do NOT change technical ask.
2. "improvements": array of 2-4 specific changes, each:
   - "what": label ("word choice", "grammar", "tone", "clarity", "structure")
   - "original": original phrase
   - "revised": improved version  
   - "note": short Turkish explanation (1 sentence max)
3. "vocabulary": array of 1-2 interesting words, each:
   - "word": the word/phrase
   - "meaning": short Turkish explanation
   - "alternative": a similar alternative

Rules:
- Keep technical terms, code, domain jargon untouched
- Do NOT change intent or add new instructions
- "improvements" should teach, not just rewrite
- Return ONLY valid JSON, no other text
```

**Model:** openai/gpt-4o-mini (veya deepseek-chat, haiku — prompt improvement için yeterli). Temperature: 0.3. Max tokens: 800.

---

## 5. Edge Cases & Unknown Unknowns (Çözümleriyle)

### 5.1 Boş prompt / whitespace only
→ Hata mesajı göster, exit 1.

### 5.2 API key yok
→ "API key bulunamadı. `pi --setup` ile yapılandır." → exit 1. Hata mesajında link: openrouter.ai/keys

### 5.3 API timeout / network error
→ "⚠️  Prompt iyileştirilemedi. Orijinal kullanılıyor." → orijinal prompt'u stdout'a bas, exit 0 (hata değil, degrade)

### 5.4 LLM geçersiz JSON döndürdü (halüsinasyon)
→ JSON parse hatasını yakala, orijinal prompt'u kullan, exit 0

### 5.5 LLM boş/kırpılmış revised döndürdü
→ `revised = data.get("revised", prompt) or prompt` — fallback

### 5.6 Terminal width çok dar (< 40 kolon)
→ Kartı gösterme, sadece tek satır: `✓ Improved: <50 karakter>'`. width < 40'da kart bozulur.

### 5.7 Pipe modu (non-TTY)
→ stdout yoksa, interactive input'sa: "Use revised?" sorusunu atla, direkt revised'ı bas. Kart yine stderr'e gider.
→ stdin pipe: `echo "explain" | pi` çalışır, kart stderr'de, çıktı stdout'ta.

### 5.8 Çok uzun prompt (>2000 token)
→ Kes veya warning bas. gpt-4o-mini 8K context limit. Max_prompt_length: 4000 chars. Aşarsa warning + orijinal.

### 5.9 API rate limit
→ HTTP 429 hatasını yakala, 2 sn bekle, tekrar dene (max 2 retry). Hala hata → fallback.

### 5.10 Kullanıcı Ctrl+C yaparsa
→ `KeyboardInterrupt` yakala, orijinal prompt'u stdout'a bas, exit 0.

### 5.11 Config dosyası bozuk JSON
→ Hata mesajı + `pi --setup` ile yeniden yapılandırmayı öner.

### 5.12 Prompt tek kelime
→ Yine de LLM'e gönder. Tutarlı ol: her prompt'a aynı muamele.

### 5.13 Prompt zaten iyi İngilizce
→ LLM küçük değişiklikler yapar (grammar polish). improvements array'i boş olabilir. Revised = orijinal. Vocabulary yine dolu gelir — o zaman sadece vocab göster.

### 5.14 Çok kısa prompt (<5 karakter)
→ LLM anlamlı bir rewrite yapamaz. "Prompt çok kısa" warning'i bas, orijinali kullan.

### 5.15 Emoji / special chars
→ UTF-8 desteklenir. Unicode sorunu varsa LLM'in çıktısında görünür — ayrıca ele alınmaz.

### 5.16 LLM'in cevabı çok uzun (>2000 char)
→ Kes. Kart max 80 kolon, overflow olursa truncate. `t[:card_width - 7] + "..."`

### 5.17 Aynı prompt'u tekrar gönderme
→ Basit cache: son 5 prompt'un MD5 hash'ini memory'de tut. Aynı hash varsa LLM çağrısı yapma, cached sonucu göster.

### 5.18 Cost tracking
→ Her çağrıda token sayısını logla. `--stats` flag'i ile toplam cost göster.

### 5.19 Non-English prompt (kullanıcı Türkçe yazarsa)
→ LLM prompt'u ve açıklamaları İngilizce'ye çevirir. improvements ve vocabulary Türkçe açıklamalı kalır (system prompt'ta "Turkish explanation" deniyor, bu korunur).

### 5.20 Dosyadan okuma
→ pi --file prompt.txt argümanı ekle.

---

## 6. Implementation Details

### 6.1 Dependencies
- Python 3.10+
- Zero external dependencies (stdlib only: json, os, sys, urllib.request, hashlib, argparse)
- Install: `pip install pi` değil, direkt `./pi.py` veya PATH'e symlink

### 6.2 File Structure
```
prompt-improver/
├── pi.py           # Ana CLI (executable, shebang)
├── pi              # Shell wrapper: exec python3 /abs/path/pi.py "$@"
└── README.md       # Kurulum + kullanım
```

### 6.3 Terminal UI Tasarım İlkeleri
- Kutular için Unicode box-drawing: ╭─╮╰─╯│ (U+256D, U+256E, U+2570, U+256F, U+2500, U+2502)
- Semboller: ✨ ✓ ✗ ● → ↩
- Renk: ANSI color kullanma (taşınabilirlik için) — Unicode glyp'ler yeterli
- width: terminal - 2 (sağ padding), max 78
- Padding: her satırda `│ ` ve ` │`
- Kartı **stderr'e** yaz — stdout temiz kalsın

### 6.4 Config
- `~/.config/pi/config.json` — sadece API key, base_url, model
- `pi --setup` interactive wizard
- Env override: PI_API_KEY, PI_BASE_URL, PI_MODEL

### 6.5 API Call Details
- Endpoint: `{base_url}/chat/completions` (OpenAI-compatible)
- Method: POST
- Headers: `Content-Type: application/json`, `Authorization: Bearer {key}`
- Body: `model`, `messages` (system + user), `temperature: 0.3`, `max_tokens: 800`

---

## 7. Out of Scope (Bu adımda yapılmayacak)

| Feature | Neden? |
|---------|--------|
| Hermes pre-llm hook | CLI çalışsın, sonra entegre ederiz |
| Browser extension | Terminal-first MVP |
| History / log | İlk versiyonda yok |
| Renkli output (ANSI) | Unicode yeterli, taşınabilir |
| Cost dashboard | `--stats` flag'i ile sonra |
| GitHub Copilot / IDE entegrasyonu | CLI MVP'nin çok ötesi |
| Multi-language (Türkçe-Türkçe vb.) | Sadece İngilizce hedef |
| Cache disk persistence | Cache sadece memory'de (son 5) |

---

## 8. Başarı Kriterleri (Done Definition)

- [ ] `pi "write code"` → kart gösterir + stdout'a revised prompt basar
- [ ] `echo "explain" | pi` → pipe'dan okur, kart stderr'de
- [ ] `pi` tek başına → interactive mode, Ctrl+D ile okur
- [ ] `pi --setup` → API key sorar, config'e kaydeder
- [ ] API yoksa → degrade: orijinal prompt'u basar, hata mesajı stderr'de
- [ ] Terminal width < 40 → tek satır modu
- [ ] Non-TTY stdout → "Use revised?" sorusunu atlar
- [ ] Config bozuk → `pi --setup` önerisi
- [ ] Tüm hatalar stderr'de, stdout sadece prompt
- [ ] `pi.py` ve `pi` (shell wrapper) çalışır

---

## 9. Takvim

| Adım | Süre |
|------|------|
| Build | ~30 dk (Fable 5) |
| Test (10+ edge case) | ~10 dk |
| Error handling validation | ~5 dk |
| Total | ~45 dk |

---

## 10. Referans Dosyalar

Bu repo'da zaten `pi.py` prototipi var — %70 çalışır. Fark:
- Edge case handling eksik (onlar yukarıda listelendi)
- Cache yok
- Terminal width handling zayıf
- Non-TTY/pipe modu test edilmemiş
- Çok uzun prompt handling yok

Fable'ın `dev/prompt-improver/pi.py`'yi OKUYUP üzerine inşa etmesi LAZIM, sıfırdan yazması değil. Mevcut kodun iyi kısımlarını koru, edge case'leri ekle.