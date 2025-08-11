#!/bin/bash

set -e

echo "🔧 Setting up pre-push formatting automation..."

# Git hooksディレクトリを作成
echo "📁 Creating .githooks directory..."
mkdir -p .githooks

# Git設定を更新してhooksPathを.githooksに設定
echo "⚙️  Configuring Git to use .githooks directory..."
git config core.hooksPath .githooks

# pre-pushスクリプトに実行権限を付与
echo "🔐 Setting executable permissions on pre-push hook..."
chmod +x .githooks/pre-push

echo ""
echo "✅ Pre-push formatting automation setup complete!"
echo ""
echo "📋 What's been configured:"
echo "   • Git hooks directory: .githooks/"
echo "   • Pre-push hook: .githooks/pre-push"
echo "   • Auto-formatting: Black + isort"
echo "   • Linting checks: Flake8 + MyPy"
echo ""
echo "🚀 Usage:"
echo "   • Formatting will run automatically on git push"
echo "   • If formatting changes are made, they'll be auto-committed"
echo "   • Linting errors will block the push until fixed"
echo ""
echo "💡 Manual commands available:"
echo "   • make format        - Format code manually"
echo "   • make format-check  - Check formatting without changes"
echo "   • make lint          - Run linting checks"
echo "   • make setup-hooks   - Re-run hooks setup"
echo ""
echo "🎯 Ready to go! Your next push will automatically format code and run lint checks."