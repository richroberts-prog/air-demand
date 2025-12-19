#!/bin/bash
# UI Iteration Script - Run tests, capture screenshots, and analyze results

set -e

echo "🎨 Starting UI iteration..."
echo ""

# Ensure screenshot directory exists
mkdir -p test-results/screenshots

# Run screenshot tests
echo "📸 Capturing screenshots..."
npx playwright test tests/screenshot.spec.ts --headed --reporter=line

echo ""
echo "✅ Screenshots captured to: test-results/screenshots/"
echo ""
echo "📁 Available screenshots:"
ls -lh test-results/screenshots/

echo ""
echo "🔍 Run functional tests..."
npx playwright test tests/dashboard.spec.ts --reporter=line

echo ""
echo "✨ Iteration complete!"
echo ""
echo "To view screenshots, run:"
echo "  open test-results/screenshots/  # macOS"
echo "  xdg-open test-results/screenshots/  # Linux"
echo ""
echo "To run Playwright UI mode for interactive testing:"
echo "  npx playwright test --ui"
