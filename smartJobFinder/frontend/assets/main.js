/* ===========================
   ENHANCED ANIMATIONS & INTERACTIONS
=========================== */

// Intersection Observer for scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fadeInUp');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe elements for animation on scroll
document.addEventListener('DOMContentLoaded', function() {
    // Animate cards, features, testimonials
    const animateElements = document.querySelectorAll('.job-card, .feature-box, .testimonial-card, .category-box, .stat-card');
    animateElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.animationDelay = `${index * 0.1}s`;
        observer.observe(el);
    });
    
    // Initialize all features
    initializeNavbar();
    initializeScrollToTop();
    initializeSearch();
    initializeSmoothScroll();
    initializeCounterAnimations();
    checkAuth();
    updateNavbar();
});

/* ===========================
   NAVBAR SCROLL EFFECT
=========================== */
function initializeNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        // Hide navbar on scroll down, show on scroll up
        if (currentScroll > lastScroll && currentScroll > 500) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScroll = currentScroll;
    });
}

/* ===========================
   SCROLL TO TOP BUTTON
=========================== */
function initializeScrollToTop() {
    // Create scroll to top button
    const scrollBtn = document.createElement('div');
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    document.body.appendChild(scrollBtn);
    
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollBtn.classList.add('show');
        } else {
            scrollBtn.classList.remove('show');
        }
    });
    
    scrollBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/* ===========================
   SMOOTH SCROLL FOR ANCHOR LINKS
=========================== */
function initializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/* ===========================
   COUNTER ANIMATIONS
=========================== */
function initializeCounterAnimations() {
    const counters = document.querySelectorAll('.stat-card h2, .stat-card h3');
    
    const animateCounter = (counter) => {
        const target = parseInt(counter.textContent);
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = Math.ceil(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target;
            }
        };
        
        updateCounter();
    };
    
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                counterObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        if (!isNaN(parseInt(counter.textContent))) {
            counterObserver.observe(counter);
        }
    });
}

/* ===========================
   ENHANCED SEARCH FUNCTIONALITY
=========================== */
function initializeSearch() {
    // Handle index page search
    const indexSearchForm = document.getElementById('indexSearchForm');
    if (indexSearchForm) {
        indexSearchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('indexJobSearch');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                showNotification('Please enter a search term', 'warning');
                searchInput.focus();
            } else {
                localStorage.setItem('lastSearch', searchInput.value);
            }
        });
    }
    
    // Handle dashboard search
    const dashboardSearchForm = document.getElementById('dashboardSearchForm');
    if (dashboardSearchForm) {
        dashboardSearchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('dashboardJobSearch');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                showNotification('Please enter a search term', 'warning');
                searchInput.focus();
            } else {
                localStorage.setItem('lastSearch', searchInput.value);
            }
        });
    }
    
    // Apply stored search on jobs page
    if (window.location.pathname.includes('jobs.html')) {
        const lastSearch = localStorage.getItem('lastSearch');
        if (lastSearch) {
            const searchInput = document.getElementById('jobSearch');
            if (searchInput) {
                searchInput.value = lastSearch;
                localStorage.removeItem('lastSearch');
            }
        }
    }
}

/* ===========================
   LIVE SEARCH FILTER WITH ANIMATION
=========================== */
const searchInput = document.querySelector('#jobSearch');
const jobCards = document.querySelectorAll('.job-card');

if (searchInput) {
    searchInput.addEventListener('keyup', debounce(function () {
        const text = searchInput.value.toLowerCase();

        jobCards.forEach((card, index) => {
            const title = card.dataset.title?.toLowerCase() || '';
            const company = card.dataset.company?.toLowerCase() || '';
            const location = card.dataset.location?.toLowerCase() || '';

            if (title.includes(text) || company.includes(text) || location.includes(text)) {
                card.style.display = "block";
                card.style.animation = `fadeInUp 0.5s ease ${index * 0.1}s forwards`;
            } else {
                card.style.display = "none";
            }
        });
    }, 300));
}

/* ===========================
   SAVE JOB INTERACTION WITH ANIMATION
=========================== */
document.querySelectorAll('.save-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const jobCard = this.closest('.job-card');
        const jobId = jobCard?.dataset.jobId || Math.random().toString(36).substr(2, 9);
        
        if (this.classList.contains('saved')) {
            this.innerHTML = '<i class="far fa-heart me-1"></i>Save Job';
            this.classList.remove('saved');
            unsaveJob(jobId);
            showNotification('Job removed from saved', 'info');
        } else {
            this.innerHTML = '<i class="fas fa-heart me-1"></i>Saved ✓';
            this.classList.add('saved');
            saveJob(jobId, jobCard);
            showNotification('Job saved successfully!', 'success');
            
            // Add celebration animation
            createConfetti(this);
        }
    });
});

function saveJob(jobId, jobCard) {
    const savedJobs = JSON.parse(localStorage.getItem('savedJobs') || '[]');
    
    const jobData = {
        id: jobId,
        title: jobCard?.dataset.title || 'Unknown',
        company: jobCard?.dataset.company || 'Unknown',
        location: jobCard?.dataset.location || 'Unknown',
        savedAt: new Date().toISOString()
    };
    
    if (!savedJobs.find(job => job.id === jobId)) {
        savedJobs.push(jobData);
        localStorage.setItem('savedJobs', JSON.stringify(savedJobs));
    }
}

function unsaveJob(jobId) {
    const savedJobs = JSON.parse(localStorage.getItem('savedJobs') || '[]');
    const updatedJobs = savedJobs.filter(job => job.id !== jobId);
    localStorage.setItem('savedJobs', JSON.stringify(updatedJobs));
}

/* ===========================
   CONFETTI ANIMATION
=========================== */
function createConfetti(element) {
    const colors = ['#0096C7', '#0077B6', '#48CAE4', '#90E0EF', '#10b981'];
    const confettiCount = 15;
    
    for (let i = 0; i < confettiCount; i++) {
        const confetti = document.createElement('div');
        confetti.style.position = 'fixed';
        confetti.style.width = '10px';
        confetti.style.height = '10px';
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.borderRadius = '50%';
        confetti.style.pointerEvents = 'none';
        confetti.style.zIndex = '9999';
        
        const rect = element.getBoundingClientRect();
        confetti.style.left = rect.left + rect.width / 2 + 'px';
        confetti.style.top = rect.top + rect.height / 2 + 'px';
        
        document.body.appendChild(confetti);
        
        const angle = (Math.PI * 2 * i) / confettiCount;
        const velocity = 100 + Math.random() * 50;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity;
        
        let x = 0;
        let y = 0;
        let opacity = 1;
        
        const animate = () => {
            x += vx * 0.02;
            y += vy * 0.02 + 2;
            opacity -= 0.02;
            
            confetti.style.transform = `translate(${x}px, ${y}px)`;
            confetti.style.opacity = opacity;
            
            if (opacity > 0) {
                requestAnimationFrame(animate);
            } else {
                confetti.remove();
            }
        };
        
        animate();
    }
}

/* ===========================
   NOTIFICATION SYSTEM
=========================== */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.style.animation = 'slideInRight 0.5s ease-out';
    
    const icons = {
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        danger: 'fa-times-circle',
        info: 'fa-info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas ${icons[type]} me-2"></i>
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-out';
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

/* ===========================
   SESSION MANAGEMENT
=========================== */
function checkAuth() {
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const currentPage = window.location.pathname.split('/').pop();
    
    const publicPages = ['index.html', 'login.html', 'register.html', 'forgot-password.html', 'jobs.html', 'job-details.html'];
    const protectedPages = ['dashboard.html', 'profile.html', 'upload-cv.html', 'apply-job.html'];
    
    if (!isLoggedIn && protectedPages.includes(currentPage)) {
        window.location.href = 'login.html';
        return false;
    }
    
    if (isLoggedIn && (currentPage === 'login.html' || currentPage === 'register.html') && currentPage !== 'upload-cv.html') {
        window.location.href = 'dashboard.html';
        return false;
    }
    
    return requireCV();
}

function logout() {
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('isAdmin');
    localStorage.removeItem('adminEmail');
    localStorage.removeItem('adminName');
    showNotification('Logged out successfully', 'success');
    setTimeout(() => {
        window.location.href = 'index.html';
    }, 1000);
}

function updateNavbar() {
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const navAuthButtons = document.getElementById('navAuthButtons');
    
    if (navAuthButtons) {
        if (isLoggedIn) {
            navAuthButtons.innerHTML = `
                <a href="dashboard.html" class="btn btn-outline-primary rounded-pill me-2">Dashboard</a>
                <a href="profile.html" class="btn btn-outline-primary rounded-pill me-2">Profile</a>
                <a href="index.html" class="btn btn-primary rounded-pill" onclick="logout()">Logout</a>
            `;
        } else {
            navAuthButtons.innerHTML = `
                <a href="login.html" class="btn btn-outline-primary rounded-pill me-2">Login</a>
                <a href="register.html" class="btn btn-primary rounded-pill">Sign Up</a>
            `;
        }
    }
}

/* ===========================
   CV STATUS CHECKING
=========================== */
function checkCVStatus() {
    const userData = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const localStorageHasCV = localStorage.getItem('hasCV') === 'true';
    const userDataHasCV = userData.hasCV === true;
    
    return localStorageHasCV || userDataHasCV;
}

function requireCV() {
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const currentPage = window.location.pathname.split('/').pop();
    
    const pagesRequiringCV = ['dashboard.html', 'profile.html', 'apply-job.html'];
    
    if (isLoggedIn && pagesRequiringCV.includes(currentPage)) {
        const hasCV = checkCVStatus();
        if (!hasCV) {
            window.location.href = 'upload-cv.html';
            return false;
        }
    }
    return true;
}

/* ===========================
   PASSWORD TOGGLE FUNCTIONALITY
=========================== */
function initializePasswordToggles() {
    const passwordToggles = document.querySelectorAll('.password-toggle');
    
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            this.innerHTML = type === 'password' ? '<i class="far fa-eye"></i>' : '<i class="far fa-eye-slash"></i>';
        });
    });
}

/* ===========================
   JOB APPLICATION MANAGEMENT
=========================== */
function trackApplication(jobId, jobData) {
    const appliedJobs = JSON.parse(localStorage.getItem('appliedJobs') || '[]');
    
    if (appliedJobs.find(app => app.jobId === jobId)) {
        return { success: false, message: 'You have already applied to this job' };
    }
    
    const application = {
        id: 'app_' + Date.now(),
        jobId: jobId,
        jobTitle: jobData.title,
        company: jobData.company,
        location: jobData.location,
        appliedAt: new Date().toISOString(),
        status: 'pending'
    };
    
    appliedJobs.push(application);
    localStorage.setItem('appliedJobs', JSON.stringify(appliedJobs));
    
    return { success: true, message: 'Application submitted successfully!' };
}

function getApplicationStatus(jobId) {
    const appliedJobs = JSON.parse(localStorage.getItem('appliedJobs') || '[]');
    const application = appliedJobs.find(app => app.jobId === jobId);
    return application ? application.status : 'not_applied';
}

function applyForJob(jobId, jobData) {
    const result = trackApplication(jobId, jobData);
    
    if (result.success) {
        updateJobUI(jobId, 'applied');
        showNotification(result.message, 'success');
        return true;
    } else {
        showNotification(result.message, 'warning');
        return false;
    }
}

function updateJobUI(jobId, status) {
    const applyButtons = document.querySelectorAll(`[data-job-id="${jobId}"]`);
    applyButtons.forEach(btn => {
        if (btn.textContent.includes('Apply')) {
            btn.textContent = 'Applied ✓';
            btn.classList.add('disabled');
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-success');
        }
    });
}

/* ===========================
   PROFILE COMPLETION CALCULATION
=========================== */
function calculateProfileCompletion(userData) {
    let completion = 0;
    const totalFields = 8;
    
    if (userData.fullName) completion++;
    if (userData.email) completion++;
    if (userData.phone) completion++;
    if (userData.location) completion++;
    if (userData.experience) completion++;
    if (userData.education) completion++;
    if (userData.skills && userData.skills.length > 0) completion++;
    if (userData.about) completion++;
    
    return Math.round((completion / totalFields) * 100);
}

/* ===========================
   DEBOUNCE UTILITY FUNCTION
=========================== */
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

/* ===========================
   CATEGORY NAVIGATION WITH ANIMATION
=========================== */
function initializeCategoryNavigation() {
    const categoryBoxes = document.querySelectorAll('.category-box');
    categoryBoxes.forEach(box => {
        box.addEventListener('click', function() {
            const category = this.dataset.category;
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
                localStorage.setItem('selectedCategory', category);
                window.location.href = 'jobs.html';
            }, 150);
        });
    });
}

/* ===========================
   INITIALIZE DEMO DATA
=========================== */
function initializeDemoData() {
    if (!localStorage.getItem('demoDataInitialized')) {
        const sampleAdminJobs = [
            {
                id: 'admin_job_1',
                title: 'Senior Frontend Developer',
                company: 'Google',
                location: 'California, USA',
                type: 'Full-Time',
                salary: '$120,000 - $150,000',
                experience: 'senior',
                description: 'Lead frontend development for our core products. Must have 5+ years experience with React and modern JavaScript.',
                postedDate: '2025-10-20',
                skills: ['React', 'JavaScript', 'TypeScript', 'HTML/CSS'],
                status: 'active',
                applications: 15
            },
            {
                id: 'admin_job_2',
                title: 'Product Designer',
                company: 'Figma',
                location: 'Remote',
                type: 'Remote',
                salary: '$95,000 - $125,000',
                experience: 'mid',
                description: 'Design intuitive user interfaces for our design tools. Collaborate with engineering to implement designs.',
                postedDate: '2025-10-18',
                skills: ['UI/UX', 'Figma', 'Prototyping', 'User Research'],
                status: 'active',
                applications: 8
            }
        ];
        
        if (!localStorage.getItem('adminJobs')) {
            localStorage.setItem('adminJobs', JSON.stringify(sampleAdminJobs));
        }
        
        localStorage.setItem('demoDataInitialized', 'true');
    }
}

/* ===========================
   FORM VALIDATION WITH ANIMATION
=========================== */
function animateFormError(input) {
    input.style.animation = 'shake 0.5s ease';
    setTimeout(() => {
        input.style.animation = '';
    }, 500);
}

// Shake animation for form errors
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    @keyframes slideOutRight {
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize all functionality
initializeDemoData();
initializePasswordToggles();
initializeCategoryNavigation();
// ADD THIS TO THE END OF main.js (after line 600)

/* ===========================
   TOAST NOTIFICATION SYSTEM
=========================== */

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    
    const colors = {
        success: 'success',
        error: 'danger',
        warning: 'warning',
        info: 'info'
    };
    
    toast.className = `alert alert-${colors[type]} position-fixed d-flex align-items-center`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
        animation: slideInRight 0.5s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    toast.innerHTML = `
        <i class="fas fa-${icons[type]} me-2"></i>
        <div class="flex-grow-1">${message}</div>
        <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.5s ease-out';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// Add CSS animations
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(toastStyles);

// Make globally available
window.showToast = showToast;

/* ===========================
   OFFLINE/ONLINE DETECTION
=========================== */

window.addEventListener('offline', () => {
    showToast('⚠️ No internet connection. Some features may not work.', 'warning');
});

window.addEventListener('online', () => {
    showToast('✅ Back online!', 'success');
});

/* ===========================
   LOADING BUTTON UTILITY
=========================== */

function setButtonLoading(button, isLoading, loadingText = 'Loading...') {
    if (!button) return;
    
    if (isLoading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${loadingText}`;
        button.disabled = true;
    } else {
        button.innerHTML = button.dataset.originalText || 'Submit';
        button.disabled = false;
    }
}

window.setButtonLoading = setButtonLoading;