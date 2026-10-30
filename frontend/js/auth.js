/**
 * BloomCraft AI - Faculty Authentication & Past Papers History Module
 * Enforces mandatory login gate, strict faculty isolation, session security,
 * and personal question paper archive management.
 */

// API_BASE is declared once in app.js (loaded before this file)

const AuthModule = {
  currentUser: null,
  authToken: null,
  cachedHistory: [],

  _initialized: false,

  async init() {
    if (this._initialized) return;
    this._initialized = true;

    this.bindEvents();
    const savedToken = localStorage.getItem("bloom_faculty_token");
    let restored = false;
    if (savedToken) {
      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, { headers: { "Authorization": `Bearer ${savedToken}` } });
        const data = await res.json();
        if (res.ok && data.success && data.user) {
          this.setSession(data.user, savedToken);
          this.showDashboardView();
          await this.refreshHistory();
          restored = true;
        } else if (res.status === 401) {
          // Token explicitly rejected by server
          localStorage.removeItem("bloom_faculty_user");
          localStorage.removeItem("bloom_faculty_token");
        }
      } catch (e) {
        console.warn("Session check failed (backend may be reloading):", e);
        // Do NOT wipe localStorage on network glitch or during server reload!
        const savedUserStr = localStorage.getItem("bloom_faculty_user");
        if (savedUserStr) {
          try {
            const savedUser = JSON.parse(savedUserStr);
            this.setSession(savedUser, savedToken);
            this.showDashboardView();
            restored = true;
          } catch (_) {}
        }
      }
    }
    if (!restored) {
      this.showAuthGate();
    }
  },

  activateDefaultSession() {
    // Auto-login removed: teachers must sign in with their own account.
    this.showAuthGate();
  },

  showAuthGate() {
    this.currentUser = null;
    this.authToken = null;
    if (window.AppState) {
      window.AppState.currentUser = null;
      window.AppState.authToken = null;
    }

    const authGate = document.getElementById("auth-gate-view");
    const dashboard = document.getElementById("dashboard-view");

    if (authGate) {
      authGate.style.display = "flex";
      authGate.style.setProperty("display", "flex", "important");
      authGate.classList.remove("hidden");
    }
    if (dashboard) {
      dashboard.style.display = "none";
      dashboard.style.setProperty("display", "none", "important");
      dashboard.classList.add("hidden");
    }

    this.clearAuthErrors();
  },

  showDashboardView() {
    const authGate = document.getElementById("auth-gate-view");
    const dashboard = document.getElementById("dashboard-view");

    if (authGate) {
      authGate.style.display = "none";
      authGate.style.setProperty("display", "none", "important");
      authGate.classList.add("hidden");
    }
    if (dashboard) {
      dashboard.style.display = "block";
      dashboard.style.setProperty("display", "block", "important");
      dashboard.classList.remove("hidden");
    }

    // Scroll directly to the top of dashboard view
    window.scrollTo({ top: 0, behavior: "instant" });

    // Immediately route into the dashboard workspace stage (Stage 1: Syllabus & Document Ingestion)
    if (typeof window.switchTab === "function") {
      window.switchTab("syllabus");
    } else {
      const tabSyllabus = document.getElementById("tab-syllabus");
      if (tabSyllabus) tabSyllabus.style.display = "block";
    }

    try {
      this.updateNavbarUserUI();
      this.updateSyllabusUserBanner();
    } catch (e) {
      console.warn("UI banner update notice:", e);
    }
  },

  bindEvents() {
    // History Modal Openers
    const historyBtn = document.getElementById("btn-open-history");
    if (historyBtn) {
      historyBtn.addEventListener("click", () => {
        this.openHistoryModal();
      });
    }

    const studioHistoryBtn = document.getElementById("btn-studio-history");
    if (studioHistoryBtn) {
      studioHistoryBtn.addEventListener("click", () => {
        this.openHistoryModal();
      });
    }

    const refreshHistoryBtn = document.getElementById("btn-refresh-history");
    if (refreshHistoryBtn) {
      refreshHistoryBtn.addEventListener("click", () => {
        this.renderHistoryModal();
      });
    }

    const btnCloseGate = document.getElementById("btn-close-auth-gate");
    if (btnCloseGate) {
      btnCloseGate.addEventListener("click", () => {
        if (!this.currentUser) {
          this.activateDefaultSession();
        } else {
          this.showDashboardView();
        }
      });
    }

    const historyNewBtn = document.getElementById("btn-history-create-new");
    if (historyNewBtn) {
      historyNewBtn.addEventListener("click", () => {
        const modal = document.getElementById("modal-history");
        if (modal) modal.classList.remove("active");
        if (typeof window.switchTab === "function") {
          window.switchTab("syllabus");
        }
      });
    }

    // Auth Tabs switching (Sign In vs Sign Up vs Forgot Password)
    const tabLogin = document.getElementById("tab-btn-login");
    const tabSignup = document.getElementById("tab-btn-signup");
    const formLogin = document.getElementById("form-faculty-login");
    const formSignup = document.getElementById("form-faculty-signup");
    const formForgot = document.getElementById("form-faculty-forgot");
    const btnForgotLink = document.getElementById("btn-forgot-password-link");
    const btnBackToLogin = document.getElementById("btn-back-to-login");

    if (tabLogin && tabSignup && formLogin && formSignup) {
      tabLogin.addEventListener("click", () => {
        tabLogin.classList.add("active");
        tabSignup.classList.remove("active");
        formLogin.style.display = "block";
        formSignup.style.display = "none";
        if (formForgot) formForgot.style.display = "none";
        this.clearAuthErrors();
      });

      tabSignup.addEventListener("click", () => {
        tabSignup.classList.add("active");
        tabLogin.classList.remove("active");
        formLogin.style.display = "none";
        formSignup.style.display = "block";
        if (formForgot) formForgot.style.display = "none";
        this.clearAuthErrors();
      });
    }

    // Forgot Password Tab / View Triggers
    if (btnForgotLink && formForgot) {
      btnForgotLink.addEventListener("click", () => {
        if (formLogin) formLogin.style.display = "none";
        if (formSignup) formSignup.style.display = "none";
        formForgot.style.display = "block";
        if (tabLogin) tabLogin.classList.remove("active");
        if (tabSignup) tabSignup.classList.remove("active");
        this.clearAuthErrors();

        // Auto-transfer username if already typed in login
        const loginUserVal = document.getElementById("login-username") ? document.getElementById("login-username").value.trim() : "";
        const forgotUserInput = document.getElementById("forgot-username");
        if (forgotUserInput && loginUserVal) {
          forgotUserInput.value = loginUserVal;
        }
      });
    }

    if (btnBackToLogin && formForgot && formLogin) {
      btnBackToLogin.addEventListener("click", () => {
        formForgot.style.display = "none";
        formLogin.style.display = "block";
        if (tabLogin) tabLogin.classList.add("active");
        if (tabSignup) tabSignup.classList.remove("active");
        this.clearAuthErrors();
      });
    }

    if (formForgot) {
      formForgot.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("forgot-username").value.trim();
        const newPwd = document.getElementById("forgot-new-pwd").value;
        const confirmPwd = document.getElementById("forgot-confirm-pwd").value;

        if (!username) {
          this.showAuthError("forgot", "Please enter your faculty username or ID.");
          return;
        }
        if (newPwd.length < 6) {
          this.showAuthError("forgot", "New password must be at least 6 characters long.");
          return;
        }
        if (newPwd !== confirmPwd) {
          this.showAuthError("forgot", "Passwords do not match. Please verify.");
          return;
        }

        await this.resetPassword(username, newPwd);
      });
    }

    // Toggle Password Visibility
    const btnTogglePwd = document.getElementById("btn-toggle-login-pwd");
    if (btnTogglePwd) {
      btnTogglePwd.addEventListener("click", () => {
        const pwdInput = document.getElementById("login-password");
        if (pwdInput) {
          pwdInput.type = pwdInput.type === "password" ? "text" : "password";
        }
      });
    }

    // Login Form Submit (Single robust submit listener prevents race conditions)
    if (formLogin) {
      formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const usernameInput = document.getElementById("login-username");
        const pwdInput = document.getElementById("login-password");
        const username = usernameInput ? usernameInput.value.trim() : "";
        const password = pwdInput ? pwdInput.value : "";
        if (!username || !password) return;
        await this.login(username, password);
      });
    }

    // Quick demo account pills
    document.querySelectorAll(".btn-demo-quick-login").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const u = btn.getAttribute("data-user");
        const p = btn.getAttribute("data-pwd");
        const userInput = document.getElementById("login-username");
        const pwdInput = document.getElementById("login-password");
        if (userInput) userInput.value = u;
        if (pwdInput) pwdInput.value = p;
        this.login(u, p);
      });
    });

    // Signup Form Submit
    if (formSignup) {
      formSignup.addEventListener("submit", async (e) => {
        e.preventDefault();
        const displayName = document.getElementById("signup-fullname").value.trim();
        const username = document.getElementById("signup-username").value.trim();
        const department = document.getElementById("signup-dept").value.trim();
        const password = document.getElementById("signup-password").value;
        const confirmPwd = document.getElementById("signup-confirm-pwd").value;

        if (password.length < 6) {
          this.showAuthError("signup", "Password must be at least 6 characters long.");
          return;
        }
        if (password !== confirmPwd) {
          this.showAuthError("signup", "Passwords do not match. Please verify.");
          return;
        }

        await this.register({
          display_name: displayName,
          username: username,
          department: department,
          password: password
        });
      });
    }

    // History Search Filter
    const searchInput = document.getElementById("history-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        this.filterHistoryList(query);
      });
    }
  },

  _isLoggingIn: false,

  async login(username, password) {
    if (this._isLoggingIn) return;
    this._isLoggingIn = true;

    const submitBtn = document.getElementById("btn-submit-login");
    const origHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
      submitBtn.innerHTML = "<span>Authenticating Faculty Credentials...</span>";
      submitBtn.disabled = true;
    }

    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: (username || "").trim(), password: password || "" })
      });
      const data = await res.json();

      if (data.success && data.user && data.token) {
        this.setSession(data.user, data.token);
        this.showDashboardView();
        window.showToast(`Welcome back, ${data.user.display_name}! Faculty session active.`, "success");
        await this.refreshHistory();
      } else {
        this.showAuthError("login", data.error || "Invalid username or password. Please verify credentials.");
      }
    } catch (err) {
      console.warn("Login request failed:", err);
      this.showAuthError("login", "Cannot reach the server. Make sure the backend is running (python backend/app.py) and try again.");
    } finally {
      this._isLoggingIn = false;
      if (submitBtn) {
        submitBtn.innerHTML = origHtml;
        submitBtn.disabled = false;
      }
    }
  },

  async register(userData) {
    const submitBtn = document.getElementById("btn-submit-signup");
    const origHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
      submitBtn.innerHTML = "<span>Registering Faculty Profile...</span>";
      submitBtn.disabled = true;
    }

    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData)
      });
      const data = await res.json();

      if (data.success && data.user && data.token) {
        this.setSession(data.user, data.token);
        this.showDashboardView();
        window.showToast(`Faculty account created! Welcome, ${data.user.display_name}.`, "success");
        await this.refreshHistory();
      } else {
        this.showAuthError("signup", data.error || "Registration failed. Please choose another username.");
      }
    } catch (err) {
      console.error(err);
      this.showAuthError("signup", "Network error communicating with registration service.");
    } finally {
      if (submitBtn) {
        submitBtn.innerHTML = origHtml;
        submitBtn.disabled = false;
      }
    }
  },

  setSession(user, token) {
    this.currentUser = user;
    this.authToken = token;
    window.AppState.currentUser = user;
    window.AppState.authToken = token;

    localStorage.setItem("bloom_faculty_user", JSON.stringify(user));
    localStorage.setItem("bloom_faculty_token", token);

    this.updateNavbarUserUI();
    this.updateSyllabusUserBanner();
  },

  async logout() {
    try {
      if (this.authToken) {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${this.authToken}` }
        });
      }
    } catch (e) {
      console.warn("Logout request failed:", e);
    }

    localStorage.removeItem("bloom_faculty_user");
    localStorage.removeItem("bloom_faculty_token");

    this.currentUser = null;
    this.authToken = null;
    this.cachedHistory = [];
    window.AppState.currentUser = null;
    window.AppState.authToken = null;

    this.showAuthGate();
    window.showToast("Signed out successfully. Authentication required to access workspace.", "info");
  },

  updateNavbarUserUI() {
    const container = document.getElementById("nav-user-container");
    if (!container) return;

    if (this.currentUser) {
      const initials = (this.currentUser.display_name || "Faculty")
        .split(" ")
        .map(n => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();

      container.innerHTML = `
        <div class="user-nav-wrapper">
          <button class="user-profile-btn" id="btn-user-dropdown-toggle" title="Faculty Profile: ${this.currentUser.display_name}">
            <div class="user-avatar-badge">${initials}</div>
            <div class="user-profile-text">
              <span class="user-profile-name">${this.currentUser.display_name}</span>
              <span class="user-profile-dept">${this.currentUser.department || 'Faculty'}</span>
            </div>
            <svg class="icon-svg icon-xs" viewBox="0 0 24 24" style="color: var(--text-muted);">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          
          <div class="user-dropdown-menu" id="user-dropdown-menu">
            <div class="dropdown-header">
              <strong>${this.currentUser.display_name}</strong>
              <div style="font-size: 11px; color: var(--text-muted);">${this.currentUser.role || 'Faculty Member'} &bull; ${this.currentUser.department || ''}</div>
            </div>
            <div class="dropdown-divider"></div>
            <button class="dropdown-item" id="btn-dropdown-history">
              <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <span>Past Examination Papers</span>
            </button>
            <div class="dropdown-divider"></div>
            <button class="dropdown-item text-danger" id="btn-logout">
              <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      `;

      // Wire dropdown toggling
      const toggleBtn = document.getElementById("btn-user-dropdown-toggle");
      const menu = document.getElementById("user-dropdown-menu");
      if (toggleBtn && menu) {
        toggleBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          menu.classList.toggle("show");
        });

        document.addEventListener("click", () => {
          menu.classList.remove("show");
        });
      }

      const logoutBtn = document.getElementById("btn-logout");
      if (logoutBtn) {
        logoutBtn.addEventListener("click", () => this.logout());
      }

      const dropHistoryBtn = document.getElementById("btn-dropdown-history");
      if (dropHistoryBtn) {
        dropHistoryBtn.addEventListener("click", () => this.openHistoryModal());
      }
    } else {
      container.innerHTML = "";
    }
  },

  updateSyllabusUserBanner() {
    const bannerContainer = document.getElementById("syllabus-user-banner");
    if (!bannerContainer) return;

    if (this.currentUser) {
      bannerContainer.style.display = "flex";
      bannerContainer.innerHTML = `
        <div class="user-welcome-info">
          <div class="user-welcome-title">
            <svg class="icon-svg icon-sm" style="color: var(--primary-color);" viewBox="0 0 24 24">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <span>Authenticated Faculty Session: <strong>${this.currentUser.display_name}</strong> (${this.currentUser.department || 'Academic Department'})</span>
          </div>
          <div class="user-welcome-stats">
            Private and isolated workspace. <span id="banner-history-count">${this.cachedHistory.length} examination paper${this.cachedHistory.length === 1 ? '' : 's'} recorded</span> in your archive.
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-outline btn-sm" id="btn-banner-view-history">
            <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>View Archive (${this.cachedHistory.length})</span>
          </button>
        </div>
      `;

      const btn = document.getElementById("btn-banner-view-history");
      if (btn) {
        btn.addEventListener("click", () => this.openHistoryModal());
      }
    } else {
      bannerContainer.style.display = "none";
    }
  },

  async refreshHistory() {
    if (!this.currentUser || !this.authToken) {
      this.updateHistoryBadge(0);
      return [];
    }

    try {
      const res = await fetch(`${API_BASE}/api/history`, {
        headers: {
          "Authorization": `Bearer ${this.authToken}`
        }
      });
      const data = await res.json();
      if (data.success && Array.isArray(data.history)) {
        this.cachedHistory = data.history;
        this.updateHistoryBadge(data.history.length);
        this.updateSyllabusUserBanner();
        return data.history;
      }
    } catch (err) {
      console.warn("Error refreshing user history:", err);
    }
    return [];
  },

  updateHistoryBadge(count) {
    const badge = document.getElementById("nav-history-badge");
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? "inline-flex" : "none";
    }

    const bannerCount = document.getElementById("banner-history-count");
    if (bannerCount) {
      bannerCount.textContent = `${count} examination paper${count === 1 ? '' : 's'} recorded`;
    }
  },

  async openHistoryModal() {
    if (!this.currentUser) {
      this.showAuthGate();
      return;
    }

    const modal = document.getElementById("modal-history");
    if (modal) {
      modal.classList.add("active");
      await this.renderHistoryModal();
    }
  },

  async renderHistoryModal() {
    const container = document.getElementById("history-papers-list");
    const subtitle = document.getElementById("history-modal-subtitle");
    const footerSummary = document.getElementById("history-footer-summary");

    if (subtitle && this.currentUser) {
      subtitle.textContent = `Private archive for ${this.currentUser.display_name} (${this.currentUser.department || 'Faculty'})`;
    }

    if (!container) return;
    container.innerHTML = `
      <div style="text-align:center; padding: 40px; color: var(--text-muted);">
        <div class="spinner" style="margin: 0 auto 12px;"></div>
        <div>Loading your archived question papers...</div>
      </div>
    `;

    const history = await this.refreshHistory();

    if (!history || history.length === 0) {
      container.innerHTML = `
        <div class="history-empty-state">
          <div class="empty-icon-wrapper" style="margin-bottom: 12px;">
            <svg class="icon-svg" style="width:48px; height:48px; color: var(--border-medium);" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <line x1="9" y1="15" x2="15" y2="15"/>
            </svg>
          </div>
          <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">No Saved Question Papers In Your Account</h4>
          <p style="font-size: 13px; color: var(--text-muted); max-width: 380px; margin: 0 auto 16px;">
            Generate an examination paper in Stage 1 & 2. Every synthesized paper will automatically be archived exclusively to your account.
          </p>
          <button class="btn btn-primary btn-sm" onclick="document.getElementById('modal-history').classList.remove('active'); window.switchTab('syllabus');">
            <span>Synthesize First Examination Paper</span>
          </button>
        </div>
      `;
      if (footerSummary) footerSummary.textContent = "0 archived question papers";
      return;
    }

    if (footerSummary) {
      footerSummary.textContent = `${history.length} archived question paper${history.length > 1 ? 's' : ''}`;
    }

    this.renderHistoryItems(history);
  },

  renderHistoryItems(items) {
    const container = document.getElementById("history-papers-list");
    if (!container) return;

    container.innerHTML = items.map(p => {
      const cog = p.cognitive_index ? Number(p.cognitive_index).toFixed(1) : "3.0";
      return `
        <div class="history-paper-item" data-paper-id="${p.paper_id}">
          <div class="history-paper-info">
            <div class="history-paper-title">
              <span class="course-code-pill">${p.course_code || 'EXAM'}</span>
              <span>${p.exam_title || 'Semester Examination'}</span>
              <span class="history-paper-subject">&bull; ${p.course_name || 'Curriculum Subject'}</span>
            </div>
            <div class="history-paper-meta">
              <span><strong>Marks:</strong> ${p.total_marks || 100}</span>
              <span><strong>Duration:</strong> ${p.duration || '3 Hours'}</span>
              <span><strong>Questions:</strong> ${p.question_count || 10}</span>
              <span><strong>Cognitive Depth:</strong> <span class="cog-metric">${cog}/6.0</span></span>
              <span><strong>Synthesized:</strong> ${p.created_at || 'Recently'}</span>
            </div>
          </div>
          <div class="history-paper-actions">
            <button class="btn btn-primary btn-sm btn-load-history-paper" data-paper-id="${p.paper_id}" title="Open this paper in Paper Studio">
              <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <span>Load in Studio</span>
            </button>
            <button class="btn btn-secondary btn-sm btn-doc-history-paper" data-paper-id="${p.paper_id}" title="Download as Word .doc file">
              <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              <span>Word .doc</span>
            </button>
            <button class="btn btn-outline btn-sm btn-delete-history-paper text-danger" data-paper-id="${p.paper_id}" title="Delete this paper from your archive">
              <svg class="icon-svg icon-xs" viewBox="0 0 24 24">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      `;
    }).join("");

    // Wire action buttons
    container.querySelectorAll(".btn-load-history-paper").forEach(btn => {
      btn.addEventListener("click", () => {
        const pid = btn.getAttribute("data-paper-id");
        this.loadPaperIntoStudio(pid);
      });
    });

    container.querySelectorAll(".btn-doc-history-paper").forEach(btn => {
      btn.addEventListener("click", () => {
        const pid = btn.getAttribute("data-paper-id");
        this.exportPaperDoc(pid);
      });
    });

    container.querySelectorAll(".btn-delete-history-paper").forEach(btn => {
      btn.addEventListener("click", () => {
        const pid = btn.getAttribute("data-paper-id");
        this.deletePaper(pid);
      });
    });
  },

  filterHistoryList(query) {
    if (!query) {
      this.renderHistoryItems(this.cachedHistory);
      return;
    }
    const filtered = this.cachedHistory.filter(p => {
      const text = `${p.course_code} ${p.course_name} ${p.exam_title} ${p.created_at}`.toLowerCase();
      return text.includes(query);
    });
    this.renderHistoryItems(filtered);
  },

  async loadPaperIntoStudio(paperId) {
    if (!this.currentUser || !this.authToken) return;

    window.showToast("Loading archived question paper...", "info");
    try {
      const res = await fetch(`${API_BASE}/api/history/${paperId}`, {
        headers: { "Authorization": `Bearer ${this.authToken}` }
      });
      const data = await res.json();

      if (data.success && data.paper) {
        const paper = data.paper;
        window.AppState.currentPaper = paper;

        // Restore custom layout if present in the paper
        if (paper.custom_layout) {
          window.AppState.customLayout = Object.assign({}, window.AppState.customLayout, paper.custom_layout);
        }

        // Close history modal
        const modal = document.getElementById("modal-history");
        if (modal) modal.classList.remove("active");

        // Render in studio
        if (window.GeneratorModule && window.GeneratorModule.renderPaper) {
          window.GeneratorModule.renderPaper(paper);
        }

        // Switch to Studio Tab
        window.switchTab("studio");
        window.showToast(`Loaded "${paper.course_code || 'Paper'}: ${paper.exam_title}" into Studio.`, "success");
      } else {
        window.showToast(data.error || "Failed to load past question paper.", "error");
      }
    } catch (err) {
      console.error(err);
      window.showToast("Error retrieving paper from server.", "error");
    }
  },

  async exportPaperDoc(paperId) {
    if (!this.currentUser || !this.authToken) return;

    window.showToast("Preparing Microsoft Word document export...", "info");
    try {
      const res = await fetch(`${API_BASE}/api/history/${paperId}`, {
        headers: { "Authorization": `Bearer ${this.authToken}` }
      });
      const data = await res.json();

      if (data.success && data.paper) {
        const docRes = await fetch(`${API_BASE}/api/paper/export-doc`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ paper: data.paper })
        });

        if (docRes.ok) {
          const blob = await docRes.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.style.display = "none";
          a.href = url;
          const code = (data.paper.course_code || "EXAM").replace(/\s+/g, "_");
          a.download = `${code}_Question_Paper.doc`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          a.remove();
          window.showToast("Word document exported successfully.", "success");
        } else {
          window.showToast("Failed to generate Word document.", "error");
        }
      }
    } catch (err) {
      console.error(err);
      window.showToast("Error exporting Word document.", "error");
    }
  },

  async deletePaper(paperId) {
    if (!this.currentUser || !this.authToken) return;
    if (!confirm("Are you sure you want to permanently delete this question paper from your archive?")) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/history/${paperId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${this.authToken}` }
      });
      const data = await res.json();

      if (data.success) {
        window.showToast("Question paper removed from history.", "success");
        await this.renderHistoryModal();
      } else {
        window.showToast(data.error || "Failed to delete question paper.", "error");
      }
    } catch (err) {
      console.error(err);
      window.showToast("Network error deleting question paper.", "error");
    }
  },

  async resetPassword(username, newPassword) {
    const submitBtn = document.getElementById("btn-submit-forgot");
    const origHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
      submitBtn.innerHTML = "<span>Updating Credentials...</span>";
      submitBtn.disabled = true;
    }

    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, new_password: newPassword })
      });
      const data = await res.json();

      if (data.success) {
        const successMsg = document.getElementById("forgot-success-msg");
        if (successMsg) {
          successMsg.textContent = data.message || "Password reset successfully!";
          successMsg.style.display = "block";
        }
        window.showToast("Password updated successfully! You can now sign in.", "success");
        setTimeout(() => {
          const formForgot = document.getElementById("form-faculty-forgot");
          const formLogin = document.getElementById("form-faculty-login");
          const tabLogin = document.getElementById("tab-btn-login");
          if (formForgot) formForgot.style.display = "none";
          if (formLogin) {
            formLogin.style.display = "block";
            const loginUser = document.getElementById("login-username");
            const loginPwd = document.getElementById("login-password");
            if (loginUser) loginUser.value = username;
            if (loginPwd) {
              loginPwd.value = newPassword;
              loginPwd.focus();
            }
          }
          if (tabLogin) tabLogin.classList.add("active");
          this.clearAuthErrors();
        }, 1200);
      } else {
        this.showAuthError("forgot", data.error || "Failed to reset password. Please verify username.");
      }
    } catch (err) {
      console.warn("Password reset request failed:", err);
      this.showAuthError("forgot", "Cannot reach the server. Make sure the backend is running and try again.");
    } finally {
      if (submitBtn) {
        submitBtn.innerHTML = origHtml;
        submitBtn.disabled = false;
      }
    }
  },

  showAuthError(formType, message) {
    const errorEl = document.getElementById(`${formType}-error-msg`);
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = "block";
    }
  },

  clearAuthErrors() {
    const lErr = document.getElementById("login-error-msg");
    const sErr = document.getElementById("signup-error-msg");
    const fErr = document.getElementById("forgot-error-msg");
    const fSucc = document.getElementById("forgot-success-msg");
    if (lErr) lErr.style.display = "none";
    if (sErr) sErr.style.display = "none";
    if (fErr) fErr.style.display = "none";
    if (fSucc) fSucc.style.display = "none";
  }
};

window.AuthModule = AuthModule;

// Guaranteed auto-initialization regardless of script loading order or timing
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      AuthModule.init();
    });
  } else {
    AuthModule.init();
  }
}
