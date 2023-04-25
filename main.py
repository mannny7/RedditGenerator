import praw
import os
import pyttsx3
import time
import random
import json


from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from pynput.mouse import Button

from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KeyboardController

from moviepy.editor import *

from colorama import just_fix_windows_console
from termcolor import colored

just_fix_windows_console()


def log(text, text_color="green"):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print(f'{current_time} >>> {colored(text, text_color)}')


def click(location: tuple, button=Button.left):
    # Click the mouse at the given location
    mouse.position = location
    mouse.click(button, 1)


def getPosts():
    # Get the posts from the subreddit defined
    posts = []
    for submission in reddit.subreddit(SUBREDDIT).top(time_filter="all", limit=POSTS_LIMIT):

        valid = True

        # Ensure we haven't already made a video on this post
        if submission.id in existingPosts:
            valid = False

        # Ensure the post isn't an NSFW post
        if submission.over_18:
            valid = False

        # Ensure there aren't any banned words in the title
        for word in banned_words:
            if word in submission.title:
                valid = False

        if valid:
            posts.append(submission)
            log(f"Found post {submission.title}")
    return posts


def getExistingPosts():
    # Read the text file that contains posts already used
    with open(f"{real_path}/postids.txt", "r") as f:
        postids = f.read().split("\n")
    log(f"Got existing posts: {postids}")
    return postids


def writeExistingPosts(ids):
    # Write to the text file that contains posts already used
    with open(f"{real_path}/postids.txt", "w") as f:
        f.write("\n".join(ids))
    log("Wrote existing posts")


def getComments(post):
    # Retrieve the comments from a post
    log("Getting comments from post - " + post.title)
    comments = []
    found = 0

    for comment in post.comments:

        valid = True

        if found > COMMENTS_LIMIT:
            break

        # Make sure the comment is valid
        if (isinstance(comment, praw.models.Comment)):
            # It must be shorter than 200 characters
            if len(comment.body.split()) > 200:
                valid = False

            # It must be longer than 30 characters
            if len(comment.body.split()) < 30:
                valid = False

            # The author of the comment's account must not be deleted
            if comment.author == "[deleted]":
                valid = False

            # The comment should not be an automatic reply by AutoModerator
            if comment.author == "AutoModerator":
                valid = False

            # The comment should not contain banned words
            for word in banned_words:
                if word in comment.body:
                    valid = False

            # If it passes these checks we can use it
            if valid:
                found += 1
                log(f"Got comment {comment}")
                comments.append(comment)

    return comments


def voiceOver(id, text, type="comment"):
    # Use the voice engine to create a new file with the voiceover
    engine.save_to_file(text, real_path + f"/Voiceovers/{type}-{id}.mp3")
    engine.runAndWait()
    log(f"Saved voiceover {id}")


def getValidWebsite(postid):

    # For some reason when using Selenium to access reddit sometimes the website will look different
    # It's a different style or something, so we need to ensure we get the right version

    global driver
    valid = False

    while not valid:
        # Create a new driver
        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()))

        driver.get(f"https://www.reddit.com/r/{SUBREDDIT}/comments/{postid}/")

        # The invalid website contains this element
        temp = driver.find_elements(
            By.XPATH, '/html/body/shreddit-app/reddit-header-large/header/nav')

        # If the list is empty it means the element does not exist
        # Therefore we are on the correct website
        if len(temp) == 0:
            valid = True
            log("Got valid browser")
        else:

            # If the list is not empty we are on the wrong style

            log("Invalid browser style. Retrying...")
            driver.close()

    time.sleep(0.5)

    # Update the driver variable to the new driver
    driver = driver
    driver.maximize_window()

    # Click the accept all cookies button
    click((1197, 1356))

    time.sleep(1)


def takeScreenshot(thing, type="comment"):
    global working
    # Working is a list of comments that we successfully screenshotted

    # Sometimes the website goes dark for fun
    # So we click the bottom right corner to go back to normal
    click((2480, 1300))
    time.sleep(0.25)

    valid = True

    if type == "comment":
        # Try to find the comment
        try:
            item = driver.find_element(By.ID, f"t1_{thing.id}")
            # The comment was found so we add it to a working list
            # To be used when we create voiceovers
            working.append(thing)
            log(f"Sucessfully screenshotted {thing.id}")
        except:

            # If an error is thrown it is invalid
            valid = False

            log(f"Failed to screenshotted {thing.id}")
    else:
        # If the type is not comment is post
        # So we just need to find the post
        item = driver.find_element(By.ID, f"t3_{thing.id}")

    # If no error was thrown then we can screenshot it
    if valid:
        item.screenshot(f"{real_path}/Screenshots/{type}-{thing.id}.png")


def createClip(screenshot, voiceover):
    image = ImageClip(screenshot)
    audio = AudioFileClip(voiceover)

    # Create a video where the image is the screenshot and the audio is the voiceover
    video = image.set_audio(audio)

    # Set the duration of the video to the length of the audio
    video = video.set_duration(audio.duration)

    # The dimensions of the phone is 1080 x 1920
    # So we resize the video to take up most the phone
    video = video.resize(width=1020)

    log(f"Created clip {screenshot}")
    return video


real_path = os.path.dirname(os.path.realpath(__file__))


# Define the mouse and keyboard
mouse = MouseController()
keyboard = KeyboardController()

# General configuration of the bot
log("Enter subreddit: ")
SUBREDDIT = input()
COMMENTS_LIMIT = 7
POSTS_LIMIT = 20

with open(f"{real_path}/login.txt") as f:
    data = json.load(f)


# Create the client to make requests to Reddit
reddit = praw.Reddit(
    client_id=data["client-id"],
    client_secret=data["client-secret"],
    password=data["password"],
    user_agent="A test bot",
    username=data["username"],)


banned_words = ["dick", "http", "pussy",
                "penis", "fuck", "cunt", "bitch", "slut"]

# Create the voice engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('rate', 260)

# Chose the voice
engine.setProperty('voice', voices[1].id)

driver = ""


# Get the posts that videos have already been made from
existingPosts = getExistingPosts()

# Get some posts
submissions = getPosts()

log(f"Continue with {len(submissions)} posts? [Y/N]")
cont = input()

if cont.upper() != "Y":
    exit()


for submission in submissions:

    # Get the comments from the post
    comments = getComments(submission)

    working = []

    # Get a reddit window using selenium
    getValidWebsite(submission.id)

    # Create the voice over for the title of the post
    voiceOver(submission.id, submission.title, "post")
    # Also create the screenshot
    takeScreenshot(submission, "post")

    # Make sure there are commets
    if len(comments) > 0:
        for comment in comments:

            # Make sure we aren't over the limit of comments
            if not (len(working) > COMMENTS_LIMIT):

                # Create the screenshot of the comment
                takeScreenshot(comment)

        # Sometimes an error is thrown when trying to screenshot a post
        # The list of working comments is made in the screenshot function
        # We only need to create a voiceover for the working comments
        for comment in working:
            voiceOver(comment.id, comment.body)

    if len(working) == 0:
        log(f"No comments found for {submission.title}")
        existingPosts.append(submission.id)
        continue

    driver.close()

    clips = []

    title = createClip(f"{real_path}/Screenshots/post-{submission.id}.png",
                       f"{real_path}/Voiceovers/post-{submission.id}.mp3")

    clips.append(title)

    current_duration = title.duration

    # Create a clip for each comment
    for comment in working:

        clip = createClip(f"{real_path}/Screenshots/comment-{comment.id}.png",
                          f"{real_path}/Voiceovers/comment-{comment.id}.mp3")

        # Store the current duration of the concatenated clips
        current_duration += clip.duration

        # If the current length is less than a minute we can add it
        if not (current_duration > 60):
            clips.append(clip)
            log(f"Added comment {comment.id} to video, current length is {current_duration}")
        else:
            # YouTube shorts cannot be over 60 seconds
            log("Video reached over 60 seconds")
            break
    title_and_comments = concatenate_videoclips(clips)
    title_and_comments = title_and_comments.set_position("center")

    # If the the video is over 60 seconds we trim it down to fit YouTube shorts
    if title_and_comments.duration > 60:
        title_and_comments = title_and_comments.subclip(0, 59)

    # Chose a random background video
    background = VideoFileClip(
        f"{real_path}/Videos/Backgrounds/{random.randint(1,4)}.mp4")

    # Create a random start time for the video
    t_start = random.randint(0, int(background.duration - 60))

    # Trim the background to 60 seconds
    background = background.subclip(t_start, t_start + 60)

    # Set the duration of the background to the length of the title and comments
    background = background.set_duration(title_and_comments.duration)

    # Create a final clip by combining the background and title and comments
    final_clip = CompositeVideoClip(
        clips=[background, title_and_comments],
    )

    # Output the final clip to a file
    output = f"{real_path}/Videos/Output/{submission.id}.mp4"
    final_clip.write_videofile(
        output,
        codec="mpeg4",
        threads=12,
        fps=24,
    )

    log(f"Outputted {submission.title} to file {submission.id}.mp4",
        text_color="red")

    existingPosts.append(submission.id)

# Update the file containing the posts videos have been made on
writeExistingPosts(existingPosts)
