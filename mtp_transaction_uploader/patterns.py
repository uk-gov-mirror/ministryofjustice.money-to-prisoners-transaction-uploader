import re

from . import settings


_PRISONER_PATTERNS = {
    'number': '''
        (?P<number>[A-Z][0-9]{4}[A-Z]{2})  # match prisoner number
    ''',
    'date_of_birth': '''
        (?P<day>[0-9]{1,2})          # match 1 or 2 digit day of month
        [^0-9]*                      # skip until next digit
        (?P<month>[0-9]{1,2})        # match 1 or 2 digit month
        [^0-9]*                      # skip until next digit
        (?P<year>[0-9]{4}|[0-9]{2})  # match 4 or 2 digit year
    '''
}
CREDIT_REF_PATTERN = re.compile('''
    ^
    [^A-Z]*              # skip until first letter
    %(number)s
    [^0-9A-Z]*           # skip until dob, forbid trailing letters as they can be typos
    %(date_of_birth)s
    [^0-9]*              # forbid trailing numbers as they can be typos
    $
''' % _PRISONER_PATTERNS, re.X | re.I)
CREDIT_REF_PATTERN_REVERSED = re.compile('''
    ^
    [^0-9]*              # skip until first digit
    %(date_of_birth)s
    [^0-9A-Z]*           # skip until prisoner number, forbid trailing digits as they can be typos
    %(number)s
    [^A-Z]*              # forbid trailing letters as they can be typos
    $
''' % _PRISONER_PATTERNS, re.X | re.I)

FILE_PATTERN_STR = (
    '''
    Y01A\.CARS\.\#D\.             # static file format
    %(code)s\.                    # our unique account code
    D(?P<date>[0-9]{6})           # date that file was generated (ddmmyy)
    '''
)

EIGHT_DIGIT = re.compile('[0-9]{8}')
NINE_DIGIT = re.compile('[0-9]{9}')
TEN_DIGIT = re.compile('[0-9]{10}')
ELEVEN_DIGIT = re.compile('[0-9]{11}')
FOURTEEN_DIGIT = re.compile('[0-9]{14}')
N_DIGIT = re.compile('[0-9]+')
NINE_DIGIT_WITH_TRAILING_X = re.compile('[0-9]{9}[0-9Xx]')

ROLL_NUMBER_PATTERNS = {
    '621719': TEN_DIGIT,
    '623045': {None: EIGHT_DIGIT},
    '209778': {'00968773': N_DIGIT},
    '134000': {None: re.compile('[0-9]{3}([A-Za-z] |[A-Za-z]{2})[0-9]{6}[A-Za-z]')},
    '134012': FOURTEEN_DIGIT,
    '134013': FOURTEEN_DIGIT,
    '134014': FOURTEEN_DIGIT,
    '134015': FOURTEEN_DIGIT,
    '134016': FOURTEEN_DIGIT,
    '134017': FOURTEEN_DIGIT,
    '571184': {'53731530': N_DIGIT},
    '571327': {None: re.compile('[0-9]{8,9}')},
    '201722': {'40338346': TEN_DIGIT},
    '609595': '.*',
    '207842': {'70798924': NINE_DIGIT},
    '205377': {'50244961': re.compile('[0-9]{9,11}')},
    '161622': {'11758805': NINE_DIGIT_WITH_TRAILING_X},
    '401903': {'40277061': EIGHT_DIGIT},
    '570055': {None: re.compile('[0-9]{8,9}')},
    '089048': {'70715024': NINE_DIGIT},
    '839207': {None: N_DIGIT},
    '601106': {'13761536': NINE_DIGIT_WITH_TRAILING_X},
    '089072': {'70361591': TEN_DIGIT},
    '151000': {'23114065': NINE_DIGIT},
    '402311': {'01246356': NINE_DIGIT_WITH_TRAILING_X},
    '402419': {'81228218': ELEVEN_DIGIT},
    '234448': {'00004000': NINE_DIGIT},
    '622497': {None: re.compile('[A-Za-z]{2,3}[0-9]{7}[A-Za-z]{3}')},
    '402715': {'12440040': TEN_DIGIT},
    '402801': {'11012258': ELEVEN_DIGIT},
    '300080': {'01781004': NINE_DIGIT},
    '089000': {'70127065': TEN_DIGIT},
    '205562': {'10613185': EIGHT_DIGIT},
    '204908': {'70608386': ELEVEN_DIGIT},
    '609495': TEN_DIGIT,
    '403214': {'10572780': re.compile('[A-Za-z]{3}[0-9]{7}[A-Za-z]{3}')},
    '403427': {'10600717': NINE_DIGIT_WITH_TRAILING_X},
    '402024': {'90614629': TEN_DIGIT},
    '070093': {
        '33333334': re.compile('([0-9]{4}/[0-9]{8,9}|[0-9]{6}-[0-9]{3}|'
                               '[0-9]{2}-[0-9]{6}-[0-9]{5}|'
                               '[0-9]{3}-[0-9]-[0-9]{8}-[0-9]{2})')
    },
    '622874': {None: TEN_DIGIT},
    '235954': {'00000008': re.compile('([A-Za-z0-9]{3}[0-9]{7}[A-Za-z0-9]{3}|[0-9]{9})')},
    '608009': {'96875364': TEN_DIGIT},
    '601621': {'77173163': NINE_DIGIT_WITH_TRAILING_X},
    '201815': {'90653535': N_DIGIT},
    '207405': {'00775991': EIGHT_DIGIT},
    '090000': {'00050005': re.compile('[A-Za-z][0-9]{8}([A-Za-z]{3})?')},
    '830608': {'00255419': re.compile('[0-9]{4}-?[0-9]{5}-?[0-9Xx]')},
    '404303': {'81645846': re.compile('[A-Za-z]{3}[0-9]{7}[A-Za-z]{3}')},
    '309546': {'01464485': NINE_DIGIT},
    '202717': {'70885096': EIGHT_DIGIT},
    '086115': {'00000515': N_DIGIT},
    '404613': {'91066277': N_DIGIT},
    '609204': TEN_DIGIT,
    '622337': TEN_DIGIT
}


class PaymentIdentifier:

    def __init__(self, account_number, sort_code, reference):
        self.account_number = account_number
        self.sort_code = sort_code
        self.reference = reference

    def _field_matches(self, field, value):
        value = value.strip() if value else value
        return field is None or field == value

    def matches(self, account_number, sort_code, reference):
        return (
            self._field_matches(self.account_number, account_number) and
            self._field_matches(self.sort_code, sort_code) and
            self._field_matches(self.reference, reference)
        )


ADMINISTRATIVE_IDENTIFIERS = [
    PaymentIdentifier(
        settings.NOMS_AGENCY_ACCOUNT_NUMBER, settings.NOMS_AGENCY_SORT_CODE, None
    ),
    PaymentIdentifier(
        None, None, settings.WORLDPAY_SETTLEMENT_REFERENCE
    ),
]
