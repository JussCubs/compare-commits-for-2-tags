import streamlit as st
import requests
import openai

# Load secrets from Streamlit
GITHUB_API_KEY = st.secrets["GITHUB_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

HEADERS = {
    "Authorization": f"token {GITHUB_API_KEY}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_URL = "https://api.github.com"


def get_user_repos():
    """Fetch all repositories the authenticated user has access to (including private ones)."""
    url = f"{BASE_URL}/user/repos?per_page=100&type=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return {repo["full_name"]: repo["html_url"] for repo in response.json()}
    else:
        st.error(f"Failed to fetch user repositories: {response.text}")
        return {}


def get_org_repos():
    """Fetch all repositories from organizations the user is part of."""
    url = f"{BASE_URL}/user/orgs"
    org_response = requests.get(url, headers=HEADERS)
    
    org_repos = {}

    if org_response.status_code == 200:
        orgs = org_response.json()
        for org in orgs:
            org_name = org["login"]
            repo_url = f"{BASE_URL}/orgs/{org_name}/repos?per_page=100&type=all"
            repo_response = requests.get(repo_url, headers=HEADERS)
            if repo_response.status_code == 200:
                for repo in repo_response.json():
                    org_repos[repo["full_name"]] = repo["html_url"]
            else:
                st.warning(f"Failed to fetch repositories for {org_name}: {repo_response.text}")
    
    return org_repos


def get_all_repos():
    """Combine user and organization repositories."""
    user_repos = get_user_repos()
    org_repos = get_org_repos()
    return {**user_repos, **org_repos}


def get_tags(repo_full_name):
    """Fetch all tags from the selected GitHub repository."""
    url = f"{BASE_URL}/repos/{repo_full_name}/tags"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return [tag["name"] for tag in response.json()]
    else:
        st.error(f"Failed to fetch tags: {response.text}")
        return []


def get_commits_between_tags(repo_full_name, tag1, tag2):
    """Get all commits between two tags."""
    url = f"{BASE_URL}/repos/{repo_full_name}/compare/{tag1}...{tag2}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch commits: {response.text}")
        return None


def generate_commit_summary(repo_full_name, commit_data):
    """Generate a detailed summary of changes between the selected tags."""
    commit_messages = [commit["commit"]["message"] for commit in commit_data["commits"]]
    files_changed = []

    for commit in commit_data["commits"]:
        sha = commit["sha"]
        url = f"{BASE_URL}/repos/{repo_full_name}/commits/{sha}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            commit_details = response.json()
            for file in commit_details.get("files", []):
                files_changed.append(f"{file['filename']} ({file['status']})")

    change_summary = f"""
    📌 **Number of commits:** {len(commit_messages)}
    📂 **Files changed:** {len(set(files_changed))}
    
    🔹 **List of changed files:**
    {chr(10).join(set(files_changed))}

    📝 **Commit Messages:**
    {chr(10).join(commit_messages)}
    """

    # Generate an AI summary
    return generate_ai_summary(change_summary)


def generate_ai_summary(text):
    """Use OpenAI API to summarize the commit changes."""
    openai.api_key = OPENAI_API_KEY
    prompt = f"""
    You are an expert software engineer. Summarize the following commit history with insights about the code changes:

    {text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )

    return response["choices"][0]["message"]["content"]


# Streamlit UI
st.title("🔍 GitHub Repo Tag Comparison Tool")

# Fetch all repositories the user has access to
repos = get_all_repos()
repo_names = list(repos.keys())

if repo_names:
    selected_repo = st.selectbox("Select Repository", repo_names)

    # Fetch tags for the selected repository
    tags = get_tags(selected_repo)

    if tags:
        tag1 = st.selectbox("Select First Tag", tags, index=0)
        tag2 = st.selectbox("Select Second Tag", tags, index=1)

        if st.button("Compare Tags"):
            if tag1 == tag2:
                st.warning("Please select two different tags for comparison.")
            else:
                st.info(f"Comparing `{tag1}` to `{tag2}` in `{selected_repo}`...")
                commit_data = get_commits_between_tags(selected_repo, tag1, tag2)
                if commit_data:
                    summary = generate_commit_summary(selected_repo, commit_data)
                    st.subheader("📋 Summary of Changes:")
                    st.write(summary)
else:
    st.warning("No repositories found. Ensure your GitHub API token has `repo` and `read:org` permissions.")
