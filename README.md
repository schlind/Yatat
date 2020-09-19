# Yatat
Yet another (public domain) Twitter archive tool! 

A (Linux/MacOS) commandline application to help you bulk delete some tweets from your Twitter archive.


### Offline browsing steps:

#### 1. Download your [twitter-archive.zip](https://help.twitter.com/managing-your-account/how-to-download-your-twitter-archive) from Twitter:
    https://help.twitter.com/managing-your-account/how-to-download-your-twitter-archive
    
#### 2. Create your local working directory
````bash
$ mkdir /path/to/workdir/
````

#### 3. Unpack your twitter-archive.zip, copy data file "tweet.js" to a working directory:
```bash
$ unzip twitter.zip 
$ cp twitter/data/tweet.js /path/to/workdir
```

#### 4. Open the "tweet.js" copy in a text-editor
and remove ```window.YTD.tweet.part0 = ``` from the first line of your tweet.js working copy! Otherwise it can't be read by the app.

#### 5. Run Yatat in offline browsing mode:
```bash
$ python3 yatat.py /path/to/workdir
```

* You will be asked to enter your Twitter username for internal textual representation only. No login, credentials needed at this point!

Now browse your archive, make decisions... should be self-explaining...


---

### Perform online tweet destruction:

Once you've browsed your archive and selected a bunch of tweets for destruction, you might want to destroy them for real.

Get your [Twitter API credentials](https://developer.twitter.com) ready.
 You'll need 
         'YOUR-CONSUMER-KEY', 'YOUR-CONSUMER-SECRET',
        'YOUR-ACCESS-KEY', 'YOUR-ACCESS-SECRET'

 and run Yatat in online mode:  

```bash
$ python3 yatat.py /path/to/workdir /path/to/auth.yaml
```

The path to file auth.yaml must be writable and the file is created on-the-fly during first run. You will be asked for your Twitter credentials!

When successfully logged in, you can choose to destroy selected tweets from the menu.

---

##### Files

Browsing and decision progress is stored in files in the working directory:

+ *yatat.keep* - stores tweets you keep
+ *yatat.destroy* - stores tweets you want to delete
+ *yatat.destroyed* - stores tweet ids of already destroyed tweets

---

This software is distributed as source from GIT only.
Find the source at [github.com/schlind/Yatat](https://github.com/schlind/Yatat) - Cheers! 
