"""Every piece of text the player can see, in English and Turkish.

Nothing else in the package hard-codes user-facing text; call ``t(lang, key)``.
"""

import locale
import os

LANGS = ("en", "tr")
DEFAULT_LANG = "en"

STRINGS = {
    "en": {
        "app_title": "Splashback",
        "tagline": "Paint the arena. Sweep away the gloom.",
        "intro": "Grey gloom creatures crawl in and drain the colour from the floor. Paint them away!",
        "press_to_play": "Click anywhere or press Enter to play",
        "controls_1": "Move: WASD or arrow keys   ·   Aim: mouse   ·   Paint: hold left click",
        "controls_2": "Paint bomb: Space or right click   ·   Pause: Esc   ·   Language: L",
        "demo_label": "demo: the computer is playing",
        "menu_play": "Play",
        "menu_continue": "Continue from wave {wave}",
        "menu_settings": "Settings",
        "menu_scores": "Best scores",
        "menu_quit": "Quit",
        "menu_resume": "Resume",
        "menu_to_title": "Back to title",
        "menu_back": "Back",
        "menu_again": "Play again",
        "hud_wave": "Wave {wave}",
        "hud_score": "Score {score}",
        "hud_bombs": "Bombs {bombs}",
        "hud_painted": "Painted {pct}%",
        "hud_left": "Gloom left: {count}",
        "wave_start": "Wave {wave}",
        "wave_clear": "Wave cleared!",
        "paint_bonus": "Paint bonus +{points}",
        "big_wave": "Big ones incoming!",
        "perk_title": "Pick a boost",
        "perk_hint": "Click a card or press 1, 2 or 3",
        "perk_level": "level {level}",
        "perk_swift": "Quick feet",
        "perk_swift_desc": "Run 12% faster",
        "perk_rapid": "Fast brush",
        "perk_rapid_desc": "Throw paint 18% more often",
        "perk_wide": "Wide splash",
        "perk_wide_desc": "Your splashes cover more floor",
        "perk_heavy": "Thick paint",
        "perk_heavy_desc": "Every blob hits harder",
        "perk_spread": "Twin nozzle",
        "perk_spread_desc": "One more blob per shot",
        "perk_tough": "Big heart",
        "perk_tough_desc": "One more heart, and heal one",
        "perk_bomber": "Bomb bag",
        "perk_bomber_desc": "Carry one more bomb, bag refilled",
        "perk_heal": "Fresh coat",
        "perk_heal_desc": "Heal two hearts",
        "perk_rich": "Rich pigment",
        "perk_rich_desc": "Splashes soak the floor deeper",
        "paused": "Paused",
        "game_over": "The gloom got you",
        "final_score": "Score: {score}",
        "reached_wave": "You reached wave {wave}",
        "new_best": "New best score!",
        "settings_title": "Settings",
        "setting_language": "Language: {value}",
        "lang_name": "English",
        "setting_difficulty": "Difficulty: {value}",
        "diff_easy": "Easy",
        "diff_normal": "Normal",
        "diff_hard": "Hard",
        "setting_shake": "Screen shake: {value}",
        "on": "On",
        "off": "Off",
        "settings_hint": "Click an option to change it. A new difficulty applies to the next game.",
        "scores_title": "Best scores",
        "scores_empty": "No scores yet. Go and paint something!",
        "score_row": "{rank}.   {score} points   ·   wave {wave}   ·   {difficulty}   ·   {date}",
        "pickup_heart": "+1 heart",
        "pickup_bomb": "+1 bomb",
        "pickup_rapid": "Rapid paint!",
        "pickup_triple": "Triple spray!",
        "cli_description": "Splashback: a top-down arena game where you paint away grey gloom creatures.",
        "cli_lang": "interface language (tr or en)",
        "cli_seed": "use a fixed number so every game gets the same arenas",
        "cli_reset": "forget saved settings, scores and the unfinished game",
        "cli_reset_done": "Saved data removed from {path}",
        "cli_no_tk": "This Python has no Tk support, so the game window cannot open. "
                     "Use a Python that ships with tkinter (the python.org installers do).",
        "cli_no_window": "Could not open the game window: {error}",
        "cli_storage_warning": "Could not write to {path}; progress will not be kept this time.",
    },
    "tr": {
        "app_title": "Splashback",
        "tagline": "Arenayı boya, kasveti süpür.",
        "intro": "Gri kasvet yaratıkları içeri sızıp zemindeki renkleri söndürüyor. Hepsini boyayla temizle!",
        "press_to_play": "Oynamak için herhangi bir yere tıkla ya da Enter'a bas",
        "controls_1": "Yürü: WASD ya da ok tuşları   ·   Nişan: fare   ·   Boya: sol tıkı basılı tut",
        "controls_2": "Boya bombası: Boşluk ya da sağ tık   ·   Duraklat: Esc   ·   Dil: L",
        "demo_label": "tanıtım: şu an bilgisayar oynuyor",
        "menu_play": "Oyna",
        "menu_continue": "{wave}. dalgadan devam et",
        "menu_settings": "Ayarlar",
        "menu_scores": "En iyi skorlar",
        "menu_quit": "Çık",
        "menu_resume": "Devam et",
        "menu_to_title": "Ana ekrana dön",
        "menu_back": "Geri",
        "menu_again": "Yeniden oyna",
        "hud_wave": "Dalga {wave}",
        "hud_score": "Skor {score}",
        "hud_bombs": "Bomba {bombs}",
        "hud_painted": "Boyalı %{pct}",
        "hud_left": "Kalan kasvet: {count}",
        "wave_start": "{wave}. dalga",
        "wave_clear": "Dalga temizlendi!",
        "paint_bonus": "Boya bonusu +{points}",
        "big_wave": "İri olanlar geliyor!",
        "perk_title": "Bir güçlendirme seç",
        "perk_hint": "Bir karta tıkla ya da 1, 2, 3 tuşlarından birine bas",
        "perk_level": "seviye {level}",
        "perk_swift": "Çevik adımlar",
        "perk_swift_desc": "%12 daha hızlı koş",
        "perk_rapid": "Hızlı fırça",
        "perk_rapid_desc": "%18 daha sık boya fırlat",
        "perk_wide": "Geniş sıçrama",
        "perk_wide_desc": "Boya lekelerin daha geniş alanı kaplar",
        "perk_heavy": "Koyu boya",
        "perk_heavy_desc": "Her damla daha sert vurur",
        "perk_spread": "Çift ağız",
        "perk_spread_desc": "Her atışta bir damla daha",
        "perk_tough": "Geniş yürek",
        "perk_tough_desc": "Bir kalp daha, üstüne bir kalp iyileşme",
        "perk_bomber": "Bomba çantası",
        "perk_bomber_desc": "Bir bomba fazla taşı, çanta dolsun",
        "perk_heal": "Taze kat",
        "perk_heal_desc": "İki kalp iyileş",
        "perk_rich": "Yoğun pigment",
        "perk_rich_desc": "Sıçramalar zemine daha koyu işler",
        "paused": "Duraklatıldı",
        "game_over": "Kasvet seni yakaladı",
        "final_score": "Skor: {score}",
        "reached_wave": "{wave}. dalgaya kadar geldin",
        "new_best": "Yeni rekor!",
        "settings_title": "Ayarlar",
        "setting_language": "Dil: {value}",
        "lang_name": "Türkçe",
        "setting_difficulty": "Zorluk: {value}",
        "diff_easy": "Kolay",
        "diff_normal": "Normal",
        "diff_hard": "Zor",
        "setting_shake": "Ekran sarsıntısı: {value}",
        "on": "Açık",
        "off": "Kapalı",
        "settings_hint": "Değiştirmek için bir seçeneğe tıkla. Yeni zorluk bir sonraki oyunda geçerli olur.",
        "scores_title": "En iyi skorlar",
        "scores_empty": "Henüz skor yok. Hadi git biraz boya!",
        "score_row": "{rank}.   {score} puan   ·   {wave}. dalga   ·   {difficulty}   ·   {date}",
        "pickup_heart": "+1 kalp",
        "pickup_bomb": "+1 bomba",
        "pickup_rapid": "Seri boya!",
        "pickup_triple": "Üçlü sprey!",
        "cli_description": "Splashback: gri kasvet yaratıklarını boyayla sildiğin, yukarıdan bakışlı bir arena oyunu.",
        "cli_lang": "arayüz dili (tr ya da en)",
        "cli_seed": "sabit bir sayı ver, her oyunda aynı arenalar gelsin",
        "cli_reset": "kayıtlı ayarları, skorları ve yarım kalan oyunu sil",
        "cli_reset_done": "Kayıtlı veriler silindi: {path}",
        "cli_no_tk": "Bu Python kurulumunda Tk desteği yok, bu yüzden oyun penceresi açılamıyor. "
                     "tkinter ile gelen bir Python kullanın (python.org kurulumlarında vardır).",
        "cli_no_window": "Oyun penceresi açılamadı: {error}",
        "cli_storage_warning": "{path} konumuna yazılamadı; bu sefer ilerleme kaydedilmeyecek.",
    },
}

def normalize_lang(value):
    """Map anything that looks like a language tag to 'tr', 'en' or None."""
    if not value:
        return None
    value = str(value).strip().lower()
    if value.startswith("tr") or value.startswith("turkish"):
        return "tr"
    if value.startswith("en") or value.startswith("english"):
        return "en"
    return None

def detect_system_lang(environ=None, getlocale=None):
    """Pick 'tr' when the system locale is Turkish, otherwise 'en'."""
    environ = os.environ if environ is None else environ
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        raw = environ.get(name)
        if raw:
            # LANGUAGE may hold a priority list such as "tr:en".
            return "tr" if raw.split(":")[0].lower().startswith("tr") else "en"
    getlocale = getlocale or locale.getlocale
    try:
        code = getlocale()[0]
    except (ValueError, TypeError, IndexError):
        code = None
    return "tr" if normalize_lang(code) == "tr" else DEFAULT_LANG

def t(lang, key, **params):
    table = STRINGS.get(lang) or STRINGS[DEFAULT_LANG]
    text = table.get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANG].get(key, key)
    return text.format(**params) if params else text

def other_lang(lang):
    return "en" if lang == "tr" else "tr"
