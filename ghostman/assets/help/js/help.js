// Help Documentation JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeHelp();
});

function initializeHelp() {
    initializeSearch();
    initializeNavigation();
    initializeFAQ();
    initializeScrollSpy();
    initializeThemeToggle();
    updateVersion();
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    let searchTimeout;
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(e.target.value);
        }, 300);
    });
    
    // Handle search keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
        
        if (e.key === 'Escape' && document.activeElement === searchInput) {
            searchInput.blur();
            clearSearch();
        }
    });
}

function performSearch(query) {
    const sections = document.querySelectorAll('.content-section, .subsection');
    const searchResults = [];
    
    if (!query.trim()) {
        clearSearch();
        return;
    }
    
    sections.forEach(section => {
        const text = section.textContent.toLowerCase();
        const searchTerm = query.toLowerCase();
        
        if (text.includes(searchTerm)) {
            const title = section.querySelector('h2, h3')?.textContent || 'Untitled';
            const id = section.id || section.closest('[id]')?.id;
            
            if (id) {
                searchResults.push({
                    title,
                    id,
                    element: section
                });
            }
        }
    });
    
    displaySearchResults(searchResults, query);
}

function displaySearchResults(results, query) {
    // Hide all sections first
    const allSections = document.querySelectorAll('.content-section');
    allSections.forEach(section => {
        section.style.display = results.length > 0 ? 'none' : 'block';
    });
    
    // Show matching sections
    results.forEach(result => {
        const section = document.getElementById(result.id);
        if (section) {
            section.style.display = 'block';
            highlightSearchTerms(section, query);
        }
    });
    
    // Update sidebar to show only matching items
    updateSidebarForSearch(results);
}

function clearSearch() {
    // Show all sections
    const allSections = document.querySelectorAll('.content-section');
    allSections.forEach(section => {
        section.style.display = 'block';
    });
    
    // Remove highlights
    const highlights = document.querySelectorAll('.search-highlight');
    highlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
    
    // Reset sidebar
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    sidebarLinks.forEach(link => {
        link.style.display = 'block';
    });
}

function highlightSearchTerms(element, query) {
    if (!query.trim()) return;
    
    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    let node;
    
    while (node = walker.nextNode()) {
        if (node.parentNode.tagName !== 'SCRIPT' && node.parentNode.tagName !== 'STYLE') {
            textNodes.push(node);
        }
    }
    
    textNodes.forEach(textNode => {
        const text = textNode.textContent;
        const regex = new RegExp(`(${query})`, 'gi');
        
        if (regex.test(text)) {
            const highlightedText = text.replace(regex, '<mark class="search-highlight">$1</mark>');
            const span = document.createElement('span');
            span.innerHTML = highlightedText;
            textNode.parentNode.replaceChild(span, textNode);
        }
    });
}

function updateSidebarForSearch(results) {
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    
    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');
        const isVisible = results.some(result => href === `#${result.id}`);
        link.style.display = isVisible ? 'block' : 'none';
    });
}

// Navigation functionality
function initializeNavigation() {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active navigation
                updateActiveNavigation(targetId);
                
                // Clear search if active
                const searchInput = document.getElementById('searchInput');
                if (searchInput && searchInput.value) {
                    searchInput.value = '';
                    clearSearch();
                }
            }
        });
    });
    
    // Mobile navigation toggle (if needed)
    const mobileToggle = document.querySelector('.mobile-nav-toggle');
    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('mobile-open');
        });
    }
}

function updateActiveNavigation(activeId) {
    // Remove active class from all links
    document.querySelectorAll('.sidebar-nav a').forEach(link => {
        link.classList.remove('active');
    });
    
    // Add active class to current link
    const activeLink = document.querySelector(`.sidebar-nav a[href="#${activeId}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

// FAQ functionality
function initializeFAQ() {
    const faqItems = document.querySelectorAll('.faq-item h4');
    
    faqItems.forEach(question => {
        question.addEventListener('click', function() {
            const answer = this.nextElementSibling;
            const isOpen = answer.style.display === 'block';
            
            // Close all other FAQ items
            document.querySelectorAll('.faq-answer').forEach(ans => {
                ans.style.display = 'none';
            });
            
            // Toggle current item
            if (!isOpen) {
                answer.style.display = 'block';
                this.classList.add('active');
            } else {
                this.classList.remove('active');
            }
        });
    });
}

// Scroll spy functionality
function initializeScrollSpy() {
    const sections = document.querySelectorAll('.content-section[id]');
    const navLinks = document.querySelectorAll('.sidebar-nav a[href^="#"]');
    
    function updateScrollSpy() {
        let currentSection = '';
        
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            if (rect.top <= 100 && rect.bottom >= 100) {
                currentSection = section.id;
            }
        });
        
        if (currentSection) {
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${currentSection}`) {
                    link.classList.add('active');
                }
            });
        }
    }
    
    // Throttle scroll events
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
        }
        scrollTimeout = setTimeout(updateScrollSpy, 100);
    });
    
    // Initial update
    updateScrollSpy();
}

// Theme toggle functionality
function initializeThemeToggle() {
    // Auto-detect system theme preference
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    function updateTheme(isDark) {
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    }
    
    // Listen for system theme changes
    prefersDarkScheme.addEventListener('change', function(e) {
        updateTheme(e.matches);
    });
    
    // Initialize theme
    updateTheme(prefersDarkScheme.matches);
    
    // Optional: Add manual theme toggle button
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            updateTheme(newTheme === 'dark');
            
            // Store preference
            localStorage.setItem('theme-preference', newTheme);
        });
    }
}

// Update version information
function updateVersion() {
    try {
        // Try to get version from Python backend if available
        if (window.electronAPI || window.pywebview) {
            // Implementation for electron or pywebview
            updateVersionFromBackend();
        } else {
            // Fallback to static version
            const versionElements = document.querySelectorAll('.version');
            versionElements.forEach(el => {
                if (!el.textContent.trim()) {
                    el.textContent = 'v1.0.0';
                }
            });
        }
    } catch (error) {
        console.log('Could not update version information:', error);
    }
}

function updateVersionFromBackend() {
    // This would be implemented when integrating with the Python backend
    // For now, we'll use the static version
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Copy code functionality
function initializeCodeCopy() {
    const codeBlocks = document.querySelectorAll('.code-block pre');
    
    codeBlocks.forEach(block => {
        const copyButton = document.createElement('button');
        copyButton.textContent = 'Copy';
        copyButton.className = 'copy-button';
        copyButton.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;
        
        block.style.position = 'relative';
        block.appendChild(copyButton);
        
        block.addEventListener('mouseenter', () => {
            copyButton.style.opacity = '1';
        });
        
        block.addEventListener('mouseleave', () => {
            copyButton.style.opacity = '0';
        });
        
        copyButton.addEventListener('click', async () => {
            const code = block.querySelector('code').textContent;
            try {
                await navigator.clipboard.writeText(code);
                copyButton.textContent = 'Copied!';
                setTimeout(() => {
                    copyButton.textContent = 'Copy';
                }, 2000);
            } catch (error) {
                console.error('Failed to copy code:', error);
            }
        });
    });
}

// Initialize code copy when DOM is ready
document.addEventListener('DOMContentLoaded', initializeCodeCopy);

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + / to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('searchInput');
        if (searchInput && document.activeElement === searchInput) {
            searchInput.value = '';
            clearSearch();
            searchInput.blur();
        }
    }
});

// Add loading animation
function showLoading() {
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <p>Loading...</p>
        </div>
    `;
    document.body.appendChild(loading);
}

function hideLoading() {
    const loading = document.querySelector('.loading-overlay');
    if (loading) {
        loading.remove();
    }
}