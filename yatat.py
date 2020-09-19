# __   __    _        _
# \ \ / /_ _| |_ __ _| |_
#  \ V / _` | __/ _` | __|
#   | | (_| | || (_| | |_
#   |_|\__,_|\__\__,_|\__| Yet another twitter archive tool
"""See README.md for details"""

import json
import os
import sys
from datetime import datetime
from time import sleep

# Promotion for https://twitter.com/Karlsruher
from karlsruher import tweepyx

__version__ = '1.0b1'
__license__ = "Public Domain"
__author__ = 'Sascha Schlindwein'


class Archive:
    """The Archive loads and provides tweets from the Twitter archive data."""

    def __init__(self, working_dir):
        """
        Load tweets from 'tweet.js' in the working directory.

        => Remember to remove the part "window.YTD.tweet.part0 = " from the
        first line!

        :param working_dir: The working directory that contains 'tweet.js' and
        will be populated with other files
        """
        if not os.path.isdir(working_dir):
            raise Oops('Working Directory "{0}" does not exist.'.format(working_dir))

        path_to_archive = '{0}/{1}'.format(working_dir, 'tweet.js')

        if not os.path.isfile(path_to_archive):
            raise Oops('File "{0}" does not exist.'.format(path_to_archive))

        self.tweets = []

        with open(path_to_archive) as archive_data_file:
            for json_obj in json.load(archive_data_file):
                self.tweets.append(Tweet(json_obj['tweet']))

        print('Loaded', len(self.tweets), 'tweets from', path_to_archive)

    def find(self, tweet_id):
        """
        :param tweet_id: The ID of the tweet to find
        :return: The tweet, if available, otherwise None
        """
        for tweet in self.tweets:
            if tweet.tweet_id == str(tweet_id):
                return tweet
        return None

    def index(self):
        """
        :return: A sorted string of date based indices, the "%Y-%M" (7 chars)
            portion of "tweet.timestamp".
        """
        index, magic = set(), 7
        for tweet in self.tweets:
            index.add(tweet.timestamp[:magic])
        return ', '.join(sorted(index))


class Tweet:
    """It's all about tweets!"""

    def __init__(self, json_tweet):
        """
        :param json_tweet: The tweet portion as extracted from 'tweet.js'
        """
        self.tweet_id = json_tweet["id"]
        self.text = json_tweet["full_text"]
        self.timestamp = datetime.strftime(datetime.strptime(
                json_tweet["created_at"], '%a %b %d %H:%M:%S +0000 %Y'
            ), '%Y-%m-%d %H:%M:%S' )
        self.in_reply_to_status_id = \
            json_tweet["in_reply_to_status_id"] \
                if "in_reply_to_status_id" in json_tweet else None

    def __repr__(self):
        """String representation: 'YYYY-MM-DD <tweet_id> <text>'"""
        return '{0} {1} {2}'.format(self.timestamp[:10], self.tweet_id, self.text)

    def is_reply(self):
        """Tweets with an "in_reply_to_status_id" set are replies."""
        return self.in_reply_to_status_id is not None

    def is_retweet(self):
        """Tweets text starting with "RT @" are interpreted as retweets."""
        return self.text.startswith("RT @")

    def is_tweet(self):
        """Tweets that are not retweets and not replies are tweets. ;)"""
        return not self.is_retweet() and not self.is_reply()


class Decisions:
    """
    Make persistent decisions about subjects!

    The related use-case is that we want to store meta information about
    tweets that we already browsed in the archive. We want to remember
    tweets that we'd like to keep or to destroy (later).

    The "subject" is a tweet_id and the related "decision" might be
    either "keep" or "destroy" or anything else.

    Decisions are mapped lazy to files, so *please use valid file names*
    as possible decision keys.
    """

    def __init__(self, work_dir, possible_decisions):
        """
        :param work_dir: The working directory for decision files
        :param possible_decisions: All possible decisions
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
        """Write subjects and decisions to files."""
        for _, subjects, filename in self.possible():
            with open(filename, 'w') as file:
                file.writelines(['{0}\n'.format(subject) for subject in subjects])

    def possible(self):
        """:return: All possible decisions (generator)"""
        for decision in self.possible_decisions:
            yield self.decision(decision)

    def decision(self, decision):
        """
        :param decision: The decision
        :return: Tupel of the given decision, its subjects and related
            filename (str decision, set subjects, str filename)
        """
        return (
            decision,
            self.decisions[decision] if decision in self.decisions else None,
            '/'.join([self.work_dir, decision])
        )

    def decide(self, subject, decision):
        """
        :param subject: The subject to decide about
        :param decision: The decision
        """
        self.decisions[decision].add(str(subject))

    def revoke(self, subject, decision):
        """
        :param subject: The subject to revoke the decision from
        :param decision: The decision to revoke
        """
        if str(subject) in self.decisions[decision]:
            self.decisions[decision].remove(str(subject))

    def count(self, decision):
        """
        :param decision:
        :return: The number of subjects for the given decision
        """
        subjects = self.decision(decision)[1]
        return len(subjects)

    def made(self, subject, explicit_decision=None):
        """
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
    """Works for me on Linux & Mac:"""
    os.system('clear')  # pragma: no cover


# pylint: disable=too-many-branches,bare-except,missing-docstring
class UserInterface:
    """
    Commandline UI to wire Archive and Decisions classes to an application.
    """

    # Declare for testing/mocking and offline mode:
    api = None

    # Declare possible decisions about tweets:
    keep, destroy, destroyed = 'yatat.keep', 'yatat.destroy', 'yatat.destroyed'

    def __init__(self, argv):
        """
        :param argv: sys.argv as given at command line
        """
        if len(argv) < 2:
            print('Usage: $ {0} /path/to/workdir [/path/to/auth.yaml]'.format(argv[0]))
            return

        work_dir = argv[1]
        self.archive = Archive(work_dir)
        possible_decisions = {self.keep, self.destroy, self.destroyed}
        self.decisions = Decisions(work_dir, possible_decisions)

        try:
            if len(argv) == 3:
                # Go online, connect api
                self.api = tweepyx.API(argv[2], True)
                self.display_username = self.api.me().screen_name
                print('Authenticated as:', self.display_username)
                sleep(0.75)
            else:
                # Offline, ask for a username
                print('Please enter your Twitter username: (to display)')
                self.display_username = input('> ').strip()

            # Start user interaction loop
            self.loop()

        except KeyboardInterrupt:
            # Catch ctrl-c
            print('Aborted.')
        finally:
            # Always persist decisions
            self.decisions.commit()
            print('Cheers!')

    def __repr__(self):
        nr_of_tweets_in_archive = len(self.archive.tweets)
        nr_of_tweets_to_keep = self.decisions.count(self.keep)
        nr_of_tweets_to_destroy = self.decisions.count(self.destroy)
        nr_of_tweets_already_destroyed = self.decisions.count(self.destroyed)
        nr_of_tweets_read = nr_of_tweets_to_keep \
                            + nr_of_tweets_to_destroy \
                            + nr_of_tweets_already_destroyed
        nr_of_tweets_not_read = nr_of_tweets_in_archive - nr_of_tweets_read
        # pylint: disable=bad-indentation
        return '''
==========================================
Yatat v{0} - @{1}'s tweet archive
------------------------------------------
 in archive .: {2}
 unread .....: {3}
 read .......: {4}
 keeping ....: {5}
 to destroy .: {6}
 destroyed ..: {7}
------------------------------------------
        '''.strip().format(
            __version__, self.display_username,
            nr_of_tweets_in_archive, nr_of_tweets_not_read,
            nr_of_tweets_read, nr_of_tweets_to_keep,
            nr_of_tweets_to_destroy, nr_of_tweets_already_destroyed
        )

    def loop(self):
        """The application loop."""
        user_did_not_quit = True
        while user_did_not_quit:
            clear_screen()
            # pylint: disable=bad-indentation
            print('''
{0}
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
            print('\nSearch')
            search = input('? ').strip().lower()
            tweets = [
                tweet for tweet in self.archive.tweets
                if search in tweet.text.lower()
            ]
        elif action == 'T':
            clear_screen()
            print('\nAvailable:', self.archive.index())
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

        self.filter(tweets)
        self.browse(tweets)
        return True

    def filter(self, tweets):
        if tweets:
            clear_screen()
            print(self)
            print('\nHaving', len(tweets), 'tweets to read.')
            print('Filter out already read tweets? [y|n] Y')
            if input('? ').strip().upper() != 'N':
                for tweet in list(tweets):
                    if self.decisions.made(tweet.tweet_id):
                        tweets.remove(tweet)
        if tweets:
            clear_screen()
            print(self)
            print('\nStill', len(tweets), 'tweets...')
            print('Filter out retweets? [y|n] Y')
            if input('? ').strip().upper() != 'N':
                for tweet in list(tweets):
                    if tweet.is_retweet():
                        tweets.remove(tweet)
        if tweets:
            clear_screen()
            print(self)
            print('\nStill', len(tweets), 'tweets...')
            print('Filter out replies? [y|n] N')
            if input('? ').strip().upper() == 'Y':
                for tweet in list(tweets):
                    if tweet.is_reply():
                        tweets.remove(tweet)
        if tweets:
            clear_screen()
            print(self)
            print('\nStill', len(tweets), 'tweets...')
            print('Filter out tweets? [y|n] N')
            if input('? ').strip().upper() == 'Y':
                for tweet in list(tweets):
                    if tweet.is_tweet():
                        tweets.remove(tweet)

    def browse(self, tweets):
        clear_screen()
        print(self)
        if tweets:
            try:
                print('\n{0} tweets to read, hit ENTER to start...'.format(len(tweets)))
                input()
                for tweet in tweets:
                    if self.decide(tweet) == 'Q':
                        break
            except KeyboardInterrupt:
                print('Aborted.')
        else:
            print('\nNo tweets to read, hit ENTER to go back...')
            input()

    def decide(self, tweet):
        clear_screen()
        # pylint: disable=bad-indentation
        print('''
{0}

{1}

------------------------------------------

 ENTER - Keep tweet and read next
     X - Mark tweet to be deleted
     C - Continue without decision
     Q - Quit reading

==========================================
        '''.strip().format(self, self.pretty(tweet)))
        decision = input('\n> ').strip().upper()
        if decision == 'C':
            print('DECIDE LATER')
        elif decision == 'X':
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
            self.decisions.decide(tweet.tweet_id, self.destroy)
            sleep(0.2)
        elif decision != 'Q':
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
            self.decisions.decide(tweet.tweet_id, self.keep)
            sleep(0.2)
        return decision

    def pretty(self, tweet):
        """
        :param tweet: The tweet
        :return: The pretty string representation of the tweet
        """
        return '{4}{5}{1} https://twitter.com/{0}/status/{2}\n{3}'.format(
            self.display_username,
            tweet.timestamp, tweet.tweet_id, tweet.text,
            self.parent(tweet),
            '-> is a retweet:\n---\n\n' if tweet.is_retweet() else ''
        )

    def parent(self, tweet):
        if not tweet.is_reply():
            return ''
        parent = self.archive.find(tweet.in_reply_to_status_id)
        if parent:
            return '-> is part of a thread:\n{0}\n---\n\n'.format(self.pretty(parent))
        return '-> is a reply:\n---\n\n'

    def destroy_tweets(self):
        """
        Destroy all selected tweets if API connection is present
        :return: True
        """
        if not self.api:
            print('API not connected, you are offline!') # pragma: no cover
            print('Please restart the application in online-mode.') # pragma: no cover
            print('(See README.md for details)') # pragma: no cover
            print('Hit ENTER to go back...') # pragma: no cover
            input() # pragma: no cover
            return True # pragma: no cover

        tweets_to_destroy = self.decisions.decision(self.destroy)[1]
        nr_of_tweets_to_destroy = len(tweets_to_destroy)
        clear_screen()
        try:
            print('{0} tweets marked to DESTROY, hit ENTER to start...'
                  .format(nr_of_tweets_to_destroy))
            input()
            destroyed_tweets_count = 0
            for tweet_to_destroy in tweets_to_destroy:
                if self.decisions.made(tweet_to_destroy, self.keep):
                    continue
                if self.decisions.made(tweet_to_destroy, self.destroyed):
                    continue # pragma: no cover
                print(
                    'DESTROYING',
                    nr_of_tweets_to_destroy - destroyed_tweets_count,
                    self.archive.find(tweet_to_destroy)
                )
                sleep(1.5)
                try:
                    self.api.destroy_status(tweet_to_destroy)
                    self.decisions.decide(tweet_to_destroy, self.destroyed)
                    destroyed_tweets_count += 1
                # pylint: disable=broad-except
                except Exception as error:  # pragma: no cover
                    print("Error", error)
        except KeyboardInterrupt:  # pragma: no cover
            print('Aborted.')

        print('Cleaning up.')
        for destroyed_tweet in self.decisions.decision(self.destroyed)[1]:
            self.decisions.revoke(destroyed_tweet, self.destroy)

        sleep(0.5)
        return True


class Oops(Exception):
    """Exceptions occur, be sure!"""


def main():
    """Start application"""
    UserInterface(sys.argv)  # pragma: no cover


if __name__ == '__main__':
    main()  # pragma: no cover
