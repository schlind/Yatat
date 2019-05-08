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
        self.csv = {}
        self.csv["tweet_id"] = 0
        self.csv["timestamp"] = 'test_timestamp'
        self.csv["source"] = 'test_source'
        self.csv["text"] = 'test_text'
        self.csv["expanded_urls"] = 'test_expanded_urls'
        self.csv["in_reply_to_status_id"] = None
        self.csv["in_reply_to_user_id"] = None
        self.csv["retweeted_status_id"] = None
        self.csv["retweeted_status_user_id"] = None
        self.csv["retweeted_status_timestamp"] = None

    def test_create(self):
        """Handle CSV Tweet."""
        tweet = Tweet(self.csv)
        self.assertTrue(tweet.is_tweet())
        self.assertFalse(tweet.is_reply())
        self.assertFalse(tweet.is_retweet())
        self.assertEqual('test_timestamp', tweet.timestamp)
        self.assertEqual('test_source', tweet.source)
        self.assertEqual('test_text', tweet.text)
        self.assertEqual('test_expanded_urls', tweet.expanded_urls)
        self.assertIsNone(tweet.in_reply_to_status_id)
        self.assertIsNone(tweet.in_reply_to_user_id)
        self.assertIsNone(tweet.retweeted_status_id)
        self.assertIsNone(tweet.retweeted_status_user_id)
        self.assertIsNone(tweet.retweeted_status_timestamp)
        self.assertTrue(tweet.timestamp[:10] in str(tweet))
        self.assertTrue(str(tweet.tweet_id) in str(tweet))
        self.assertTrue(tweet.text in str(tweet))

    def test_create_reply(self):
        """Handle Reply."""
        self.csv["in_reply_to_status_id"] = 7
        self.csv["in_reply_to_user_id"] = 4
        tweet = Tweet(self.csv)
        self.assertTrue(tweet.is_reply())
        self.assertFalse(tweet.is_tweet())
        self.assertFalse(tweet.is_retweet())
        self.assertEqual(7, tweet.in_reply_to_status_id)
        self.assertEqual(4, tweet.in_reply_to_user_id)

    def test_create_retweet(self):
        """Handle Retweet."""
        self.csv["retweeted_status_id"] = 11
        self.csv["retweeted_status_user_id"] = 23
        self.csv["retweeted_status_timestamp"] = 'test_rs_timestamp'
        tweet = Tweet(self.csv)
        self.assertTrue(tweet.is_retweet())
        self.assertFalse(tweet.is_tweet())
        self.assertFalse(tweet.is_reply())
        self.assertEqual(11, tweet.retweeted_status_id)
        self.assertEqual(23, tweet.retweeted_status_user_id)
        self.assertEqual('test_rs_timestamp', tweet.retweeted_status_timestamp)


class ArchiveTestCase(TestCase):

    csv_tweets = [
        '"tweet_id","in_reply_to_status_id","in_reply_to_user_id","timestamp","source","text","retweeted_status_id","retweeted_status_user_id","retweeted_status_timestamp","expanded_urls"',
        '"666","999","1","2525-03-07 14:15:16 +0000","test_source","Reply to other Tweet","","","",""',
        '"555","","","2525-03-04 08:11:05 +0000","test_source","Third Tweet","","","",""',
        '"444","","","2525-02-03 17:23:42 +0000","test_source","RT @SCREEN_NAME: Second Tw...","333","1","",""',
        '"333","","","2525-02-03 07:32:24 +0000","test_source","Second Tweet","","","",""',
        '"222","111","1","2525-01-03 23:45:00 +0000","test_source","Reply to first Tweet","","","",""',
        '"111","","","2525-01-02 12:34:56 +0000","test_source","First Tweet","","","","http://expanded_url.test"',
    ]

    def setUp(self):
        self.work_dir = tempfile.gettempdir()
        self.keep_file = '{}/yatat.keep'.format(self.work_dir)
        self.kill_file = '{}/yatat.destroy'.format(self.work_dir)
        self.kill2_file = '{}/yatat.destroyed'.format(self.work_dir)
        self.tweets_csv = '{}/tweets.csv'.format(self.work_dir)
        with open(self.tweets_csv, 'w') as f:
            for csv_tweet in self.csv_tweets:
                f.write(csv_tweet + '\n')

    def tearDown(self):
        if os.path.exists(self.tweets_csv):
            os.remove(self.tweets_csv)
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

    def test_fail_without_tweets_csv(self):
        """Fail without tweets.csv"""
        if os.path.exists(self.tweets_csv):
            os.remove(self.tweets_csv)
        self.assertRaises(FileNotFoundError, Archive, self.work_dir)

    def test_expected_values(self):
        """Import CSV"""
        archive = Archive(self.work_dir)
        self.assertEqual(6, len(archive.tweets))
        self.assertEqual(111, archive.tweets[5].tweet_id)
        self.assertEqual(222, archive.tweets[4].tweet_id)
        self.assertEqual(333, archive.tweets[3].tweet_id)
        self.assertEqual(444, archive.tweets[2].tweet_id)
        self.assertEqual(555, archive.tweets[1].tweet_id)
        self.assertEqual(666, archive.tweets[0].tweet_id)
        self.assertEqual(111, archive.tweets[4].in_reply_to_status_id)
        self.assertEqual(333, archive.tweets[2].retweeted_status_id)
        self.assertEqual(999, archive.tweets[0].in_reply_to_status_id)

    def test_find(self):
        """Find tweets"""
        a = Archive(self.work_dir)
        self.assertEqual(111, a.find(111).tweet_id)
        self.assertEqual(222, a.find(222).tweet_id)
        self.assertEqual(333, a.find(333).tweet_id)
        self.assertIsNone(a.find(7))

    def test_index(self):
        """Index tweets"""
        a = Archive(self.work_dir)
        self.assertEqual('2525-01, 2525-02, 2525-03', a.index())


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

    def test_except(self):
        """Boom"""
        with managed_io() as (out):
            UserInterface([''])
        console = str(out.getvalue().strip())
        self.assertTrue('Usage:' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
        'Q'
    ]))
    def test_username(self):
        """Ask username"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Please enter your Twitter username:' in console)
        self.assertTrue("@username's tweet archive" in console)
        self.assertTrue('Quit.' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
        KeyboardInterrupt()
    ]))
    def test_ctrlc(self):
        """Quit by ctrl-C"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Aborted.' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
        'Q'
    ]))
    def test_quit(self):
        """Quit by Q"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('in archive .: 6' in console)
        self.assertTrue('unread .....: 6' in console)
        self.assertTrue('read .......: 0' in console)
        self.assertTrue('keeping ....: 0' in console)
        self.assertTrue('to destroy .: 0' in console)
        self.assertTrue('Quit.' in console)

    @patch('karlsruher.tweepyx.API', mock.Mock())
    @patch('builtins.input', mock.Mock(side_effect=[
        'Q'
    ]))
    def test_twitter(self):
        """Having twitter"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir, '{}/testauth.yml'.format(self.work_dir)])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Authenticated' in console)
        self.assertTrue('Quit.' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        self.assertTrue('Filter already read tweets?' in console)
        self.assertTrue('Filter retweets?' in console)
        self.assertTrue('Filter replies?' in console)
        self.assertTrue('Filter tweets?' in console)
        self.assertTrue('Still 6 tweets' in console)
        self.assertTrue('Reply to other' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
        'A','N','N','N','N','ENTER',KeyboardInterrupt(),'Q'
    ]))
    def test_all_no_filter_abort(self):
        """Browse archive, no filters"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        self.assertTrue('Filter already read tweets?' in console)
        self.assertTrue('Filter retweets?' in console)
        self.assertTrue('Filter replies?' in console)
        self.assertTrue('Filter tweets?' in console)
        self.assertTrue('Still 6 tweets' in console)
        self.assertTrue('Still 5 tweets' in console)
        self.assertTrue('Still 3 tweets' in console)
        self.assertTrue('No tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        'username',
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
        'username',
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
        'username',
        'S','first','N','N','N','N','ENTER','C','C',
        'Q','Q'
    ]))
    def test_search(self):
        """Find the first tweet"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('Having 2 tweets' in console)
        self.assertTrue('First Tweet' in console)
        self.assertTrue('Reply to first Tweet' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        'username',
        'T','2525-01','N','N','N','N','ENTER',
        'Q','Q'
    ]))
    def test_indexed(self):
        """Index tweets"""
        with managed_io() as (out):
            UserInterface(['', self.work_dir])
        console = str(out.getvalue().strip())
        self.assertTrue(console.endswith('Cheers!'))
        self.assertTrue('2 tweets to read' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        self.assertTrue('2525-03-04 555' in console)
        self.assertTrue('2525-02-03 444' in console)
        self.assertTrue('to destroy .: 0' in console)
        self.assertTrue('destroyed ..: 2' in console)

    @patch('builtins.input', mock.Mock(side_effect=[
        'username',
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
        self.assertFalse('2525-03-04 555' in console)
        self.assertTrue('2525-02-03 444' in console)
        self.assertTrue('to destroy .: 1' in console)
        self.assertTrue('destroyed ..: 1' in console)
