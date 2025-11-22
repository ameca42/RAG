"""
Comment parser module.
Recursively parses HN comment trees and formats them for analysis.
"""

import asyncio
from typing import List, Dict, Any, Optional
import html

from app.crawler.hn_api import HNAPIClient
from app.core.config import MAX_TOP_LEVEL_COMMENTS, MAX_REPLIES_PER_COMMENT, HIGH_SCORE_THRESHOLD
from app.core.logger import app_logger


class CommentParser:
    """
    Parses HN comment trees with configurable depth limits.
    """

    def __init__(self):
        self.api_client = HNAPIClient()
        self.max_top_comments = MAX_TOP_LEVEL_COMMENTS
        self.max_replies = MAX_REPLIES_PER_COMMENT
        self.high_score_threshold = HIGH_SCORE_THRESHOLD

    def _clean_text(self, text: str) -> str:
        """
        Clean HTML entities and extra whitespace from comment text.

        Args:
            text: Raw comment text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Unescape HTML entities
        text = html.unescape(text)

        # Remove excessive newlines
        text = "\n".join(line.strip() for line in text.split("\n"))

        # Remove <p> tags (simple approach)
        text = text.replace("<p>", "\n").replace("</p>", "")

        return text.strip()

    def _format_comment(self, comment: Dict[str, Any], indent_level: int = 0) -> str:
        """
        Format a single comment with score and user info.

        Args:
            comment: Comment data from HN API
            indent_level: Indentation level (for replies)

        Returns:
            Formatted comment string
        """
        author = comment.get("by", "anonymous")
        text = self._clean_text(comment.get("text", ""))
        score = comment.get("score", 0)

        indent = "  " * indent_level
        prefix = "|-" if indent_level > 0 else ""

        return f"{indent}{prefix} [Score: {score}] {author}: {text}"

    async def _fetch_top_replies(self, kid_ids: List[int], max_replies: int) -> List[Dict[str, Any]]:
        """
        Fetch top replies sorted by score.

        Args:
            kid_ids: List of child comment IDs
            max_replies: Maximum number of replies to fetch

        Returns:
            List of comment dicts, sorted by score
        """
        if not kid_ids:
            return []

        # Fetch all kids
        kids = await self.api_client.fetch_multiple_items(kid_ids)

        # Filter to only comments and sort by score
        comments = [k for k in kids if k.get("type") == "comment"]
        comments.sort(key=lambda x: x.get("score", 0), reverse=True)

        return comments[:max_replies]

    async def parse_comment_tree(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse comment tree for a story.

        Args:
            story: Story dict with 'kids' field

        Returns:
            Dict with 'comments_summary', 'top_comments', and 'comment_count'
        """
        kid_ids = story.get("kids", [])

        if not kid_ids:
            app_logger.info(f"Story {story.get('id')} has no comments")
            return {
                "comments_summary": "",
                "top_comments": [],
                "comment_count": 0
            }

        app_logger.info(f"Parsing comments for story {story.get('id')} ({len(kid_ids)} top-level comments)")

        # Fetch top-level comments
        top_comments = await self._fetch_top_replies(kid_ids, self.max_top_comments)

        if not top_comments:
            return {
                "comments_summary": "",
                "top_comments": [],
                "comment_count": 0
            }

        # Format comments with replies
        formatted_lines = []
        high_score_comments = []

        for comment in top_comments:
            # Format main comment
            formatted = self._format_comment(comment, indent_level=0)
            formatted_lines.append(formatted)

            # Check if high score
            if comment.get("score", 0) >= self.high_score_threshold:
                high_score_comments.append({
                    "author": comment.get("by", "anonymous"),
                    "text": self._clean_text(comment.get("text", "")),
                    "score": comment.get("score", 0)
                })

            # Fetch replies
            reply_ids = comment.get("kids", [])
            if reply_ids:
                replies = await self._fetch_top_replies(reply_ids, self.max_replies)

                for reply in replies:
                    formatted_reply = self._format_comment(reply, indent_level=1)
                    formatted_lines.append(formatted_reply)

                    # Check if high score reply
                    if reply.get("score", 0) >= self.high_score_threshold:
                        high_score_comments.append({
                            "author": reply.get("by", "anonymous"),
                            "text": self._clean_text(reply.get("text", "")),
                            "score": reply.get("score", 0)
                        })

        comments_summary = "\n\n".join(formatted_lines)

        result = {
            "comments_summary": comments_summary,
            "top_comments": high_score_comments,
            "comment_count": len(top_comments)
        }

        app_logger.info(f"Parsed {len(top_comments)} comments, {len(high_score_comments)} high-score comments")

        return result


async def parse_story_comments(story: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to parse comments for a story.

    Args:
        story: Story dict from HN API

    Returns:
        Enhanced story dict with comment data
    """
    parser = CommentParser()

    comment_data = await parser.parse_comment_tree(story)

    # Add to story dict
    result = story.copy()
    result.update(comment_data)

    return result


async def parse_multiple_stories(stories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse comments for multiple stories concurrently.

    Args:
        stories: List of story dicts

    Returns:
        List of enhanced story dicts with comment data
    """
    app_logger.info(f"Parsing comments for {len(stories)} stories")

    tasks = [parse_story_comments(story) for story in stories]
    results = await asyncio.gather(*tasks)

    total_comments = sum(r.get("comment_count", 0) for r in results)
    app_logger.info(f"Parsed total of {total_comments} top-level comments")

    return results


# Test function
async def test_parser():
    """Test the comment parser."""
    print("Testing Comment Parser...")
    print("-" * 50)

    # Fetch a real story with comments
    from app.crawler.hn_api import get_top_stories

    print("\nFetching top stories...")
    stories = await get_top_stories(limit=2)

    if not stories:
        print("Failed to fetch stories")
        return

    # Find story with comments
    story_with_comments = None
    for story in stories:
        if story.get("kids") and len(story.get("kids", [])) > 0:
            story_with_comments = story
            break

    if not story_with_comments:
        print("No stories with comments found")
        return

    print(f"\nTest Story: {story_with_comments['title']}")
    print(f"  Score: {story_with_comments.get('score', 0)}")
    print(f"  Comments: {len(story_with_comments.get('kids', []))}")

    # Parse comments
    print("\nParsing comments...")
    result = await parse_story_comments(story_with_comments)

    print(f"\n✓ Parsing complete:")
    print(f"  Parsed comments: {result['comment_count']}")
    print(f"  High-score comments: {len(result['top_comments'])}")
    print(f"  Summary length: {len(result['comments_summary'])} chars")

    if result['top_comments']:
        print(f"\n  Top high-score comment:")
        top = result['top_comments'][0]
        print(f"    Author: {top['author']}")
        print(f"    Score: {top['score']}")
        print(f"    Text preview: {top['text'][:100]}...")

    if result['comments_summary']:
        print(f"\n  Comments summary preview:")
        lines = result['comments_summary'].split('\n\n')[:2]
        for line in lines:
            preview = line[:150] + "..." if len(line) > 150 else line
            print(f"    {preview}")

    print("\n" + "-" * 50)
    print("Parser tests complete! ✓")


if __name__ == "__main__":
    asyncio.run(test_parser())
