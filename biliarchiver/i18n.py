import gettext

appname = "biliarchiver"

i18n = gettext.translation(
    appname, localedir="biliarchiver/locales", fallback=True, languages=["en"]
)

_ = i18n.gettext
ngettext = i18n.ngettext
