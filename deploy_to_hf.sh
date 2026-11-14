#!/bin/bash
echo "🚀 Starting Deployment to Hugging Face Spaces..."

# 1. Clean previous attempts
rm -rf hf_deploy

# 2. Clone the Space
echo "📥 Cloning User's Space..."
git clone git@hf.co:spaces/Jatin04/TradeWise hf_deploy

if [ ! -d "hf_deploy" ]; then
    echo "❌ Failed to clone. Please check the URL or your internet connection."
    exit 1
fi

# 3. Copy Backend Files (Using rsync to exclude garbage)
echo "📂 Copying Backend Files..."
# Ensure rsync exists, else fall back? Mac has rsync.
rsync -av --exclude='venv' \
          --exclude='__pycache__' \
          --exclude='.env' \
          --exclude='models' \
          --exclude='.DS_Store' \
          backend/ hf_deploy/

# 4. Commit and Push
echo "Vk Committing and Pushing..."
cd hf_deploy
git add .
git status
git commit -m "Deploying Backend v1.0"

echo "⬆️ Pushing to Hugging Face over SSH..."
git push
PUSH_STATUS=$?

# 5. Cleanup
cd ..
rm -rf hf_deploy

if [ $PUSH_STATUS -ne 0 ]; then
    echo "❌ Push to Hugging Face failed. Nothing was deployed."
    exit 1
fi

echo "✅ Deployment Instructions Completed!"
