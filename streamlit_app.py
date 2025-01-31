import streamlit as st
import requests
from openai import OpenAI
import concurrent.futures

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


def get_commits_between_tags(repo_full_name, tag1, tag2, commit_limit=10):
    """Get all commits between two tags with a fallback approach."""
    compare_url = f"{BASE_URL}/repos/{repo_full_name}/compare/{tag1}...{tag2}"
    compare_response = requests.get(compare_url, headers=HEADERS)

    if compare_response.status_code == 200:
        data = compare_response.json()
        commits = data.get("commits", [])

        if commits:
            return commits[:commit_limit] if commit_limit else commits

    # If /compare/ fails or returns no commits, fetch manually from tag1 onward
    fallback_url = f"{BASE_URL}/repos/{repo_full_name}/commits?sha={tag1}&per_page=100"
    fallback_response = requests.get(fallback_url, headers=HEADERS)

    if fallback_response.status_code == 200:
        commits = fallback_response.json()
        return commits[:commit_limit] if commit_limit else commits
    else:
        st.error(f"Failed to fetch commits manually: {fallback_response.text}")
        return None


def fetch_commit_details(repo_full_name, commit):
    """Fetch detailed commit changes using threading."""
    sha = commit["sha"]
    url = f"{BASE_URL}/repos/{repo_full_name}/commits/{sha}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        commit_details = response.json()
        commit_message = commit_details["commit"]["message"]
        changed_files = [f"{file['filename']} ({file['status']})" for file in commit_details.get("files", [])]
        return commit_message, changed_files
    else:
        return commit["commit"]["message"], []


def generate_commit_summary(repo_full_name, commits, custom_prompt):
    """Generate a detailed summary of commit changes using threading."""
    if not commits:
        return "No commit data available."

    commit_messages = []
    files_changed = set()

    # Use threading for faster commit fetching
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_commit_details, repo_full_name, commit) for commit in commits]

        for future in concurrent.futures.as_completed(futures):
            commit_message, changed_files = future.result()
            commit_messages.append(commit_message)
            files_changed.update(changed_files)

    change_summary = f"""
    📌 **Number of commits analyzed:** {len(commits)}
    📂 **Files changed:** {len(files_changed)}
    
    🔹 **List of changed files:**
    {chr(10).join(files_changed)}

    📝 **Commit Messages:**
    {chr(10).join(commit_messages)}
    """

    return generate_ai_summary(custom_prompt, change_summary)


def generate_ai_summary(custom_prompt, text):
    """Use OpenAI API to summarize the commit changes."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"{custom_prompt}\n\n{text}"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response.choices[0].message.content


# Streamlit UI
st.title("🔍 GitHub Repo Tag Comparison Tool (Multi-Threaded)")

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
        
        commit_limit = st.number_input("Limit commits (0 = all)", min_value=0, value=10, step=1)

        # Editable AI Prompt
        default_prompt = """You are an expert software engineer. Summarize the following commit history with insights about the code changes."""
        custom_prompt = st.text_area("Edit AI Prompt:", default_prompt, height=150)

        if st.button("Compare Tags"):
            if tag1 == tag2:
                st.warning("Please select two different tags for comparison.")
            else:
                st.info(f"Comparing `{tag1}` to `{tag2}` in `{selected_repo}`...")
                commits = get_commits_between_tags(selected_repo, tag1, tag2, commit_limit)
                if commits:
                    summary = generate_commit_summary(selected_repo, commits, custom_prompt)
                    st.subheader("📋 Summary of Changes:")
                    st.write(summary)
                else:
                    st.warning("No commits found, even after fallback attempt.")
else:
    st.warning("No repositories found. Ensure your GitHub API token has `repo` and `read:org` permissions.")
