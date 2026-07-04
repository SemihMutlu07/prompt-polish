# prompt-polish

AI kullanırken İngilizceni geliştiren terminal aracı.

Prompt engineering asistanı değil, dil öğrenme arkadaşı: AI'a göndereceğin prompt'u alır, daha akıcı İngilizce versiyonunu, yapılan düzeltmelerin Türkçe açıklamalarını ve 1-2 kelimelik mini vocabulary kartını gösterir. Kartı okursun, dilin gelişir, sonra AI cevabını alırsın.

```
╭──────────────────────────────────────────────╮
│ ✨ Prompt Polish                             │
│                                              │
│ Original prompt                              │
│   write code for sort algorithm fastly       │
│                                              │
│ ✓ Revised                                    │
│   Could you help me write code for a fast    │
│   sorting algorithm?                         │
│                                              │
│ 📝 Improvements                              │
│   • word choice                              │
│     ✗ fastly                                 │
│     ✓ fast                                   │
│     "fastly" bir kelime değil; sıfat olarak  │
│     "fast" kullanılır.                       │
│                                              │
│ 📖 Vocabulary                                │
│   • sorting algorithm                        │
│     → sıralama algoritması                   │
│     ↩ alt: ordering method                   │
╰──────────────────────────────────────────────╯
│ Use revised? [Y/n]
```

## Kurulum

Python 3.10+ yeterli, sıfır dependency (sadece stdlib).

```bash
git clone https://github.com/<user>/prompt-polish
cd prompt-polish
ln -s "$(pwd)/polish.py" ~/.local/bin/polish
polish --setup   # API key gir (OpenRouter önerilir: openrouter.ai/keys)
```

## Kullanım

```bash
polish "write code for sort algorithm"    # argüman olarak
echo "explain recursion" | polish         # pipe ile
polish                                    # interactive mode (Ctrl+D)
polish --file prompt.txt                  # dosyadan
polish --setup                            # API key yapılandırma
```

Kart **stderr**'e çizilir, **stdout**'a sadece seçilen prompt yazılır — çıktı pipe edilebilir:

```bash
polish "write code" | hermes ask     # revised prompt direkt başka araca
polish "write code" > prompt.txt     # dosyaya kaydet
```

## Yapılandırma

`~/.config/prompt-polish/config.json` (0600):

```json
{
  "api_key": "sk-or-...",
  "base_url": "https://openrouter.ai/api/v1",
  "model": "openai/gpt-4o-mini"
}
```

Env var override: `POLISH_API_KEY`, `POLISH_BASE_URL`, `POLISH_MODEL`. OpenAI-uyumlu her API çalışır (OpenRouter, OpenAI, DeepSeek...).

## Davranış notları

- API hatası, timeout, bozuk JSON → araç çökmez; orijinal prompt stdout'a basılır, uyarı stderr'e (exit 0).
- Rate limit (429) → 2 sn bekleyip 2 kez yeniden dener.
- Non-TTY modda (pipe/redirect) "Use revised?" sorusu atlanır, revised direkt basılır.
- Terminal < 40 kolon → kart yerine tek satır özet.
- 5 karakterden kısa veya 4000 karakterden uzun prompt'lar dokunulmadan geçirilir.

## Test

```bash
python3 test_polish.py   # ağ gerektirmeyen 15 kontrol (motor + adapter)
```

## Otomatik hook (Claude Code / Codex / Hermes)

CLI'ı elle çağırmak yerine, harness'in prompt akışına otomatik bağlanabilirsin:

```bash
./install.sh           # kurulu harness'leri tespit eder, snippet basar
./install.sh --apply   # Claude Code + Codex config'lerine otomatik ekler (yedekli)
```

Hermes YAML dosyasına otomatik yazılmaz (format riski), `--apply` çıktısındaki
snippet'i `~/.hermes/config.yaml`'a elle eklemen gerekir.

**Nasıl çalışır:** `adapters/polish-hook.py` üç harness'in de hook JSON'unu
stdin'den okur, prompt'u çıkarır, `polish.py --hook` ile motoru çağırır, kartı
`/dev/tty`'ye basar (terminalde anında görünür) ve revised versiyonu context
olarak enjekte eder — Claude Code/Codex plain stdout, Hermes `{"context": ...}`
JSON.

**Önemli sınır:** Hiçbir harness'in hook sistemi kullanıcının promptunu
sessizce değiştiremiyor (resmi Claude Code docs bunu doğruluyor — sadece context
eklenebilir veya submission tamamen bloklanabilir). Bu yüzden gerçek bir "swap"
değil, LLM'e "kullanıcının orijinal + daha akıcı versiyonu — revised'ı esas al"
diyen bir not ekleniyor. Davranışsal olarak swap'a denk, teknik olarak değil.

Devre dışı bırakmak için: `POLISH_HOOK_DISABLE=1` env var (kalıcı olarak
istersen shell rc'ne ekle). `/` ile başlayan slash command'lar zaten otomatik
atlanır. Her hook çağrısı ~1-2 sn gecikme ekler; API hatası/timeout'ta sessizce
geçilir (fail-open, prompt asla bloklanmaz).
