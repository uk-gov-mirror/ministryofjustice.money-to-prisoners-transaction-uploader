from unittest import mock, TestCase
from datetime import datetime
import io

from mtp_transaction_uploader import upload


class ReferenceParsingTestCase(TestCase):

    def _test_successful_parse(self, reference, prisoner_number, prisoner_dob):
        parsed_number, parsed_dob = upload.parse_reference(reference)
        self.assertEqual(parsed_number, prisoner_number)
        self.assertEqual(parsed_dob, prisoner_dob)

    def test_correct_format_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_no_space_parses(self):
        self._test_successful_parse(
            'A1234GY09/12/86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_arbitrary_divider_parses(self):
        self._test_successful_parse(
            'A1234GY:::09/12/1986', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_hyphenated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 09-12-86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_non_separated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 091286', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_non_zero_padded_date_parses(self):
        self._test_successful_parse(
            'A1234GY 9/6/86', 'A1234GY', datetime(1986, 6, 9)
        )

    def test_four_digit_year_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/1986', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_invalid_prisoner_number_does_not_parse(self):
        self.assertEqual(upload.parse_reference('A1234Y 09/12/1986'), None)

    def test_invalid_year_does_not_parse(self):
        self.assertEqual(upload.parse_reference('A1234GY 1/1/1'), None)


class FilenameParsingTestCase(TestCase):

    def test_correct_format_returns_correct_date(self):
        filename = 'YO1A.REC.#D.444444.D091214'
        expected_date = datetime(2014, 12, 9).date()
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_datetime.date())

    def test_correct_format_returns_correct_date_pre_2000(self):
        filename = 'YO1A.REC.#D.444444.D091299'
        expected_date = datetime(1999, 12, 9).date()
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_datetime.date())

    def test_incorrect_format_returns_none(self):
        filename = 'unrelated_file'
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_datetime)

    def test_incorrect_account_code_returns_none(self):
        filename = 'YO1A.REC.#D.555555.D091214'
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_datetime)


@mock.patch('mtp_transaction_uploader.upload.settings')
@mock.patch('mtp_transaction_uploader.upload.Connection')
class FileDownloadTestCase(TestCase):

    def test_download_new_files(self, mock_connection_class, mock_settings):
        dirlist = [
            'YO1A.REC.#D.444444.D091214',
            'YO1A.REC.#D.444444.D101214',
            'YO1A.REC.#D.444444.D111214',
            'YO1A.REC.#D.444444.D121214',
            'YO1A.REC.#D.444444.D131214',
            'YO1A.REC.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        new_dates, new_filenames = upload.download_new_files(None)

        self.assertEqual([
            datetime(2014, 12, 9).date(),
            datetime(2014, 12, 10).date(),
            datetime(2014, 12, 11).date(),
            datetime(2014, 12, 12).date(),
            datetime(2014, 12, 13).date(),
            datetime(2014, 12, 14).date(),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/YO1A.REC.#D.444444.D091214',
            '/YO1A.REC.#D.444444.D101214',
            '/YO1A.REC.#D.444444.D111214',
            '/YO1A.REC.#D.444444.D121214',
            '/YO1A.REC.#D.444444.D131214',
            '/YO1A.REC.#D.444444.D141214',
        ], new_filenames)

    def test_download_new_files_skips_other_accounts(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'YO1A.REC.#D.444444.D091214',
            'YO1A.REC.#D.444444.D101214',
            'YO1A.REC.#D.444444.D111214',
            'YO1A.REC.#D.444444.D121214',
            'YO1A.REC.#D.555555.D131214',
            'YO1A.REC.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        new_dates, new_filenames = upload.download_new_files(None)

        self.assertEqual([
            datetime(2014, 12, 9).date(),
            datetime(2014, 12, 10).date(),
            datetime(2014, 12, 11).date(),
            datetime(2014, 12, 12).date(),
            datetime(2014, 12, 14).date(),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/YO1A.REC.#D.444444.D091214',
            '/YO1A.REC.#D.444444.D101214',
            '/YO1A.REC.#D.444444.D111214',
            '/YO1A.REC.#D.444444.D121214',
            '/YO1A.REC.#D.444444.D141214',
        ], new_filenames)

    def test_download_new_files_skips_old_files(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'YO1A.REC.#D.444444.D091214',
            'YO1A.REC.#D.444444.D101214',
            'YO1A.REC.#D.444444.D111214',
            'YO1A.REC.#D.444444.D121214',
            'YO1A.REC.#D.444444.D131214',
            'YO1A.REC.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        new_dates, new_filenames = upload.download_new_files(datetime(2014, 12, 11))

        self.assertEqual([
            datetime(2014, 12, 12).date(),
            datetime(2014, 12, 13).date(),
            datetime(2014, 12, 14).date(),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/YO1A.REC.#D.444444.D121214',
            '/YO1A.REC.#D.444444.D131214',
            '/YO1A.REC.#D.444444.D141214',
        ], new_filenames)

    def test_download_new_files_skips_large_files(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'YO1A.REC.#D.444444.D091214',
            'YO1A.REC.#D.444444.D101214',
            'YO1A.REC.#D.444444.D111214',
            'YO1A.REC.#D.444444.D121214',
            'YO1A.REC.#D.444444.D131214',
            'YO1A.REC.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.side_effect = [
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 100000000})(),
            type("", (), {'st_size': 1000})(),
        ]

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        new_dates, new_filenames = upload.download_new_files(None)

        self.assertEqual([
            datetime(2014, 12, 9).date(),
            datetime(2014, 12, 10).date(),
            datetime(2014, 12, 11).date(),
            datetime(2014, 12, 12).date(),
            datetime(2014, 12, 14).date(),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/YO1A.REC.#D.444444.D091214',
            '/YO1A.REC.#D.444444.D101214',
            '/YO1A.REC.#D.444444.D111214',
            '/YO1A.REC.#D.444444.D121214',
            '/YO1A.REC.#D.444444.D141214',
        ], new_filenames)


class RetrieveNewFilesTestCase(TestCase):

    @mock.patch('mtp_transaction_uploader.upload.Connection')
    @mock.patch('mtp_transaction_uploader.upload.settings')
    @mock.patch('mtp_transaction_uploader.upload.os')
    @mock.patch('mtp_transaction_uploader.upload.shutil')
    @mock.patch('builtins.open')
    def test_retrieve_new_files(
        self,
        mock_open,
        mock_shutil,
        mock_os,
        mock_settings,
        mock_connection_class
    ):
        mock_os.path.exists.side_effect = [False, True]
        mock_open.return_value = io.StringIO("111214")

        dirlist = [
            'YO1A.REC.#D.444444.D091214',
            'YO1A.REC.#D.444444.D101214',
            'YO1A.REC.#D.444444.D111214',
            'YO1A.REC.#D.444444.D121214',
            'YO1A.REC.#D.444444.D131214',
            'YO1A.REC.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'
        mock_os.path.join = lambda a, b: a + b

        new_last_date, new_filenames = upload.retrieve_data_services_files()

        self.assertFalse(mock_shutil.rmtree.called)

        self.assertEqual([
            '/YO1A.REC.#D.444444.D121214',
            '/YO1A.REC.#D.444444.D131214',
            '/YO1A.REC.#D.444444.D141214',
        ], new_filenames)
        self.assertEqual(datetime(2014, 12, 14).date(), new_last_date.date())
