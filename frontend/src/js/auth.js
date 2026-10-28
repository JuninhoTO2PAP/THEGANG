/** Telas de login e cadastro por convite. */

import { api, clearSession, saveSession } from "./api.js";
import { playBrandChime } from "./sounds.js";
import { toast } from "./ui.js";

export function renderAuth(root, { onSuccess }) {
  let mode = "login";

  root.innerHTML = `
    <div class="auth-shell">
      <div class="auth-splash" id="auth-splash" aria-hidden="true">
        <div class="splash-mark">TG</div>
        <strong class="splash-title">THE GANG</strong>
        <span class="splash-sub">Tropa Free Fire</span>
      </div>
      <div class="auth-card auth-card-enter">
        <div class="brand">
          <div class="brand-logo" aria-hidden="true">TG</div>
          <strong>THE GANG</strong>
          <span>Entrada só com convite do time</span>
        </div>
        <div class="tabs">
          <button type="button" class="tab active" data-mode="login">Entrar</button>
          <button type="button" class="tab" data-mode="register">Cadastrar</button>
        </div>
        <form id="auth-form" class="stack"></form>
      </div>
    </div>
  `;

  const splash = root.querySelector("#auth-splash");
  requestAnimationFrame(() => splash?.classList.add("show"));
  setTimeout(() => {
    splash?.classList.add("hide");
    playBrandChime();
  }, 900);
  setTimeout(() => splash?.remove(), 1400);

  const form = root.querySelector("#auth-form");
  const tabs = root.querySelectorAll(".tab");

  function paintForm() {
    if (mode === "login") {
      form.innerHTML = `
        <label>Usuário ou e-mail
          <input name="login" autocomplete="username" required />
        </label>
        <label>Senha
          <input name="password" type="password" autocomplete="current-password" required />
        </label>
        <button class="btn btn-primary" type="submit">Entrar</button>
      `;
    } else {
      form.innerHTML = `
        <p class="hint">Sem código de convite gerado pelo admin, o cadastro é bloqueado.</p>
        <label>Código de convite
          <input name="invite_code" placeholder="GANG-XXXXXXXX" required />
        </label>
        <label>Usuário
          <input name="username" autocomplete="username" minlength="3" maxlength="32" required />
        </label>
        <label>E-mail
          <input name="email" type="email" autocomplete="email" required />
        </label>
        <label>Apelido
          <input name="nickname" minlength="2" maxlength="32" required />
        </label>
        <label>Senha
          <input name="password" type="password" autocomplete="new-password" minlength="8" required />
        </label>
        <button class="btn btn-primary" type="submit">Criar conta</button>
      `;
    }
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      mode = tab.dataset.mode;
      tabs.forEach((item) => item.classList.toggle("active", item === tab));
      paintForm();
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      const payload =
        mode === "login"
          ? await api("/api/auth/login", {
              method: "POST",
              auth: false,
              body: { login: data.login, password: data.password },
            })
          : await api("/api/auth/register", {
              method: "POST",
              auth: false,
              body: {
                invite_code: data.invite_code,
                username: data.username,
                email: data.email,
                nickname: data.nickname,
                password: data.password,
              },
            });
      saveSession(payload);
      playBrandChime();
      toast(mode === "login" ? "Bem-vindo de volta." : "Conta criada.");
      onSuccess(payload.user);
    } catch (error) {
      toast(error.message || "Falha na autenticação", true);
    }
  });

  paintForm();
}

export async function logout() {
  const refresh = localStorage.getItem("tg_refresh");
  try {
    if (refresh) {
      await api("/api/auth/logout", {
        method: "POST",
        auth: false,
        body: { refresh_token: refresh },
      });
    }
  } catch {
    /* ignore */
  }
  clearSession();
}
