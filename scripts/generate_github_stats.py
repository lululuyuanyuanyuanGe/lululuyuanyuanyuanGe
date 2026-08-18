#!/usr/bin/env python3
"""Generate the SVG used by the profile README from GitHub's GraphQL API."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


DEMO_DATA = {
    "contributions": 318,
    "commits": 294,
    "repositories": 37,
    "contributed_repositories": 3,
    "pull_requests": 2,
}


def fetch_stats(username: str, token: str) -> dict[str, int]:
    now = dt.datetime.now(dt.timezone.utc)
    previous_year = now - dt.timedelta(days=365)
    query = """
    query ProfileStats($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        repositories(first: 1, ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
        repositoriesContributedTo(
          first: 1
          contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
          includeUserRepositories: true
        ) { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
          totalCommitContributions
          totalPullRequestContributions
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": username,
            "from": previous_year.isoformat(),
            "to": now.isoformat(),
        },
    }).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"], indent=2))
    user = result["data"]["user"]
    if user is None:
        raise RuntimeError(f"GitHub user not found: {username}")
    contributions = user["contributionsCollection"]
    return {
        "contributions": contributions["contributionCalendar"]["totalContributions"],
        "commits": contributions["totalCommitContributions"],
        "repositories": user["repositories"]["totalCount"],
        "contributed_repositories": user["repositoriesContributedTo"]["totalCount"],
        "pull_requests": contributions["totalPullRequestContributions"],
    }


def render_svg(stats: dict[str, int], username: str, updated: str) -> str:
    cards = [
        ("CONTRIBUTIONS · LAST 365 DAYS", stats["contributions"], "#22d3ee"),
        ("PUBLIC REPOSITORIES", stats["repositories"], "#818cf8"),
        ("COMMITS · LAST 365 DAYS", stats["commits"], "#c084fc"),
        ("CONTRIBUTED REPOSITORIES", stats["contributed_repositories"], "#fb7185"),
    ]
    card_markup = []
    for index, (label, value, color) in enumerate(cards):
        x = 26 + index * 236
        card_markup.append(
            f'''<g transform="translate({x} 76)">
  <rect width="218" height="102" rx="13" fill="#0d192b" stroke="#26364f"/>
  <rect width="4" height="102" rx="2" fill="{color}"/>
  <text x="18" y="31" class="label">{label}</text>
  <text x="18" y="75" class="value" fill="{color}">{value:,}</text>
</g>'''
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230" role="img" aria-labelledby="title desc">
  <title id="title">{username}'s GitHub engineering activity</title>
  <desc id="desc">Public GitHub activity, refreshed daily.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#07111f"/><stop offset="1" stop-color="#15112f"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#22d3ee"/><stop offset="0.5" stop-color="#818cf8"/><stop offset="1" stop-color="#c084fc"/>
    </linearGradient>
    <style>
      .title {{ font: 700 18px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #e2e8f0; letter-spacing: 1px; }}
      .label {{ font: 600 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #94a3b8; letter-spacing: .7px; }}
      .value {{ font: 800 34px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .small {{ font: 500 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #64748b; }}
    </style>
  </defs>
  <rect x="1" y="1" width="998" height="228" rx="18" fill="url(#bg)" stroke="url(#edge)" stroke-width="2"/>
  <text x="26" y="38" class="title">ENGINEERING ACTIVITY</text>
  <text x="974" y="38" class="small" text-anchor="end">@{username}</text>
  <path d="M26 55 H974" stroke="#334155"/>
  {''.join(card_markup)}
  <circle cx="29" cy="204" r="4" fill="#4ade80"/>
  <text x="42" y="208" class="small">PUBLIC DATA · UPDATED {updated} · {stats['pull_requests']} PULL REQUESTS IN THE LAST 365 DAYS</text>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="render with local sample data")
    parser.add_argument("--output", default="assets/github-stats.svg")
    args = parser.parse_args()
    username = os.environ.get("PROFILE_USERNAME", "lululuyuanyuanyuanGe")
    if args.demo:
        stats = DEMO_DATA
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required unless --demo is used")
        stats = fetch_stats(username, token)
    updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d UTC")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_svg(stats, username, updated), encoding="utf-8")


if __name__ == "__main__":
    main()
