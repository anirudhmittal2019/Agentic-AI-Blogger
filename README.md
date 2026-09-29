# Blogger: Multi-Agent Blog Generator (Google ADK)

An orchestrator agent that **researches** a topic on the web, **plans** an outline, **writes** a cited
article, has **critic agents** review each stage, and **saves only after human approval**.

```mermaid
flowchart TD
    U[User topic] --> B[Blogger root agent]
    B -->|tool| R[BlogResearcher<br/>google_search]
    B -->|tool| P
    B -->|tool| W
    subgraph P[RobustBlogPlanner loop]
      P1[BlogPlanner] --> P2[OutlineValidationChecker]
    end
    subgraph W[RobustBlogWriter loop]
      W1[BlogWriter] --> W2[BlogPostValidationChecker]
    end
    B -->|after user says approve| S[save_post -> posts/*.md]
```

## Run
```bash
pip install -r requirements.txt
adk web                      # pick blog_agent, send a topic, then reply "approve"
python -m evals.run_eval     # metrics over 10 topics
```
