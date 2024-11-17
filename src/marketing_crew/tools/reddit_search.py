from typing import Type, Optional, Dict
from crewai_tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
import praw
from datetime import datetime, timedelta
import os

class RedditSearchInput(BaseModel):
    """Input schema for RedditSearch."""
    subreddit: str = Field(..., description="Subreddit name to search in")
    query: str = Field(None, description="Search query (optional)")
    time_filter: str = Field(
        "month",
        description="Time filter: hour, day, week, month, year, all"
    )
    sort: str = Field(
        "top",
        description="Sort method: relevance, hot, top, new, comments"
    )

class RedditSearchTool(BaseTool):
    name: str = "Reddit Search Tool"
    description: str = """
        Search Reddit posts and comments in a specific subreddit.
        Useful for finding user discussions, problems, and pain points.
        Returns top posts with their scores, comments, and content.
        Can search by specific keywords or analyze top posts.
    """
    args_schema: Type[BaseModel] = RedditSearchInput
    _credentials: Dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize credentials from environment variables
        self._credentials = {
            "REDDIT_CLIENT_ID": os.getenv("REDDIT_CLIENT_ID"),
            "REDDIT_CLIENT_SECRET": os.getenv("REDDIT_CLIENT_SECRET")
        }

    def _run(self, subreddit: str, query: str = None, time_filter: str = "month", sort: str = "top") -> str:
        try:
            if not self._credentials.get("REDDIT_CLIENT_ID") or not self._credentials.get("REDDIT_CLIENT_SECRET"):
                return "Error: Reddit API credentials not found in environment variables. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."

            # Initialize PRAW with credentials
            reddit = praw.Reddit(
                client_id=self._credentials["REDDIT_CLIENT_ID"],
                client_secret=self._credentials["REDDIT_CLIENT_SECRET"],
                user_agent="CrewAI Reddit Analyzer v1.0"
            )
            
            # Access subreddit
            subreddit = reddit.subreddit(subreddit.replace("r/", ""))
            
            results = []
            if query:
                # Search with query
                posts = subreddit.search(query, sort=sort, time_filter=time_filter, limit=10)
            else:
                # Get top posts if no query
                if sort == "top":
                    posts = subreddit.top(time_filter=time_filter, limit=10)
                elif sort == "hot":
                    posts = subreddit.hot(limit=10)
                else:
                    posts = subreddit.new(limit=10)
            
            for post in posts:
                try:
                    # Get top comments
                    post.comments.replace_more(limit=0)
                    top_comments = [comment.body for comment in post.comments.list()[:3]]
                    
                    results.append({
                        "title": post.title,
                        "score": post.score,
                        "comments_count": post.num_comments,
                        "content": post.selftext[:500] + "..." if len(post.selftext) > 500 else post.selftext,
                        "top_comments": top_comments,
                        "url": f"https://reddit.com{post.permalink}"
                    })
                except Exception as e:
                    print(f"Error processing post: {str(e)}")
                    continue
            
            if not results:
                return "No results found for the given query."
            
            # Format results as a string
            output = ""
            for i, post in enumerate(results, 1):
                output += f"\n--- Post {i} ---\n"
                output += f"Title: {post['title']}\n"
                output += f"Score: {post['score']} | Comments: {post['comments_count']}\n"
                output += f"Content: {post['content']}\n"
                output += "Top Comments:\n"
                for j, comment in enumerate(post['top_comments'], 1):
                    output += f"{j}. {comment[:200]}...\n"
                output += f"URL: {post['url']}\n"
            
            return output

        except Exception as e:
            return f"Error searching Reddit: {str(e)}" 