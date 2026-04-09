function o(){const t=document.getElementById("settings-dropdown-root");if(!t||t.dataset.settingsDropdownMounted==="true")return;const n=t.getAttribute("data-logout-url")||t.dataset.logoutUrl||"/accounts/logout/";t.innerHTML=`
    <a href="${n}" style="
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
  `;const e=t.querySelector("a");e&&(e.addEventListener("mouseenter",()=>{e.style.backgroundColor="rgba(148,163,184,0.12)"}),e.addEventListener("mouseleave",()=>{e.style.backgroundColor="transparent"})),t.dataset.settingsDropdownMounted="true"}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",o,{once:!0}):o();
