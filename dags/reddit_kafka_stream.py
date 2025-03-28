from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import json
import os
import praw
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

default_args = {
    'owner': 'airmeet',
    'start_date': datetime(2025, 3, 27, 9, 0)
}

def init_reddit_client():
    """
    Initialize and return a Reddit API client.
    """
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

def get_top_comments(submission, top_n=5):
    """
    Retrieve the top N comments from a submission based on comment score.
    Returns a list of comment bodies.
    """
    submission.comments.replace_more(limit=0)
    all_comments = submission.comments.list()
    sorted_comments = sorted(
        all_comments,
        key=lambda comment: comment.score if hasattr(comment, 'score') else 0,
        reverse=True
    )
    top_comments = sorted_comments[:top_n]
    return [comment.body for comment in top_comments if hasattr(comment, 'body')]

def get_reddit_data(reddit, subreddits, limit=1):
    """
    Retrieve submissions from the specified subreddits using the stream API.
    If selftext is empty or very short, fetch the top 5 comments separately.
    The function collects submissions until the specified limit is reached.
    """
    submissions = reddit.subreddit(subreddits).stream.submissions(skip_existing=False)
    results = []
    for submission in submissions:
        # Combine title and selftext
        text = f"{submission.title or ''}\n{submission.selftext or ''}".strip()
        
        # If selftext is empty or very short, retrieve top 5 comments (kept separate)
        if not submission.selftext or len(submission.selftext) < 200:
            top_comments = get_top_comments(submission, top_n=5)
        else:
            top_comments = []
        
        data = {
            "id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext,
            "top_comments": top_comments,  # List of separate comment bodies
            "subreddit": submission.subreddit.display_name,
            "created_utc": submission.created_utc,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "url": submission.url,
            "domain": submission.domain,
            "author": str(submission.author),
            "text_length": len(text)
        }
        results.append(data)
        if len(results) >= limit:
            break
    return results

def fetch_reddit_data(**kwargs):
    """
    Initializes the Reddit client, retrieves submissions from the specified subreddit(s)
    using the stream API, and prints the results as JSON.
    """
    reddit = init_reddit_client()
    subreddits = "Spiderman"  # Modify this to your desired subreddit(s)
    results = get_reddit_data(reddit, subreddits, limit=5)
    
    # Print the results as a formatted JSON string
    print(json.dumps(results, indent=3))
    return results

# with DAG(
#     dag_id='reddit_data_ingestion',
#     default_args=default_args,
#     schedule_interval='@daily',
#     catchup=False,
# ) as dag:
    
#     reddit_data_task = PythonOperator(
#         task_id='fetch_reddit_data',
#         python_callable=fetch_reddit_data,
#         provide_context=True,
#     )

# For local testing, you can run:
if __name__ == "__main__":
    fetch_reddit_data()
