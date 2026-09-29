"""Run the blogger over fixed topics and report quality, cost and latency metrics.

Run from the project root (the folder that contains blog_agent/):
    python -m evals.run_eval
"""
import asyncio
import json
import re
import statistics
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("blog_agent/.env")

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from blog_agent.agent import as_dict, root_agent  # noqa: E402

APP = "blog_agent"
HERE = Path(__file__).parent
sessions = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP, session_service=sessions)


async def run_topic(topic: str) -> dict:
    sid = uuid.uuid4().hex
    await sessions.create_session(app_name=APP, user_id="eval", session_id=sid)
    msg = types.Content(role="user", parts=[types.Part(text=topic)])
    start = time.time()
    async for _ in runner.run_async(user_id="eval", session_id=sid, new_message=msg):
        pass
    latency = time.time() - start
    st = (await sessions.get_session(app_name=APP, user_id="eval", session_id=sid)).state
    post = st.get("blog_post", "") or ""
    review = as_dict(st.get("post_validation")) or {}
    return {
        "topic": topic,
        "approved": bool(review.get("approved")),
        "score": review.get("score"),
        "planner_rounds": st.get("OutlineValidationChecker_rounds", 0),
        "writer_rounds": st.get("BlogPostValidationChecker_rounds", 0),
        "sources": len(set(re.findall(r"https?://\S+", post))),  # independent of the LLM judge
        "words": len(post.split()),
        "tokens": st.get("usage_tokens", 0),
        "latency_s": round(latency, 1),
    }


def avg(rows, key, nd=1):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.mean(vals), nd) if vals else 0


async def main():
    topics = json.loads((HERE / "topics.json").read_text())
    rows = []
    for t in topics:
        try:
            r = await run_topic(t)
        except Exception as e:  # failures are data too
            r = {"topic": t, "error": str(e)[:200]}
        rows.append(r)
        print(r)
        await asyncio.sleep(5)  # gentle on free-tier rate limits
    ok = [r for r in rows if "error" not in r]
    summary = {
        "runs": len(rows),
        "failures": len(rows) - len(ok),
        "approval_rate": round(sum(r["approved"] for r in ok) / max(len(ok), 1), 2),
        "avg_score": avg(ok, "score"),
        "avg_planner_rounds": avg(ok, "planner_rounds"),
        "avg_writer_rounds": avg(ok, "writer_rounds"),
        "avg_sources": avg(ok, "sources"),
        "avg_words": int(avg(ok, "words", 0)),
        "avg_tokens": int(avg(ok, "tokens", 0)),
        "avg_latency_s": avg(ok, "latency_s"),
    }
    (HERE / "results.json").write_text(json.dumps({"summary": summary, "runs": rows}, indent=2))
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k:>20}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
