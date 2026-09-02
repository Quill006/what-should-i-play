# Ne Oynasam?

Altı soru cevapla, üç oyun önerisi al. Bir tuşla üç tane daha.

Hesap yok, takip yok, okuyamayacağın bir algoritma yok. Puanlama mantığının tamamı açıp değiştirebileceğin tek bir dosyada.

**[English](README.md)**

---

## Çalıştırma

```bash
git clone https://github.com/KULLANICI_ADIN/what-should-i-play.git
cd what-should-i-play

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

<http://127.0.0.1:8000> adresini aç.

Projede 40 oyunluk küçük bir örnek katalog gömülü olduğu için hemen çalışır. Gerçek veri için aşağıya bak.

## Gerçek oyun verisini yükleme

Katalog [RAWG](https://rawg.io)'dan geliyor. RAWG, her oyunun Metacritic puanını kendi API'sinde yayınlıyor.

```bash
cp .env.example .env
# https://rawg.io/apidocs adresinden ücretsiz anahtar al ve .env içine yapıştır

python scripts/fetch_games.py --pages 50    # yaklaşık 2.000 oyun
```

Sunucuyu yeniden başlat.

Kullanışlı seçenekler:

```bash
python scripts/fetch_games.py --pages 125                  # ~5.000 oyun
python scripts/fetch_games.py --ordering -metacritic       # en iyi puanlılar önce
python scripts/fetch_games.py --ordering -released         # en yeniler önce
```

### Neden doğrudan Metacritic'ten çekmiyoruz?

Metacritic'in halka açık bir API'si yok ve kullanım şartları otomatik veri toplamayı yasaklıyor. Ayrıca scraping yapsaydık, site HTML'i her değiştiğinde proje bozulacaktı — birinin sürekli scraper tamir etmek zorunda kalacağı bir açık kaynak deposu iyi bir fikir değil.

RAWG, Metacritic puanını kendi veri setinin parçası olarak yeniden yayınlıyor. Yani aynı sayıya açık bir kapıdan ulaşıyoruz.

RAWG kendisini kaynak göstermeni ve geri link vermeni istiyor, verinin yeniden dağıtımına ise izin vermiyor. Bu yüzden depoda hazır veritabanı dosyası yok — herkes kendi anahtarıyla kendi kopyasını indiriyor.

## Nasıl çalışıyor

```
  Tarayıcı                   FastAPI                   Motor
 ──────────                ──────────               ──────────
 static/app.js  ──────►  GET /api/questions  ────►  questions.py
                ◄──────  sorular + etiketler

 cevaplar       ──────►  POST /api/recommend ────►  recommender.py
                ◄──────  3 oyun                     ▲
                                                    │
                                              SQLite (data/games.db)
                                                    ▲
                                          scripts/fetch_games.py ──► RAWG API
```

Öneri iki aşamada oluyor ve sıra önemli.

**Birinci aşama: sert filtreler.** Yanlış platformdaysa, çok uzunsa, çok eskiyse veya zorunlu bir etiketi yoksa oyun doğrudan eleniyor. Bunlar tercih değil: sadece Switch'i olan biri için bir PlayStation özel oyunu "biraz daha kötü" bir cevap değil, yanlış bir cevap. Bunu skora ceza olarak eklemek klasik hatadır — yüksek puanlı bir oyun cezayı yer ama yine de listeye girer ve kullanıcı oynayamadığı bir oyunu önerilmiş bulur.

**İkinci aşama: puanlama.** Elemeden geçenler bir sayı alıyor:

```
skor =   0,45 × istediğin etiketlerden kaçına sahip
       + 0,20 × istediğin türlerden kaçına sahip
       + 0,30 × eleştirmen puanı / 100
       + 0,05 × çok bilinen bir oyun değilse küçük bir avantaj
       − 0,15 × istemediğini söylediğin her etiket için ceza
```

Ağırlıklar [`app/config.py`](app/config.py) içinde. Birini değiştir, sunucuyu yeniden başlat, ne olduğuna bak.

### Metacritic bir kalite filtresi, eşleştirme sinyali değil

Projeyi ayakta tutan ya da batıran tasarım kararı bu.

Eleştirmen puanları "bu oyun iyi mi" sorusunu cevaplar. "Bu oyun **sana** uygun mu" sorusu hakkında hiçbir şey söylemez. Sadece puana göre sıralarsan herkes aynı on oyunu alır — Zelda, Elden Ring, Baldur's Gate 3, sonsuza kadar.

Bu yüzden puan toplam ağırlığın sadece %30'u ve esas işlevi, zaten senin istediklerine uyan oyunlar arasında eşitlik bozmak. Asıl eşleştirmeyi etiketler yapıyor.

### Her öneri kendini açıklıyor

Her sonuç, listeye girmesini sağlayan etiketleri başlığın altında rozetler halinde taşıyor. Bu süs değil: açıklanmayan bir öneriye kullanıcı güvenmeyi öğrenemez, sen de hata ayıklayamazsın. Sonuç yanlış göründüğünde rozetler hangi kuralın ters teptiğini söylüyor.

## Proje yapısı

```
app/
  config.py       puanlama ağırlıkları — deney yapmaya buradan başla
  questions.py    sorular, Türkçe ve İngilizce, etkileriyle birlikte
  recommender.py  filtreleme ve puanlama — asıl motor
  database.py     SQLite depolama
  main.py         HTTP uç noktaları
scripts/
  fetch_games.py  RAWG'dan katalog indirir
  seed_data.json  anahtarın yokken de çalışsın diye 40 örnek oyun
static/           web sayfası: bir HTML, bir CSS, bir JS; derleme adımı yok
```

## API

Otomatik dokümantasyon: <http://127.0.0.1:8000/docs> — her uç noktayı tarayıcıdan çağırabilirsin.

### `GET /api/questions?lang=tr`

Soru akışını ve tüm arayüz metinlerini seçilen dilde döndürür (`en` veya `tr`). Cevap seçeneklerinin *etkileri* sunucuda kalır; böylece puanlama kurallarını istemci tarafından kurcalamak mümkün olmaz.

### `POST /api/recommend`

```json
{
  "answers": { "platform": ["pc"], "mood": ["relaxing"], "time": ["short"] },
  "offset": 0,
  "lang": "tr"
}
```

Üç oyun ile birlikte `total` ve `has_more` döner. "3 tane daha göster" tuşu sadece aynı çağrıyı `offset: 3`, sonra `6`, sonra `9` ile tekrarlıyor. Sıralama deterministik ve eşitlik oyun id'siyle bozuluyor, bu yüzden ikinci sayfa asla tekrar etmiyor veya oyun atlamıyor — sunucu tarafında oturum tutmaya gerek yok.

## Yeni soru ekleme

Sorular kod değil, veri. `app/questions.py` içindeki `QUESTIONS` listesine bir kayıt ekle:

```python
{
    "id": "vibe",
    "type": "single",          # veya "multi"
    "required": True,
    "text": {"en": "Realistic or stylised?", "tr": "Gerçekçi mi, stilize mi?"},
    "options": [
        {
            "id": "stylised",
            "label": {"en": "Stylised", "tr": "Stilize"},
            "effects": {"want_tags": ["pixel-graphics", "cartoon", "hand-drawn"]},
        },
    ],
}
```

Motorun hiçbir yerinde `if answer == "stylised"` gibi bir dal yok — sadece kullanıcının seçtiği seçeneklerin etkilerini topluyor. Kullanılabilir etki anahtarları `questions.py` dosyasının başında açıklanmış.

## Yeni dil ekleme

1. Dil kodunu `app/questions.py` içindeki `SUPPORTED_LANGUAGES` listesine ekle
2. O dosyadaki her `{"en": ..., "tr": ...}` bloğuna çevirini ekle
3. `static/index.html` içindeki dil seçiciye bir buton ekle

Başka hiçbir dosyaya dokunman gerekmiyor. Motor etiket slug'ları üzerinde çalışıyor, onlar çevrilmiyor; sadece kullanıcının gördüğü metinler çevriliyor.

## Sırada ne var

- Sonuçlara beğendim/beğenmedim geri bildirimi toplayıp ağırlıkları buna göre ayarlamak
- "X gibi oyunlar" — sevdiği bir oyunu sorup onun etiket vektörüyle eşleştirmek
- Kullanıcının zaten oynadığı oyunları elemek
- İkinci veri kaynağı olarak Steam etiketleri; türlerden çok daha zenginler
- Tarayıcı açmak istemeyenler için komut satırı sürümü

Katkılar açık — "ağırlıklar yanlış" diyen bir PR bile olsa.

## Lisans

MIT. Oyun verisi RAWG'a aittir ve kendi API şartları kapsamında kullanılır.
