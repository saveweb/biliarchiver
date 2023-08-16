import gettext
import locale

default_lang, default_enc = locale.getdefaultlocale()

languages = ["en"] if not default_lang.lower().startswith("zh") else ["zh_CN"]

appname = "biliarchiver"

i18n = gettext.translation(
    appname, localedir="biliarchiver/locales", fallback=True, languages=languages
)

_ = i18n.gettext
ngettext = i18n.ngettext
