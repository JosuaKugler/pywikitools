"""
4training.net library

Contains common functions, many of wrapping API calls
We didn't name this 4traininglib.py because starting a python file name with a number causes problems
"""
import logging
import re
from typing import List, Optional
import requests

BASEURL: str = "https://www.4training.net"
APIURL: str = BASEURL + "/mediawiki/api.php"
logger = logging.getLogger('4training.lib')

def get_worksheet_list() -> list:
    """
    Returns the list of all worksheets. For now hard-coded as this doesn't change very often. Could be changed to
    retrieve that information from the backend.
    @param: -
    @return: worksheet_list (list): List of all worksheets.
    """
    return ["God's_Story_(five_fingers)", "God's_Story_(first_and_last_sacrifice)",
            "Baptism", "Prayer", "Forgiving_Step_by_Step", "Confessing_Sins_and_Repenting",
            "Time_with_God", "Hearing_from_God", "Church", "Healing",
            "My_Story_with_God", "Bible_Reading_Bookmark", "The_Three-Thirds_Process",
            # "Bible_Reading_Bookmark_(Seven_Stories_full_of_Hope)",
            # "Bible_Reading_Bookmark_(Starting_with_the_Creation)",
            "Training_Meeting_Outline", "A_Daily_Prayer",
            "Overcoming_Fear_and_Anger", "Getting_Rid_of_Colored_Lenses", "Family_and_our_Relationship_with_God",
            "Overcoming_Negative_Inheritance",
            "Forgiving_Step_by_Step:_Training_Notes", "Leading_Others_Through_Forgiveness",
            "The_Role_of_a_Helper_in_Prayer", "Four_Kinds_of_Disciples"]

def get_file_types() -> list:
    """
    Returns the supported file types.
    @param: -
    @return: file_types (list): list of supported file types
    """
    return ['pdf', 'odt', 'odg']


def get_language_direction(languagecode: str) -> str:
    """ Returns language direction 'rtl' or 'ltr'
    This is hard-coded here.
    It is possible to request this from the mediawiki API e.g. with
    https://www.4training.net/mediawiki/api.php?action=query&titles=Prayer/ckb&prop=info
    but this has the cost of an extra API call...
    """
    RTL = ["ar", "fa", "ckb", "ar-urdun", "ps", "ur"] # TODO perhaps not complete
    if languagecode in RTL:
        return "rtl"
    return "ltr"

def get_language_name(language_code: str, translate_to: Optional[str] = None) -> Optional[str]:
    """ Returns the name of a language as either the autonym or translated into another language
    This function is calling the mediawiki {{#language:}} parser function and does no additional checks
    See https://www.mediawiki.org/wiki/Help:Magic_words#Miscellaneous
    Examples:
        get_language_name('de') = 'Deutsch'
        get_language_name('de','en') = 'German'
        get_language_name('nonsense') = 'nonsense' FYI
    @param language_code: identifies the language we're interested in
    @param translate_to: optional target language the language name should be translated into (None returns autonym)
    @return Language name if successful
    @return None in case of error
    """
    lang_parameter = language_code
    if isinstance(translate_to, str):
        lang_parameter += '|' + translate_to
    response = requests.get(APIURL, params={
        'action' : 'parse',
        'text' : '{{#language:' + lang_parameter + '}}',
        'contentmodel' : 'wikitext',
        'format' : 'json',
        'prop' : 'text',
        'disablelimitreport' : 'true'})
    if 'parse' in response.json():
        if 'text' in response.json()['parse']:
            if '*' in response.json()['parse']['text']:
                langname = re.search('<p>([^<]*)</p>', response.json()['parse']['text']['*'], re.MULTILINE)
                if langname:
                    return langname.group(1).strip()
                return None
    return None

def get_file_url(filename: str):
    """ Return the full URL of the requested file

    @return string with the URL or None in case of an error
    """
    # request url for downloading odt-file
    parameters = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": "File:" + filename,
        "iiprop": "url"
    }

    response_url = requests.get(APIURL, params=parameters)
    logger.info("Retrieving URL of file " + filename + "... " + str(response_url.status_code))
    url_json = response_url.json()
    logger.debug(url_json)

    # check if there is only one page in the answer and get its name
    if len(list(url_json["query"]["pages"])) == 1:
        page_number = list(url_json["query"]["pages"])[0]
    else:
        logger.warning(F"fortraininglib:get_file_url: Couldn't get URL of file {filename}: multiple pages detected")
        return None

    if int(page_number) == -1:
        logger.info(F"fortraininglib:get_file_url: file {filename} doesn't seem to exist.")
        return None
    return url_json["query"]["pages"][page_number]["imageinfo"][0]["url"]

def get_pdf_name(worksheet: str, languagecode: str):
    """ returns the name of the PDF associated with that worksheet translated into a specific language

    @param languagecode shouldn't be 'en'
    @return None in case we didn't find it
    """
    if languagecode == 'en':
        # This is more complicated: as we need to retrieve the page source and scan it for the name of the PDF file
        response = requests.get(APIURL, params={
            "action" : "query",
            "prop" : "revisions",
            "rvlimit" : 1,
            "rvprop" : "content",
            "format" : "json",
            "titles" : worksheet})
        if not 'query' in response.json():
            return None
        if not 'pages' in response.json()["query"]:
            return None
        pageid = next(iter(response.json()["query"]["pages"]))
        if not 'revisions' in response.json()["query"]["pages"][pageid]:
            return None
        if not len (response.json()["query"]["pages"][pageid]['revisions']) > 0:
            return None
        if not '*' in response.json()["query"]["pages"][pageid]['revisions'][0]:
            return None
        content = response.json()["query"]["pages"][pageid]['revisions'][0]['*']
        # Now we have the page source, scan it for the PDF file name now
        pdfdownload = re.search('{{PdfDownload[^}]*}', content)
        if not pdfdownload:
            return None
        pdffile = re.search(r'\w+\.pdf', pdfdownload.group())
        if pdffile:
            return pdffile.group()
        return None

    # It's a translation - that's easier, we just look through the translation unit and find the one of the PDF file
    response = requests.get(APIURL, params={
        "action" : "query",
        "format" : "json",
        "list" : "messagecollection",
        "mcgroup" : "page-" + worksheet,
        "mclanguage" : languagecode})
    translations = response.json()["query"]["messagecollection"]
    for t in translations:
        if re.search(r'\.pdf$', t["definition"]):
            pdf = t["translation"]
    return pdf

def get_msggroupstats(page: str) -> str:
    """ Returns messagegroupstats json from the given page.
        In case of an error, returns empty string or None.
        Example: https://www.4training.net/mediawiki/api.php?action=query&meta=messagegroupstats&mgsgroup=page-Church
    """
    counter = 1
    while counter < 4:
        # Tricky: Often we need to run this query for a second time so that all data is gathered.
        response = requests.get(APIURL, params={
            'action' : 'query',
            'meta' : 'messagegroupstats',
            'format' : 'json',
            'mgsgroup': 'page-' + page})
        logger.info(f"Retrieving translation information of {page}, try #{counter}. Response: {response.status_code}")
        json = response.json()

        if not 'continue' in json:  # Now we have a complete response
            break
        counter += 1
    if ('continue' in json) or (counter == 4):
        logger.warning(f"Error while trying to get all translations of {page} - tried 3 times, still no result")
    if not 'query' in json:
        return ""
    if not 'messagegroupstats' in json['query']:
        return ""
    else:
        return json


def list_page_translations(page: str) -> List[str]:
    """ Returns a list of language codes of all the existing translations of the page
    Unfinished translations will be ignored (TODO: make the details of this configurable by an optional parameter)

    Example: https://www.4training.net/mediawiki/api.php?action=query&meta=messagegroupstats&mgsgroup=page-Church
    @return a list with language codes like ['en','de','ar','kn']
            In case no other translation exists the result will be ['en']
            In case of an error the list will be empty []
    """
    json = get_msggroupstats(page)
    if json == "":
        return []

    available_translations = []     # list of language codes of the available translations
    for line in json['query']['messagegroupstats']:
        if line['translated'] > 0:
            # This looks like an unfinished translation, we just ignore it
            if (line['total'] - line['fuzzy'] - line['translated']) > 4:
                logger.info(f"Ignoring translation {page}/{line['language']} ({line['translated']}+{line['fuzzy']}"
                            f"/{line['total']} translation units translated)")
                continue
            available_translations.append(line['language'])
            if ((line['translated'] + line ['fuzzy']) < line['total']):
                logger.warning("Warning: incomplete translation " + str(line['translated']) + '+' + str(line['fuzzy'])
                        + '/' + str(line['total']) + ' (' + page + '/' + line['language'] + ')')

    return available_translations

def list_page_templates(page: str) -> List[str]:
    """ Returns list of templates that are transcluded by a given page
    Strips potential language code at the end of a template used (e.g. returns 'Template:Italic' and not 'Template:Italic/en')
    See also https://translatewiki.net/w/api.php?action=help&modules=query%2Btemplates
    Example: https://www.4training.net/mediawiki/api.php?action=query&format=json&titles=Bible_Reading_Bookmark&prop=templates
    @return empty list in case of an error
    """
    response = requests.get(APIURL, params={
        'action': 'query',
        'format': 'json',
        'titles' : page,
        'prop': 'templates'})
    json = response.json()
    if not 'query' in json:
        return []
    if not 'pages' in json['query']:
        return []
    if len(list(json["query"]["pages"])) == 1:
        pageid = list(json["query"]["pages"])[0]
    else:
        logger.warning("fortraininglib:list_page_templates: Error, multiple pages detected")
        return []
    if not 'templates' in json['query']['pages'][pageid]:
        return []
    result = []
    for line in json['query']['pages'][pageid]['templates']:
        if 'title' in line:
            language_code = line['title'].find('/')
            if language_code == -1:
                result.append(line['title'])
            else:
                result.append(line['title'][0:language_code])
    return result


def get_translation_units(worksheet: str, languagecode: str):
    """
    List the translation units of worksheet translated into the language identified by languagecode
    Example: https://www.4training.net/mediawiki/api.php?action=query&format=json&list=messagecollection&mcgroup=page-Forgiving_Step_by_Step&mclanguage=de
    @return if successful than returns the structure as is in response.json()["query"]["messagecollection"]
    @return on error: returns string with error message
    """
    parameters = {
        "action": "query",
        "format": "json",
        "list": "messagecollection",
        "mcgroup": "page-" + worksheet,
        "mclanguage": languagecode,
    }

    response = requests.get(APIURL, params=parameters)
    logger.info(F"Retrieving translation of {worksheet} into language {languagecode}... {response.status_code}")
    json = response.json()
    if "error" in json:
        if "info" in json["error"]:
            return "Couldn't get translation units. Error: " + json["error"]["info"]
        return "Couldn't get translation units. Strange error."
    if not "query" in json:
        return "Couldn't get translation units. Some serious error"
    if not "messagecollection" in json["query"]:
        return "Couldn't get translation units. Unexpected error."
    return json["query"]["messagecollection"]

def title_to_message(title: str) -> str:
    """Converts a mediawiki title to its corresponding system message
    Examples:
        Prayer -> sidebar-prayer
        Forgiving_Step_by_Step -> sidebar-forgivingstepbystep
        The_Three-Thirds_Process -> sidebar-thethreethirdsprocess
        God's_Story_(five_fingers) -> sidebar-godsstory-fivefingers
    """
    ret = title.replace("-", '')
    ret = ret.replace('_(', '-')
    ret = ret.replace(')', '')
    ret = ret.replace("'", '')
    ret = ret.replace("_", '')
    ret = ret.replace(':', '')
    ret = ret.lower()
    return 'sidebar-' + ret

def expand_template(raw_template: str) -> str:
    """
    TODO more documentation
    https://www.4training.net/mediawiki/api.php?action=expandtemplates&text={{CC0Notice/de|1.3}}&prop=wikitext&format=json
    """
    response = requests.get(APIURL, params={
        "action": "expandtemplates",
        "text": raw_template,
        "prop": "wikitext",
        "format": "json"})
    if "expandtemplates" in response.json():
        if "wikitext" in response.json()["expandtemplates"]:
            return response.json()["expandtemplates"]["wikitext"]
    logger.warning(f"Warning: couldn't expand template {raw_template}")
    return ""

def get_cc0_notice(version: str, languagecode: str) -> str:
    """
    Returns the translated CC0 notice (https://www.4training.net/Template:CC0Notice)
    @param version Version number to put in
    @param languagecode Which language to translate it
    @return The translated notice (for footers in worksheets)
    @return string with a TODO in case the translation doesn't exist
    """
    expanded = expand_template("{{CC0Notice/" + languagecode + "|" + version + "}}")
    if "mw-translate-fuzzy" in expanded:
        logger.warning("Warning: Template:CC0Notice doesn't seem to be correctly translated into this language."
                       "Please check https://www.4training.net/Template:CC0Notice")
    if "Template:CC0Notice" in expanded:
        logger.warning("Warning: Template:CC0Notice doesn't seem to be translated into this language."
                       "Please translate https://www.4trai  ning.net/Template:CC0Notice")
        return "TODO translate https://www.4training.net/Template:CC0Notice"
    return expanded

# Other possibly relevant API calls:
# https://www.4training.net/mediawiki/api.php?action=query&meta=messagetranslations&mttitle=Translations:Church/44
# Is equivalent to https://www.4training.net/Special:Translations?message=Church%2F44&namespace=1198
# Directly lists all translations of one specific translation unit