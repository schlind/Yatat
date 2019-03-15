# __   __    _        _
# \ \ / /_ _| |_ __ _| |_
#  \ V / _` | __/ _` | __|
#   | | (_| | || (_| | |_
#   |_|\__,_|\__\__,_|\__|
"""
Yatat - Yet another twitter archive tool

Simple commandline application to let you decide
about tweets while browsing the Twitter archive.
Decisions to make: keep or delete, decide later.
"""

import os
import sys
import time
from csv import DictReader

from karlsruher import tweepyx

__version__ = '1.0b0'
__license__ = "Public Domain"
__author__ = 'Sascha Schlindwein'


class Tweet:
    """
    It's all about tweets!
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, csv):
        """
        Tweets are materialized from your archive file "tweets.csv".
        :param csv: The csv representation of a tweet
        """
        self.tweet_id = int(csv["tweet_id"])
        self.timestamp = str(csv["timestamp"])
        self.source = str(csv["source"])
        self.text = str(csv["text"])
        self.expanded_urls = str(csv["expanded_urls"])
        if csv["in_reply_to_status_id"]:
            self.in_reply_to_status_id = int(csv["in_reply_to_status_id"])
        else:
            self.in_reply_to_status_id = None
        if csv["in_reply_to_user_id"]:
            self.in_reply_to_user_id = int(csv["in_reply_to_user_id"])
        else:
            self.in_reply_to_user_id = None
        if csv["retweeted_status_id"]:
            self.retweeted_status_id = int(csv["retweeted_status_id"])
        else:
            self.retweeted_status_id = None
        if csv["retweeted_status_user_id"]:
            self.retweeted_status_user_id = int(csv["retweeted_status_user_id"])
        else:
            self.retweeted_status_user_id = None
        if csv["retweeted_status_timestamp"]:
            self.retweeted_status_timestamp = str(csv["retweeted_status_timestamp"])
        else:
            self.retweeted_status_timestamp = None

    def __repr__(self):
        return '{} {}|{}'.format(self.timestamp[:10], self.tweet_id, self.text)

    def is_reply(self):
        """
        Tweets with "in_reply_to_status_id" are replies.
        """
        return self.in_reply_to_status_id is not None

    def is_retweet(self):
        """
        Tweets with "retweeted_status_id" are retweets.
        """
        return self.retweeted_status_id is not None

    def is_tweet(self):
        """
        Tweets without "in_reply_to_status_id" and "retweeted_status_id".
        """
        return not self.is_reply() and not self.is_retweet()


class Archive:
    """
    Represent the tweet archive
    """

    def __init__(self, archive_dir):
        """
        Map tweets from "tweets.csv" to a list of Tweet instances.

        :param archive_dir: The working directory with "tweets.csv"
        """
        if not os.path.isdir(archive_dir):
            raise Oops('Directory {} does not exist.'.format(archive_dir))
        self.tweets = []
        with open('{}/tweets.csv'.format(archive_dir), 'r') as file:
            for csv_tweet in DictReader(file):
                self.tweets.append(Tweet(csv_tweet))

    def find(self, tweet_id):
        """
        Brute find the given tweet in the archive.

        :param tweet_id: The ID of the tweet to find
        :return: The tweet, if available, otherwise None
        """
        for tweet in self.tweets:
            if tweet.tweet_id == int(tweet_id):
                return tweet
        return None

    def index(self):
        """
        Provide a selectable index of months containing tweets.

        :return: A sorted set of indices, the "%Y-%M" (7 chars)
            portion of "tweet.timestamp".
        """
        index, magic = set(), 7
        for tweet in self.tweets:
            index.add(tweet.timestamp[:magic])
        return ', '.join(sorted(index))


class Decisions:
    """
    Make persistent decisions about subjects
    """

    def __init__(self, work_dir, possible_decisions):
        """
        :param work_dir: The working directory for decision files
        :param possible_decisions: All decisions
        """
        self.work_dir = work_dir
        self.possible_decisions = possible_decisions
        self.decisions = {}
        for decision, _, filename in self.possible():
            with open(filename, 'a') as touch:
                touch.close()
            with open(filename, 'r') as file:
                subjects = {line.strip() for line in file.readlines()}
            self.decisions[decision] = subjects

    def commit(self):
        """
        Write the current in memory decisions subjects to their files.
        """
        for _, subjects, filename in self.possible():
            with open(filename, 'w') as file:
                file.writelines(['{}\n'.format(subject) for subject in subjects])

    def possible(self):
        """
        :return: All possible decisions (generator)
        """
        for decision in self.possible_decisions:
            yield self.decision(decision)

    def decision(self, decision):
        """
        Tupel for a decision.

            (str decision, set subjects, str filename)

        :param decision: The decision
        :return: Tupel of the given decision, its subjects and related filename
        """
        subjects = self.decisions[decision] if decision in self.decisions else None
        filename = '/'.join([self.work_dir, decision])
        return (decision, subjects, filename)

    def decide(self, subject, decision):
        """
        Add the given subject to the decision.

        :param subject: The subject to decide about
        :param decision: The decision
        """
        self.decisions[decision].add(str(subject))

    def count(self, decision):
        """
        :param decision:
        :return: The number of subjects for the given decision
        """
        subjects = self.decision(decision)[1]
        return len(subjects)

    def made(self, subject, explicit_decision=None):
        """
        Was a decision made for the given subject?

        :param subject: The subject to check
        :param explicit_decision: Optional, an explicit decision
        :return: True if decision was made on subject, otherwise False
        """
        for decision, subjects, _ in self.possible():
            if explicit_decision:
                if decision == explicit_decision and str(subject) in subjects:
                    return True
            else:
                if str(subject) in subjects:
                    return True
        return False


def clear_screen():
    """Works on Linux & Mac:"""
    os.system('clear') # pragma: no cover


# pylint: disable=too-many-branches,bare-except,missing-docstring
class UserInterface:
    """
    Provide simple commandline UI
    """

    # Possible decisions:
    read_and_keep, destroy = 'yatat.keep', 'yatat.kill'

    def __init__(self, argv):
        """
        :param argv: sys.argv
        """
        if len(argv) < 2:
            print('Usage: {} </path/to/workdir>'.format(argv[0]))
            return
        work_dir = argv[1]
        self.archive = Archive(work_dir)
        self.decisions = Decisions(work_dir, {self.read_and_keep, self.destroy})
        try:
            if len(argv) == 3:
                self.api = tweepyx.API(argv[2], True)
                self.screen_name = self.api.me().screen_name
                print('Authenticated as:', self.screen_name)
                time.sleep(0.75)
            else:
                self.api = None
                print('Please enter your Twitter username: (to display links)')
                self.screen_name = input('> ').strip()

            self.loop()
        except KeyboardInterrupt:
            print('Aborted.')
        finally:
            self.decisions.commit()
            print('Cheers!')

    def __repr__(self):
        total = len(self.archive.tweets)
        kept = self.decisions.count(self.read_and_keep)
        kill = self.decisions.count(self.destroy)
        done = kept + kill
        todo = total - done
        # pylint: disable=bad-indentation
        return '''
==========================================
Yatat v{0} - @{1}'s tweet archive
------------------------------------------
 total ...: {2}
 todo ....: {3}
 done ....: {4} 
 kept ....: {5} 
 kill ....: {6}
------------------------------------------
        '''.strip().format(__version__, self.screen_name, total, todo, done, kept, kill)

    def loop(self):
        user_did_not_quit = True
        while user_did_not_quit:
            clear_screen()
            # pylint: disable=bad-indentation
            print('''
{}
Menu:

  A - Read all tweets chronologically
  T - Read tweets by time span
  S - Search tweets for text
  X - Delete marked tweets
  Q - Quit

==========================================
            '''.strip().format(self))
            user_did_not_quit = self.action(input('> ').strip().upper())

    def action(self, action):
        if action == 'Q':
            print('Quit.')
            return False
        if action == 'X':
            return self.destroy_tweets()
        if action == 'A':
            print('All...')
            tweets = list(self.archive.tweets)
        elif action == 'S':
            clear_screen()
            #print(self)
            print('\nSearch')
            search = input('? ').strip().lower()
            tweets = [
                tweet for tweet in self.archive.tweets
                if search in tweet.text.lower()
            ]
        elif action == 'T':
            clear_screen()
            #print(self)
            print('Available:', self.archive.index())
            print('\nSelect')
            selector = input('? ').strip()
            if not selector:
                selector = '-'
            tweets = [
                tweet for tweet in self.archive.tweets
                if tweet.timestamp.startswith(selector)
            ]

        else:
            return True

        try:
            if tweets:
                self.filter(tweets)
            if not tweets:
                clear_screen()
                print(self)
                print('\nNo tweets to read, hit ENTER to go back...')
                input()
                return True
            print('\n{} tweets to read, hit ENTER to start...'.format(len(tweets)))
            input()
            for tweet in tweets:
                if self.decide(tweet) == 'Q':
                    break
        except KeyboardInterrupt:
            print('Aborted.')
            time.sleep(0.5)

        return True

    def filter(self, tweets):
        """

        :param tweets:
        :return:
        """
        clear_screen()
        print(self)
        print('\nHaving', len(tweets), 'tweets to read.')
        print('Filter already read tweets? [y|n] Y')
        if input('? ').strip().upper() != 'N':
            for tweet in list(tweets):
                if self.decisions.made(tweet.tweet_id):
                    tweets.remove(tweet)

        clear_screen()
        print(self)
        print('\nStill', len(tweets), 'tweets...')
        print('Filter retweets? [y|n] Y')
        if input('? ').strip().upper() != 'N':
            for tweet in list(tweets):
                if tweet.is_retweet():
                    tweets.remove(tweet)

        clear_screen()
        print(self)
        print('\nStill', len(tweets), 'tweets...')
        print('Filter replies? [y|n] N')
        if input('? ').strip().upper() == 'Y':
            for tweet in list(tweets):
                if tweet.is_reply():
                    tweets.remove(tweet)

        clear_screen()
        print(self)
        print('\nStill', len(tweets), 'tweets...')
        print('Filter tweets? [y|n] N')
        if input('? ').strip().upper() == 'Y':
            for tweet in list(tweets):
                if tweet.is_tweet():
                    tweets.remove(tweet)

    def decide(self, tweet):
        clear_screen()
        # pylint: disable=bad-indentation
        print('''
{}

{}

------------------------------------------

 ENTER - Keep tweet and read next
     X - Mark tweet to be deleted
     C - Continue without decision
     Q - Quit reading

==========================================
        '''.strip().format(self, self.pretty(tweet)))
        decision = input('\n> ').strip().upper()
        if decision == 'X':
            self.decisions.decide(tweet.tweet_id, self.destroy)
            clear_screen()
            # pylint: disable=anomalous-backslash-in-string
            # pylint: disable=bad-indentation
            print(r'''
{0}
  ____   _____  _      _____  _____  _____
 |  _ \ | ____|| |    | ____||_   _|| ____|
 | | | ||  _|  | |    |  _|    | |  |  _|
 | |_| || |___ | |___ | |___   | |  | |___
 |____/ |_____||_____||_____|  |_|  |_____|
            '''.strip().format(self))
            time.sleep(0.3)
        elif decision == 'C':
            print('LATER')
        elif decision != 'Q':
            self.decisions.decide(tweet.tweet_id, self.read_and_keep)
            clear_screen()
            # pylint: disable=anomalous-backslash-in-string
            print(r'''
{0}
  _  __ _____  _____  ____
 | |/ /| ____|| ____||  _ \\
 | ' / |  _| ||  _|  | |_) |
 | . \ | |___|| |___ |  __/
 |_|\_\|_____||_____||_|
            '''.strip().format(self))
            time.sleep(0.2)
        return decision

    def pretty(self, tweet):
        """
        Provide a pretty string representation of the given tweet.

        Implemented rather here than in Tweet.__repr__ to provide
        the account's "screen_name" for pretty and click-able URLs.
        The archive csv doesn't provide that account information.

        :param tweet: The tweet
        :return: The pretty string representation of the tweet
        """
        return '{1} https://twitter.com/{0}/status/{2}{4}{5}\n\n{3}{6}'.format(
            self.screen_name, tweet.timestamp, tweet.tweet_id, tweet.text,
            '\n  retweeted: {}'.format(
                tweet.retweeted_status_id) if tweet.is_retweet() else '',
            '\n  replies to: {}'.format(
                tweet.in_reply_to_status_id) if tweet.is_reply() else '',
            self.parent(tweet)
        )

    def parent(self, tweet):
        if tweet is None or tweet.in_reply_to_status_id is None:
            return ''
        parent = self.archive.find(tweet.in_reply_to_status_id)
        if parent:
            return '\n\n__in_reply_to:\n{}'.format(self.pretty(parent))
        return ''

    def destroy_tweets(self):
        # TODO adapt tests and enable api *iargs
        #if not self.api:
        #    print('Offline, API not connected. Hit ENTER to go back...')
        #    input()
        #    return True
        _, subjects, _ = self.decisions.decision(self.destroy)
        clear_screen()
        print('{} tweets marked to DELETE:'.format(len(subjects)))
        try:
            for subject in subjects:
                if self.decisions.made(subject, self.read_and_keep):
                    continue
                print('DELETE', self.archive.find(subject))
                #self.api.destroy_status(subject)
                time.sleep(2.75)
        except KeyboardInterrupt: # pragma: no cover
            print('Aborted.')
            time.sleep(0.5)
        return True


class Oops(Exception):
    """
    Problems occur
    """


def main():
    """Start Yatat application."""
    UserInterface(sys.argv) # pragma: no cover


if __name__ == '__main__':
    main() # pragma: no cover
