import asyncio
import unittest
from decimal import Decimal, InvalidOperation

from aioresponses import aioresponses

from hummingbot.data_feed.custom_api_data_feed import CustomAPIDataFeed


class TestCustomApiDataFeed(unittest.TestCase):

    def test_init(self):
        feed = CustomAPIDataFeed('fakeUrl')

        self.assertEqual(feed.name, 'custom_api')
        self.assertEqual(feed.api_url, 'fakeUrl')
        self.assertEqual(feed.update_interval, 5.0)
        self.assertEqual(feed.max_price_age, -1)
        self.assertEqual(feed.health_check_endpoint, 'fakeUrl')

    def test_init_throws_when_max_price_age_less_than_update_interval(self):
        with self.assertRaises(ValueError):
            CustomAPIDataFeed('fakeUrl', 60.0, 50)

    def test_init_with_custom_params(self):
        feed = CustomAPIDataFeed('fakeUrl', 10.0, 30)
        self.assertEqual(feed.update_interval, 10.0)
        self.assertEqual(feed.max_price_age, 30)

    @aioresponses()
    @unittest.mock.patch('time.time')
    def test_price_is_updated_when_api_response_is_valid(self, mock_api, mock_time):
        mock_timestamp = 1231006505
        mock_price = 1.09213849
        mock_time.return_value = mock_timestamp
        mock_api.get(url='fakeUrl', body=str(mock_price))

        feed = CustomAPIDataFeed('fakeUrl')
        asyncio.get_event_loop().run_until_complete(feed.fetch_price())

        self.assertEqual(feed.get_price(), Decimal(str(mock_price)))
        self.assertEqual(feed.last_updated_timestamp, mock_timestamp)

    @aioresponses()
    def test_price_is_not_updated_when_api_response_is_invalid(self, mock_api):
        initial_price = '1.0'
        mock_api.get(url='fakeUrl', body=initial_price)
        feed = CustomAPIDataFeed('fakeUrl')

        asyncio.get_event_loop().run_until_complete(feed.fetch_price())
        self.assertEqual(feed.get_price(), Decimal(initial_price))

        with self.assertRaises(Exception):
            mock_api.get(url='fakeUrl', status=500, body="10.0")
            asyncio.get_event_loop().run_until_complete(feed.fetch_price())

        self.assertEqual(feed.get_price(), Decimal(initial_price))

        with self.assertRaises(InvalidOperation):
            mock_api.get(url='fakeUrl', status=200, body="invalid_price")
            asyncio.get_event_loop().run_until_complete(feed.fetch_price())

        self.assertEqual(feed.get_price(), Decimal(initial_price))

    @aioresponses()
    @unittest.mock.patch('time.time')
    def test_price_is_invalidated_when_last_updated_exceeds_max_age(self, mock_api, mock_time):
        mock_timestamp = 1231006505
        mock_price = 1.09213849
        mock_time.return_value = mock_timestamp
        mock_api.get(url='fakeUrl', body=str(mock_price))

        feed = CustomAPIDataFeed('fakeUrl', max_price_age=10)
        asyncio.get_event_loop().run_until_complete(feed.fetch_price())

        self.assertEqual(feed.get_price(), Decimal(str(mock_price)))
        self.assertEqual(feed.last_updated_timestamp, mock_timestamp)

        mock_time.return_value = mock_timestamp + feed.max_price_age + 1
        self.assertTrue(feed.get_price().is_nan())

    @aioresponses()
    @unittest.mock.patch('time.time')
    def test_price_is_not_invalidated_when_max_age_is_disabled(self, mock_api, mock_time):
        mock_timestamp = 1231006505
        initial_price = 1.09213849
        mock_time.return_value = mock_timestamp
        mock_api.get(url='fakeUrl', body=str(initial_price))

        feed = CustomAPIDataFeed('fakeUrl')
        asyncio.get_event_loop().run_until_complete(feed.fetch_price())

        self.assertEqual(feed.get_price(), Decimal(str(initial_price)))
        self.assertEqual(feed.last_updated_timestamp, mock_timestamp)

        far_timestamp = mock_timestamp + 1000000
        mock_time.return_value = far_timestamp
        self.assertEqual(feed.get_price(), Decimal(str(initial_price)))