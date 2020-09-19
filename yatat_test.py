"""
Test Yatat module
"""

import os
import sys
import io

from unittest import mock, TestCase
from unittest.mock import patch
import tempfile

import contextlib

from yatat import Archive, Tweet, Decisions, UserInterface, Oops


@contextlib.contextmanager
def managed_io():
    stdout, stderr = sys.stdout, sys.stderr
    try:
        stdio = io.StringIO()
        sys.stdout, sys.stderr = stdio, stdio
        yield stdio
    finally:
        sys.stdout, sys.stderr = stdout, stderr


class TweetTest(TestCase):

    def setUp(self):
        self.json = {}
        self.json["id"] = "0"
        self.json["created_at"] = 'Thu Feb 02 14:05:28 +0000 2012'
        self.json["full_text"] = 'test_text'

    def test_create(self):
        """Handle CSV Tweet."""
        tweet = Tweet(self.json)
        self.assertTrue(tweet.is_tweet())
        self.assertFalse(tweet.is_reply())
        self.assertFalse(tweet.is_retweet())
        self.assertEqual('2012-02-02 14:05:28', tweet.timestamp)
        self.assertEqual('test_text', tweet.text)
        self.assertIsNone(tweet.in_reply_to_status_id)
        self.assertTrue(tweet.timestamp[:10] in str(tweet))
        self.assertTrue(str(tweet.tweet_id) in str(tweet))
        self.assertTrue(tweet.text in str(tweet))

    def test_create_reply(self):
        """Handle Reply."""
        self.json["in_reply_to_status_id"] = "7"
        tweet = Tweet(self.json)
        self.assertTrue(tweet.is_reply())
        self.assertFalse(tweet.is_tweet())
        self.assertFalse(tweet.is_retweet())
        self.assertEqual("7", tweet.in_reply_to_status_id)

    def test_create_retweet(self):
        """Handle Retweet."""
        self.json["full_text"] = 'RT @TEST ...'
        tweet = Tweet(self.json)
        self.assertTrue(tweet.is_retweet())
        self.assertFalse(tweet.is_tweet())
        self.assertFalse(tweet.is_reply())


class ArchiveTestCase(TestCase):

    json_test_data = '''[ 
    { "tweet" : {
            "id" : "11111",
            "created_at" : "Mon Aug 31 12:34:56 +0000 2020",
            "full_text" : "Hello, world!"
    }},
    { "tweet" : {
            "id" : "22222",
            "created_at" : "Fri Sep 18 18:18:22 +0000 2020",
            "full_text" : "Foo, Bar & Baz."
    }},
    { "tweet" : {
            "id" : "33333",
            "created_at" : "Fri Sep 18 18:18:33 +0000 2020",
            "full_text" : "RT @Test3 ..."
    }},
    { "tweet" : {
            "id" : "44444",
            "created_at" : "Sat Sep 19 19:19:44 +0000 2020",
            "full_text" : "Foo only!",
            "in_reply_to_status_id" : "11111"
    }},
    { "tweet" : {
            "id" : "55555",
            "created_at" : "Sat Sep 19 19:19:55 +0000 2020",
            "full_text" : "RT @Test5 ..."
    }},
    { "tweet" : {
            "id" : "66666",
            "created_at" : "Sat Sep 19 19:19:59 +0000 2020",
            "full_text" : "Baz, please!",
            "in_reply_to_status_id" : "44444"
    }}]'''.strip()

    def setUp(self):
        self.work_dir = tempfile.gettempdir()
        self.keep_file = '{}/yatat.keep'.format(self.work_dir)
        self.kill_file = '{}/yatat.destroy'.format(self.work_dir)
        self.kill2_file = '{}/yatat.destroyed'.format(self.work_dir)
        self.tweets_json_file = '{}/tweet.js'.format(self.work_dir)
        with open(self.tweets_json_file, 'w') as f:
                f.write(self.json_test_data + '\n')

    def tearDown(self):
        if os.path.exists(self.tweets_json_file):
            os.remove(self.tweets_json_file)
        if os.path.exists(self.keep_file):
            os.remove(self.keep_file)
        if os.path.exists(self.kill_file):
            os.remove(self.kill_file)
        if os.path.exists(self.kill2_file):
            os.remove(self.kill2_file)


class ArchiveTest(ArchiveTestCase):

    def test_fail_without_work_dir(self):
        """Fail without work dir"""
        self.assertRaises(TypeError, Archive, None)
        self.assertRaises(Oops, Archive, '/not/existing/f*i,l')

    def test_fail_without_tweet_js(self):
        """Fail without tweet.js"""
        if os.path.exists(self.tweets_json_file):
            os.remove(self.tweets_json_file)
        self.assertRaises(Oops, Archive, self.work_dir)

    def test_expected_values(self):
        """Process JSON as expected"""
        archive = Archive(self.work_dir)
        self.assertEqual(6, len(archive.tweets))
        self.assertEqual("11111", archive.tweets[0].tweet_id)
        self.assertEqual("22222", archive.tweets[1].tweet_id)
        self.assertEqual("33333", archive.tweets[2].tweet_id)
        self.assertEqual("44444", archive.tweets[3].tweet_id)
        self.assertEqual("55555", archive.tweets[4].tweet_id)
        self.assertEqual("66666", archive.tweets[5].tweet_id)
        self.assertEqual("11111", archive.tweets[3].in_reply_to_status_id)
        self.assertEqual("44444", archive.tweets[5].in_reply_to_status_id)

    def test_find(self):
        """Find tweets by id"""
        a = Archive(self.work_dir)
        self.assertIsNone(a.find("no such tweet"))
        self.assertEqual("11111", a.find("11111").tweet_id)
        self.assertEqual("55555", a.find("55555").tweet_id)

    def test_index(self):
        """Index tweets"""
        a = Archive(self.work_dir)
        self.assertEqual('2020-08, 2020-09', a.index())


class DecisionsTest(ArchiveTestCase):

    def setUp(self):
        super().setUp()
        self.decisions = Decisions(self.work_dir, ['a','b','c'])

    def tearDown(self):
        super().tearDown()
        for _, _, filename in self.decisions.possible():
            if os.path.exists(os.path.exists(filename)):
                os.remove(filename)

    def test_can_create_name_file_data(self):
        """Create decisions"""
        for decision, subjects, filename in self.decisions.possible():
            self.assertTrue(decision in filename)
            self.assertTrue(os.path.exists(filename))
            self.assertEqual(0, len(subjects))

    def test_decisions_unique(self):
        """Decisions are unique"""
        for subject in [1,1,1,2,2,3,3]:
            self.decisions.decide(subject, 'a')
        for subject in [1,2,3,4,5,6,7]:
            self.decisions.decide(subject, 'b')
        self.assertEqual(3, self.decisions.count('a'))
        self.assertEqual(7, self.decisions.count('b'))

    def test_decisions_made(self):
        """Decisions are unique"""
        for subject in [1,1,1,2,2,3,3]:
            self.decisions.decide(subject, 'a')
        for subject in [1,2,3,4,5,6,7]:
            self.decisions.decide(subject, 'b')
        self.assertTrue(self.decisions.made(4))
        self.assertTrue(self.decisions.made(4,'b'))
        self.assertFalse(self.decisions.made(4,'a'))

    def test_can_remember_decisions(self):
        """Remembering decisions"""
        self.decisions.decide(8, 'a')
        self.decisions.commit()
        self.assertEqual(1, len(Decisions(self.work_dir, ['a']).decision('a')[1]))
        self.assertTrue('8' in Decisions(self.work_dir, ['a']).decision('a')[1])


def fake_clear_screen():
    print('\n\t[ -- FAKE CLEAR SCREEN -- ]\n')
    pass


@patch('yatat.clear_screen', fake_clear_screen)
class UserInterfaceTest(ArchiveTestCase):

    def test_usage_hint(self):
        """User must get a hint about usage"""
        with managed_io() as (out):
            UserInterface([''])
        console = str(out.getvalue().strip())
        self.assertTrue('Usage:' in console)

    @patch('builtins.input', mock.Mock(side_effect=['test_username', 'Q']))
    def test_username(self):
        """Start app, enter username, quit"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Please enter your Twitter username:' in console)
        self.assertTrue("@test_username's tweet archive" in console)
        self.assertTrue('in archive .: 6' in console)
        self.assertTrue('unread .....: 6' in console)
        self.assertTrue('read .......: 0' in console)
        self.assertTrue('keeping ....: 0' in console)
        self.assertTrue('to destroy .: 0' in console)
        self.assertTrue('Quit.' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username', KeyboardInterrupt()
    ]))
    def test_ctrlc(self):
        """Start app, quit with ctrl-C"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Aborted.' in console)


    @patch('karlsruher.tweepyx.API', mock.Mock())
    @patch('builtins.input', mock.Mock(side_effect=['Q']))
    def test_twitter_auth(self):
        """Start app, authenticate Twitter api, quit"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir, '{}/testauth.yml'.format(self.work_dir)])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Authenticated' in console)
        self.assertTrue('Quit.' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER','Q','Q'
    ]))
    def test_all_no_filter_quit(self):
        """Browse archive, no filters"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('FAKE CLEAR SCREEN' in console)
        self.assertTrue('Having 6 tweets to read' in console)
        self.assertTrue('Filter out already read tweets?' in console)
        self.assertTrue('Filter out retweets?' in console)
        self.assertTrue('Filter out replies?' in console)
        self.assertTrue('Filter out tweets?' in console)
        self.assertTrue('Still 6 tweets' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER',KeyboardInterrupt(),'Q'
    ]))
    def test_all_no_filter_abort(self):
        """Browse archive, no filters"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','Y','Y','Y','Y','ENTER','Q','Q'
    ]))
    def test_all_filters_quit(self):
        """Browse archive, all filters"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('FAKE CLEAR SCREEN' in console)
        self.assertTrue('Having 6 tweets to read' in console)
        self.assertTrue('Filter out already read tweets?' in console)
        self.assertTrue('Filter out retweets?' in console)
        self.assertTrue('Filter out replies?' in console)
        self.assertTrue('Filter out tweets?' in console)
        self.assertTrue('Still 6 tweets' in console)
        self.assertTrue('Still 4 tweets' in console)
        self.assertTrue('Still 2 tweets' in console)
        self.assertTrue('No tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER',
        'C','X','X','','Q',
        'A','Y','N','N','N','ENTER',
        'Q','Q'
    ]))
    def test_all_mix(self):
        """Read all tweets and apply actions"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('in archive .: 6' in console)
        self.assertTrue('unread .....: 6' in console)
        self.assertTrue('unread .....: 5' in console)
        self.assertTrue('unread .....: 4' in console)
        self.assertTrue('unread .....: 3' in console)
        self.assertTrue('read .......: 0' in console)
        self.assertTrue('read .......: 1' in console)
        self.assertTrue('read .......: 2' in console)
        self.assertTrue('read .......: 3' in console)
        self.assertTrue('keeping ....: 1' in console)
        self.assertTrue('to destroy .: 2' in console)
        self.assertTrue('Having 6 tweets' in console)
        self.assertTrue('Still 3 tweets' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER','','','','','','',
        'Q'
    ]))
    def test_all_read_and_keep(self):
        """Browse archive and keep all"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('unread .....: 0' in console)
        self.assertTrue('read .......: 6' in console)
        self.assertTrue('keeping ....: 6' in console)
        self.assertTrue('to destroy .: 0' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER','X','X','X','X','X','X',
        'Q'
    ]))
    def test_all_read_and_kill(self):
        """Browse archive and kill all"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('unread .....: 0' in console)
        self.assertTrue('read .......: 6' in console)
        self.assertTrue('keeping ....: 0' in console)
        self.assertTrue('to destroy .: 1' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'S','Hello','N','N','N','N','ENTER','ENTER',
        'Q','Q'
    ]))
    def test_search_hello(self):
        """Find the first tweet"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        #print(console)
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Having 1 tweets' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'S','Foo','N','N','N','N','ENTER','ENTER',
        'Q','Q'
    ]))
    def test_search_foo(self):
        """Find the first tweet"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        #print(console)
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Having 2 tweets' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'T','','N','N','N','N','ENTER',
        'Q','Q'
    ]))
    def test_indexed_none(self):
        """Index none"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('No tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'T','2020-08','N','N','N','N','ENTER',
        'Q','Q'
    ]))
    def test_indexed_08(self):
        """Index tweets"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('1 tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'T','2020-09','N','N','N','N','ENTER',
        'Q','Q'
    ]))
    def test_indexed_09(self):
        """Index tweets"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('5 tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER',
        'C','X','X','','Q',
        'X','ENTER','Q'
    ]))
    @patch('yatat.UserInterface.api', mock.Mock())
    def test_destroy(self):
        """Destroy tweets"""
        with managed_io() as (out):
            ui = UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('2 tweets marked to DESTROY' in console)
        self.assertTrue('DESTROYING' in console)
        self.assertTrue('2020-09-18 22222' in console)
        self.assertTrue('2020-09-18 33333' in console)
        self.assertTrue('to destroy .: 0' in console)
        self.assertTrue('destroyed ..: 2' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'test_username',
        'A','N','N','N','N','ENTER',
        'C','X','X','','Q',
        'A','N','N','N','N','ENTER',
        'C','','X','','Q',
        'X','ENTER','Q'
    ]))
    @patch('yatat.UserInterface.api', mock.Mock())
    def test_destroy_safe(self):
        """Don't destroy kept tweets"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('2 tweets marked to DESTROY' in console)
        self.assertTrue('DESTROYING' in console)
        self.assertFalse('2020-09-18 22222' in console)
        self.assertTrue('2020-09-18 33333' in console)
        self.assertTrue('to destroy .: 1' in console)
        self.assertTrue('destroyed ..: 1' in console)
