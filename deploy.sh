#!/bin/bash

echo "🚀 ESA-KU Website Deployment Preparation"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please update it with your settings."
fi

# Make build script executable
chmod +x build.sh

# Test the build script
echo "🧪 Testing build script..."
if ./build.sh; then
    echo "✅ Build script test passed!"
else
    echo "❌ Build script test failed!"
    exit 1
fi

echo ""
echo "🎉 Preparation complete! Your project is ready for deployment."
echo ""
echo "Next steps:"
echo "1. Push your code to GitHub:"
echo "   git add ."
echo "   git commit -m 'Prepare for deployment'"
echo "   git push origin main"
echo ""
echo "2. Deploy to Render.com:"
echo "   - Go to https://render.com"
echo "   - Create a new Web Service"
echo "   - Connect your GitHub repository"
echo "   - Follow the deployment guide in DEPLOYMENT.md"
echo ""
echo "3. Or deploy to Railway.app:"
echo "   - Go to https://railway.app"
echo "   - Connect your GitHub repository"
echo "   - Deploy automatically"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md" 