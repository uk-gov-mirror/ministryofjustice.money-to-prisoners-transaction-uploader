import os
import shutil
import re
from datetime import datetime
from collections import namedtuple

from bankline_parser.data_services import parse_file
from bankline_parser.data_services.enums import TransactionCode
from pysftp import Connection

from .api_client import get_authenticated_connection
from . import settings

DATE_FORMAT = '%d%m%y'

ref_pattern = re.compile('''
    ([A-Za-z][0-9]{4}[A-Za-z]{2}) # match the prisoner number
    .*?                           # skip until next digit
    ([0-9]{1,2})                  # match 1 or 2 digit day of month
    .*?                           # skip until next digit
    ([0-9]{1,2})                  # match 1 or 2 digit month
    .*?                           # skip until next digit
    ([0-9]{2,4})                  # match 2 or 4 digit year
    ''', re.X)
file_pattern = re.compile('''
    YO1A\.REC\.#D\.               # static file format
    (%(code)s)\.                  # our unique account code
    D([0-9]{6})                   # date that file was generated (ddmmyy)
    ''' % {'code': settings.ACCOUNT_CODE}, re.X)


def retrieve_data_services_files():
    # check for existing downloaded files and remove if found
    if os.path.exists(settings.DS_NEW_FILES_DIR):
        shutil.rmtree(settings.DS_NEW_FILES_DIR)
    os.mkdir(settings.DS_NEW_FILES_DIR)

    # check if we recorded date of last file downloaded
    last_date = None
    if (os.path.exists(settings.DS_LAST_DATE_FILE)):
        with open(settings.DS_LAST_DATE_FILE) as f:
            last_date_str = f.read()
            last_date = datetime.strptime(last_date_str, DATE_FORMAT)

    new_files = []
    new_dates = []
    with Connection(settings.SFTP_HOST, username=settings.SFTP_USER,
                    private_key=settings.SFTP_PRIVATE_KEY) as conn:
        with conn.cd(settings.SFTP_DIR):
            dir_listing = conn.listdir()
            for filename in dir_listing:
                m = file_pattern.match(filename)

                if m:
                    date = datetime.strptime(m.group(2), DATE_FORMAT)
                    if last_date is None or date > last_date:
                        local_path = os.path.join(settings.DS_NEW_FILES_DIR,
                                                  filename)
                        new_files.append(local_path)
                        new_dates.append(date)
                        conn.get(filename, local_path=local_path)

    # find last dated file
    if len(new_dates) > 0:
        new_last_date = sorted(new_dates)[-1]

    FileDownload = namedtuple('FileDownload', ['new_last_date', 'new_files'])
    return FileDownload(new_last_date, new_files)


def upload_transactions_from_files(files):
    transactions = []
    for filename in files:
        transactions += get_transactions_from_file(filename)
    conn = get_authenticated_connection()
    conn.bank_admin.transactions.post(transactions)


def get_transactions_from_file(filename):
    with open(filename) as f:
        data_services_file = parse_file(f)

    if not data_services_file.is_valid():
        raise ValueError("%s invalid: %s" % (filename, data_services_file.errors))

    transactions = []
    for record in data_services_file:
        if (record.transaction_code == TransactionCode.credit_bacs_credit or
                record.transaction_code == TransactionCode.credit_sundry_credit):
            transaction = {}
            transaction['amount'] = record.amount
            transaction['sender_sort_code'] = record.originators_sort_code
            transaction['sender_account_number'] = record.originators_account_number
            transaction['sender_name'] = record.transaction_description
            transaction['reference'] = record.reference_number
            transaction['received_at'] = record.date

            parsed_ref = parse_reference(record.reference_number)
            if parsed_ref:
                number, dob = parsed_ref
                transaction['prisoner_number'] = number
                transaction['prisoner_dob'] = parsed_ref

            transactions.append(transaction)
    return transactions


def parse_reference(ref):
    m = ref_pattern.match(ref)

    if m:
        date_str = '%s/%s/%s' % (m.group(2), m.group(3), m.group(4))
        try:
            dob = datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            dob = datetime.strptime(date_str, '%d/%m/%y')

            # set correct century for 2 digit year
            if dob.year > datetime.today().year - 10:
                dob = dob.replace(year=dob.year-100)

        ParsedReference = namedtuple('ParsedReference', ['prisoner_number', 'prisoner_dob'])
        return ParsedReference(m.group(1), dob)


def main():
    last_date, files = retrieve_data_services_files()
    print("Downloaded...")
    for filename in files:
        print(filename)
    print("Uploading...")
    upload_transactions_from_files(files)
    print("Upload complete.")

    print("Files recorded as processed up to " % last_date)
    if (os.path.exists(settings.DS_LAST_DATE_FILE)):
        os.unlink(settings.DS_LAST_DATE_FILE)
    with open(settings.DS_LAST_DATE_FILE, 'w+') as f:
        f.write(datetime.strftime(last_date, DATE_FORMAT))
