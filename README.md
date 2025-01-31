# compare-commits-for-2-tags

## 📌 Overview
This **Streamlit app** compares two GitHub tags, fetches commit history, analyzes file changes, and generates **AI-powered summaries** using GPT-4o-mini. Designed for **Streamlit Cloud**, it supports **private & organization repositories** and runs efficiently with **multi-threading**.

## 🛠️ Setup on Streamlit Cloud
1. **Generate a Fine-Grained GitHub Token** with these **permissions**:
   - ✅ Metadata (Read-only) → Access repository metadata
   - ✅ Contents (Read-only) → Fetch commits, branches, tags, file changes
   - ✅ Commit Statuses (Read-only) → View commit statuses (CI/CD)
2. **Go to Streamlit Cloud → App Settings → Secrets Manager**  
3. **Add Secrets**:
```GITHUB_API_KEY=“your_generated_token”```
```OPENAI_API_KEY=“your_openai_api_key”```
4. **Deploy & Run on Streamlit Cloud**.

## 🖥️ How to Use
1. **Select a repository**  
2. **Choose two tags to compare**  
3. **Set commit limit (default 10, 0 = all)**  
4. **Edit AI prompt (optional)**  
5. **Click "Compare Tags" → View AI-powered summary of changes**  

## 🔥 Features
✅ **Fast multi-threaded commit retrieval**  
✅ **Works with private & organization repos**  
✅ **AI-generated summaries for commit insights**  
✅ **Customizable AI prompt for summaries**  

🚀 **Designed for developers needing quick GitHub commit comparisons.**  
