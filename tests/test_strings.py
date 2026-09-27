import string
import unittest

from splashback.strings import (STRINGS, detect_system_lang, normalize_lang, other_lang, t)

def placeholders(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}

class StringTableTests(unittest.TestCase):
    def test_both_languages_have_the_same_keys(self):
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["tr"]))

    def test_placeholders_match_between_languages(self):
        for key, english in STRINGS["en"].items():
            with self.subTest(key=key):
                self.assertEqual(placeholders(english), placeholders(STRINGS["tr"][key]))

    def test_no_empty_strings(self):
        for lang, table in STRINGS.items():
            for key, value in table.items():
                with self.subTest(lang=lang, key=key):
                    self.assertTrue(value.strip())

    def test_formatting_and_fallbacks(self):
        self.assertEqual(t("en", "hud_wave", wave=3), "Wave 3")
        self.assertEqual(t("tr", "hud_wave", wave=3), "Dalga 3")
        self.assertEqual(t("xx", "menu_play"), "Play")
        self.assertEqual(t("en", "no_such_key"), "no_such_key")

    def test_every_perk_and_pickup_has_text(self):
        from splashback.perks import PERKS
        from splashback.world import PICKUP_KINDS
        for lang in STRINGS:
            for pid in PERKS:
                self.assertIn("perk_" + pid, STRINGS[lang])
                self.assertIn("perk_%s_desc" % pid, STRINGS[lang])
            for kind in PICKUP_KINDS:
                self.assertIn("pickup_" + kind, STRINGS[lang])

class LanguageDetectionTests(unittest.TestCase):
    def test_env_variables_win(self):
        self.assertEqual(detect_system_lang({"LANG": "tr_TR.UTF-8"}), "tr")
        self.assertEqual(detect_system_lang({"LC_ALL": "en_US.UTF-8", "LANG": "tr_TR"}), "en")
        self.assertEqual(detect_system_lang({"LANGUAGE": "tr:en"}), "tr")

    def test_falls_back_to_locale_then_english(self):
        self.assertEqual(detect_system_lang({}, lambda: ("Turkish_Türkiye", "1254")), "tr")
        self.assertEqual(detect_system_lang({}, lambda: ("de_DE", "UTF-8")), "en")
        self.assertEqual(detect_system_lang({}, lambda: (None, None)), "en")

        def broken():
            raise ValueError("unknown locale")
        self.assertEqual(detect_system_lang({}, broken), "en")

    def test_normalize(self):
        self.assertEqual(normalize_lang("TR"), "tr")
        self.assertEqual(normalize_lang("en-GB"), "en")
        self.assertIsNone(normalize_lang("fr"))
        self.assertIsNone(normalize_lang(""))
        self.assertEqual(other_lang("tr"), "en")
        self.assertEqual(other_lang("en"), "tr")

if __name__ == "__main__":
    unittest.main()
