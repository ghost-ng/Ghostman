#!/usr/bin/env python3
"""
Test the new Pygments-based syntax highlighting with multiple languages.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from ghostman.src.presentation.widgets.mixed_content_display import MixedContentDisplay

def test_pygments_multilanguage():
    """Test Pygments syntax highlighting with multiple languages."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Pygments Multi-Language Syntax Highlighting Test")
    window.resize(1000, 800)
    
    # Central widget and layout
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    window.setCentralWidget(central_widget)
    
    # Create test display
    display = MixedContentDisplay()
    
    # Test theme colors (Solarized Dark)
    theme_colors = {
        'bg_primary': '#002b36',
        'bg_secondary': '#073642', 
        'bg_tertiary': '#094352',
        'text_primary': '#839496',
        'text_secondary': '#586e75',
        'border': '#073642',
        'info': '#268bd2',
        'warning': '#cb4b16',
        'error': '#dc322f',
        'keyword': '#859900',     # Green
        'string': '#2aa198',      # Cyan
        'comment': '#586e75',     # Gray
        'function': '#b58900',    # Yellow  
        'number': '#d33682',      # Magenta
        'builtin': '#4ec9b0',     # Cyan
        'operator': '#d4d4d4',    # Light gray
        'class': '#4ec9b0',       # Cyan
        'variable': '#9cdcfe',    # Light blue
        'constant': '#4fc1ff',    # Bright blue
        'decorator': '#ffd700',   # Gold
        'docstring': '#6a9955',   # Green
        'preprocessor': '#c586c0', # Purple
        'interactive': '#073642',
        'interactive_hover': '#094352',
    }
    display.set_theme_colors(theme_colors)
    
    # Control buttons
    button_layout = QHBoxLayout()
    
    test_python_btn = QPushButton("Test Python")
    test_js_btn = QPushButton("Test JavaScript") 
    test_html_btn = QPushButton("Test HTML")
    test_json_btn = QPushButton("Test JSON")
    test_multiple_btn = QPushButton("Test Multiple Languages")
    clear_btn = QPushButton("Clear Display")
    
    button_layout.addWidget(test_python_btn)
    button_layout.addWidget(test_js_btn)
    button_layout.addWidget(test_html_btn)
    button_layout.addWidget(test_json_btn)
    button_layout.addWidget(test_multiple_btn)
    button_layout.addWidget(clear_btn)
    button_layout.addStretch()
    
    layout.addLayout(button_layout)
    
    # Status label
    status_label = QLabel("Ready to test Pygments multi-language syntax highlighting")
    status_label.setStyleSheet("color: #268bd2; padding: 5px; background: #073642; border-radius: 3px;")
    layout.addWidget(status_label)
    
    layout.addWidget(display)
    
    def test_python():
        status_label.setText("Testing Python syntax highlighting with Pygments...")
        display.add_html_content("<h2>🐍 Python Code</h2>", "info")
        
        python_code = '''import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class APIResponse:
    """Data class for API responses."""
    status: int
    data: Optional[Dict] = field(default_factory=dict)
    error: Optional[str] = None

async def fetch_data(url: str, session) -> APIResponse:
    """Fetch data from API with error handling."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                return APIResponse(status=200, data=data)
            else:
                error_msg = f"HTTP {response.status}: {await response.text()}"
                return APIResponse(status=response.status, error=error_msg)
                
    except asyncio.TimeoutError:
        return APIResponse(status=408, error="Request timeout")
    except Exception as e:
        return APIResponse(status=500, error=str(e))

# Example usage with context manager
async def main():
    urls = [
        "https://api.github.com/users/octocat", 
        "https://jsonplaceholder.typicode.com/posts/1"
    ]
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(url, session) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            print(f"URL {i+1}: {response.status} - {response.data or response.error}")

if __name__ == "__main__":
    asyncio.run(main())'''
        
        display.add_code_snippet(python_code, "python")
        
    def test_javascript():
        status_label.setText("Testing JavaScript syntax highlighting with Pygments...")
        display.add_html_content("<h2>📜 JavaScript Code</h2>", "info")
        
        js_code = '''// Modern JavaScript with ES6+ features
class DataProcessor {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.cache = new Map();
        this.retryAttempts = 3;
    }

    /**
     * Process data with error handling and retry logic
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Processed data
     */
    async processData(endpoint, options = {}) {
        const cacheKey = `${endpoint}_${JSON.stringify(options)}`;
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            console.log(`🎯 Cache hit for: ${endpoint}`);
            return this.cache.get(cacheKey);
        }

        // Fetch with retry logic
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(endpoint, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${this.apiKey}`,
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                
                // Transform data using modern array methods
                const processed = data
                    .filter(item => item.active && item.score > 0.5)
                    .map(item => ({
                        id: item.id,
                        name: item.name?.trim() || 'Unknown',
                        score: Math.round(item.score * 100) / 100,
                        tags: item.tags?.join(', ') || 'No tags',
                        createdAt: new Date(item.created_at).toLocaleDateString()
                    }))
                    .sort((a, b) => b.score - a.score);

                // Cache the result
                this.cache.set(cacheKey, processed);
                
                return processed;

            } catch (error) {
                console.warn(`⚠️ Attempt ${attempt}/${this.retryAttempts} failed:`, error.message);
                
                if (attempt === this.retryAttempts) {
                    throw new Error(`Failed after ${this.retryAttempts} attempts: ${error.message}`);
                }
                
                // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
    }

    // Static method with arrow function
    static validateConfig = (config) => {
        const required = ['apiKey', 'endpoint'];
        return required.every(field => config[field]);
    };
}

// Usage with destructuring and template literals
const processor = new DataProcessor(process.env.API_KEY);
const { data, error } = await processor.processData('/api/v1/data');

if (error) {
    console.error(`❌ Error: ${error}`);
} else {
    console.log(`✅ Processed ${data.length} items`);
}'''
        
        display.add_code_snippet(js_code, "javascript")
        
    def test_html():
        status_label.setText("Testing HTML syntax highlighting with Pygments...")
        display.add_html_content("<h2>🌐 HTML Code</h2>", "info")
        
        html_code = '''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modern Web App</title>
    
    <!-- Progressive Web App manifest -->
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e1e1e">
    
    <!-- Preload critical resources -->
    <link rel="preload" href="/fonts/Inter-Variable.woff2" as="font" type="font/woff2" crossorigin>
    
    <style>
        :root {
            --primary-color: #007acc;
            --secondary-color: #f0f0f0;
            --text-color: #333;
            --background: #ffffff;
        }
        
        [data-theme="dark"] {
            --text-color: #e0e0e0;
            --background: #1e1e1e;
            --secondary-color: #2d2d2d;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            background: var(--background);
            color: var(--text-color);
            transition: all 0.3s ease;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
    </style>
</head>

<body>
    <header class="header" role="banner">
        <nav class="nav" aria-label="Main navigation">
            <div class="nav__brand">
                <img src="/logo.svg" alt="Company Logo" width="120" height="40">
            </div>
            
            <ul class="nav__menu" role="menubar">
                <li role="none">
                    <a href="#home" role="menuitem" aria-current="page">Home</a>
                </li>
                <li role="none">
                    <a href="#about" role="menuitem">About</a>
                </li>
                <li role="none">
                    <a href="#contact" role="menuitem">Contact</a>
                </li>
            </ul>
            
            <button class="theme-toggle" aria-label="Toggle dark mode" data-toggle="theme">
                🌙
            </button>
        </nav>
    </header>

    <main class="container" role="main">
        <section class="hero" aria-labelledby="hero-heading">
            <h1 id="hero-heading">Welcome to Modern Web</h1>
            <p class="hero__subtitle">
                Building fast, accessible, and beautiful web experiences.
            </p>
            
            <!-- Call to action with loading state -->
            <button class="btn btn--primary" data-action="signup" aria-describedby="signup-desc">
                <span class="btn__text">Get Started</span>
                <span class="btn__loader" hidden aria-hidden="true">Loading...</span>
            </button>
            <p id="signup-desc" class="sr-only">Sign up for a free account</p>
        </section>

        <section class="features grid" aria-labelledby="features-heading">
            <h2 id="features-heading" class="sr-only">Features</h2>
            
            <article class="card" data-feature="performance">
                <h3>⚡ Fast Performance</h3>
                <p>Optimized for speed with lazy loading and code splitting.</p>
            </article>
            
            <article class="card" data-feature="accessibility">
                <h3>♿ Accessible</h3>
                <p>WCAG 2.1 AA compliant with full keyboard navigation.</p>
            </article>
            
            <article class="card" data-feature="responsive">
                <h3>📱 Responsive</h3>
                <p>Mobile-first design that works on all screen sizes.</p>
            </article>
        </section>
    </main>

    <!-- Service Worker registration -->
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('SW registered', reg))
                .catch(err => console.log('SW registration failed', err));
        }
    </script>
    
    <script type="module" src="/js/main.js"></script>
</body>
</html>'''
        
        display.add_code_snippet(html_code, "html")
        
    def test_json():
        status_label.setText("Testing JSON syntax highlighting with Pygments...")
        display.add_html_content("<h2>📄 JSON Configuration</h2>", "info")
        
        json_code = '''{
  "name": "modern-web-app",
  "version": "2.1.0",
  "description": "A modern progressive web application",
  "main": "dist/index.js",
  "type": "module",
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=9.0.0"
  },
  "scripts": {
    "dev": "vite serve --host 0.0.0.0 --port 3000",
    "build": "vite build --mode production",
    "preview": "vite preview --port 4173",
    "test": "vitest run --coverage",
    "test:watch": "vitest --ui --coverage",
    "lint": "eslint src --ext .ts,.tsx,.js,.jsx --fix",
    "typecheck": "tsc --noEmit",
    "format": "prettier --write src/**/*.{ts,tsx,js,jsx,css,md}"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "@tanstack/react-query": "^4.24.6",
    "axios": "^1.3.1",
    "zustand": "^4.3.2",
    "@headlessui/react": "^1.7.8",
    "@heroicons/react": "^2.0.16",
    "clsx": "^1.2.1",
    "tailwind-merge": "^1.10.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.28",
    "@types/react-dom": "^18.0.10",
    "@typescript-eslint/eslint-plugin": "^5.52.0",
    "@typescript-eslint/parser": "^5.52.0",
    "@vitejs/plugin-react": "^3.1.0",
    "autoprefixer": "^10.4.13",
    "eslint": "^8.34.0",
    "eslint-plugin-react": "^7.32.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "postcss": "^8.4.21",
    "prettier": "^2.8.4",
    "tailwindcss": "^3.2.6",
    "typescript": "^4.9.5",
    "vite": "^4.1.1",
    "vite-plugin-pwa": "^0.14.1",
    "vitest": "^0.28.5",
    "@vitest/ui": "^0.28.5"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/company/modern-web-app.git"
  },
  "keywords": [
    "react",
    "typescript",
    "vite",
    "pwa",
    "modern",
    "web-app"
  ],
  "author": {
    "name": "Development Team",
    "email": "dev@company.com",
    "url": "https://company.com"
  },
  "license": "MIT",
  "config": {
    "api": {
      "baseUrl": "https://api.company.com/v1",
      "timeout": 30000,
      "retries": 3
    },
    "features": {
      "analytics": true,
      "offline": true,
      "notifications": false,
      "darkMode": true
    },
    "build": {
      "sourceMaps": true,
      "minify": true,
      "treeshake": true,
      "splitting": true
    }
  }
}'''
        
        display.add_code_snippet(json_code, "json")
        
    def test_multiple():
        status_label.setText("Testing multiple languages with Pygments...")
        
        display.add_html_content("<h1>🌍 Multi-Language Syntax Highlighting Test</h1>", "info")
        display.add_html_content(
            "<p>Testing Pygments with multiple programming languages. "
            "Each code block should have proper syntax highlighting:</p>", 
            "normal"
        )
        
        # Python
        display.add_html_content("<h3>Python (Data Science)</h3>", "info")
        python_code = '''import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

def analyze_dataset(filepath: str) -> dict:
    """Analyze dataset and train ML model."""
    # Load and explore data
    df = pd.read_csv(filepath)
    print(f"Dataset shape: {df.shape}")
    
    # Feature engineering
    numeric_features = df.select_dtypes(include=[np.number]).columns
    X = df[numeric_features].fillna(df[numeric_features].mean())
    y = df['target']
    
    # Train model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    return {"accuracy": model.score(X_test, y_test), "features": len(X.columns)}'''
        display.add_code_snippet(python_code, "python")
        
        # Rust
        display.add_html_content("<h3>Rust (Systems Programming)</h3>", "info") 
        rust_code = '''use std::collections::HashMap;
use tokio::net::TcpListener;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct ApiResponse<T> {
    status: u16,
    data: Option<T>,
    error: Option<String>,
}

impl<T> ApiResponse<T> {
    fn success(data: T) -> Self {
        Self {
            status: 200,
            data: Some(data),
            error: None,
        }
    }
    
    fn error(status: u16, message: &str) -> Self {
        Self {
            status,
            data: None,
            error: Some(message.to_string()),
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:8080").await?;
    println!("🚀 Server running on http://127.0.0.1:8080");
    
    loop {
        let (stream, addr) = listener.accept().await?;
        println!("📥 Connection from {}", addr);
        
        tokio::spawn(async move {
            if let Err(e) = handle_connection(stream).await {
                eprintln!("❌ Error handling connection: {}", e);
            }
        });
    }
}'''
        display.add_code_snippet(rust_code, "rust")
        
        # SQL
        display.add_html_content("<h3>SQL (Database Query)</h3>", "info")
        sql_code = '''-- Complex analytics query with CTEs and window functions
WITH monthly_sales AS (
    SELECT 
        DATE_TRUNC('month', order_date) as month,
        product_category,
        SUM(order_total) as total_sales,
        COUNT(DISTINCT customer_id) as unique_customers,
        AVG(order_total) as avg_order_value
    FROM orders o
    JOIN products p ON o.product_id = p.id
    WHERE order_date >= '2023-01-01'
    GROUP BY 1, 2
),
growth_metrics AS (
    SELECT 
        month,
        product_category,
        total_sales,
        LAG(total_sales) OVER (
            PARTITION BY product_category 
            ORDER BY month
        ) as prev_month_sales,
        ROUND(
            (total_sales - LAG(total_sales) OVER (
                PARTITION BY product_category 
                ORDER BY month
            )) * 100.0 / NULLIF(LAG(total_sales) OVER (
                PARTITION BY product_category 
                ORDER BY month
            ), 0), 2
        ) as growth_percentage
    FROM monthly_sales
)
SELECT 
    month,
    product_category,
    TO_CHAR(total_sales, 'FM$999,999,990.00') as formatted_sales,
    COALESCE(growth_percentage, 0) as growth_rate,
    CASE 
        WHEN growth_percentage > 20 THEN '🚀 High Growth'
        WHEN growth_percentage > 0 THEN '📈 Growing' 
        WHEN growth_percentage < -10 THEN '📉 Declining'
        ELSE '➡️ Stable'
    END as performance_status
FROM growth_metrics
ORDER BY month DESC, total_sales DESC
LIMIT 50;'''
        display.add_code_snippet(sql_code, "sql")
        
    def clear_display():
        display.clear()
        status_label.setText("Display cleared. Ready for next test.")
    
    # Connect buttons
    test_python_btn.clicked.connect(test_python)
    test_js_btn.clicked.connect(test_javascript)
    test_html_btn.clicked.connect(test_html)
    test_json_btn.clicked.connect(test_json)
    test_multiple_btn.clicked.connect(test_multiple)
    clear_btn.clicked.connect(clear_display)
    
    # Add initial content
    display.add_html_content("<h1>🧪 Pygments Multi-Language Test</h1>", "info")
    display.add_html_content(
        "<p>This test validates Pygments syntax highlighting across multiple languages:</p>"
        "<ul>"
        "<li><b>500+ languages supported</b> - No hardcoded syntax patterns needed</li>"
        "<li><b>Automatic language detection</b> - Smart detection from code content</li>"
        "<li><b>Theme integration</b> - Colors adapt to current theme automatically</li>"
        "<li><b>Performance optimized</b> - Fast highlighting with token caching</li>"
        "</ul>", 
        "normal"
    )
    
    # Show window
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    test_pygments_multilanguage()