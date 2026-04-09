/**
 * Safe non-React navbar settings fallback.
 * This entrypoint intentionally avoids React mounting so navbar widget failures
 * cannot blank critical pages like Analytics.
 */
function mountSettingsDropdownFallback() {
  const container = document.getElementById('settings-dropdown-root');
  if (!container || container.dataset.settingsDropdownMounted === 'true') {
    return;
  }

  const logoutUrl =
    container.getAttribute('data-logout-url') ||
    (container as HTMLElement).dataset.logoutUrl ||
    '/accounts/logout/';

  container.innerHTML = `
    <a href="${logoutUrl}" style="
      color: inherit;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 34px;
      height: 34px;
      border-radius: 6px;
      border: 1px solid rgba(148,163,184,0.35);
      font-size: 12px;
      font-weight: 600;
      line-height: 1;
      user-select: none;
      transition: background-color 0.2s ease;
    " title="Logout" aria-label="Logout">Out</a>
  `;

  const link = container.querySelector('a');
  if (link) {
    link.addEventListener('mouseenter', () => {
      (link as HTMLElement).style.backgroundColor = 'rgba(148,163,184,0.12)';
    });
    link.addEventListener('mouseleave', () => {
      (link as HTMLElement).style.backgroundColor = 'transparent';
    });
  }

  container.dataset.settingsDropdownMounted = 'true';
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountSettingsDropdownFallback, { once: true });
} else {
  mountSettingsDropdownFallback();
}

