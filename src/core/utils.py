"""
Lab 11 — Helper Utilities
"""
from google.genai import types


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    Args:
        agent: The LlmAgent instance
        runner: The InMemoryRunner instance
        user_message: Plain text message to send
        session_id: Optional session ID to continue a conversation

    Returns:
        Tuple of (response_text, session)
    """
    import asyncio
    import re

    user_id = "student"
    app_name = runner.app_name

    session = None
    if session_id is not None:
        try:
            session = await runner.session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        except (ValueError, KeyError):
            pass

    if session is None:
        try:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )
        except Exception:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    for attempt in range(4):
        try:
            final_response = ""
            async for event in runner.run_async(
                user_id=user_id, session_id=session.id, new_message=content
            ):
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_response += part.text
            return final_response, session
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Limit" in err_str:
                sleep_time = 25.0
                match = re.search(r"Please retry in (\d+(?:\.\d+)?)s", err_str)
                if match:
                    sleep_time = float(match.group(1)) + 1.0
                elif "retryDelay" in err_str:
                    match_delay = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
                    if match_delay:
                        sleep_time = float(match_delay.group(1)) + 1.0
                print(f"  [Rate limit hit in chat_with_agent, sleeping {sleep_time:.2f}s... attempt {attempt+1}/4]")
                await asyncio.sleep(sleep_time)
            else:
                raise e

    raise RuntimeError("Max retries exceeded in chat_with_agent due to rate limiting")

