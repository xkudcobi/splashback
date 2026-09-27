In English: [README.md](README.md)

# Splashback

Splashback, yukarıdan bakışlı küçük bir arena oyunu. Gri kasvet yaratıkları içeri sızıp zemindeki renkleri söndürüyor. Sen de ortalıkta koşup onlara boya fırlatıyorsun, ta ki oda yeniden rengârenk olana kadar.

```
python3 play.py
```

Bu kadar. Pencere açıldığında arkada bilgisayar zaten bir tur oynuyor olur. Herhangi bir yere tıkla ya da Enter'a bas, oyun başlasın.

## Nasıl oynanır

| | |
|---|---|
| Yürü | WASD ya da ok tuşları |
| Nişan al | fare |
| Boya at | sol tıkı basılı tut |
| Boya bombası | Boşluk ya da sağ tık |
| Duraklat | Esc |
| Dil değiştir | L ya da sağ üst köşedeki `TR │ EN` düğmesi |

- Fırlattığın her damla zemine renk bırakır. Boyalı karolarda daha hızlı koşarsın, yaratıklar ise yavaşlar.
- Yaratıklar yürüdükleri yere gri kasvet bırakır. Kasvet seni yavaşlatır, onları hızlandırır. Rengin görünmeden önce o kasvetin silinmesi gerekir.
- Bir dalgayı temizlediğinde, zeminin ne kadarı boyalıysa o kadar boya bonusu kazanırsın. Ardından üç güçlendirmeden birini seçersin: daha çevik adımlar, daha geniş sıçramalar, fazladan bir kalp gibi.
- Her beşinci dalgada iri olanlar gelir.

## Yaratıklar

- **Sürüngenler** doğrudan üstüne yürür, arkalarında gri bir iz kalır.
- **Tükürükçüler** mesafeyi korur, uzaktan kasvet topakları fırlatır.
- **Bölünenler** patlayınca iki küçük ve hızlı sürüngene ayrılır.
- **İriler** bir an titrer, sonra hücum eder. Yolundan çekil.

## Neler kaydedilir

Dil, zorluk, ekran sarsıntısı ayarı ve en iyi on skorun oturumlar arasında saklanır. Oyun her dalganın başında da kaydedilir, yani ana ekrandaki **Devam et** seni kaldığın yere geri götürür. Veriler Windows'ta `%APPDATA%\Splashback`, diğer sistemlerde `~/.splashback` klasöründe durur. Başka bir klasör kullanmak istersen `SPLASHBACK_HOME` değişkenini ayarla.

## Dil

Oyun sistem dilini izler (Türkçe ya da İngilizce). Dili istediğin an `TR │ EN` düğmesiyle ya da L tuşuyla değiştirebilirsin, seçimin hatırlanır. Terminalden belirli bir dilde başlatmak için `python3 play.py --lang tr` ya da `--lang en` yazman yeterli.

## Komut satırı

```
python3 play.py                 # oyunu başlat
python3 play.py --lang tr       # Türkçe başlat
python3 play.py --seed 1234     # her oyunda aynı arenalar
python3 play.py --reset         # ayarları, skorları ve kayıtlı oyunu sil
python3 -m splashback           # play.py ile aynı
```

Tek gereksinim tkinter içeren Python 3.8 veya üstü; python.org kurulumlarında tkinter zaten geliyor. Başka hiçbir bağımlılık yok.

## İşin içi

Simülasyon pencereden habersizdir, pencere de hiçbir karar vermez:

- `world.py` bir dalgayı saniyede sabit 60 adımla yürütür: hareket, mermiler, çarpışmalar, toplanan eşyalar. Olup biteni olay listesi olarak bildirir.
- `navigation.py` oyuncunun karosundan dışarı doğru tek bir Dijkstra akış alanı kurar. Bu alan yalnızca oyuncu başka bir karoya geçtiğinde yeniden hesaplanır. Her yaratık kendi karosunun en iyi komşusuna adım atar, bu yüzden yol bulmanın maliyeti düşman sayısıyla artmaz. Görüş hattı ızgara üzerinde adım adım yürüyerek bulunur; her yaratık bunu kendi sırasına göre, dağınık aralıklarla yeniden kontrol eder.
- `physics.py` dairelerin karolara çarpıp kaymasını ve bir spatial hash'i yönetir. Hash'in kovaları bir kez ayrılır, sonra yerinde temizlenir.
- `arena_gen.py` tohuma bağlı, simetrik haritalar üretir. Merkezden ulaşılamayan cepleri duvarla kapatır.
- `game.py` tek durum makinesidir (ana ekran, oyun, duraklatma, güçlendirme, oyun sonu, ayarlar, skorlar). `render.py` bunu yeniden kullanılan canvas öğe havuzlarıyla bir Tk canvas'ına çizer ve yalnızca boyası gerçekten değişen karoları yeniden renklendirir.
- `autopilot.py` ana ekrandaki tanıtım turunu oynar. Testler de onu kullanarak koca dalgalar oynatır.
- Ekranda görünen bütün metinler `strings.py` içinde durur.

Testleri çalıştırmak için:

```
python3 -m unittest discover -s tests
```

## Lisans

MIT
